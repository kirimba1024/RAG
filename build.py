import time
from pathlib import Path
from datetime import datetime, UTC

from elasticsearch import Elasticsearch, helpers
from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from utils import (
    ES_URL, ES_INDEX, ES_MANIFEST_INDEX,
    EMBED_MODEL, setup_logging, is_ignored
)
from sourcegraph import (
    get_file_chunks, sg_list_repos, sg_list_repo_files,
    sg_list_repo_branches
)

logger = setup_logging(Path(__file__).stem)

ES = Elasticsearch(ES_URL, request_timeout=30, max_retries=3, retry_on_timeout=True)

Settings.embed_model = HuggingFaceEmbedding(EMBED_MODEL, normalize=True)

def upsert_manifest(rel_path, new_hash, branch):
    manifest_id = f"{rel_path}#{branch}"
    ES.index(
        index=ES_MANIFEST_INDEX,
        id=manifest_id,
        document={
            "path": rel_path,
            "hash": new_hash,
            "branch": branch,
            "updated_at": datetime.now(UTC).isoformat()
        }
    )

def delete_manifest(rel_path, branch):
    manifest_id = f"{rel_path}#{branch}"
    ES.delete(index=ES_MANIFEST_INDEX, id=manifest_id)

def delete_chunks(rel_path, branch):
    query = {"bool": {"must": [{"term": {"doc_id": rel_path}}, {"term": {"metadata.branch": branch}}]}}
    ES.options(request_timeout=120).delete_by_query(
        index=ES_INDEX,
        body={"query": query},
        conflicts="proceed",
        refresh=True,
        allow_no_indices=True
    )

def chunks_to_actions(chunks: list[dict], rel_path: str, branch: str) -> list[dict]:
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
                "branch": branch,
            },
        })
    return actions

def add_file(rel_path, new_hash, branch):
    t0 = time.time()
    chunks = get_file_chunks(rel_path, branch)
    actions = chunks_to_actions(chunks, rel_path, branch)
    helpers.bulk(ES.options(request_timeout=120), actions, chunk_size=2000, raise_on_error=True)
    logger.info(f"➕ Added {rel_path} ({len(chunks)} chunks, branch={branch}) in {time.time()-t0:.2f}s")
    upsert_manifest(rel_path, new_hash, branch)

def process_files():
    manifest_response = ES.search(
        index=ES_MANIFEST_INDEX,
        body={
            "query": {"match_all": {}},
            "size": 10000,
            "_source": ["path", "branch", "hash"]
        }
    )
    manifest_hash_by_file = {
        (hit["_source"]["path"], hit["_source"]["branch"]): hit["_source"]["hash"]
        for hit in manifest_response["hits"]["hits"]
    }
    repos = sg_list_repos(prefix="")
    processed_keys = set()
    for repo in repos:
        branches = sg_list_repo_branches(repo)
        for branch in branches:
            for rel_path, current_hash in sg_list_repo_files(repo, branch):
                try:
                    key = (rel_path, branch)
                    processed_keys.add(key)
                    stored_hash = manifest_hash_by_file.get(key)
                    if current_hash == stored_hash and current_hash is not None:
                        logger.debug(f"⏭️  Skipped {rel_path} (unchanged, branch={branch})")
                        continue
                    if is_ignored(Path(rel_path)) or not current_hash:
                        if stored_hash:
                            delete_chunks(rel_path, branch)
                            delete_manifest(rel_path, branch)
                        continue
                    if stored_hash and stored_hash != current_hash:
                        delete_chunks(rel_path, branch)
                    add_file(rel_path, current_hash, branch)
                except Exception as e:
                    logger.error(f"Failed to process file {rel_path} (branch={branch}): {e}")
    for rel_path, branch in manifest_hash_by_file.keys():
        if (rel_path, branch) not in processed_keys:
            try:
                delete_chunks(rel_path, branch)
                delete_manifest(rel_path, branch)
            except Exception as e:
                logger.error(f"Failed to delete file {rel_path} (branch={branch}): {e}")

def main():
    try:
        process_files()
    finally:
        ES.close()

if __name__ == "__main__":
    main()
