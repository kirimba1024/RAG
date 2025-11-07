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
    "description": "Семантический поиск по коду.",
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
    "description": "Базовая статистика по кодовой базе.",
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
    "description": "Выполнение команд в изолированном контейнере.",
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
        "required": ["blocks"],
        "properties": {
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

DESCRIBE_IDENTITY_TOOL = {
    "name": "describe_identity",
    "description": "Объект с полями идентификации.",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["name","title","description","summary","detailed","language","purpose","file_type","tags","key_points"],
        "properties": {
            "name": {"type": "string", "minLength": 1, "maxLength": 32, "pattern": "^\\S+$"},
            "title": {"type": "string", "minLength": 1, "maxLength": 128},
            "description": {"type": "string", "minLength": 1, "maxLength": 256},
            "summary": {"type": "string", "minLength": 1, "maxLength": 1024},
            "detailed": {"type": "string", "minLength": 1, "maxLength": 2048},
            "language": {"type": "string", "minLength": 1, "maxLength": 32},
            "purpose": {"type": "string", "minLength": 1, "maxLength": 240},
            "file_type": {"type": "string", "enum": ["code","markup","config","schema","doc","data","binary","mixed"]},
            "tags": {"type": "array", "minItems": 1, "uniqueItems": True, "items": {"type": "string", "minLength": 1, "maxLength": 40}, "maxItems": 10},
            "key_points": {"type": "array", "minItems": 1, "uniqueItems": True, "items": {"type": "string", "minLength": 1, "maxLength": 80}, "maxItems": 3}
        }
    }
}

DESCRIBE_API_TOOL = {
    "name": "describe_api",
    "description": "API/интерфейсы и I/O.",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["http_endpoints","apis","io"],
        "properties": {
            "http_endpoints": {"type": "array", "items": {"type": "string"}},
            "apis": {"type": "array", "items": {"type": "string"}},
            "io": {"type": "array", "items": {"type": "string"}}
        }
    }
}

DESCRIBE_ENTITIES_TOOL = {
    "name": "describe_entities",
    "description": "Сущности и колонки.",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["entities","domain_objects","table_columns"],
        "properties": {
            "entities": {"type": "array", "items": {"type": "string"}},
            "domain_objects": {"type": "array", "items": {"type": "string"}},
            "table_columns": {"type": "array", "items": {"type": "string"}}
        }
    }
}

DESCRIBE_DEPS_TOOL = {
    "name": "describe_deps",
    "description": "Импорты и зависимости.",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["imports","dependencies"],
        "properties": {
            "imports": {"type": "array", "items": {"type": "string"}},
            "dependencies": {"type": "array", "items": {"type": "string"}}
        }
    }
}

DESCRIBE_SECURITY_TOOL = {
    "name": "describe_security",
    "description": "Права и безопасность.",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["permissions_roles","security_flags","vulnerabilities","secrets_found"],
        "properties": {
            "permissions_roles": {"type": "array", "items": {"type": "string"}},
            "security_flags": {"type": "array", "items": {"type": "string"}},
            "vulnerabilities": {"type": "string"},
            "secrets_found": {"type": "array", "items": {"type": "string"}}
        }
    }
}

DESCRIBE_FLAGS_TOOL = {
    "name": "describe_flags",
    "description": "Конфиги и фичи.",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["config_keys","feature_flags","todos"],
        "properties": {
            "config_keys": {"type": "array", "items": {"type": "string"}},
            "feature_flags": {"type": "array", "items": {"type": "string"}},
            "todos": {"type": "array", "items": {"type": "string"}}
        }
    }
}

DESCRIBE_GRAPH_TOOL = {
    "name": "describe_graph",
    "description": "Связи и символы.",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["edges","anchors","symbols"],
        "properties": {
            "edges": {"type": "array", "items": {"type": "string"}},
            "anchors": {"type": "array", "items": {"type": "string"}},
            "symbols": {"type": "array", "items": {"type": "string"}}
        }
    }
}

DESCRIBE_QUALITY_TOOL = {
    "name": "describe_quality",
    "description": "Качество и слой.",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["has_documentation","layer","bm25_boost_terms","likely_queries","complexity","confidence"],
        "properties": {
            "has_documentation": {"type": "boolean"},
            "layer": {"type": "string"},
            "bm25_boost_terms": {"type": "array", "items": {"type": "string"}},
            "likely_queries": {"type": "array", "items": {"type": "string"}},
            "complexity": {"type": "number"},
            "confidence": {"type": "number"}
        }
    }
}

DESCRIBE_CODE_TOOL = {
    "name": "describe_code",
    "description": "Имена символов кода.",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["function_names","class_names","variable_names"],
        "properties": {
            "function_names": {"type": "array", "items": {"type": "string"}},
            "class_names": {"type": "array", "items": {"type": "string"}},
            "variable_names": {"type": "array", "items": {"type": "string"}}
        }
    }
}

DESCRIBE_FINDINGS_TOOL = {
    "name": "describe_findings",
    "description": "Выводы и баги.",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["improvements","potential_bugs","notes","conclusions","open_questions","highlights"],
        "properties": {
            "improvements": {"type": "string"},
            "potential_bugs": {"type": "string"},
            "notes": {"type": "string"},
            "conclusions": {"type": "string"},
            "open_questions": {"type": "string"},
            "highlights": {"type": "string"}
        }
    }
}

DESCRIBE_TOOLS = [
    DESCRIBE_IDENTITY_TOOL,
    DESCRIBE_API_TOOL,
    DESCRIBE_ENTITIES_TOOL,
    DESCRIBE_DEPS_TOOL,
    DESCRIBE_SECURITY_TOOL,
    DESCRIBE_FLAGS_TOOL,
    DESCRIBE_GRAPH_TOOL,
    DESCRIBE_QUALITY_TOOL,
    DESCRIBE_CODE_TOOL,
    DESCRIBE_FINDINGS_TOOL,
]