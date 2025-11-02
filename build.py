import time
from pathlib import Path
from datetime import datetime, UTC

from elasticsearch import Elasticsearch, helpers
from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from utils import (
    ES_URL, ES_INDEX, ES_MANIFEST_INDEX,
    EMBED_MODEL, REPOS_SAFE_ROOT, git_blob_oid, setup_logging, is_ignored, to_posix
)
from sourcegraph import (
    get_file_chunks
)

logger = setup_logging(Path(__file__).stem)

ES = Elasticsearch(ES_URL, request_timeout=30, max_retries=3, retry_on_timeout=True)

Settings.embed_model = HuggingFaceEmbedding(EMBED_MODEL, normalize=True)

def upsert_manifest(rel_path, new_hash):
    ES.index(
        index=ES_MANIFEST_INDEX,
        id=rel_path,
        document={
            "path": rel_path,
            "hash": new_hash,
            "updated_at": datetime.now(UTC).isoformat()
        }
    )

def delete_manifest(rel_path):
    ES.delete(index=ES_MANIFEST_INDEX, id=rel_path, ignore=[404])

def delete_chunks(rel_path):
    query = {"term": {"doc_id": rel_path}}
    ES.options(request_timeout=120).delete_by_query(
        index=ES_INDEX,
        body={"query": query},
        conflicts="proceed",
        refresh=True,
        allow_no_indices=True
    )

def chunks_to_actions(chunks: list[dict], rel_path: str) -> list[dict]:
    total = len(chunks)
    actions = []
    for i, chunk in enumerate(chunks, start=1):
        chunk_id = f"{rel_path}#{i}/{total}"
        embedding = Settings.embed_model.get_text_embedding(chunk["text"])
        actions.append({
            "_op_type": "index",
            "_index": ES_INDEX,
            "_id": chunk_id,
            "doc_id": rel_path,
            "text": chunk["text"],
            "embedding": embedding,
            "metadata": {
                "doc_id": rel_path,
                "start_line": chunk["start_line"],
                "end_line": chunk["end_line"],
                "kind": chunk["kind"],
                "chunk_id": i,
                "chunk_total": total,
            },
        })
    return actions

def add_file(rel_path, new_hash):
    t0 = time.time()
    chunks = get_file_chunks(rel_path)
    actions = chunks_to_actions(chunks, rel_path)
    helpers.bulk(ES.options(request_timeout=120), actions, chunk_size=2000, raise_on_error=True)
    logger.info(f"➕ Added {rel_path} ({len(chunks)} chunks) in {time.time()-t0:.2f}s")
    upsert_manifest(rel_path, new_hash)

def process_files():
    manifest_hash_by_file = {
        hit["_source"]["path"]: hit["_source"]["hash"]
        for hit in helpers.scan(
            ES,
            index=ES_MANIFEST_INDEX,
            query={
                "query": {"match_all": {}},
                "_source": ["path", "hash"]
            },
            size=1000
        )
    }
    processed_paths = set()
    for full in (f for f in REPOS_SAFE_ROOT.rglob('**/*') if f.is_file()):
        rel_path = to_posix(full.relative_to(REPOS_SAFE_ROOT))
        if is_ignored(rel_path):
            current_hash = None
        else:
            current_hash = git_blob_oid(full)
        try:
            processed_paths.add(rel_path)
            stored_hash = manifest_hash_by_file.get(rel_path)
            if current_hash == stored_hash and current_hash is not None:
                logger.debug(f"⏭️  Skipped {rel_path} (unchanged, hash={current_hash[:8]})")
                continue
            if not current_hash:
                if stored_hash:
                    delete_chunks(rel_path)
                    delete_manifest(rel_path)
                continue
            if stored_hash and stored_hash != current_hash:
                delete_chunks(rel_path)
            add_file(rel_path, current_hash)
        except Exception as e:
            logger.error(f"Failed to process file {rel_path}: {e}")
    for rel_path in manifest_hash_by_file.keys():
        if rel_path not in processed_paths:
            try:
                delete_chunks(rel_path)
                delete_manifest(rel_path)
            except Exception as e:
                logger.error(f"Failed to delete file {rel_path}: {e}")

def main():
    try:
        process_files()
    finally:
        ES.close()

if __name__ == "__main__":
    main()
