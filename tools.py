import subprocess
from pathlib import Path
import docker
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from retriever import retrieve_fusion_nodes, get_code_stats, get_architecture_stats
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

def code_stats(path_prefix: str = "") -> str:
    return get_code_stats(path_prefix)

def architecture_stats(path_prefix: str = "") -> str:
    return get_architecture_stats(path_prefix)

def execute_command(command: str) -> str:
    client = docker.from_env()
    container = client.containers.run(
        image="rag-sandbox:stable",
        command=["sh", "-c", command],
        mem_limit="200m",
        cpu_period=100000,
        cpu_quota=50000,
        user="nobody",
        read_only=True,
        network_mode="none",
        remove=True,
        detach=False
    )
    return container.decode('utf-8')

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
    },
    {
        "name": "code_stats",
        "description": "Базовая статистика по кодовой базе",
        "input_schema": {
            "type": "object",
            "properties": {
                "path_prefix": {"type": "string", "description": "Префикс пути для фильтрации"}
            },
            "required": []
        }
    },
    {
        "name": "architecture_stats",
        "description": "Архитектурная статистика кодовой базы",
        "input_schema": {
            "type": "object",
            "properties": {
                "path_prefix": {"type": "string", "description": "Префикс пути для фильтрации"}
            },
            "required": []
        }
    },
    {
        "name": "execute_command",
        "description": "Выполнение команд в изолированном контейнере",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Команда для выполнения"}
            },
            "required": ["command"]
        }
    }
]