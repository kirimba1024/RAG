import subprocess
import docker
from retriever import retrieve_fusion_nodes, get_code_stats, get_architecture_stats
from utils import REPOS_ROOT, to_posix
from sourcegraph import sg_search, sg_codeintel, sg_blob


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


def code_stats(path_prefix: str = "") -> str:
    return get_code_stats(path_prefix)

def architecture_stats(path_prefix: str = "") -> str:
    return get_architecture_stats(path_prefix)

def execute_command(command: str) -> str:
    client = docker.from_env()
    container = client.containers.get("rag-assistant-rag-sandbox-1")
    result = container.exec_run(
        cmd=["timeout", "30", "sh", "-c", command],
        user="nobody"
    )
    return result.output.decode('utf-8')

def graphrag_query(task: str, root: str = None, k: int = 5) -> str:
    base = REPOS_ROOT
    root_path = to_posix(base if not root else base / root)
    proc = subprocess.run(
        ["graphrag", "run", "query", "-t", task, "-k", str(k)],
        cwd=root_path,
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return proc.stdout

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
        "name": "graphrag_query",
        "description": "Запрос к индексу GraphRAG CLI",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Вопрос/задача"},
                "root": {"type": "string", "description": "путь к папке"},
                "k": {"type": "integer", "description": "Кол-во источников", "default": 5}
            },
            "required": ["task"]
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
    },
    {
        "name": "sg_search",
        "description": "Sourcegraph поиск по коду",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Поисковый запрос"},
                "repo": {"type": "string", "description": "Репозиторий для поиска"},
                "limit": {"type": "integer", "description": "Максимум результатов"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "sg_codeintel",
        "description": "Sourcegraph code intelligence - definitions, references, callers, callees",
        "input_schema": {
            "type": "object",
            "properties": {
                "mode": {"type": "string", "description": "Режим: definitions, references, callers, callees"},
                "symbol": {"type": "string", "description": "Имя символа"},
                "doc_id": {"type": "string", "description": "ID документа"},
                "line": {"type": "integer", "description": "Номер строки"}
            },
            "required": ["mode"]
        }
    },
    {
        "name": "sg_blob",
        "description": "Sourcegraph blob - фрагмент кода по строкам",
        "input_schema": {
            "type": "object",
            "properties": {
                "doc_id": {"type": "string", "description": "ID документа"},
                "start_line": {"type": "integer", "description": "Начальная строка"},
                "end_line": {"type": "integer", "description": "Конечная строка"}
            },
            "required": ["doc_id", "start_line", "end_line"]
        }
    }
]