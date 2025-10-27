import subprocess
from pathlib import Path
from typing import Any, Dict, List, Union
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from retriever import retrieve_fusion_nodes
from utils import KNOWLEDGE_ROOT, to_posix, NEO4J_BOLT_URL, NEO4J_USER, NEO4J_PASS

GRAPH_STORE = Neo4jPropertyGraphStore(url=NEO4J_BOLT_URL, username=NEO4J_USER, password=NEO4J_PASS)

def main_search(question: str, path_prefix: str) -> List[Dict[str, Any]]:
    nodes = retrieve_fusion_nodes(question, path_prefix)
    return [{
        "path": n.metadata['doc_id'],
        "chunk": f"{n.metadata['chunk_id']}/{n.metadata['chunk_total']}",
        "lines": f"{n.metadata['start_line']}-{n.metadata['end_line']}",
        "text": n.text
    } for n in nodes]

def grep_files(pattern: str, path_prefix: str = "", case_sensitive: bool = True) -> Dict[str, Any]:
    root = str(KNOWLEDGE_ROOT / path_prefix.lstrip("/") if path_prefix else KNOWLEDGE_ROOT)
    cmd = ["grep", "-rn"] + (["-i"] if not case_sensitive else []) + ["-e", pattern, "--", root]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout.strip()
    if not out:
        return {"matches": [], "message": f"Паттерн '{pattern}' не найден"}
    matches = []
    for line in out.split("\n")[:64]:
        p = line.split(":", 2)
        matches.append({"file": p[0], "line": p[1], "content": p[2]} if len(p) >= 3 else {"raw": line})
    return {"matches": matches, "total": len(matches)}

def browse_path(path_str: str = "") -> Dict[str, Any]:
    p = (KNOWLEDGE_ROOT / path_str.lstrip("/")).resolve()
    if not p.is_relative_to(KNOWLEDGE_ROOT):
        return {"error": f"Доступ запрещен: {path_str}"}
    if not p.exists():
        return {"error": f"Путь не существует: {path_str}"}
    if p.is_file():
        return {"type": "file", "path": path_str, "content": p.read_text(encoding="utf-8", errors="ignore")}
    if p.is_dir():
        items = [{"type": "dir" if i.is_dir() else "file", "path": to_posix(i.relative_to(KNOWLEDGE_ROOT))} for i in sorted(p.iterdir())]
        return {"type": "directory", "path": path_str or "/", "items": items}
    return {"error": f"Неизвестный тип: {path_str}"}

def query_graph(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    result = GRAPH_STORE.structured_query(query)
    if not result:
        return []
    return [item.__dict__ if hasattr(item, "__dict__") else {"value": str(item)} for item in result[:limit]]

def read_file_lines(path: str, start_line: int, end_line: int) -> Dict[str, Any]:
    fp = (KNOWLEDGE_ROOT / path.lstrip("/")).resolve()
    if not fp.exists():
        return {"error": f"Файл не найден: {path}"}
    if not fp.is_relative_to(KNOWLEDGE_ROOT):
        return {"error": f"Доступ запрещен: {path}"}
    lines = fp.read_text(encoding="utf-8", errors="ignore").split('\n')
    s, e = max(1, start_line), min(len(lines), end_line)
    if s > e:
        return {"error": f"Некорректный диапазон: start_line={s} > end_line={e}"}
    return {"path": path, "start_line": s, "end_line": e, "content": "\n".join(lines[s-1:e])}

TOOLS_SCHEMA = [
    {
        "name": "main_search",
        "description": "Семантический поиск по коду",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "Поисковый запрос"},
                "path_prefix": {"type": "string", "description": "Префикс пути"}
            },
            "required": ["question"]
        }
    },
    {
        "name": "grep_files",
        "description": "Поиск по регулярному выражению",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Регулярное выражение"},
                "path_prefix": {"type": "string", "description": "Префикс пути"},
                "case_sensitive": {"type": "boolean", "description": "Учитывать регистр"}
            },
            "required": ["pattern"]
        }
    },
    {
        "name": "browse_path",
        "description": "Просмотр файлов и директорий",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Путь"}
            },
            "required": []
        }
    },
    {
        "name": "query_graph",
        "description": "Cypher-запрос к графу знаний",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Cypher запрос"},
                "limit": {"type": "integer", "description": "Максимум результатов"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "read_file_lines",
        "description": "Читает диапазон строк из файла",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Путь к файлу"},
                "start_line": {"type": "integer", "description": "Начальная строка"},
                "end_line": {"type": "integer", "description": "Конечная строка"}
            },
            "required": ["path", "start_line", "end_line"]
        }
    }
]