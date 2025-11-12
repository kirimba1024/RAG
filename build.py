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

def analyze_block_issues(blocks, total_lines, rel_path):
    sorted_blocks = sorted(blocks, key=lambda b: (b["start_line"], b["end_line"]))
    block_count = len(sorted_blocks)
    unsorted = sorted_blocks != blocks
    out_of_bounds_start = sum(b["start_line"] < 1 for b in blocks)
    out_of_bounds_end = sum(b["end_line"] > total_lines for b in blocks)
    gaps, overlaps = [], []
    previous_end = 0
    max_end = 0
    for b in sorted_blocks:
        s, e = b["start_line"], b["end_line"]
        if s > previous_end + 1:
            gaps.append((previous_end + 1, s - 1))
        if s <= previous_end:
            overlaps.append((s, previous_end))
        if e > max_end:
            max_end = e
        if e > previous_end:
            previous_end = e
    if max_end < total_lines:
        gaps.append((max_end + 1, total_lines))
    gap_lines = sum(b - a + 1 for a, b in gaps)
    overlap_lines = sum(b - a + 1 for a, b in overlaps)
    raw_coverage_pct = 0.0 if total_lines == 0 else min(max_end, total_lines) / total_lines * 100.0
    gaps_preview = ", ".join(f"{a}-{b}" for a, b in gaps[:3]) + ("…" if len(gaps) > 3 else "")
    overlaps_preview = ", ".join(f"{a}-{b}" for a, b in overlaps[:3]) + ("…" if len(overlaps) > 3 else "")
    logger.info(f"🧪 {rel_path}: blocks={block_count}, unsorted={'yes' if unsorted else 'no'}, "
                f"oob=({out_of_bounds_start} start,{out_of_bounds_end} end), "
                f"gaps={len(gaps)}[{gap_lines}] {gaps_preview}, "
                f"overlaps={len(overlaps)}[{overlap_lines}] {overlaps_preview}, "
                f"raw={raw_coverage_pct:.1f}%")

def normalize_blocks(blocks, total_lines, rel_path):
    sorted_blocks = sorted(blocks, key=lambda b: (b["start_line"], b["end_line"]))
    normalized_blocks = []
    previous_end_line = 0
    for block in sorted_blocks:
        raw_start_line = block["start_line"]
        raw_end_line = block["end_line"]
        if raw_start_line < 1:
            logger.warning(f"⚠️  start_line={raw_start_line} < 1 in {rel_path}, clamped to 1")
        if raw_end_line > total_lines:
            logger.warning(f"⚠️  end_line={raw_end_line} exceeds file lines={total_lines} in {rel_path}, clamped to {total_lines}")
        start_line = max(1, raw_start_line)
        end_line = min(raw_end_line, total_lines)
        if start_line > end_line:
            continue
        if not normalized_blocks:
            start_line = 1
        else:
            if start_line > previous_end_line + 1:
                gap_start = previous_end_line + 1
                gap_end = start_line - 1
                midpoint_line = (previous_end_line + start_line) // 2
                normalized_blocks[-1]["end_line"] = midpoint_line
                start_line = midpoint_line + 1
                logger.warning(f"⚠️  Gap {gap_start}-{gap_end} ({gap_end - gap_start + 1} lines) between blocks in {rel_path}, extended to midpoint")
            elif start_line <= previous_end_line:
                start_line = previous_end_line + 1
        if start_line > end_line:
            continue
        new_block = dict(block)
        new_block["start_line"] = start_line
        new_block["end_line"] = end_line
        normalized_blocks.append(new_block)
        previous_end_line = end_line
    if not normalized_blocks:
        return [{"start_line": 1, "end_line": total_lines, "title": "logic", "kind": "logic_block", "bm25_boost_terms": [], "symbols": [], "graph_questions": [], "graph_answers": []}]
    if normalized_blocks[-1]["end_line"] < total_lines:
        missing_start = normalized_blocks[-1]["end_line"] + 1
        logger.warning(f"⚠️  Last block ends at line {normalized_blocks[-1]['end_line']}, file has {total_lines} lines. Extending last block to cover {missing_start}-{total_lines}")
        normalized_blocks[-1]["end_line"] = total_lines
    covered_lines = 0
    for b in normalized_blocks:
        covered_lines += b["end_line"] - b["start_line"] + 1
    coverage_pct = 0.0 if total_lines == 0 else min(100.0, covered_lines / total_lines * 100.0)
    logger.info(f"📦 Split {rel_path} into {len(normalized_blocks)} blocks")
    logger.info(f"📊 Coverage: {coverage_pct:.1f}%, overlap: 0.0%")
    return normalized_blocks

