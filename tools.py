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
    "description": "Верни один объект по схеме ниже.",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["name","title","description","summary","detailed","language","purpose","file_type","tags","key_points","blocks"],
        "properties": {
            "name":        {"type": "string", "minLength": 1, "maxLength": 32, "pattern": "^\\S+$", "description": "Имя файла одним словом, отражающее суть."},
            "title":       {"type": "string", "minLength": 1, "maxLength": 128, "description": "Заголовок, кратко описывающий назначение файла."},
            "description": {"type": "string", "minLength": 1, "maxLength": 256, "description": "Одна фраза о содержимом файла."},
            "summary":     {"type": "string", "minLength": 1, "maxLength": 1024, "description": "Краткое содержание и цель файла."},
            "detailed":    {"type": "string", "minLength": 1, "maxLength": 2048, "description": "Подробное описание структуры и смысла."},
            "language":    {"type": "string", "minLength": 1, "maxLength": 32, "description": "Основной язык/диалект (java, ts, yaml, md, sql…)."},
            "purpose":     {"type": "string", "minLength": 1, "maxLength": 240, "description": "Зачем нужен файл."},
            "file_type":   {"type": "string", "enum": ["code", "markup", "config", "schema", "doc", "data", "binary", "mixed"], "description": "Общий тип содержимого."},
            "tags":        {"type": "array", "minItems": 1, "uniqueItems": True, "items": {"type": "string", "minLength": 1, "maxLength": 40}, "maxItems": 10, "description": "Главные ключевые теги, метки."},
            "key_points":  {"type": "array", "minItems": 1, "uniqueItems": True, "items": {"type": "string", "minLength": 1, "maxLength": 80}, "maxItems": 3, "description": "Ключевые тезисы."},
            "blocks": {
                "type": "array",
                "minItems": 1,
                "description": "Список смысловых блоков, полностью покрывающих файл.",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["start_line","end_line","title","kind"],
                    "properties": {
                        "start_line": { "type": "integer", "minimum": 1, "description": "Первая строка блока (1-индексация)." },
                        "end_line":   { "type": "integer", "minimum": 1, "description": "Последняя строка блока (включительно)." },
                        "title":      { "type": "string",  "minLength": 1, "maxLength": 120, "description": "Короткое имя блока (функция/секция/таблица и т.п.)." },
                        "kind":       { "type": "string",  "minLength": 1, "maxLength": 32, "description": "Тип блока; предпочитай section, paragraph, list, list_item, table, table_header, table_row, code, config, class, function; при сомнении — logic_block; допускается своё слово." }
                    }
                }
            }
        }
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