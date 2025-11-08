from retriever import main_search, code_stats
from utils import execute_command, setup_logging
from pathlib import Path

logger = setup_logging(Path(__file__).stem)

TOOLS_MAP = {
    "main_search": lambda p: main_search(p["question"], p["path_prefix"], p["top_n"], p.get("signals"), p.get("fields"), p.get("show_line_numbers")),
    "code_stats": lambda p: code_stats(p.get("path_prefix", "")),
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
            "question": {"type": "string"},
            "path_prefix": {"type": "string"},
            "top_n": {"type": "integer", "minimum": 1, "maximum": 30},
            "signals": {"type": "object", "additionalProperties": {"type": "array", "items": {"type": "string"}}},
            "fields": {"type": "array", "items": {"type": "string"}},
            "show_line_numbers": {"type": "boolean"}
        },
        "required": ["question", "path_prefix", "top_n"]
    }
}

CODE_STATS_TOOL = {
    "name": "code_stats",
    "input_schema": {
        "type": "object",
        "properties": {
            "path_prefix": {"type": "string"}
        }
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
                    "required": ["start_line","end_line","title","kind"],
                    "properties": {
                        "start_line": { "type": "integer", "minimum": 1 },
                        "end_line":   { "type": "integer", "minimum": 1 },
                        "title":      { "type": "string",  "minLength": 1, "maxLength": 120 },
                        "kind":       { "type": "string",  "minLength": 1, "maxLength": 32 }
                    }
                }
            }
        }
    }
}

DESCRIBE_CORE_TOOL = {
    "name": "describe_core",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["name", "title", "description", "summary", "detailed", "language", "purpose", "file_type", "notes", "conclusions", "open_questions", "highlights", "has_documentation", "layer", "complexity", "confidence", "improvements", "bugs", "vulnerabilities", "bm25_boost_terms"],
        "properties": {
            "name":                {"type": "string", "maxLength": 32, "pattern": "^\\S+$"},
            "title":               {"type": "string", "maxLength": 128},
            "description":         {"type": "string", "maxLength": 256},
            "summary":             {"type": "string", "maxLength": 1024},
            "detailed":            {"type": "string", "maxLength": 2048},
            "language":            {"type": "string", "maxLength": 32},
            "purpose":             {"type": "string", "maxLength": 240},
            "file_type":           {"type": "string", "maxLength": 32},
            "notes":               {"type": "string", "maxLength": 512},
            "conclusions":         {"type": "string", "maxLength": 512},
            "open_questions":      {"type": "string", "maxLength": 512},
            "highlights":          {"type": "string", "maxLength": 512},
            "has_documentation":   {"type": "boolean"},
            "layer":               {"type": "string", "maxLength": 32},
            "complexity":          {"type": "number", "minimum": 0, "maximum": 1},
            "confidence":          {"type": "number", "minimum": 0, "maximum": 1},
            "improvements":        {"type": "string", "maxLength": 512},
            "bugs":                {"type": "string", "maxLength": 512},
            "vulnerabilities":     {"type": "string", "maxLength": 512},
            "bm25_boost_terms":    {"type": "array", "items": {"type": "string"}}
        }
    }
}

DESCRIBE_SIGNALS_A_TOOL = {
    "name": "describe_signals_a",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["symbols", "paths", "keys", "api_endpoints", "db_entities", "dependencies", "events_queues", "idents", "headers_auth_scopes", "errors_codes", "imports", "functions", "classes", "variables"],
        "properties": {
            "symbols":             {"type": "array", "items": {"type": "string"}},
            "paths":               {"type": "array", "items": {"type": "string"}},
            "keys":                {"type": "array", "items": {"type": "string"}},
            "api_endpoints":       {"type": "array", "items": {"type": "string"}},
            "db_entities":         {"type": "array", "items": {"type": "string"}},
            "dependencies":        {"type": "array", "items": {"type": "string"}},
            "events_queues":       {"type": "array", "items": {"type": "string"}},
            "idents":              {"type": "array", "items": {"type": "string"}},
            "headers_auth_scopes": {"type": "array", "items": {"type": "string"}},
            "errors_codes":        {"type": "array", "items": {"type": "string"}},
            "imports":             {"type": "array", "items": {"type": "string"}},
            "functions":           {"type": "array", "items": {"type": "string"}},
            "classes":             {"type": "array", "items": {"type": "string"}},
            "variables":           {"type": "array", "items": {"type": "string"}}
        }
    }
}

DESCRIBE_SIGNALS_B_TOOL = {
    "name": "describe_signals_b",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["feature_flags", "secrets", "permissions", "roles", "config_keys", "dtos", "entities", "domain_objects", "io", "tags", "key_points", "security_flags", "todos"],
        "properties": {
            "feature_flags":       {"type": "array", "items": {"type": "string"}},
            "secrets":             {"type": "array", "items": {"type": "string"}},
            "permissions":         {"type": "array", "items": {"type": "string"}},
            "roles":               {"type": "array", "items": {"type": "string"}},
            "config_keys":         {"type": "array", "items": {"type": "string"}},
            "dtos":                {"type": "array", "items": {"type": "string"}},
            "entities":            {"type": "array", "items": {"type": "string"}},
            "domain_objects":      {"type": "array", "items": {"type": "string"}},
            "io":                  {"type": "array", "items": {"type": "string"}},
            "tags":                {"type": "array", "items": {"type": "string"}},
            "key_points":          {"type": "array", "items": {"type": "string"}},
            "security_flags":      {"type": "array", "items": {"type": "string"}},
            "todos":               {"type": "array", "items": {"type": "string"}}
        }
    }
}

DESCRIBE_SIGNALS_C_TOOL = {
    "name": "describe_signals_c",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["graph_questions", "graph_answers"],
        "properties": {
            "graph_questions":     {"type": "array", "items": {"type": "string"}},
            "graph_answers":      {"type": "array", "items": {"type": "string"}}
        }
    }
}