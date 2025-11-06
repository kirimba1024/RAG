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

DESCRIBE_TOOL = {
    "name": "describe_tool",
    "description": "Верни один объект по схеме ниже.",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "name",
            "title",
            "description",
            "summary",
            "detailed",
            "language",
            "purpose",
            "file_type",
            "tags",
            "key_points",
            "http_endpoints",
            "apis",
            "entities",
            "imports",
            "dependencies",
            "permissions_roles",
            "config_keys",
            "feature_flags",
            "todos",
            "has_documentation",
            "layer",
            "bm25_boost_terms",
            "likely_queries",
            "domain_objects",
            "complexity",
            "confidence",
            "vulnerabilities",
            "secrets_found",
            "table_columns",
            "improvements",
            "potential_bugs",
            "function_names",
            "class_names",
            "variable_names",
            "io",
            "symbols",
            "security_flags",
            "notes",
            "conclusions",
            "open_questions",
            "highlights",
            "anchors"
        ],
        "properties": {
            "name": {"type": "string", "minLength": 1, "maxLength": 32, "pattern": "^\\S+$", "description": "Имя одним словом, отражающее суть."},
            "title": {"type": "string", "minLength": 1, "maxLength": 128, "description": "Заголовок, кратко описывающий назначение."},
            "description": {"type": "string", "minLength": 1, "maxLength": 256, "description": "Одна фраза о содержимом."},
            "summary": {"type": "string", "minLength": 1, "maxLength": 1024, "description": "Краткое содержание и цель."},
            "detailed": {"type": "string", "minLength": 1, "maxLength": 2048, "description": "Подробное описание структуры и смысла."},
            "language": {"type": "string", "minLength": 1, "maxLength": 32, "description": "Основной язык/диалект (java, ts, yaml, md, sql…)."},
            "purpose": {"type": "string", "minLength": 1, "maxLength": 240, "description": "Зачем нужен файл."},
            "file_type": {"type": "string", "enum": ["code", "markup", "config", "schema", "doc", "data", "binary", "mixed"], "description": "Общий тип содержимого."},
            "tags": {"type": "array", "minItems": 1, "uniqueItems": true, "items": {"type": "string", "minLength": 1, "maxLength": 40}, "maxItems": 10, "description": "Главные ключевые теги, метки."},
            "key_points": {"type": "array", "minItems": 1, "uniqueItems": true, "items": {"type": "string", "minLength": 1, "maxLength": 80}, "maxItems": 3, "description": "Ключевые тезисы."},
            "http_endpoints": { "type": "array", "items": {"type": "string"}, "description": "HTTP endpoints (method path)"},
            "apis": { "type": "array", "items": {"type": "string"}, "description": "API спецификации/идентификаторы" },
            "entities": { "type": "array", "items": {"type": "string"}, "description": "Сущности/доменные объекты" },
            "imports": { "type": "array", "items": {"type": "string"}, "description": "Импорты" },
            "dependencies": { "type": "array", "items": {"type": "string"}, "description": "Зависимости" },
            "permissions_roles": { "type": "array", "items": {"type": "string"}, "description": "Права/роли" },
            "config_keys": { "type": "array", "items": {"type": "string"}, "description": "Ключи конфигов" },
            "feature_flags": { "type": "array", "items": {"type": "string"}, "description": "Фичефлаги" },
            "todos": { "type": "array", "items": {"type": "string"}, "description": "TODO/FIXME/XXX" },
            "edges": { "type": "array", "items": { "type": "string" }, "description": "Функциональные зависимости для графа (кто вызывает/зависит/использует). Формат: typeA@nameA→typeB@nameB, напр. python-function@foo→sql-select@get_users." },
            "likely_queries": { "type": "array", "items": {"type": "string"}, "description": "Ожидаемые вопросы по файлу." },
            "io": { "type": "array", "items": {"type": "string"}, "description": "I/O артефакты: таблицы, топики, файлы, URLs." },
            "symbols": { "type": "array", "items": {"type": "string"}, "description": "Символы/идентификаторы (универсально)." },
            "security_flags": { "type": "array", "items": {"type": "string", "enum": ["pii","secrets","crypto","authz","audit"]}, "description": "Флаги безопасности." },
            "has_documentation": {"type": "boolean", "description": "Есть ли в файле заметная документация/комментарии."},
            "layer": {"type": "string", "minLength": 1, "maxLength": 32, "description": "Архитектурный слой: frontend/backend/data/ops и т.п."},
            "bm25_boost_terms": {"type": "array", "items": {"type": "string", "minLength": 1, "maxLength": 40}, "uniqueItems": True, "maxItems": 20, "description": "Термы для буста BM25."},
            "domain_objects": {"type": "array", "items": {"type": "string", "minLength": 1, "maxLength": 40}, "uniqueItems": True, "maxItems": 30, "description": "Предметные сущности."},
            "complexity": {"type": "number", "minimum": 0, "description": "Оценка сложности/LOC."},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1, "description": "Уверенность в корректности извлечённых фактов (0–1)."},
            "vulnerabilities": {"type": "string", "maxLength": 4000, "description": "Список уязвимостей (краткие описания)."},
            "secrets_found": {"type": "array", "items": {"type": "string", "minLength": 1, "maxLength": 128}, "uniqueItems": True, "maxItems": 200, "description": "Найденные секреты."},
            "table_columns": {"type": "array", "items": {"type": "string", "minLength": 1, "maxLength": 64}, "uniqueItems": True, "maxItems": 400, "description": "Имена столбцов, если это таблица/SQL."},
            "improvements": {"type": "string", "maxLength": 4000, "description": "Предложения по доработке."},
            "potential_bugs": {"type": "string", "maxLength": 4000, "description": "Возможные баги."},
            "function_names": {"type": "array", "items": {"type": "string", "minLength": 1, "maxLength": 128}, "uniqueItems": True, "maxItems": 800, "description": "Имена функций/методов."},
            "class_names": {"type": "array", "items": {"type": "string", "minLength": 1, "maxLength": 128}, "uniqueItems": True, "maxItems": 400, "description": "Имена классов/интерфейсов/структур."},
            "variable_names": {"type": "array", "items": {"type": "string", "minLength": 1, "maxLength": 128}, "uniqueItems": True, "maxItems": 2000, "description": "Имена переменных и констант."},
            "notes": {"type": "string", "maxLength": 4000, "description": "Полезные заметки."},
            "conclusions": {"type": "string", "maxLength": 4000, "description": "Выводы по файлу."},
            "open_questions": {"type": "string", "maxLength": 4000, "description": "Вопросы и непонятности."},
            "highlights": {"type": "string", "maxLength": 1000, "description": "Самое важное по файлу (коротко)."},
            "anchors": {"type": "array", "items": {"type": "string", "minLength": 1, "maxLength": 80}, "uniqueItems": True, "maxItems": 100, "description": "Якоря для поиска."}
        }
    }
}