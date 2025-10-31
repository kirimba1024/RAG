import time
import subprocess
from pathlib import Path
from datetime import datetime, UTC

from elasticsearch import Elasticsearch, helpers
from llama_index.core import Document, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from utils import (
    calc_hash, REPOS_ROOT, to_posix, setup_logging,
    ES_URL, ES_INDEX, ES_MANIFEST_INDEX,
    EMBED_MODEL,
)
from sourcegraph import sg_file_chunks, sg_get_file_content, sg_list_repos, sg_list_repo_files, sg_get_repo_rev
from utils import is_ignored, check_secrets_in_text
from mask import mask_secrets

logger = setup_logging(Path(__file__).stem)

try:
    import pytesseract
    from PIL import Image
    from llama_index.readers.file import PyMuPDFReader, DocxReader, PptxReader, PandasCSVReader, PandasExcelReader, UnstructuredReader
    BINARY_SUPPORT = True
except ImportError:
    BINARY_SUPPORT = False
    logger.warning("Binary file processing disabled (missing dependencies)")

ES = Elasticsearch(ES_URL, request_timeout=30, max_retries=3, retry_on_timeout=True)

Settings.embed_model = HuggingFaceEmbedding(EMBED_MODEL, normalize=True)

def to_es_action(node, doc, embedding):
    return {
        "_op_type": "index",
        "_index": ES_INDEX,
        "_id": node.id_,
        "doc_id": doc.doc_id,
        "text": node.text,
        "embedding": embedding,
        "metadata": node.metadata,
    }

 
def sanitize_chunk(file_rel: str, text: str) -> str:
    masked, _ = mask_secrets(text)
    findings = check_secrets_in_text(masked)
    if findings:
        logger.info(f"🔒 {file_rel}: {len(findings)}")
        for f in findings:
            logger.info(f"  {f['type']} line {f['line']}: {f['match']}")
    return masked


def get_manifest_data(rel_path):
    result = ES.get(index=ES_MANIFEST_INDEX, id=rel_path)
    if result and "_source" in result:
        src = result["_source"]
        return src.get("hash"), src.get("rev")
    return None, None

def upsert_manifest(rel_path, new_hash, rev):
    ES.index(
        index=ES_MANIFEST_INDEX,
        id=rel_path,
        document={
            "path": rel_path,
            "hash": new_hash,
            "rev": rev,
            "updated_at": datetime.now(UTC).isoformat()
        }
    )

def delete_file(rel_path):
    t0 = time.time()
    ES.options(request_timeout=120).delete_by_query(
        index=ES_INDEX,
        body={"query": {"term": {"doc_id": rel_path}}},
        conflicts="proceed",
        refresh=True,
        allow_no_indices=True
    )
    ES.delete(index=ES_MANIFEST_INDEX, id=rel_path)
    logger.info(f"🗑️ Deleted {rel_path} in {time.time()-t0:.2f}s")

