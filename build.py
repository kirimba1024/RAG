import time
from pathlib import Path
from datetime import datetime, UTC
from typing import List, Dict, Any
import mimetypes

from elasticsearch import Elasticsearch, helpers
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from anthropic import Anthropic

from utils import (
    ES_URL, ES_INDEX_CHUNKS, ES_INDEX_FILES,
    EMBED_MODEL, REPOS_SAFE_ROOT, git_blob_oid, setup_logging, is_ignored, to_posix,
    CLAUDE_MODEL, ANTHROPIC_API_KEY, LANG_BY_EXT, load_prompt
)
from tools import SPLIT_BLOCKS_TOOL, DESCRIBE_BLOCK_TOOL, DESCRIBE_FILE_TOOL

logger = setup_logging(Path(__file__).stem)

ES = Elasticsearch(ES_URL, request_timeout=30, max_retries=3, retry_on_timeout=True)
CLAUDE = Anthropic(api_key=ANTHROPIC_API_KEY)

EMBEDDING = HuggingFaceEmbedding(EMBED_MODEL, normalize=True)

SPLIT_SYSTEM = load_prompt("prompts/split_blocks.txt")
DESCRIBE_BLOCK_SYSTEM = load_prompt("prompts/describe_block.txt")
DESCRIBE_FILE_SYSTEM = load_prompt("prompts/describe_file.txt")

def warm_claude_cache():
    CLAUDE.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=128,
        temperature=0,
        system=SPLIT_SYSTEM,
        messages=[{"role": "user", "content": "warm"}],
        tools=[SPLIT_BLOCKS_TOOL]
    )
    CLAUDE.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=128,
        temperature=0,
        system=DESCRIBE_BLOCK_SYSTEM,
        messages=[{"role": "user", "content": "warm"}],
        tools=[DESCRIBE_BLOCK_TOOL]
    )
    CLAUDE.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=128,
        temperature=0,
        system=DESCRIBE_FILE_SYSTEM,
        messages=[{"role": "user", "content": "warm"}],
        tools=[DESCRIBE_FILE_TOOL]
    )

def delete_es_chunks(rel_path):
    query = {"term": {"path": rel_path}}
    ES.options(request_timeout=120).delete_by_query(
        index=ES_INDEX_CHUNKS,
        body={"query": query},
        conflicts="proceed",
        refresh=True,
        allow_no_indices=True
    )

def delete_es_file(rel_path: str):
    ES.options(request_timeout=60).delete(index=ES_INDEX_FILES, id=rel_path, ignore=[404])


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
    response = CLAUDE.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        temperature=0,
        system=SPLIT_SYSTEM,
        messages=[{"role": "user", "content": file_text}],
        tools=[SPLIT_BLOCKS_TOOL]
    )
    blocks = response.content[0].input["blocks"]
    logger.info(f"Разбито на {len(blocks)} блоков: {rel_path}")
    chunks = []
    lines_list = file_text.split('\n')
    total = len(blocks)
    for i, block_def in enumerate(blocks, start=1):
        start = block_def["start_line"]
        end = block_def["end_line"]
        block_text = '\n'.join(lines_list[start-1:end])
        block_response = CLAUDE.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            temperature=0,
            system=DESCRIBE_BLOCK_SYSTEM,
            messages=[{"role": "user", "content": block_text}],
            tools=[DESCRIBE_BLOCK_TOOL]
        )
        meta = block_response.content[0].input
        embedding = EMBEDDING.get_text_embedding(block_text)
        chunks.append({
            "_op_type": "index",
            "_index": ES_INDEX_CHUNKS,
            "_id": f"{rel_path}#{i}/{total}",
            "path": rel_path,
            "hash": new_hash,
            "text": block_text,
            "embedding": embedding,
            "chunk_id": i,
            "chunks": total,
            "start_line": start,
            "end_line": end,
            "kind": block_def.get("kind", ""),
            "lang": lang,
            "size": file_size,
            "lines": lines,
            "extension": file_extension,
            "filename": file_name,
            "mime": file_mime,
            "created_at": datetime.now(UTC).isoformat(),
            **meta,
            "llm_version": CLAUDE_MODEL,
            "updated_at": datetime.now(UTC).isoformat(),
        })
    logger.info(f"Проанализировано {len(chunks)} чанков для {rel_path}")
    lines = file_text.count('\n') + 1
    file_response = CLAUDE.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        temperature=0,
        system=DESCRIBE_FILE_SYSTEM,
        messages=[{"role": "user", "content": file_text}],
        tools=[DESCRIBE_FILE_TOOL]
    )
    file_level = file_response.content[0].input
    file_embedding = EMBEDDING.get_text_embedding(file_text)
    helpers.bulk(ES.options(request_timeout=120), chunks, chunk_size=2000, raise_on_error=True)
    doc = {
        "path": rel_path,
        "hash": new_hash,
        "text": file_text,
        "embedding": file_embedding,
        "llm_version": CLAUDE_MODEL,
        "language": lang,
        "lines": lines,
        "chunk_count": len(chunks),
        "updated_at": datetime.now(UTC).isoformat(),
        "created_at": datetime.now(UTC).isoformat(),
        "size": file_size,
        "extension": file_extension,
        "filename": file_name,
        "mime": file_mime,
        **file_level,
    }
    ES.index(index=ES_INDEX_FILES, id=rel_path, document=doc, refresh=True)
    logger.info(f"➕ Added {rel_path} ({len(chunks)} chunks) in {time.time()-t0:.2f}s")

def get_es_files():
    query = {"size": 10000, "_source": ["hash"], "query": {"match_all": {}}}
    response = ES.search(index=ES_INDEX_FILES, body=query)
    result = {}
    for hit in response.get("hits", {}).get("hits", []):
        src = hit.get("_source", {})
        result[hit["_id"]] = src.get("hash")
    return result

def process_files():
    indexed_hash_by_file = get_es_files()
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
                    delete_es_chunks(rel_path)
                    delete_es_file(rel_path)
                continue
            if stored_hash and stored_hash != current_hash:
                delete_es_chunks(rel_path)
            index_es_file(rel_path, current_hash)
        except Exception as e:
            logger.error(f"Failed to process file {rel_path}: {e}")
    for rel_path in indexed_hash_by_file.keys():
        if rel_path not in processed_paths:
            try:
                delete_es_chunks(rel_path)
                delete_es_file(rel_path)
            except Exception as e:
                logger.error(f"Failed to delete file {rel_path}: {e}")

def main():
    try:
        process_files()
    finally:
        ES.close()

if __name__ == "__main__":
    main()
