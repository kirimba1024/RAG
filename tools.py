import subprocess
from pathlib import Path
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from retriever import retrieve_fusion_nodes
from utils import KNOWLEDGE_ROOT, to_posix, NEO4J_BOLT_URL, NEO4J_USER, NEO4J_PASS

GRAPH_STORE = Neo4jPropertyGraphStore(url=NEO4J_BOLT_URL, username=NEO4J_USER, password=NEO4J_PASS)

def main_search(question: str, path_prefix: str) -> str:
    nodes = retrieve_fusion_nodes(question, path_prefix)
    results = []
    for node in nodes:
        doc_id = node.metadata['doc_id']
        chunk_info = f"[chunk {node.metadata['chunk_id']}/{node.metadata['chunk_total']}]"
        line_info = f"lines {node.metadata['start_line']}-{node.metadata['end_line']}"
        header = f"{doc_id} {chunk_info} {line_info}"
        results.append(f"{header}:\n{node.text}")
    return "\n\n".join(results)

def grep_files(pattern: str, path_prefix: str = "", case_sensitive: bool = True) -> str:
    root = str(KNOWLEDGE_ROOT / path_prefix.lstrip("/") if path_prefix else KNOWLEDGE_ROOT)
    cmd = ["grep", "-rn"] + (["-i"] if not case_sensitive else []) + ["-e", pattern, "--", root]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout.strip()
    if not out:
        return f"Паттерн '{pattern}' не найден"
    results = []
    for line in out.split("\n")[:64]:
        p = line.split(":", 2)
        if len(p) >= 3:
            results.append(f"{p[0]}:{p[1]}: {p[2]}")
        else:
            results.append(line)
    return "\n".join(results)

def browse_path(path_str: str = "") -> str:
    p = (KNOWLEDGE_ROOT / path_str.lstrip("/")).resolve()
    if not p.is_relative_to(KNOWLEDGE_ROOT):
        return f"Доступ запрещен: {path_str}"
    if not p.exists():
        return f"Путь не существует: {path_str}"
    if p.is_file():
        content = p.read_text(encoding="utf-8", errors="ignore")
        return f"📄 {path_str}:\n{content}"
    if p.is_dir():
        items = [f"{'📁' if i.is_dir() else '📄'} {to_posix(i.relative_to(KNOWLEDGE_ROOT))}" for i in sorted(p.iterdir())]
        return f"📁 {path_str or '/'}:\n" + "\n".join(items)
    return f"Неизвестный тип: {path_str}"

def query_graph(query: str, limit: int = 20) -> str:
    result = GRAPH_STORE.structured_query(query)
    if not result:
        return "Результаты не найдены"
    results = []
    for item in result[:limit]:
        if hasattr(item, "__dict__"):
            results.append(str(item.__dict__))
        else:
            results.append(str(item))
    return "\n".join(results)

def read_file_lines(path: str, start_line: int, end_line: int) -> str:
    fp = (KNOWLEDGE_ROOT / path.lstrip("/")).resolve()
    if not fp.exists():
        return f"Файл не найден: {path}"
    if not fp.is_relative_to(KNOWLEDGE_ROOT):
        return f"Доступ запрещен: {path}"
    lines = fp.read_text(encoding="utf-8", errors="ignore").split('\n')
    s, e = max(1, start_line), min(len(lines), end_line)
    if s > e:
        return f"Некорректный диапазон: start_line={s} > end_line={e}"
    content = "\n".join(lines[s-1:e])
    return f"📄 {path} (lines {s}-{e}):\n{content}"

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