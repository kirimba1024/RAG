"""Sourcegraph инструменты для работы с кодом через GraphQL API"""

from pathlib import Path

import requests

from utils import SOURCEGRAPH_URL, SOURCEGRAPH_TOKEN, SOURCEGRAPH_REPO_NAME, setup_logging

logger = setup_logging(Path(__file__).stem)

GRAPHQL_ENDPOINT = f"{SOURCEGRAPH_URL}/.api/graphql"
HEADERS = {
    "Content-Type": "application/json",
}
if SOURCEGRAPH_TOKEN:
    HEADERS["Authorization"] = f"token {SOURCEGRAPH_TOKEN}"

CHUNK_SIZE = 512

def _execute_graphql(query: str, variables: dict | None = None) -> dict:
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    resp = requests.post(GRAPHQL_ENDPOINT, json=payload, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()

def get_file_chunks(rel_path: str) -> list[dict]:
    gql = f"""
    query FileChunks($path: String!) {{
      repository(name: "{SOURCEGRAPH_REPO_NAME}") {{
        commit(rev: HEAD) {{
          file(path: $path) {{
            content
            binary
            symbols(first: 2000) {{
              nodes {{
                name
                kind
                range {{ start {{ line }} end {{ line }} }}
              }}
            }}
          }}
        }}
      }}
    }}
    """
    result = _execute_graphql(gql, {"path": rel_path})
    file_data = result["data"]["repository"]["commit"]["file"]
    if file_data.get("binary"):
        raise Exception(f"Бинарный файл {rel_path} не обрабатывается")
    content = file_data.get("content")
    if not content:
        raise Exception(f"Файл {rel_path} имеет пустое содержимое")
    symbols = (file_data.get("symbols", {}) or {}).get("nodes", [])
    lines = content.split("\n")
    chunks = []
    if symbols:
        for s in symbols:
            start = s["range"]["start"]["line"]
            end = s["range"]["end"]["line"]
            text = "\n".join(lines[start-1:end])
            chunks.append({
                "start_line": start,
                "end_line": end,
                "kind": s["kind"],
                "text": text,
            })
        return chunks
    start_line = 1
    while start_line <= len(lines):
        end_line = min(start_line + CHUNK_SIZE - 1, len(lines))
        text = "\n".join(lines[start_line-1:end_line])
        chunks.append({
            "start_line": start_line,
            "end_line": end_line,
            "kind": "text",
            "text": text,
        })
        start_line = end_line + 1
    return chunks

def sg_search(query: str, path_prefix: str, limit: int) -> str:
    path_prefix = path_prefix.lstrip("/").lstrip(".")
    if path_prefix:
        search_query = f"file:{path_prefix} {query}"
    else:
        search_query = query
    gql_query = """
    query SearchResults($query: String!, $limit: Int!) {
      search(query: $query, first: $limit) {
        results { results { ... on FileMatch { file { path url } lineMatches { lineNumber preview } } } }
      }
    }
    """
    result = _execute_graphql(gql_query, {"query": search_query, "limit": limit})
    matches = result["data"]["search"]["results"]["results"]
    if not matches:
        return f"Поиск: '{query}' не дал результатов"
    prefix_info = f" ({path_prefix})" if path_prefix else ""
    out = [f"🔍 Sourcegraph поиск: '{query}'{prefix_info} ({len(matches)} результатов):\n"]
    for m in matches:
        f = m["file"]
        out.append(f"\n📄 {f['path']}")
        for lm in m["lineMatches"][:5]:
            out.append(f"  {lm['lineNumber']}: {lm['preview'].strip()}")
    return "\n".join(out)

def sg_codeintel(mode: str, symbol: str, path_prefix: str) -> str:
    path_prefix = path_prefix.lstrip("/").lstrip(".")
    if path_prefix:
        symbol_query = f"file:{path_prefix} {symbol}"
    else:
        symbol_query = symbol
    gql_query_map = {
        "definitions": """
          query Definitions($symbol: String!) {
            symbolSearch(query: $symbol, first: 10) {
              results { result { file { path } symbol { name containerName } locations { range { start { line } end { line } } } } }
            }
          }
        """,
        "references": """
          query References($symbol: String!) {
            symbolReferences(query: $symbol, first: 20) {
              references { file { path } symbol { name } location { range { start { line } end { line } } } }
            }
          }
        """,
    }
    gql_query = gql_query_map[mode]
    data = _execute_graphql(gql_query, {"symbol": symbol_query})["data"]
    if mode == "definitions":
        defs = data["symbolSearch"]["results"]
        if not defs:
            return f"Определения для '{symbol}' не найдены"
        out = [f"📌 Определения символа '{symbol}':\n"]
        for d in defs:
            r = d["result"]
            out.append(f"  📄 {r['file']['path']}")
            out.append(f"     Символ: {r['symbol']['name']}")
            for loc in r["locations"][:3]:
                out.append(f"     Строки: {loc['range']['start']['line']}")
        return "\n".join(out)
    if mode == "references":
        refs = data["symbolReferences"]["references"]
        if not refs:
            return f"Ссылки на '{symbol}' не найдены"
        out = [f"🔗 Ссылки на символ '{symbol}' ({len(refs)} найден):\n"]
        for r in refs[:15]:
            out.append(f"  📄 {r['file']['path']}:{r['location']['range']['start']['line']}")
        return "\n".join(out)
    return f"Обработан режим: {mode}"

def sg_blob(rel_path: str, start_line: int, end_line: int) -> str:
    gql_query = f"""
    query BlobContent($path: String!) {{
      repository(name: "{SOURCEGRAPH_REPO_NAME}") {{ commit(rev: HEAD) {{ file(path: $path) {{ content binary }} }} }}
    }}
    """
    result = _execute_graphql(gql_query, {"path": rel_path})
    file_data = result["data"]["repository"]["commit"]["file"]
    if file_data["binary"]:
        return f"Файл {rel_path} является бинарным"
    lines = file_data["content"].split("\n")
    selected = lines[start_line - 1:end_line]
    out = [f"📄 {rel_path} (строки {start_line}-{end_line}):\n"]
    for i, line in enumerate(selected, start=start_line):
        out.append(f"{i:4d} | {line}")
    return "\n".join(out)
