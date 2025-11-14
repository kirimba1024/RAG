from utils import DB_CONNECTIONS

MAIN_SEARCH_TOOL = {
    "name": "main_search",
    "description": "Гибридный поиск чанков по ES → возвращает релевантные чанки с метаданными",
    "input_schema": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "поисковый запрос"
            },
            "path_prefix": {
                "type": "string",
                "description": "префикс пути (пустая строка если не фильтруем)"
            },
            "top_n": {
                "type": "integer",
                "minimum": 1,
                "maximum": 60,
                "description": "количество запрашиваемых чанков. Начинай с малого и увеличивай если недостаточно информации. "
            },
            "symbols": {
                "type": "array",
                "items": {"type": "string"},
                "description": "массив символов для буста поиска (опционально)"
            },
            "use_reranker": {
                "type": "boolean",
                "description": (
                    "использовать reranker для улучшения результатов (по умолчанию: true). "
                    "Reranker работает только с семантическим сходством текста и не учитывает метаданные (symbols, bm25_boost_terms). "
                    "Может изменить порядок важных чанков, поднятых ES благодаря бустам. "
                    "Рекомендуется отключать, когда важны точные совпадения по символам или терминам."
                )
            }
        },
        "required": ["question", "path_prefix", "top_n", "use_reranker"]
    }
}

EXECUTE_COMMAND_TOOL = {
    "name": "execute_command",
    "description": "Выполнение любых консольных команд в изолированном контейнере для взаимодействия с исходными файлами.",
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": (
                    "команда для выполнения в изолированном контейнере. "
                    "Доступные утилиты: grep, find, awk, sed, bash, curl, wget, git, jq, tree, file, diff, less, vim, cat, head, tail, wc, sort, uniq, cut, tr, xargs, "
                    "basename, dirname, realpath, stat, ls, cmp, split, tee, seq, od, strings, tar, gzip, md5sum, sha256sum, date, env, ps, df, du, "
                    "which, type, command, test, readlink, echo, printf"
                )
            }
        },
        "required": ["command"]
    }
}

GET_CHUNKS_TOOL = {
    "name": "get_chunks",
    "description": "Запрос чанков по их chunk_id для поиска. Удобно для графовой Q-A навигации через links_out/links_in.",
    "input_schema": {
        "type": "object",
        "properties": {
            "chunk_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "массив chunk_id для получения"
            }
        },
        "required": ["chunk_ids"]
    }
}

def build_db_query_tools():
    tools = []
    for tool_name, conn in DB_CONNECTIONS.items():
        tools.append({
            "name": tool_name,
            "description": conn["description"],
            "input_schema": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "вопрос на естественном языке для генерации SQL запроса"
                    }
                },
                "required": ["question"]
            }
        })
    return tools

DB_QUERY_TOOLS = build_db_query_tools()

SPLIT_BLOCKS_TOOL = {
    "name": "split_blocks",
    "description": (
        "Разбей файл на логические блоки, полностью покрывающие строки 1..N без пропусков и перекрытий. "
        "Блоки идут по возрастанию start_line, без лишней дробности. "
        "Границы — по естественным маркерам структуры. "
        "Если есть разрыв, расширь соседние блоки к середине разрыва. "
        "Последний блок заканчивается на N."
    ),
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["blocks"],
        "properties": {
            "blocks": {
                "type": "array",
                "minItems": 1,
                "maxItems": 50,
                "description": "Логические блоки, полностью покрывающие 1..N без дыр и перекрытий.",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "start_line", "end_line", "title", "kind",
                        "bm25_boost_terms", "symbols", "graph_questions", "graph_answers"
                    ],
                    "properties": {
                        "start_line": {"type": "integer", "minimum": 1, "description": "первая строка блока (1-индексация)"},
                        "end_line":   {"type": "integer", "minimum": 1, "description": "последняя строка блока включительно (1-индексация)"},
                        "title":      {"type": "string",  "minLength": 1, "maxLength": 120, "description": "краткое имя: function: foo, class: Bar, section: Config"},
                        "kind":       {"type": "string",  "minLength": 1, "maxLength": 32,  "description": "section, paragraph, list, list_item, table, code, config, class, function; при сомнении — logic_block"},
                        "bm25_boost_terms": {"type": "array", "items": {"type": "string"}, "maxItems": 12, "description": "идентификаторы/таблицы/эндпоинты/ключи конфигов"},
                        "symbols":          {"type": "array", "items": {"type": "string"}, "maxItems": 20, "description": "каноничные имена сущностей (классы, функции, константы, env-ключи)"},
                        "graph_questions":  {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 5, "description": "кто вызывает, где определяется, что обновляет, откуда данные"},
                        "graph_answers":    {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 5, "description": "здесь определяется/обновляет/вызывает/реализует"}
                    }
                }
            }
        }
    }
}
