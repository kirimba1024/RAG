import docker

from retriever import retrieve_fusion_nodes, get_code_stats
from utils import SANDBOX_CONTAINER_NAME, GRAPHRAG_CONTAINER_NAME


def main_search(question: str, path_prefix: str, top_n: int) -> str:
    nodes = retrieve_fusion_nodes(question, path_prefix, top_n)
    results = []
    for node in nodes:
        doc_id = node.metadata['doc_id']
        chunk_info = f"[chunk {node.metadata['chunk_id']}/{node.metadata['chunk_total']}]"
        line_info = f"lines {node.metadata['start_line']}-{node.metadata['end_line']}"
        header = f"{doc_id} {chunk_info} {line_info}"
        results.append(f"{header}:\n{node.text}")
    return "\n\n".join(results)

def code_stats(path_prefix: str) -> str:
    return get_code_stats(path_prefix)

def execute_command(command: str) -> str:
    client = docker.from_env()
    container = client.containers.get(SANDBOX_CONTAINER_NAME)
    result = container.exec_run(
        cmd=["timeout", "30", "sh", "-c", command],
        user="nobody"
    )
    return result.output.decode('utf-8')

def graphrag_query(task: str, path_prefix: str, k: int) -> str:
    client = docker.from_env()
    container = client.containers.get(GRAPHRAG_CONTAINER_NAME)
    workdir = "/app/repos" + (f"/{path_prefix.lstrip('/')}" if path_prefix else "")
    exec_result = container.exec_run(
        cmd=["graphrag", "query", "-t", task, "-k", str(k)],
        workdir=workdir,
    )
    out = exec_result.output.decode("utf-8", errors="replace")
    if exec_result.exit_code != 0:
        return f"[graphrag error {exec_result.exit_code}] {out}"
    return out

TOOLS_SCHEMA = [
    {
        "name": "main_search",
        "description": "Семантический поиск по коду",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "Поисковый запрос"},
                "path_prefix": {"type": "string", "description": "Префикс пути (пустая строка если не фильтруем)"},
                "top_n": {"type": "integer", "minimum": 1, "maximum": 30, "description": "Количество результатов после reranking (диапазон 1-30, стандартное значение: 10)"}
            },
            "required": ["question", "path_prefix", "top_n"]
        }
    },
    {
        "name": "graphrag_query",
        "description": "Запрос к индексу GraphRAG CLI",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Вопрос/задача"},
                "path_prefix": {"type": "string", "description": "Целостный путь к папке относительно корня репозитория (пустая строка для корня)"},
                "k": {"type": "integer", "description": "Кол-во источников (стандартное значение: 5)"}
            },
            "required": ["task", "path_prefix", "k"]
        }
    },
    {
        "name": "code_stats",
        "description": "Базовая статистика по кодовой базе",
        "input_schema": {
            "type": "object",
            "properties": {
                "path_prefix": {"type": "string", "description": "Префикс пути (пустая строка если не фильтруем)"}
            },
            "required": ["path_prefix"]
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
                "path_prefix": {"type": "string", "description": "Префикс пути (пустая строка если не фильтруем)"},
                "limit": {"type": "integer", "description": "Максимальное количество результатов"}
            },
            "required": ["query", "path_prefix", "limit"]
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
                "path_prefix": {"type": "string", "description": "Префикс пути (пустая строка если не фильтруем)"}
            },
            "required": ["mode", "symbol", "path_prefix"]
        }
    },
    {
        "name": "sg_blob",
        "description": "Sourcegraph blob - фрагмент кода по строкам",
        "input_schema": {
            "type": "object",
            "properties": {
                "rel_path": {"type": "string", "description": "Относительный путь к файлу (например: backend/src/main.py)"},
                "start_line": {"type": "integer", "description": "Начальная строка"},
                "end_line": {"type": "integer", "description": "Конечная строка"}
            },
            "required": ["rel_path", "start_line", "end_line"]
        }
    }
]