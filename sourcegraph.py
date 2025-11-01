"""Sourcegraph инструменты для работы с кодом через GraphQL API"""

from pathlib import Path

import requests

from mask import mask_secrets, check_secrets_in_text
from utils import SOURCEGRAPH_URL, SOURCEGRAPH_TOKEN, setup_logging, clean_text, extract_binary_content

logger = setup_logging(Path(__file__).stem)

GRAPHQL_ENDPOINT = f"{SOURCEGRAPH_URL}/.api/graphql"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"token {SOURCEGRAPH_TOKEN}" if SOURCEGRAPH_TOKEN else "",
}

CHUNK_SIZE = 512

def _execute_graphql(query: str, variables: dict | None = None) -> dict:
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    resp = requests.post(GRAPHQL_ENDPOINT, json=payload, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()

def _split_file_path(rel_path: str) -> tuple[str, str]:
    parts = rel_path.split("/", 1)
    if len(parts) < 2:
        raise ValueError(f"Invalid file path format: {rel_path}. Expected format: repo/path")
    return parts[0], parts[1]

def _split_by_symbols(symbols: list, content: str) -> list[dict]:
    if not content:
        return []
    content = sanitize_chunk(content)
    lines = content.split("\n")
    chunks = []
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

def custom_split(content: str, kind: str) -> list[dict]:
    if not content:
        return []
    content = sanitize_chunk(content)
    lines = content.split("\n")
    chunks = []
    start_line = 1
    while start_line <= len(lines):
        end_line = min(start_line + CHUNK_SIZE - 1, len(lines))
        text = "\n".join(lines[start_line-1:end_line])
        chunks.append({
            "start_line": start_line,
            "end_line": end_line,
            "kind": kind,
            "text": text,
        })
        start_line = end_line + 1
    return chunks

def sanitize_chunk(text: str) -> str:
    text = clean_text(text)
    text = mask_secrets(text)
    check_secrets_in_text(text)
    return text

def get_file_chunks(rel_path: str) -> list[dict]:
    repo, path = _split_file_path(rel_path)
    gql = """
    query FileChunks($repo: String!, $path: String!, $rev: String!) {
      repository(name: $repo) {
        commit(rev: $rev) {
          file(path: $path) {
            content
            binary
            symbols(first: 2000) {
              nodes {
                name
                kind
                range { start { line } end { line } }
              }
            }
          }
        }
      }
    }
    """
    result = _execute_graphql(gql, {"repo": repo, "path": path, "rev": "HEAD"})
    file_data = result["data"]["repository"]["commit"]["file"]
    if file_data.get("binary"):
        content = extract_binary_content(rel_path)
        return custom_split(content, "binary")
    content = file_data.get("content")
    symbols = (file_data.get("symbols", {}) or {}).get("nodes", [])
    if symbols:
        return _split_by_symbols(symbols, content)
    return custom_split(content, "text")

def sg_search(query: str, path_prefix: str, limit: int) -> str:
    path_prefix = path_prefix.lstrip("/").lstrip(".")
    repo, *rest = path_prefix.split("/", 1)
    filters = [f"repo:{repo}@HEAD"]
    if rest:
        filters.append(f"file:{rest[0]}")
    search_query = f"{' '.join(filters)} {query}"
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
    repo, *rest = path_prefix.split("/", 1)
    filters = [f"repo:{repo}@HEAD"]
    if rest:
        filters.append(f"file:{rest[0]}")
    query_filter = " ".join(filters)
    symbol_query = f"{query_filter} {symbol}"
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
    gql_query = """
    query BlobContent($repo: String!, $path: String!, $rev: String!) {
      repository(name: $repo) { commit(rev: $rev) { file(path: $path) { content binary } } }
    }
    """
    repo, file_path = rel_path.split("/", 1)
    result = _execute_graphql(gql_query, {"repo": repo, "path": file_path, "rev": "HEAD"})
    file_data = result["data"]["repository"]["commit"]["file"]
    if file_data["binary"]:
        return f"Файл {rel_path} является бинарным"
    lines = file_data["content"].split("\n")
    selected = lines[start_line - 1:end_line]
    out = [f"📄 {rel_path} (строки {start_line}-{end_line}):\n"]
    for i, line in enumerate(selected, start=start_line):
        out.append(f"{i:4d} | {line}")
    return "\n".join(out)
