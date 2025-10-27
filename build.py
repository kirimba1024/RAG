import time
from pathlib import Path
from datetime import datetime, UTC

import pytesseract
from PIL import Image
from elasticsearch import Elasticsearch, helpers
from llama_index.core import Document, Settings, PropertyGraphIndex
from llama_index.core.indices.property_graph import SimpleLLMPathExtractor, ImplicitPathExtractor
from llama_index.core.node_parser import SentenceSplitter, CodeSplitter
from llama_index.core.readers.base import BaseReader
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.llms.anthropic import Anthropic as LlamaIndexAnthropic
from llama_index.readers.file import (
    PyMuPDFReader,
    DocxReader,
    PptxReader,
    UnstructuredReader,
    PandasCSVReader,
    PandasExcelReader,
)

from utils import (
    file_hash, KNOWLEDGE_ROOT, to_posix, setup_logging,
    ES_URL, ES_INDEX, ES_MANIFEST_INDEX,
    NEO4J_BOLT_URL, NEO4J_USER, NEO4J_PASS,
    CLAUDE_MODEL, ANTHROPIC_API_KEY, EMBED_MODEL, load_prompt
)

logger = setup_logging(Path(__file__).stem)

OCR_LANG = "rus+eng"

ES = Elasticsearch(ES_URL, request_timeout=30, max_retries=3, retry_on_timeout=True)
GRAPH_STORE = Neo4jPropertyGraphStore(url=NEO4J_BOLT_URL, username=NEO4J_USER, password=NEO4J_PASS)

Settings.embed_model = HuggingFaceEmbedding(EMBED_MODEL, normalize=True)

GRAPH_EXTRACTOR_LLM = LlamaIndexAnthropic(
    model=CLAUDE_MODEL,
    api_key=ANTHROPIC_API_KEY,
    temperature=0.0,
    default_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
    max_tokens=4096
)

PROP_GRAPH_INDEX = PropertyGraphIndex(
    nodes=[],
    property_graph_store=GRAPH_STORE,
    show_progress=False,
    kg_extractors=[
        SimpleLLMPathExtractor(llm=GRAPH_EXTRACTOR_LLM, num_workers=2, extract_prompt=load_prompt("prompts/graph_extraction.txt")),
        ImplicitPathExtractor(),
    ],
    include_text=False,
    embed_kg_nodes=False,
)

LANG_BY_EXT = {
    ".py": "python", ".js": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "tsx",
    ".java": "java", ".kt": "kotlin",
    ".go": "go", ".rs": "rust",
    ".c": "c", ".h": "c",
    ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp", ".hh": "cpp",
    ".cs": "c_sharp", ".php": "php", ".rb": "ruby", ".swift": "swift",
    ".scala": "scala", ".m": "objective_c", ".mm": "objective_cpp",
    ".sh": "bash", ".bash": "bash", ".zsh": "bash",
}

SENTENCE_SPLITTER = SentenceSplitter(chunk_size=800, chunk_overlap=200, paragraph_separator="\n\n")
SPLITTER_BY_LANG = {}

def get_splitter(lang):
    if not lang:
        return SENTENCE_SPLITTER
    if lang not in SPLITTER_BY_LANG:
        try:
            SPLITTER_BY_LANG[lang] = CodeSplitter(
                language=lang,
                chunk_lines=100,
                chunk_lines_overlap=25,
                max_chars=4096
            )
        except Exception:
            SPLITTER_BY_LANG[lang] = SENTENCE_SPLITTER
    return SPLITTER_BY_LANG[lang]

def split_doc_to_nodes(doc: Document):
    ext = Path(doc.doc_id).suffix.lower()
    lang = LANG_BY_EXT.get(ext)
    splitter = get_splitter(lang)
    nodes = splitter.get_nodes_from_documents([doc])
    for i, node in enumerate(nodes):
        node.id_ = f"{doc.doc_id}#{i+1}/{len(nodes)}"
        node.metadata["chunk_id"] = i + 1
        node.metadata["chunk_total"] = len(nodes)
        chunk_start = doc.text.find(node.text)
        if chunk_start != -1:
            chunk_end = chunk_start + len(node.text)
            node.metadata["start_line"] = doc.text[:chunk_start].count('\n') + 1
            node.metadata["end_line"] = doc.text[:chunk_end].count('\n') + 1
        else:
            node.metadata["start_line"] = 0
            node.metadata["end_line"] = doc.text.count('\n') + 1
    return nodes

class TesseractImageReader(BaseReader):
    def __init__(self, lang=OCR_LANG):
        self.lang = lang
    def load_data(self, file: str, extra_info=None):
        with Image.open(file) as img:
            try:
                txt = pytesseract.image_to_string(img, lang=self.lang)
            except pytesseract.TesseractError as e:
                logger.warning(f"Lang OCR failed ({self.lang}) for {file}: {e}, continuing with regular")
                txt = pytesseract.image_to_string(img)
        meta = {"file_path": str(Path(file).resolve())}
        if extra_info:
            meta.update(extra_info)
        return [Document(text=txt or "", metadata=meta)]

