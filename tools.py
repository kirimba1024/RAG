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

def query_graph(query: str, limit: int = 20) -> str:
    """Универсальный запрос к графу: семантика + AST"""
    try:
        # Пробуем семантический граф
        result = GRAPH_STORE.structured_query(query)
        if result:
            results = []
            for item in result[:limit]:
                if hasattr(item, "__dict__"):
                    results.append(str(item.__dict__))
                else:
                    results.append(str(item))
            return "\n".join(results)
    except Exception as e:
        logger.warning(f"Semantic graph query failed: {e}")
    
    # Fallback: прямой Cypher к AST графу
    try:
        from graph import GraphManager
        from utils import NEO4J_BOLT_URL, NEO4J_USER, NEO4J_PASS
        
        with GraphManager(NEO4J_BOLT_URL, NEO4J_USER, NEO4J_PASS) as gm:
            with gm.driver.session() as session:
                result = session.run(query)
                records = list(result)
                if not records:
                    return "Результаты не найдены"
                
                results = []
                for record in records[:limit]:
                    results.append(str(dict(record)))
                return "\n".join(results)
    except Exception as e:
        logger.error(f"AST graph query failed: {e}")
        return f"Ошибка выполнения запроса: {e}"

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