"""Sourcegraph инструменты для работы с кодом через GraphQL API"""

import os
from pathlib import Path

import requests

from utils import SOURCEGRAPH_URL, SOURCEGRAPH_REPO_NAME, setup_logging

logger = setup_logging(Path(__file__).stem)

GRAPHQL_ENDPOINT = f"{SOURCEGRAPH_URL}/.api/graphql"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"token {os.getenv('SOURCEGRAPH_TOKEN')}",
}

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
        commit(rev: "HEAD") {{
          file(path: $path) {{
            content
            binary
          }}
          blob(path: $path) {{
            symbols(first: 2000) {{
              nodes {{
                name
                kind
                location {{
                  range {{
                    start {{
                      line
                    }}
                    end {{
                      line
                    }}
                  }}
                }}
              }}
            }}
          }}
        }}
      }}
    }}
    """
    result = _execute_graphql(gql, {"path": rel_path})
    if "errors" in result:
        raise Exception(f"GraphQL ошибка: {result['errors']}")
    commit_data = result["data"]["repository"]["commit"]
    file_data = commit_data["file"]
    blob_data = commit_data.get("blob")
    if file_data.get("binary"):
        raise Exception(f"Бинарный файл {rel_path} не обрабатывается")
    content = file_data.get("content")
    if not content:
        raise Exception(f"Файл {rel_path} имеет пустое содержимое")
    symbols = []
    if blob_data:
        symbols = (blob_data.get("symbols", {}) or {}).get("nodes", [])
    lines = content.split("\n")
    chunks = []
    if symbols:
        for s in symbols:
            location = s.get("location", {})
            range_data = location.get("range", {})
            start = range_data.get("start", {}).get("line")
            end = range_data.get("end", {}).get("line")
            if start and end:
                text = "\n".join(lines[start-1:end])
                if text:
                    chunks.append({
                        "start_line": start,
                        "end_line": end,
                        "kind": s.get("kind", "text"),
                        "text": text,
                    })
        if chunks:
            return chunks
    logger.warning(f"No symbols found for {rel_path}, using chunking")
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
    query SearchResults($query: String!) {
      search(query: $query) {
        results { results { ... on FileMatch { file { path url } lineMatches { lineNumber preview } } } }
      }
    }
    """
    result = _execute_graphql(gql_query, {"query": search_query})
    if "errors" in result:
        raise Exception(f"GraphQL ошибка: {result['errors']}")
    matches = result["data"]["search"]["results"]["results"][:limit]
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
        search_query = f"type:symbol file:{path_prefix} {symbol}"
    else:
        search_query = f"type:symbol {symbol}"
    gql_query = """
    query SymbolSearch($query: String!) {
      search(query: $query) {
        results { results { ... on FileMatch { file { path } lineMatches { lineNumber } } } }
      }
    }
    """
    result = _execute_graphql(gql_query, {"query": search_query})
    if "errors" in result:
        raise Exception(f"GraphQL ошибка: {result['errors']}")
    matches = result["data"]["search"]["results"]["results"]
    if not matches:
        return f"Символ '{symbol}' не найден"
    out = [f"📌 {'Определения' if mode == 'definitions' else 'Ссылки'} символа '{symbol}':\n"]
    for m in matches[:15]:
        f = m["file"]
        lines = [lm["lineNumber"] for lm in m.get("lineMatches", [])[:5]]
        line_str = f":{lines[0]}" if lines else ""
        out.append(f"  📄 {f['path']}{line_str}")
    return "\n".join(out)

def sg_blob(rel_path: str, start_line: int, end_line: int) -> str:
    gql_query = f"""
    query BlobContent($path: String!) {{
      repository(name: "{SOURCEGRAPH_REPO_NAME}") {{ commit(rev: "HEAD") {{ file(path: $path) {{ content binary }} }} }}
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

def sg_file_neighbors(rel_path: str, path_prefix: str, max_neighbors: int) -> str:
    path_prefix = path_prefix.lstrip("/").lstrip(".")
    gql_symbols = f"""
    query FileSymbols($path: String!) {{
      repository(name: "{SOURCEGRAPH_REPO_NAME}") {{
        commit(rev: "HEAD") {{
          blob(path: $path) {{
            symbols(first: 50) {{
              nodes {{
                name
              }}
            }}
          }}
        }}
      }}
    }}
    """
    symbols_result = _execute_graphql(gql_symbols, {"path": rel_path})
    blob_data = symbols_result["data"]["repository"]["commit"].get("blob")
    if not blob_data:
        return f"Файл {rel_path} не найден или бинарный"
    symbols = blob_data.get("symbols", {}).get("nodes", [])
    if not symbols:
        return f"Файл {rel_path} не содержит символов"
    neighbor_files = set()
    for symbol_node in symbols:
        symbol_name = symbol_node.get("name")
        if not symbol_name:
            continue
        search_query = f"type:symbol {symbol_name}" + (f" file:{path_prefix}" if path_prefix else "")
        gql_refs = """
        query SymbolRefs($query: String!) {
          search(query: $query) {
            results { results { ... on FileMatch { file { path } } } }
          }
        }
        """
        refs_result = _execute_graphql(gql_refs, {"query": search_query})
        if "errors" in refs_result:
            continue
        matches = refs_result["data"]["search"]["results"]["results"]
        for m in matches:
            file_path = m["file"]["path"]
            if file_path != rel_path:
                neighbor_files.add(file_path)
        if len(neighbor_files) >= max_neighbors:
            break
    if not neighbor_files:
        return f"Соседние файлы для {rel_path} не найдены"
    out = [f"🔗 Соседние файлы для {rel_path}:\n"]
    for neighbor_path in sorted(neighbor_files)[:max_neighbors]:
        out.append(f"  📄 {neighbor_path}")
    return "\n".join(out)
