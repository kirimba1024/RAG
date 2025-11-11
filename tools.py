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
                "maximum": 30,
                "description": "количество результатов после reranking (1-30, стандартное: 10)"
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
        "Разбить файл на смысловые блоки, полностью покрывающие его без пропусков. "
        "Дроби файл разумно — не слишком мелко и не слишком крупно: каждый блок должен быть цельным по смыслу и полезным сам по себе."
    ),
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["blocks"],
        "properties": {
            "blocks": {
                "type": "array",
                "minItems": 1,
                "description": "массив объектов, полностью покрывающих файл",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "start_line", "end_line", "title", "kind",
                        "bm25_boost_terms", "symbols", "graph_questions", "graph_answers"
                    ],
                    "properties": {
                        "start_line": {
                            "type": "integer",
                            "minimum": 1,
                            "description": "первая строка блока (1-индексация)"
                        },
                        "end_line": {
                            "type": "integer",
                            "minimum": 1,
                            "description": "последняя строка блока (включительно)"
                        },
                        "title": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 120,
                            "description": "короткое имя блока (функция/секция/таблица и т.п.)"
                        },
                        "kind": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 32,
                            "description": (
                                "тип блока. Предпочитай: section, paragraph, list, list_item, table, table_header, table_row, code, config, class, function; "
                                "при сомнении — logic_block; допускается своё слово"
                            )
                        },
                        "bm25_boost_terms": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "Термы для буста BM25. Ключевые термины из текста для улучшения полнотекстового поиска через BM25 алгоритм. "
                                "Извлекай важные слова, которые могут встречаться в поисковых запросах."
                            )
                        },
                        "symbols": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "массив каноничных имён сущностей, символов, типов, интерфейсов, констант - "
                                "все значимые идентификаторы, которые используются для связности кода"
                            )
                        },
                        "graph_questions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "Вопросы, которые этот блок текста мог бы задать другим частям системы, если бы «спрашивал» о том, что ему нужно для работы. "
                                "Формулируй естественные короткие вопросы в контексте кода или логики: «кто вызывает...», «где определяется...», «какая функция обновляет...», «откуда берутся данные...». "
                                "Не пиши общие или риторические вопросы. 3–5 конкретных, технических вопросов. "
                                "Примеры: где определяется функция X? кто обновляет таблицу Y? какой модуль вызывает Z? где используется переменная W?"
                            )
                        },
                        "graph_answers": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "Краткие ответы, которые даёт этот блок текста на возможные технические вопросы других частей системы. "
                                "Формулируй как фактические утверждения о действиях в коде: «здесь вызывается...», «в этом файле определяется...», «этот модуль реализует...». "
                                "3–5 конкретных ответов, отражающих, что делает или предоставляет этот блок текста. "
                                "Примеры: здесь определяется функция X; этот код обновляет таблицу Y; здесь вызывается Z из модуля M; файл содержит значение константы W"
                            )
                        }
                    }
                }
            }
        }
    }
}