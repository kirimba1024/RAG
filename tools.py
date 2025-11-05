from retriever import main_search, code_stats
from utils import execute_command, setup_logging
from pathlib import Path

logger = setup_logging(Path(__file__).stem)

TOOLS_MAP = {
    "main_search": lambda p: main_search(p["question"], p["path_prefix"], p["top_n"]),
    "code_stats": lambda p: code_stats(p["path_prefix"]),
    "execute_command": lambda p: execute_command(p["command"]),
}

def execute_tool(tool_name, tool_input):
    try:
        return TOOLS_MAP[tool_name](tool_input)
    except Exception as e:
        logger.exception("Tool failed: %s %s", tool_name, tool_input)
        return f"Ошибка: {e}"

MAIN_SEARCH_TOOL = {
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
}

CODE_STATS_TOOL = {
    "name": "code_stats",
    "description": "Базовая статистика по кодовой базе",
    "input_schema": {
        "type": "object",
        "properties": {
            "path_prefix": {"type": "string", "description": "Префикс пути (пустая строка если не фильтруем)"}
        },
        "required": ["path_prefix"]
    }
}

EXECUTE_COMMAND_TOOL = {
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

SPLIT_BLOCKS_TOOL = {
    "name": "split_blocks",
    "description": "Возвращает список семантических блоков файла",
    "input_schema": {
        "type": "object",
        "properties": {
            "blocks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "start_line": {"type": "integer"},
                        "end_line": {"type": "integer"},
                        "title": {"type": "string"},
                        "kind": {"type": "string", "enum": ["function", "class", "config", "other"]}
                    },
                    "required": ["start_line", "end_line", "title", "kind"]
                }
            }
        },
        "required": ["blocks"]
    }
}

DESCRIBE_BLOCK_TOOL = {
    "name": "describe_block",
    "description": "Возвращает метаданные блока кода",
    "input_schema": {
        "type": "object",
        "properties": {
            "chunk_title": {"type": "string"},
            "chunk_summary": {"type": "string"},
            "tags": {
                "type": "array",
                "items": {"type": "string"}
            },
            "entities": {
                "type": "array",
                "items": {"type": "string"}
            },
            "public_symbols": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "kind": {"type": "string"},
                        "signature": {"type": "string"}
                    },
                    "required": ["name", "kind"]
                }
            },
            "io": {
                "type": "array",
                "items": {"type": "string"}
            },
            "security_flags": {
                "type": "array",
                "items": {"type": "string", "enum": ["pii", "secrets", "crypto", "authz", "audit"]}
            },
            "likely_queries": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "required": ["chunk_title", "chunk_summary", "tags", "entities", "public_symbols", "io", "security_flags", "likely_queries"]
    }
}