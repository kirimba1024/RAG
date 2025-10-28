from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Optional, Dict

from neo4j import GraphDatabase, Transaction
from tree_sitter_language_pack import get_language, get_parser
from utils import LANG_BY_EXT, TREE_SITTER_NAMES, setup_logging

logger = setup_logging(Path(__file__).stem)

class ASTExtractor:

    def __init__(self):
        self.parsers = {}
        self.languages = {}
        self._load_languages()

    def _load_languages(self) -> None:
        for lang_key, ts_name in TREE_SITTER_NAMES.items():
            try:
                self.parsers[lang_key] = get_parser(ts_name)
                self.languages[lang_key] = get_language(ts_name)
            except Exception as e:
                logger.warning(f"Failed to load language {lang_key} ({ts_name}): {e}")


@dataclass(frozen=True)
class AstNodeRow:
    """Строка-описание узла AST для заливки в Neo4j."""
    local_id: int
    parent_id: int  # -1 для корня
    node_type: str
    node_name: Optional[str]
    start_byte: int
    end_byte: int


@dataclass(frozen=True)
class AstEdgeRow:
    """Строка-описание ребра AST (child -> parent) с именем поля Tree-sitter."""
    child_id: int
    parent_id: int
    field_name: Optional[str]


class GraphManager:
    """Простой менеджер: Tree-sitter → Neo4j (узлы + CHILD_OF)."""

    _BATCH_SIZE = 10_000

    def __init__(self, neo4j_url: str, neo4j_user: str, neo4j_pass: str) -> None:
        self.driver = GraphDatabase.driver(neo4j_url, auth=(neo4j_user, neo4j_pass))
        self.ast = ASTExtractor()
        # Индексы/констрейнты — один раз при старте
        with self.driver.session() as session:
            session.execute_write(self._ensure_constraints)

    def close(self) -> None:
        """Закрывает соединение с Neo4j."""
        self.driver.close()

    # ------------------------ Public API ------------------------

    def ingest_ast(self, relative_path: str, source_code: str) -> None:
        """
        Заливает AST одного файла в Neo4j:
        - удаляет прошлую версию дерева файла;
        - вставляет узлы и рёбра CHILD_OF (с именами полей).
        """
        if not source_code.strip():
            logger.debug("Source is empty, skip ingest: %s", relative_path)
            return

        language_hint = LANG_BY_EXT.get(Path(relative_path).suffix.lower())
        language_key = self._normalize_language_key(language_hint)

        if not language_key:
            logger.warning("No parser found for language: %r (file: %s)", language_hint, relative_path)
            return

        node_rows, edge_rows = self._parse_ast_to_rows(source_code, language_key)
        if not node_rows:
            logger.debug("No AST nodes produced, skip: %s", relative_path)
            return

        with self.driver.session() as session:
            session.execute_write(self._delete_ast_for_file, relative_path)
            # Узлы
            for start in range(0, len(node_rows), self._BATCH_SIZE):
                chunk = node_rows[start:start + self._BATCH_SIZE]
                session.execute_write(self._upsert_nodes, relative_path, language_key, chunk)
            # Рёбра
            if edge_rows:
                for start in range(0, len(edge_rows), self._BATCH_SIZE):
                    chunk = edge_rows[start:start + self._BATCH_SIZE]
                    session.execute_write(self._upsert_edges, relative_path, chunk)

        logger.info("AST ingested: %s (nodes=%d, edges=%d)", relative_path, len(node_rows), len(edge_rows))

    # ------------------------ AST → rows ------------------------

    def _parse_ast_to_rows(
        self,
        source_code: str,
        language_key: str,
        limit_nodes: int = 50_000,
    ) -> Tuple[List[AstNodeRow], List[AstEdgeRow]]:
        """
        Преобразует дерево Tree-sitter в плоские списки узлов и рёбер.
        Узел: local_id/parent_id/node_type/node_name/start_byte/end_byte.
        Ребро: child_id/parent_id/field_name (имя поля у родителя).
        """
        parser = self.ast.parsers.get(language_key) or next(iter(self.ast.parsers.values()), None)
        if not parser:
            return [], []

        buffer = source_code.encode("utf8")
        root = parser.parse(buffer).root_node

        def text_of(node) -> str:
            return buffer[node.start_byte:node.end_byte].decode("utf8", "ignore")

        def name_of(node) -> Optional[str]:
            by_field = node.child_by_field_name("name") or node.child_by_field_name("identifier")
            if by_field:
                return text_of(by_field)
            for child in node.children:
                if "identifier" in child.type or child.type.endswith("_identifier"):
                    return text_of(child)
            if node.type in ("identifier", "type_identifier", "property_identifier", "shorthand_property_identifier"):
                return text_of(node)
            return None

        node_rows: List[AstNodeRow] = []
        edge_rows: List[AstEdgeRow] = []

        # стек: (узел, id_родителя, имя_поля_у_родителя)
        stack: List[tuple] = [(root, -1, None)]
        local_id = 0

        while stack and local_id < limit_nodes:
            node, parent_id, parent_field = stack.pop()

            node_rows.append(
                AstNodeRow(
                    local_id=local_id,
                    parent_id=parent_id,
                    node_type=node.type,
                    node_name=name_of(node),
                    start_byte=node.start_byte,
                    end_byte=node.end_byte,
                )
            )

            if parent_id != -1:
                edge_rows.append(
                    AstEdgeRow(
                        child_id=local_id,
                        parent_id=parent_id,
                        field_name=parent_field,
                    )
                )

            my_id = local_id
            local_id += 1

            # Добавляем детей в обратном порядке, сохраняя field_name для каждого
            for idx in range(len(node.children) - 1, -1, -1):
                child = node.children[idx]
                field_name = node.field_name_for_child(idx)
                stack.append((child, my_id, field_name))

        return node_rows, edge_rows

    # ------------------------ Cypher helpers ------------------------

    @staticmethod
    def _ensure_constraints(tx: Transaction) -> None:
        tx.run(
            "CREATE CONSTRAINT astnode_pk IF NOT EXISTS "
            "FOR (n:AstNode) REQUIRE (n.file, n.local_id) IS NODE KEY"
        )
        tx.run("CREATE INDEX astnode_file IF NOT EXISTS FOR (n:AstNode) ON (n.file)")
        tx.run(
            "CREATE INDEX astnode_file_type_name IF NOT EXISTS "
            "FOR (n:AstNode) ON (n.file, n.type, n.name)"
        )

    @staticmethod
    def _delete_ast_for_file(tx: Transaction, file_path: str) -> None:
        tx.run("MATCH (n:AstNode {file:$file}) DETACH DELETE n", file=file_path)

    @staticmethod
    def _upsert_nodes(
        tx: Transaction,
        file_path: str,
        language_key: str,
        rows: List[AstNodeRow],
    ) -> None:
        tx.run(
            """
            UNWIND $rows AS r
            MERGE (n:AstNode {file:$file, local_id:r.local_id})
            SET n.type       = r.node_type,
                n.name       = r.node_name,
                n.start_byte = r.start_byte,
                n.end_byte   = r.end_byte,
                n.language   = $language
            """,
            file=file_path,
            language=language_key,
            rows=[row.__dict__ for row in rows],
        )

    @staticmethod
    def _upsert_edges(
        tx: Transaction,
        file_path: str,
        edges: List[AstEdgeRow],
    ) -> None:
        tx.run(
            """
            UNWIND $edges AS e
            MATCH (c:AstNode {file:$file, local_id:e.child_id})
            MATCH (p:AstNode {file:$file, local_id:e.parent_id})
            MERGE (c)-[rel:CHILD_OF]->(p)
            SET rel.field_name = e.field_name
            """,
            file=file_path,
            edges=[edge.__dict__ for edge in edges],
        )

    # ------------------------ Helpers ------------------------

    def _normalize_language_key(self, language_hint: Optional[str]) -> Optional[str]:
        """
        Приводит подсказку языка к ключу парсера ASTExtractor.
        """
        if not language_hint:
            return None

        # Попробуем как есть
        return language_hint if language_hint in self.ast.parsers else None
