"""Sourcegraph инструменты для работы с кодом через GraphQL API"""

import requests
from pathlib import Path
from utils import SOURCEGRAPH_URL, SOURCEGRAPH_TOKEN, setup_logging, clean_text, REPOS_ROOT
from mask import mask_secrets, check_secrets_in_text

logger = setup_logging(Path(__file__).stem)

GRAPHQL_ENDPOINT = f"{SOURCEGRAPH_URL}/.api/graphql"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"token {SOURCEGRAPH_TOKEN}" if SOURCEGRAPH_TOKEN else "",
}

CHUNK_SIZE = 512

import pytesseract
from PIL import Image
from io import BytesIO
import fitz
import pandas as pd
from docx import Document as DocxDocument
from pptx import Presentation
from llama_index.readers.file import UnstructuredReader

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

def _extract_binary_content(rel_path: str, branch: str):
    repo, path = _split_file_path(rel_path)
    raw_url = f"{SOURCEGRAPH_URL}/{repo}@{branch}/-/raw/{path}"
    resp = requests.get(raw_url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    file_bytes = resp.content
    ext = Path(rel_path).suffix.lower()
    if ext == ".pdf":
        doc = fitz.open(stream=BytesIO(file_bytes), filetype="pdf")
        return "\n".join([page.get_text() for page in doc])
    elif ext == ".docx":
        docx_doc = DocxDocument(BytesIO(file_bytes))
        return "\n".join([para.text for para in docx_doc.paragraphs])
    elif ext == ".pptx":
        prs = Presentation(BytesIO(file_bytes))
        text_parts = []
        for slide in prs.slides:
            for shape in slide.shapes:
                text_parts.append(shape.text)
        return "\n".join(text_parts)
    elif ext in [".html", ".epub", ".rtf"]:
        reader = UnstructuredReader()
        docs = reader.load_data(file=BytesIO(file_bytes))
        return "\n".join([doc.text for doc in docs])
    elif ext == ".csv":
        df = pd.read_csv(BytesIO(file_bytes))
        return df.to_string(index=False)
    elif ext in [".xls", ".xlsx"]:
        df = pd.read_excel(BytesIO(file_bytes))
        return df.to_string(index=False)
    elif ext in [".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".bmp"]:
        img = Image.open(BytesIO(file_bytes))
        return pytesseract.image_to_string(img, lang="rus+eng")
    return None

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

def get_file_chunks(rel_path: str, branch: str) -> list[dict]:
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
    result = _execute_graphql(gql, {"repo": repo, "path": path, "rev": branch})
    file_data = result["data"]["repository"]["commit"]["file"]
    if file_data.get("binary"):
        content = _extract_binary_content(rel_path, branch)
        return custom_split(content, "binary")
    content = file_data.get("content")
    symbols = (file_data.get("symbols", {}) or {}).get("nodes", [])
    if symbols:
        return _split_by_symbols(symbols, content)
    return custom_split(content, "text")

def get_file_hash(rel_path: str, branch: str) -> str | None:
    repo, path = _split_file_path(rel_path)
    gql_query = """
    query BlobOid($repo: String!, $path: String!, $rev: String!) {
      repository(name: $repo) { commit(rev: $rev) { file(path: $path) { oid } } }
    }
    """
    result = _execute_graphql(gql_query, {"repo": repo, "path": path, "rev": branch})
    file_data = result["data"]["repository"]["commit"]["file"]
    return file_data.get("oid")

def sg_search(query: str, repo: str, branch: str, limit: int) -> str:
    repo_filter = f"repo:{repo}@{branch}" if repo else ""
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
        for lm in m["lineMatches"][:5]:
            out.append(f"  {lm['lineNumber']}: {lm['preview'].strip()}")
    return "\n".join(out)

def sg_codeintel(mode: str, symbol: str, repo: str, branch: str) -> str:
    query_filter = f"repo:{repo}@{branch}" if repo else ""
    symbol_query = f"{query_filter} {symbol}".strip() if query_filter else symbol
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

def sg_blob(rel_path: str, start_line: int, end_line: int, branch: str) -> str:
    gql_query = """
    query BlobContent($repo: String!, $path: String!, $rev: String!) {
      repository(name: $repo) { commit(rev: $rev) { file(path: $path) { content binary } } }
    }
    """
    repo, file_path = rel_path.split("/", 1)
    result = _execute_graphql(gql_query, {"repo": repo, "path": file_path, "rev": branch})
    file_data = result["data"]["repository"]["commit"]["file"]
    if file_data["binary"]:
        return f"Файл {rel_path} является бинарным"
    lines = file_data["content"].split("\n")
    selected = lines[start_line - 1:end_line]
    out = [f"📄 {rel_path} (строки {start_line}-{end_line}):\n"]
    for i, line in enumerate(selected, start=start_line):
        out.append(f"{i:4d} | {line}")
    return "\n".join(out)


def sg_list_repos(prefix: str) -> list[str]:
    gql = """
    query Repos($first: Int!) { repositories(first: $first) { nodes { name } } }
    """
    data = _execute_graphql(gql, {"first": 500})["data"]["repositories"]["nodes"]
    names = [n["name"] for n in data]
    return [n for n in names if n.startswith(prefix)] if prefix else names

def sg_list_repo_branches(repo: str) -> list[str]:
    gql = """
    query RepoBranches($repo: String!) {
      repository(name: $repo) {
        branches(first: 100) {
          nodes { name }
        }
      }
    }
    """
    data = _execute_graphql(gql, {"repo": repo})["data"]["repository"]
    branches = data["branches"]["nodes"]
    return [b["name"] for b in branches]

def sg_get_repo_branch(repo: str) -> str:
    repo_path = REPOS_ROOT / repo
    if not repo_path.exists():
        raise ValueError(f"Repository {repo} not found in {REPOS_ROOT}")
    git_head = repo_path / ".git" / "HEAD"
    if not git_head.exists():
        raise ValueError(f"Repository {repo} is not a git repository")
    head_content = git_head.read_text().strip()
    if head_content.startswith("ref: refs/heads/"):
        return head_content.replace("ref: refs/heads/", "")
    raise ValueError(f"Repository {repo} is in detached HEAD state")

def get_all_repos_branches_formatted() -> str | None:
    repos = sg_list_repos(prefix="")
    lines = ["## Доступные ветки репозиториев:\n"]
    for repo in sorted(repos):
        branch_names = sg_list_repo_branches(repo)
        branches_str = ", ".join(branch_names[:10])
        if len(branch_names) > 10:
            branches_str += f" (+{len(branch_names)-10} еще)"
        lines.append(f"- **{repo}**: {branches_str}")
    return "\n".join(lines) + "\n"

def sg_list_repo_files(repo: str, branch: str, limit: int = 5000) -> list[tuple[str, str | None]]:
    gql = """
    query RepoFiles($query: String!, $limit: Int!) {
      search(query: $query, first: $limit) { results { results { ... on FileMatch { file { path } } } } }
    }
    """
    q = f"repo:{repo}@{branch} type:file"
    results = _execute_graphql(gql, {"query": q, "limit": limit})["data"]["search"]["results"]["results"]
    files = []
    for r in results:
        file_path = r["file"]["path"]
        file_rel_path = f"{repo}/{file_path}"
        oid = get_file_hash(file_rel_path, branch)
        files.append((file_rel_path, oid))
    return files

