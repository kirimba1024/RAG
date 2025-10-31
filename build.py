import time
import subprocess
from pathlib import Path
from datetime import datetime, UTC

from elasticsearch import Elasticsearch, helpers
from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from utils import (
    ES_URL, ES_INDEX, ES_MANIFEST_INDEX,
    EMBED_MODEL, setup_logging, is_ignored, to_posix
)
from sourcegraph import (
    get_file_chunks, get_file_hash, sg_list_repos, sg_list_repo_files,
    sg_list_repo_branches
)

logger = setup_logging(Path(__file__).stem)

ES = Elasticsearch(ES_URL, request_timeout=30, max_retries=3, retry_on_timeout=True)

Settings.embed_model = HuggingFaceEmbedding(EMBED_MODEL, normalize=True)

def upsert_manifest(rel_path, new_hash, rev):
    manifest_id = f"{rel_path}#{rev}"
    ES.index(
        index=ES_MANIFEST_INDEX,
        id=manifest_id,
        document={
            "path": rel_path,
            "hash": new_hash,
            "rev": rev,
            "updated_at": datetime.now(UTC).isoformat()
        }
    )

def delete_manifest(rel_path, rev):
    manifest_id = f"{rel_path}#{rev}"
    ES.delete(index=ES_MANIFEST_INDEX, id=manifest_id)

def delete_chunks(rel_path, rev):
    query = {"bool": {"must": [{"term": {"doc_id": rel_path}}, {"term": {"metadata.rev": rev}}]}}
    ES.options(request_timeout=120).delete_by_query(
        index=ES_INDEX,
        body={"query": query},
        conflicts="proceed",
        refresh=True,
        allow_no_indices=True
    )

def delete_file(rel_path, rev):
    t0 = time.time()
    delete_chunks(rel_path, rev)
    delete_manifest(rel_path, rev)
    logger.info(f"🗑️ Deleted {rel_path} (rev={rev}) in {time.time()-t0:.2f}s")

def chunks_to_actions(chunks: list[dict], rel_path: str, rev: str) -> list[dict]:
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
                "symbol": chunk["title"],
                "kind": chunk["kind"],
                "chunk_id": i,
                "chunk_total": total,
                "rev": rev,
            },
        })
    return actions

def add_file(rel_path, new_hash, rev):
    t0 = time.time()
    chunks = get_file_chunks(rel_path, rev)
    if chunks:
        actions = chunks_to_actions(chunks, rel_path, rev)
        helpers.bulk(ES.options(request_timeout=120), actions, chunk_size=2000, raise_on_error=True)
        logger.info(f"➕ Added {rel_path} ({len(chunks)} chunks, rev={rev}) in {time.time()-t0:.2f}s")
    upsert_manifest(rel_path, new_hash, rev)

def process_files():
    manifest_response = ES.search(
        index=ES_MANIFEST_INDEX,
        body={
            "query": {"match_all": {}},
            "size": 10000,
            "_source": ["path", "rev", "hash"]
        }
    )
    manifest_hash_by_file = {
        (hit["_source"]["path"], hit["_source"].get("rev")): hit["_source"].get("hash")
        for hit in manifest_response["hits"]["hits"]
    }
    repos = sg_list_repos(prefix="")
    processed_keys = set()
    for repo in repos:
        branches = sg_list_repo_branches(repo)
        for branch in branches:
            for rel_path, current_hash in sg_list_repo_files(repo, branch):
                key = (rel_path, branch)
                processed_keys.add(key)
                stored_hash = manifest_hash_by_file.get(key)
                if current_hash == stored_hash and current_hash is not None:
                    logger.debug(f"⏭️  Skipped {rel_path} (unchanged, rev={branch})")
                    continue
                if is_ignored(Path(rel_path)) or not current_hash:
                    if stored_hash:
                        delete_chunks(rel_path, branch)
                        upsert_manifest(rel_path, None, branch)
                    continue
                if stored_hash and stored_hash != current_hash:
                    delete_chunks(rel_path, branch)
                add_file(rel_path, current_hash, branch)
    for rel_path, rev in set(manifest_hash_by_file.keys()) - processed_keys:
        delete_chunks(rel_path, rev)
        delete_manifest(rel_path, rev)

def main():
    try:
        process_files()
    finally:
        ES.close()

if __name__ == "__main__":
    main()
