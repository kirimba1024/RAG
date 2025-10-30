"""Sourcegraph инструменты для работы с кодом через GraphQL API"""

import requests
from utils import SOURCEGRAPH_URL, SOURCEGRAPH_TOKEN, setup_logging
from pathlib import Path

logger = setup_logging(Path(__file__).stem)

GRAPHQL_ENDPOINT = f"{SOURCEGRAPH_URL}/.api/graphql"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"token {SOURCEGRAPH_TOKEN}" if SOURCEGRAPH_TOKEN else "",
}


def _execute_graphql(query: str, variables: dict | None = None) -> dict:
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    resp = requests.post(GRAPHQL_ENDPOINT, json=payload, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def sg_search(query: str, repo: str = "", limit: int = 20) -> str:
    repo_filter = f"repo:{repo}" if repo else ""
    search_query = f"{repo_filter} {query}" if repo_filter else query
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
    out = [f"🔍 Sourcegraph поиск: '{query}' ({len(matches)} результатов):\n"]
    for m in matches:
        f = m["file"]
        out.append(f"\n📄 {f['path']}")
        for lm in m.get("lineMatches", [])[:5]:
            out.append(f"  {lm.get('lineNumber','')}: {lm.get('preview','').strip()}")
    return "\n".join(out)


def sg_codeintel(mode: str, symbol: str = "", doc_id: str = "", line: int = 0) -> str:
    if not symbol:
        return f"Необходимо указать symbol для режима {mode}"
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
    gql_query = gql_query_map.get(mode)
    if not gql_query:
        return f"Неизвестный режим: {mode}. Доступные: definitions, references, callers, callees"
    data = _execute_graphql(gql_query, {"symbol": symbol})["data"]
    if mode == "definitions":
        defs = data["symbolSearch"]["results"]
        if not defs:
            return f"Определения для '{symbol}' не найдены"
        out = [f"📌 Определения символа '{symbol}':\n"]
        for d in defs:
            r = d["result"]
            out.append(f"  📄 {r['file']['path']}")
            out.append(f"     Символ: {r['symbol'].get('name','')}")
            for loc in r.get("locations", [])[:3]:
                out.append(f"     Строки: {loc['range']['start'].get('line','N/A')}")
        return "\n".join(out)
    if mode == "references":
        refs = data["symbolReferences"]["references"]
        if not refs:
            return f"Ссылки на '{symbol}' не найдены"
        out = [f"🔗 Ссылки на символ '{symbol}' ({len(refs)} найден):\n"]
        for r in refs[:15]:
            out.append(f"  📄 {r['file'].get('path','unknown')}:{r['location']['range']['start'].get('line','N/A')}")
        return "\n".join(out)
    return f"Обработан режим: {mode}"


def sg_blob(doc_id: str, start_line: int, end_line: int) -> str:
    if not doc_id:
        return "Необходимо указать doc_id"
    gql_query = """
    query BlobContent($repo: String!, $path: String!, $rev: String!) {
      repository(name: $repo) { commit(rev: $rev) { file(path: $path) { content binary } } }
    }
    """
    repo, file_path = doc_id.split("/", 1)
    result = _execute_graphql(gql_query, {"repo": repo, "path": file_path, "rev": "HEAD"})
    file_data = result["data"]["repository"]["commit"]["file"]
    if not file_data or file_data.get("binary"):
        return f"Файл {doc_id} не найден" if not file_data else f"Файл {doc_id} является бинарным"
    lines = file_data.get("content", "").split("\n")
    end_line = min(end_line, len(lines))
    start_line = max(1, start_line)
    selected = lines[start_line - 1:end_line]
    out = [f"📄 {doc_id} (строки {start_line}-{end_line}):\n"]
    for i, line in enumerate(selected, start=start_line):
        out.append(f"{i:4d} | {line}")
    return "\n".join(out)


def sg_get_file_content(repo: str, path: str) -> str:
    gql_query = """
    query BlobContent($repo: String!, $path: String!, $rev: String!) {
      repository(name: $repo) { commit(rev: $rev) { file(path: $path) { content binary } } }
    }
    """
    result = _execute_graphql(gql_query, {"repo": repo, "path": path, "rev": "HEAD"})
    file_data = result["data"]["repository"]["commit"]["file"]
    if not file_data or file_data.get("binary"):
        return ""
    return file_data.get("content", "")


def sg_list_repos(prefix: str = "") -> list[str]:
    gql = """
    query Repos($first: Int!) { repositories(first: $first) { nodes { name } } }
    """
    data = _execute_graphql(gql, {"first": 500})["data"]["repositories"]["nodes"]
    names = [n["name"] for n in data if n.get("name")]
    return [n for n in names if n.startswith(prefix)] if prefix else names


def sg_list_repo_files(repo: str, limit: int = 5000) -> list[str]:
    gql = """
    query RepoFiles($query: String!, $limit: Int!) {
      search(query: $query, first: $limit) { results { results { ... on FileMatch { file { path } } } } }
    }
    """
    q = f"repo:{repo} type:file"
    results = _execute_graphql(gql, {"query": q, "limit": limit})["data"]["search"]["results"]["results"]
    return [r["file"]["path"] for r in results if r.get("file")]


def sg_file_chunks(repo: str, path: str, min_lines: int = 100, max_lines: int = 120) -> list[dict]:
    gql = """
    query FileSymbols($repo: String!, $path: String!) {
      repository(name: $repo) {
        commit(rev: "HEAD") {
          file(path: $path) {
            symbols(first: 2000) {
              nodes {
                name
                kind
                range { start { line } end { line } }
              }
            }
            content
          }
        }
      }
    }
    """
    data = _execute_graphql(gql, {"repo": repo, "path": path})
    file_obj = data["data"]["repository"]["commit"]["file"]
    content = file_obj.get("content", "")
    symbols = (file_obj.get("symbols", {}) or {}).get("nodes", [])
    if symbols:
        chunks = []
        for s in symbols:
            r = s.get("range", {})
            start = (r.get("start", {}) or {}).get("line", 1)
            end = (r.get("end", {}) or {}).get("line", start)
            if start <= 0:
                start = 1
            if end < start:
                end = start
            chunks.append({
                "repo": repo,
                "path": path,
                "title": s.get("name", ""),
                "kind": s.get("kind", "symbol"),
                "start_line": start,
                "end_line": end,
            })
        chunks.sort(key=lambda x: (x["start_line"], x["end_line"]))
        return chunks
    lines = content.split("\n")
    if not lines:
        return []
    chunks = []
    i = 0
    n = len(lines)
    size = max(min_lines, max_lines)
    while i < n:
        start = i + 1
        end = min(i + size, n)
        chunks.append({
            "repo": repo,
            "path": path,
            "title": f"lines_{start}_{end}",
            "kind": "lines",
            "start_line": start,
            "end_line": end,
        })
        i = end
    return chunks
