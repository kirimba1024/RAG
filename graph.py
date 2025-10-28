"""
Модуль для работы с Neo4j графом и AST
"""

from pathlib import Path
from neo4j import GraphDatabase
from ast_extractor import ASTExtractor
from utils import LANG_BY_EXT, TREE_SITTER_NAMES, setup_logging

logger = setup_logging(Path(__file__).stem)

class GraphManager:
    """Менеджер для работы с Neo4j графом"""
    
    def __init__(self, neo4j_url: str, neo4j_user: str, neo4j_pass: str):
        self.driver = GraphDatabase.driver(neo4j_url, auth=(neo4j_user, neo4j_pass))
        self.ast_extractor = ASTExtractor()
    
    def close(self):
        """Закрывает соединение с Neo4j"""
        self.driver.close()
    
    def _ast_nodes_raw(self, code: str, lang: str, limit: int = 50000):
        """
        Возвращает список узлов AST: {"i","p","t","n","s","e"}.
        i — локальный id, p — id родителя (-1 для корня),
        t — node.type, n — имя (если есть), s/e — байтовые смещения.
        """
        if not code.strip():
            return []
        parser = self.ast_extractor.parsers.get(lang) or next(iter(self.ast_extractor.parsers.values()), None)
        if not parser:
            return []
        buf = code.encode("utf8")
        root = parser.parse(buf).root_node

        def tx(n): return buf[n.start_byte:n.end_byte].decode("utf8","ignore")
        def nm(n):
            c = n.child_by_field_name("name") or n.child_by_field_name("identifier")
            if c: return tx(c)
            for ch in n.children:
                if "identifier" in ch.type or ch.type.endswith("_identifier"):
                    return tx(ch)
            if n.type in ("identifier","type_identifier","property_identifier","shorthand_property_identifier"):
                return tx(n)
            return None

        out, stack, i = [], [(root, -1)], 0
        while stack and i < limit:
            n, pid = stack.pop()
            out.append({"i": i, "p": pid, "t": n.type, "n": nm(n), "s": n.start_byte, "e": n.end_byte})
            my = i; i += 1
            for ch in reversed(n.children):
                stack.append((ch, my))
        return out

    def _ensure_constraints(self, tx):
        tx.run("CREATE CONSTRAINT astnode_pk IF NOT EXISTS FOR (n:AstNode) REQUIRE (n.file, n.i) IS NODE KEY")

    def _delete_ast_for_file(self, tx, file_path: str):
        tx.run("MATCH (n:AstNode {file:$f}) DETACH DELETE n", f=file_path)

    def _upsert_nodes(self, tx, file_path: str, lang: str, rows: list):
        tx.run("""
        UNWIND $rows AS r
        MERGE (n:AstNode {file:$f, i:r.i})
        SET n.t = r.t, n.n = r.n, n.s = r.s, n.e = r.e, n.lang = $lang
        """, rows=rows, f=file_path, lang=lang)

    def _upsert_edges(self, tx, file_path: str, rows: list):
        tx.run("""
        UNWIND $rows AS r
        MATCH (c:AstNode {file:$f, i:r.i})
        MATCH (p:AstNode {file:$f, i:r.p})
        MERGE (c)-[:CHILD_OF]->(p)
        """, rows=[r for r in rows if r["p"] != -1], f=file_path)

    def _build_semantic_edges(self, tx, file_path: str):
        """Строит семантические связи для файла"""
        # CALLS связи
        tx.run("""
        MATCH (call:AstNode)-[:CHILD_OF*]->(call_expr:AstNode {t: 'call_expression'})
        MATCH (call_expr)-[:CHILD_OF*]->(identifier:AstNode)
        WHERE identifier.t IN ['identifier', 'type_identifier', 'property_identifier']
        AND identifier.n IS NOT NULL
        AND call.file = $file_path
        WITH call, identifier.n as function_name
        MATCH (def:AstNode)
        WHERE def.t IN ['function_definition', 'method_definition', 'function_declaration']
        AND def.n = function_name
        AND def.file = $file_path
        MERGE (call)-[:CALLS]->(def)
        """, file_path=file_path)
        
        # EXTENDS связи
        tx.run("""
        MATCH (class:AstNode {t: 'class_declaration', file: $file_path})
        MATCH (class)-[:CHILD_OF*]->(superclass:AstNode)
        WHERE superclass.t IN ['type_identifier', 'identifier']
        AND superclass.n IS NOT NULL
        WITH class, superclass.n as superclass_name
        MATCH (parent_class:AstNode {t: 'class_declaration'})
        WHERE parent_class.n = superclass_name
        AND parent_class.file = $file_path
        MERGE (class)-[:EXTENDS]->(parent_class)
        """, file_path=file_path)

    def ingest_ast_to_neo4j(self, rel_path: str, code: str):
        try:
            ext = Path(rel_path).suffix.lower()
            lang = LANG_BY_EXT.get(ext)
            if not lang or not code.strip():
                return
            
            # Получаем tree-sitter имя для языка
            ts_lang = TREE_SITTER_NAMES.get(lang)
            if not ts_lang:
                logger.warning(f"No tree-sitter support for language: {lang}")
                return
                
            rows = self._ast_nodes_raw(code, ts_lang)
            if not rows:
                return
                
            with self.driver.session() as s:
                s.execute_write(self._ensure_constraints)
                s.execute_write(self._delete_ast_for_file, rel_path)
                # батчим, чтобы не уткнуться в слишком большой UNWIND
                B = 5000
                for i in range(0, len(rows), B):
                    chunk = rows[i:i+B]
                    s.execute_write(self._upsert_nodes, rel_path, lang, chunk)
                    s.execute_write(self._upsert_edges, rel_path, chunk)
                # Строим семантические связи сразу после заливки AST
                s.execute_write(self._build_semantic_edges, rel_path)
        except Exception as e:
            logger.error(f"Failed to ingest AST for {rel_path}: {e}")
            # Не поднимаем исключение, чтобы не прерывать обработку других файлов
