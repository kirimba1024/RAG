from retriever import main_search
from utils import execute_command, setup_logging
from pathlib import Path

logger = setup_logging(Path(__file__).stem)

TOOLS_MAP = {
    "main_search": lambda p: main_search(p["question"], p["path_prefix"], p["top_n"], p.get("show_line_numbers"), p.get("show_links")),
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
    "input_schema": {
        "type": "object",
        "properties": {
            "question":           {"type": "string"},
            "path_prefix":        {"type": "string"},
            "top_n":              {"type": "integer", "minimum": 1, "maximum": 30},
            "show_line_numbers":  {"type": "boolean"},
            "show_links":         {"type": "boolean"}
        },
        "required": ["question", "path_prefix", "top_n"]
    }
}

EXECUTE_COMMAND_TOOL = {
    "name": "execute_command",
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {"type": "string"}
        },
        "required": ["command"]
    }
}

SPLIT_BLOCKS_TOOL = {
    "name": "split_blocks",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["blocks"],
        "properties": {
            "blocks": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["start_line","end_line","title","kind","bm25_boost_terms","symbols","graph_questions","graph_answers"],
                    "properties": {
                        "start_line":         { "type": "integer", "minimum": 1 },
                        "end_line":           { "type": "integer", "minimum": 1 },
                        "title":              { "type": "string", "minLength": 1, "maxLength": 120 },
                        "kind":               { "type": "string", "minLength": 1, "maxLength": 32 },
                        "bm25_boost_terms":   { "type": "array", "items": {"type": "string"} },
                        "symbols":            { "type": "array", "items": {"type": "string"} },
                        "graph_questions":    { "type": "array", "items": {"type": "string"} },
                        "graph_answers":      { "type": "array", "items": {"type": "string"} }
                    }
                }
            }
        }
    }
}