class SafePlainTextReader(BaseReader):
    def load_data(self, file: str, extra_info=None):
        p = Path(file)
        raw = p.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("utf-8", errors="ignore")
        meta = {"file_path": str(p.resolve())}
        if extra_info:
            meta.update(extra_info)
        return [Document(text=text, metadata=meta)]

FILE_EXTRACTOR = {
    ".pdf": PyMuPDFReader(),
    ".docx": DocxReader(),
    ".pptx": PptxReader(),
    ".html": UnstructuredReader(),
    ".epub": UnstructuredReader(),
    ".rtf": UnstructuredReader(),
    ".csv": PandasCSVReader(concat_rows=True, row_joiner="\n"),
    ".xls": PandasExcelReader(concat_rows=True),
    ".xlsx": PandasExcelReader(concat_rows=True),
    ".png": TesseractImageReader(OCR_LANG),
    ".jpg": TesseractImageReader(OCR_LANG),
    ".jpeg": TesseractImageReader(OCR_LANG),
    ".tif": TesseractImageReader(OCR_LANG),
    ".tiff": TesseractImageReader(OCR_LANG),
    ".webp": TesseractImageReader(OCR_LANG),
    ".bmp": TesseractImageReader(OCR_LANG),
}

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

def load_doc(rel_path):
    path = (KNOWLEDGE_ROOT / rel_path).resolve()
    ext = path.suffix.lower()
    extractor = FILE_EXTRACTOR.get(ext, SafePlainTextReader())
    docs = extractor.load_data(str(path))
    text = "\n\n".join([(d.text or "") for d in docs])
    return Document(text=text, metadata=docs[0].metadata, doc_id=rel_path)

def get_manifest_hash(rel_path):
    try:
        result = ES.get(index=ES_MANIFEST_INDEX, id=rel_path)
        return result["_source"]["hash"]
    except Exception:
        return None

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

def delete_file(rel_path):
    t0 = time.time()
    PROP_GRAPH_INDEX.delete_ref_doc(rel_path, delete_from_docstore=False)
    ES.options(request_timeout=120).delete_by_query(
        index=ES_INDEX,
        body={"query": {"term": {"doc_id": rel_path}}},
        conflicts="proceed",
        refresh=True,
        allow_no_indices=True
    )
    try:
        ES.delete(index=ES_MANIFEST_INDEX, id=rel_path)
    except Exception:
        pass
    logger.info(f"🗑️ Deleted {rel_path} in {time.time()-t0:.2f}s")

def add_file(rel_path, new_hash):
    t0 = time.time()
    doc = load_doc(rel_path)
    nodes = split_doc_to_nodes(doc)
    PROP_GRAPH_INDEX.insert(doc)
    actions = []
    for node in nodes:
        embedding = Settings.embed_model.get_text_embedding(node.text)
        actions.append(to_es_action(node, doc, embedding))
    helpers.bulk(
        ES.options(request_timeout=120),
        actions,
        chunk_size=2000,
        raise_on_error=True
    )
    upsert_manifest(rel_path, new_hash)
    logger.info(f"➕ Added {rel_path} ({len(nodes)} chunks) in {time.time()-t0:.2f}s")

def process_file(rel_path):
    path = KNOWLEDGE_ROOT / rel_path
    if not path.is_relative_to(KNOWLEDGE_ROOT):
        raise ValueError(f"Path outside knowledge root: {rel_path}")
    current_hash = file_hash(path) if path.exists() else None
    stored_hash = get_manifest_hash(rel_path)
    if current_hash == stored_hash:
        logger.info(f"⏭️  Skipped {rel_path} (unchanged)")
        return
    if stored_hash:
        delete_file(rel_path)
    if current_hash:
        add_file(rel_path, current_hash)

def process_files():
    try:
        result = ES.search(
            index=ES_MANIFEST_INDEX,
            body={"query": {"match_all": {}}, "size": 10000, "_source": ["path"]}
        )
        manifest_paths = {hit["_source"]["path"] for hit in result["hits"]["hits"]}
    except Exception:
        manifest_paths = set()
    fs_files = {to_posix(p.relative_to(KNOWLEDGE_ROOT)) for p in KNOWLEDGE_ROOT.rglob("*") if p.is_file()}
    all_paths = list(manifest_paths | fs_files)
    if not all_paths:
        logger.info("📭 No files to process")
        return
    logger.info(f"📁 Processing {len(all_paths)} files")
    for rel_path in all_paths:
        try:
            process_file(rel_path)
        except Exception as e:
            logger.error(f"❌ {rel_path}: {e}")

def main():
    try:
        process_files()
    finally:
        ES.close()
        GRAPH_STORE.close()

if __name__ == "__main__":
    main()
