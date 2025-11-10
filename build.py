import time
from pathlib import Path
from datetime import datetime, UTC
from typing import List, Dict, Any
import mimetypes

from elasticsearch import Elasticsearch, helpers
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from anthropic import Anthropic

from utils import (
    ES_URL, ES_INDEX_CHUNKS, ES_INDEX_FILE_MANIFEST,
    EMBED_MODEL, REPOS_SAFE_ROOT, git_blob_oid, setup_logging, is_ignored, to_posix,
    CLAUDE_MODEL, ANTHROPIC_API_KEY, LANG_BY_EXT, load_prompt
)
from tools import SPLIT_BLOCKS_TOOL

logger = setup_logging(Path(__file__).stem)

ES = Elasticsearch(ES_URL, request_timeout=30, max_retries=3, retry_on_timeout=True)
CLAUDE = Anthropic(api_key=ANTHROPIC_API_KEY)

EMBEDDING = HuggingFaceEmbedding(EMBED_MODEL, normalize=True)

SPLIT_SYSTEM = load_prompt("prompts/system_split_blocks.txt")

def delete_file_data(rel_path):
    query = {"term": {"path": rel_path}}
    ES.options(request_timeout=120).delete_by_query(
        index=ES_INDEX_CHUNKS,
        body={"query": query},
        conflicts="proceed",
        refresh=True,
        allow_no_indices=True
    )
    ES.options(request_timeout=120).delete_by_query(
        index=ES_INDEX_FILE_MANIFEST,
        body={"query": query},
        conflicts="proceed",
        refresh=True,
        allow_no_indices=True
    )

def index_es_file(rel_path, new_hash):
    t0 = time.time()
    full_path = REPOS_SAFE_ROOT / rel_path
    if not full_path.exists():
        raise FileNotFoundError(f"Файл не найден: {rel_path}")
    file_text = full_path.read_text(encoding='utf-8', errors='ignore')
    if not file_text:
        raise RuntimeError(f"Пустой файл: {rel_path}")
    ext = full_path.suffix.lower()
    lang = LANG_BY_EXT.get(ext, "text")
    file_size = full_path.stat().st_size
    file_extension = full_path.suffix.lower()[1:] if full_path.suffix else ""
    file_name = full_path.name
    file_mime = mimetypes.guess_type(str(full_path))[0] or ""
    now_iso = datetime.now(UTC).isoformat()
    response = CLAUDE.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        temperature=0,
        system=[{"type": "text", "text": SPLIT_SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": [{"type": "text", "text": file_text, "cache_control": {"type": "ephemeral"}}]}],
        tools=[SPLIT_BLOCKS_TOOL],
        extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"}
    )
    if not response.content or response.content[0].type != "tool_use":
        raise RuntimeError(f"Claude не вернул tool_use для {rel_path} для разбиения на блоки")
    blocks = response.content[0].input["blocks"]
    lines = file_text.count('\n') + 1
    logger.info(f"Разбито на {len(blocks)} блоков: {rel_path}")
    total = len(blocks)
    lines_list = file_text.split('\n')
    chunks = []
    for i, block_def in enumerate(blocks, start=0):
        start, end = block_def["start_line"], block_def["end_line"]
        block_text = '\n'.join(lines_list[start-1:end])
        chunks.append({
            "_op_type": "index",
            "_index": ES_INDEX_CHUNKS,
            "_id": f"{rel_path}#{i}/{total}",
            "path": rel_path,
            "hash": new_hash,
            "text": block_text,
            "embedding": EMBEDDING.get_text_embedding(block_text),
            "chunk_id": i,
            "chunks": total,
            "file_size": file_size,
            "size": len(block_text.encode('utf-8')),
            "file_lines": lines,
            "extension": file_extension,
            "filename": file_name,
            "mime": file_mime,
            "lang": lang,
            "created_at": now_iso,
            "updated_at": now_iso,
            "llm_version": CLAUDE_MODEL,
            **block_def
        })
    manifest = {
        "_op_type": "index",
        "_index": ES_INDEX_FILE_MANIFEST,
        "_id": rel_path,
        "path": rel_path,
        "hash": new_hash,
        "created_at": now_iso,
        "updated_at": now_iso
    }
    logger.info(f"Проанализировано {len(chunks)} чанков для {rel_path}")
    helpers.bulk(ES.options(request_timeout=120), chunks, chunk_size=2000, raise_on_error=True)
    helpers.bulk(ES.options(request_timeout=120), [manifest], chunk_size=1, raise_on_error=True)
    logger.info(f"➕ Added {rel_path} ({len(chunks)} chunks) in {time.time()-t0:.2f}s")

def get_file_manifest():
    query = {"_source": ["path","hash"], "query": {"match_all": {}}}
    scroll = ES.search(index=ES_INDEX_FILE_MANIFEST, body=query, scroll="5m", size=1000)
    scroll_id = scroll.get("_scroll_id")
    hits = scroll["hits"]["hits"]
    result = {}
    while len(hits) > 0:
        for hit in hits:
            src = hit.get("_source", {})
            result[src.get("path")] = src.get("hash")
        scroll = ES.scroll(scroll_id=scroll_id, scroll="5m")
        hits = scroll["hits"]["hits"]
    ES.clear_scroll(scroll_id=scroll_id)
    return result

def process_files():
    indexed_hash_by_file = get_file_manifest()
    processed_paths = set()
    for full in (f for f in REPOS_SAFE_ROOT.rglob('**/*') if f.is_file()):
        rel_path = to_posix(full.relative_to(REPOS_SAFE_ROOT))
        if is_ignored(rel_path):
            current_hash = None
        else:
            current_hash = git_blob_oid(full)
        try:
            processed_paths.add(rel_path)
            stored_hash = indexed_hash_by_file.get(rel_path)
            if current_hash == stored_hash and current_hash is not None:
                logger.debug(f"⏭️  Skipped {rel_path} (unchanged, hash={current_hash[:8]})")
                continue
            if not current_hash:
                if stored_hash:
                    delete_file_data(rel_path)
                continue
            if stored_hash and stored_hash != current_hash:
                delete_file_data(rel_path)
            index_es_file(rel_path, current_hash)
        except Exception as e:
            logger.error(f"Failed to process file {rel_path}: {e}")
    for rel_path in indexed_hash_by_file.keys():
        if rel_path not in processed_paths:
            try:
                delete_file_data(rel_path)
            except Exception as e:
                logger.error(f"Failed to delete file {rel_path}: {e}")

def main():
    try:
        process_files()
    finally:
        ES.close()

if __name__ == "__main__":
    main()
