import time
from pathlib import Path
from datetime import datetime, UTC
from typing import List, Dict, Any

from elasticsearch import Elasticsearch, helpers
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from anthropic import Anthropic

from utils import (
    ES_URL, ES_INDEX, ES_MANIFEST_INDEX,
    EMBED_MODEL, REPOS_SAFE_ROOT, git_blob_oid, setup_logging, is_ignored, to_posix,
    CLAUDE_MODEL, ANTHROPIC_API_KEY, LANG_BY_EXT, load_prompt
)
from tools import SPLIT_BLOCKS_TOOL, DESCRIBE_BLOCK_TOOL

logger = setup_logging(Path(__file__).stem)

ES = Elasticsearch(ES_URL, request_timeout=30, max_retries=3, retry_on_timeout=True)
CLAUDE = Anthropic(api_key=ANTHROPIC_API_KEY)

EMBEDDING = HuggingFaceEmbedding(EMBED_MODEL, normalize=True)

LLM_VERSION = "v1"

def split_file_into_blocks(text: str, lang: str, rel_path: str) -> List[Dict[str, Any]]:
    prompt_template = load_prompt("prompts/split_blocks.txt")
    system_prompt = prompt_template.format(lang=lang, rel_path=rel_path)
    user_content = f"Разбей файл:\n\n```{lang}\n{text}\n```"
    tools = [SPLIT_BLOCKS_TOOL]
    response = CLAUDE.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        temperature=0,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
        tools=tools
    )
    tool_use = None
    for block in response.content:
        if block.type == "tool_use" and block.name == "split_blocks":
            tool_use = block
            break
    if not tool_use:
        logger.error(f"Не получен tool_use для split_blocks: {rel_path}")
        return []
    blocks = tool_use.input["blocks"]
    logger.info(f"Разбито на {len(blocks)} блоков: {rel_path}")
    return blocks

def describe_block(block_text: str, lang: str, rel_path: str, block_idx: int) -> Dict[str, Any]:
    prompt_template = load_prompt("prompts/describe_block.txt")
    system_prompt = prompt_template.format(lang=lang, rel_path=rel_path, block_idx=block_idx)
    user_content = f"Блок:\n\n```{lang}\n{block_text}\n```"
    tools = [DESCRIBE_BLOCK_TOOL]
    response = CLAUDE.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        temperature=0,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
        tools=tools
    )
    tool_use = None
    for block in response.content:
        if block.type == "tool_use" and block.name == "describe_block":
            tool_use = block
            break
    if not tool_use:
        logger.error(f"Не получен tool_use для describe_block: {rel_path} блок #{block_idx}")
        return {}
    return tool_use.input

def analyze_file(rel_path: str) -> List[Dict[str, Any]]:
    full_path = REPOS_SAFE_ROOT / rel_path
    if not full_path.exists():
        return []
    text = full_path.read_text(encoding='utf-8', errors='ignore')
    ext = full_path.suffix.lower()
    lang = LANG_BY_EXT.get(ext, "text")
    blocks = split_file_into_blocks(text, lang, rel_path)
    chunks = []
    for i, block_def in enumerate(blocks):
        start = block_def["start_line"]
        end = block_def["end_line"]
        lines = text.split('\n')
        block_text = '\n'.join(lines[start-1:end])
        meta = describe_block(block_text, lang, rel_path, i)
        chunks.append({
            "start_line": start,
            "end_line": end,
            "kind": block_def.get("kind", "other"),
            "lang": lang,
            "text": block_text,
            **meta
        })
    logger.info(f"Проанализировано {len(chunks)} чанков для {rel_path}")
    return chunks

def get_file_chunks(rel_path):
    return analyze_file(rel_path)

def delete_chunks(rel_path):
    query = {"term": {"path": rel_path}}
    ES.options(request_timeout=120).delete_by_query(
        index=ES_INDEX,
        body={"query": query},
        conflicts="proceed",
        refresh=True,
        allow_no_indices=True
    )

def chunks_to_actions(chunks: list[dict], rel_path: str, file_hash: str) -> list[dict]:
    total = len(chunks)
    actions = []
    for i, chunk in enumerate(chunks, start=1):
        chunk_id = f"{rel_path}#{i}/{total}"
        embedding = EMBEDDING.get_text_embedding(chunk["text"])
        actions.append({
            "_op_type": "index",
            "_index": ES_INDEX,
            "_id": chunk_id,
            "path": rel_path,
            "hash": file_hash,
            "text": chunk["text"],
            "embedding": embedding,
            "chunk_id": i,
            "chunks": total,
            "start_line": chunk["start_line"],
            "end_line": chunk["end_line"],
            "kind": chunk.get("kind", ""),
            "lang": chunk.get("lang", ""),
            "title": chunk.get("chunk_title", ""),
            "summary": chunk.get("chunk_summary", ""),
            "tags": chunk.get("tags", []),
            "entities": chunk.get("entities", []),
            "public_symbols": chunk.get("public_symbols", []),
            "io": chunk.get("io", []),
            "security_flags": chunk.get("security_flags", []),
            "likely_queries": chunk.get("likely_queries", []),
            "llm_version": LLM_VERSION,
            "updated_at": datetime.now(UTC).isoformat(),
        })
    return actions

def add_file(rel_path, new_hash):
    t0 = time.time()
    chunks = get_file_chunks(rel_path)
    actions = chunks_to_actions(chunks, rel_path, new_hash)
    helpers.bulk(ES.options(request_timeout=120), actions, chunk_size=2000, raise_on_error=True)
    logger.info(f"➕ Added {rel_path} ({len(chunks)} chunks) in {time.time()-t0:.2f}s")

def get_indexed_files():
    query = {
        "size": 0,
        "aggs": {
            "paths": {
                "terms": {
                    "field": "path",
                    "size": 10000
                },
                "aggs": {
                    "hash": {
                        "top_hits": {
                            "size": 1,
                            "_source": ["hash"]
                        }
                    }
                }
            }
        }
    }
    response = ES.search(index=ES_INDEX, body=query)
    result = {}
    for bucket in response["aggregations"]["paths"]["buckets"]:
        path = bucket["key"]
        hits = bucket["hash"]["hits"]["hits"]
        if hits and "hash" in hits[0]["_source"]:
            hash_value = hits[0]["_source"]["hash"]
            result[path] = hash_value
    return result

def process_files():
    indexed_hash_by_file = get_indexed_files()
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
                    delete_chunks(rel_path)
                continue
            if stored_hash and stored_hash != current_hash:
                delete_chunks(rel_path)
            add_file(rel_path, current_hash)
        except Exception as e:
            logger.error(f"Failed to process file {rel_path}: {e}")
    for rel_path in indexed_hash_by_file.keys():
        if rel_path not in processed_paths:
            try:
                delete_chunks(rel_path)
            except Exception as e:
                logger.error(f"Failed to delete file {rel_path}: {e}")

def main():
    try:
        process_files()
    finally:
        ES.close()

if __name__ == "__main__":
    main()