def extract_binary_content(rel_path):
    if not BINARY_SUPPORT:
        return None
    local_path = REPOS_ROOT / rel_path
    if not local_path.exists():
        return None
    ext = local_path.suffix.lower()
    try:
        if ext == ".pdf":
            reader = PyMuPDFReader()
            docs = reader.load_data(str(local_path))
        elif ext == ".docx":
            reader = DocxReader()
            docs = reader.load_data(str(local_path))
        elif ext == ".pptx":
            reader = PptxReader()
            docs = reader.load_data(str(local_path))
        elif ext in [".html", ".epub", ".rtf"]:
            reader = UnstructuredReader()
            docs = reader.load_data(str(local_path))
        elif ext == ".csv":
            reader = PandasCSVReader(concat_rows=True, row_joiner="\n")
            docs = reader.load_data(str(local_path))
        elif ext in [".xls", ".xlsx"]:
            reader = PandasExcelReader(concat_rows=True)
            docs = reader.load_data(str(local_path))
        elif ext in [".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".bmp"]:
            with Image.open(local_path) as img:
                try:
                    txt = pytesseract.image_to_string(img, lang="rus+eng")
                except Exception:
                    txt = pytesseract.image_to_string(img)
            docs = [Document(text=txt or "", metadata={"file_path": str(local_path)})]
        else:
            return None
        if not docs or not docs[0].text:
            return None
        return "\n".join(doc.text for doc in docs if doc.text)
    except Exception as e:
        logger.warning(f"Failed to extract binary content from {rel_path}: {e}")
        return None

def add_file(rel_path, new_hash, rev):
    t0 = time.time()
    parts = rel_path.split("/", 1)
    repo_dir = parts[0]
    file_path = parts[1] if len(parts) > 1 else ""
    repo_name = repo_dir
    content = sg_get_file_content(repo_name, file_path, rev=rev)
    if content is None:
        content = extract_binary_content(rel_path)
        if not content:
            logger.info(f"⏭️  Skipped {rel_path} (binary, extraction failed)")
            upsert_manifest(rel_path, new_hash, rev)
            return
        content = content[:4096]
        chunks = [{
            "start_line": 1,
            "end_line": 1,
            "title": "binary_content",
            "kind": "binary",
        }]
        lines = [content]
    else:
        chunks = sg_file_chunks(repo_name, file_path, rev=rev)
        if not chunks:
            logger.info(f"⏭️  Skipped {rel_path} (no chunks)")
            upsert_manifest(rel_path, new_hash, rev)
            return
        lines = content.split("\n")
    actions = []
    total = len(chunks)
    for i, ch in enumerate(chunks, start=1):
        start = max(1, int(ch["start_line"]))
        end = max(start, int(ch["end_line"]))
        text = "\n".join(lines[start-1:end])
        text = sanitize_chunk(file_path, text)
        if not text:
            continue
        node = Document(text=text, metadata={
            "doc_id": f"{repo_dir}/{file_path}",
            "start_line": start,
            "end_line": end,
            "symbol": ch.get("title", ""),
            "kind": ch.get("kind", ""),
            "chunk_id": i,
            "chunk_total": total,
            "rev": rev,
        }, doc_id=f"{repo_dir}/{file_path}#{i}/{total}")
        embedding = Settings.embed_model.get_text_embedding(node.text)
        actions.append(to_es_action(node, node, embedding))
    helpers.bulk(ES.options(request_timeout=120), actions, chunk_size=2000, raise_on_error=True)
    upsert_manifest(rel_path, new_hash, rev)
    logger.info(f"➕ Added {rel_path} ({total} chunks, rev={rev}) in {time.time()-t0:.2f}s")

def process_file(rel_path):
    parts = rel_path.split("/", 1)
    if len(parts) < 2:
        return
    repo_dir, file_rel = parts
    if is_ignored(Path(file_rel)):
        stored_hash, _ = get_manifest_data(rel_path)
        if stored_hash:
            delete_file(rel_path)
        return
    repo_name = repo_dir
    current_rev = sg_get_repo_rev(repo_name)
    content = sg_get_file_content(repo_name, file_rel, rev=current_rev)
    if content is None:
        content = extract_binary_content(rel_path)
    current_hash = calc_hash(content)
    stored_hash, stored_rev = get_manifest_data(rel_path)
    if current_hash == stored_hash and current_rev == stored_rev:
        logger.info(f"⏭️  Skipped {rel_path} (unchanged)")
        return
    if not current_hash:
        return
    if stored_hash == current_hash and stored_rev != current_rev:
        add_file(rel_path, current_hash, current_rev)
    elif stored_hash != current_hash and stored_rev == current_rev:
        ES.options(request_timeout=120).delete_by_query(
            index=ES_INDEX,
            body={"query": {"bool": {"must": [{"term": {"doc_id": rel_path}}, {"term": {"metadata.rev": current_rev}}]}}},
            conflicts="proceed",
            refresh=True,
            allow_no_indices=True
        )
        add_file(rel_path, current_hash, current_rev)
    else:
        add_file(rel_path, current_hash, current_rev)

def process_files():
    result = ES.search(index=ES_MANIFEST_INDEX, body={"query": {"match_all": {}}, "size": 10000, "_source": ["path"]})
    manifest_paths = {hit["_source"]["path"] for hit in result["hits"]["hits"]}
    fs_files = set()
    for repo_full_name in sg_list_repos(prefix=""):
        repo_dir = repo_full_name
        for path in sg_list_repo_files(repo_full_name):
            fs_files.add(f"{repo_dir}/{path}")
    deleted_paths = manifest_paths - fs_files
    for rel_path in deleted_paths:
        delete_file(rel_path)
    if not fs_files and not deleted_paths:
        logger.info("📭 No files to process")
        return
    logger.info(f"📁 Processing {len(fs_files)} files, deleting {len(deleted_paths)}")
    for rel_path in fs_files:
        process_file(rel_path)

def main():
    try:
        process_files()
    finally:
        ES.close()

if __name__ == "__main__":
    main()
