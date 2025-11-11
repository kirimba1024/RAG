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
        "Разбить файл на логические блоки, полностью покрывающие строки 1..N без пропусков и перекрытий. "
        "Блоки упорядочены по start_line. Ориентировочная длина: 32-512 строк, но можно отклоняться для целостности. "
        "Примеры: для Java файла - блоки по классам/методам; для YAML - по секциям; для MD - по разделам; для конфигов - по группам настроек."
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
                "description": "массив логических блоков файла. Блоки должны полностью покрывать файл от строки 1 до последней без пропусков. Каждый блок определяет границы через start_line и end_line (1-индексация, включительно). Обычно 5-15 блоков, максимум 50",
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
                            "description": "номер первой строки этого блока в файле (1-индексация: 1 = первая строка файла, 10 = десятая строка файла). Используется для точной привязки блока к исходному коду и навигации"
                        },
                        "end_line": {
                            "type": "integer",
                            "minimum": 1,
                            "description": "номер последней строки блока включительно (1-индексация). Должен быть >= start_line и не превышать количество строк в файле. Используется для определения границ блока"
                        },
                        "title": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 120,
                            "description": "короткое описание содержимого блока, отражающее его суть (функция, класс, секция, конфигурация и т.п.). Используется для быстрой идентификации блока в результатах поиска"
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
                            "maxItems": 12,
                            "description": (
                                "Термы для буста BM25. Ключевые термины из текста для улучшения полнотекстового поиска через BM25 алгоритм. "
                                "Извлекай важные слова, которые могут встречаться в поисковых запросах."
                            )
                        },
                        "symbols": {
                            "type": "array",
                            "items": {"type": "string"},
                            "maxItems": 20,
                            "description": (
                                "массив каноничных имён сущностей, символов, типов, интерфейсов, констант - "
                                "все значимые идентификаторы, которые используются для связности кода"
                            )
                        },
                        "graph_questions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 2,
                            "maxItems": 7,
                            "description": (
                                "Вопросы, которые этот блок текста мог бы задать другим частям системы, если бы «спрашивал» о том, что ему нужно для работы. "
                                "Формулируй естественные короткие вопросы в контексте кода или логики: «кто вызывает...», «где определяется...», «какая функция обновляет...», «откуда берутся данные...». "
                                "Не пиши общие или риторические вопросы. 2-7 конкретных, технических вопросов. "
                                "Примеры: где определяется функция X? кто обновляет таблицу Y? какой модуль вызывает Z? где используется переменная W?"
                            )
                        },
                        "graph_answers": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 2,
                            "maxItems": 7,
                            "description": (
                                "Краткие ответы, которые даёт этот блок текста на возможные технические вопросы других частей системы. "
                                "Формулируй как фактические утверждения о действиях в коде: «здесь вызывается...», «в этом файле определяется...», «этот модуль реализует...». "
                                "2-7 конкретных ответов, отражающих, что делает или предоставляет этот блок текста. "
                                "Примеры: здесь определяется функция X; этот код обновляет таблицу Y; здесь вызывается Z из модуля M; файл содержит значение константы W"
                            )
                        }
                    }
                }
            }
        }
    }
}