def delete_file_data(rel_path):
    query = {"term": {"path": rel_path}}
    chunks_result = ES.options(request_timeout=120).delete_by_query(
        index=ES_INDEX_CHUNKS,
        body={"query": query},
        conflicts="proceed",
        refresh=True,
        allow_no_indices=True
    )
    chunks_deleted = chunks_result.get("deleted", 0)
    manifest_result = ES.options(request_timeout=120).delete_by_query(
        index=ES_INDEX_FILE_MANIFEST,
        body={"query": query},
        conflicts="proceed",
        refresh=True,
        allow_no_indices=True
    )
    manifest_deleted = manifest_result.get("deleted", 0)
    logger.info(f"🗑️  Deleted {rel_path}: {chunks_deleted} chunks, {manifest_deleted} manifest")

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
    tool_use_block = next((b for b in response.content if b.type == "tool_use"), None)
    text_content = "\n".join(b.text for b in response.content if b.type == "text") if response.content else ""
    if text_content:
        logger.info(f"💬 Claude returned text for {rel_path}: {text_content}")
    if not tool_use_block:
        content_types = [b.type for b in response.content] if response.content else []
        logger.error(f"❌ Claude returned {content_types} instead of tool_use for {rel_path}. Text: {text_content}")
        raise RuntimeError(f"Claude не вернул tool_use для {rel_path} для разбиения на блоки")
    blocks = tool_use_block.input.get("blocks")
    if not isinstance(blocks, list):
        raise RuntimeError(f"Claude вернул некорректные blocks для {rel_path}: ожидается список, получен {type(blocks).__name__}")
    lines = file_text.count('\n') + 1
    analyze_block_issues(blocks, lines, rel_path)
    blocks = normalize_blocks(blocks, lines, rel_path)
    total = len(blocks)
    lines_list = file_text.split('\n')
    chunks = []
    for i, block_def in enumerate(blocks, start=1):
        start_line = block_def["start_line"]
        end_line = block_def["end_line"]
        block_text = '\n'.join(lines_list[start_line-1:end_line])
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
    helpers.bulk(ES.options(request_timeout=120), chunks, chunk_size=2000, raise_on_error=True)
    helpers.bulk(ES.options(request_timeout=120), [manifest], chunk_size=1, raise_on_error=True)
    logger.info(f"➕ Added {rel_path} ({len(chunks)} chunks) in {time.time()-t0:.2f}s")

def get_file_manifest():
    query = {"_source": ["path","hash"], "query": {"match_all": {}}, "size": 1000}
    scroll = ES.search(index=ES_INDEX_FILE_MANIFEST, body=query, scroll="5m")
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
    logger.info(f"📋 Loaded {len(result)} file manifests from ES")
    return result

def process_files():
    logger.info(f"🔍 Scanning {REPOS_SAFE_ROOT} for files...")
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
            logger.error(f"❌ Failed to process file {rel_path}: {e}")
    for rel_path in indexed_hash_by_file.keys():
        if rel_path not in processed_paths:
            try:
                delete_file_data(rel_path)
            except Exception as e:
                logger.error(f"❌ Failed to delete file {rel_path}: {e}")

def main():
    logger.info(f"🚀 Starting build process...")
    try:
        process_files()
        logger.info(f"✨ Build completed successfully")
    except Exception as e:
        logger.error(f"💥 Build failed: {e}")
        raise
    finally:
        ES.close()

if __name__ == "__main__":
    main()
