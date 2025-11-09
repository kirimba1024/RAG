import base64
import hashlib
import logging
import os
import re
import unicodedata
from pathlib import Path
from io import BytesIO

import docker
import fitz
import pandas as pd
import pytesseract
from PIL import Image
from docx import Document as DocxDocument
from pptx import Presentation
from dotenv import load_dotenv
from pathspec import PathSpec
from llama_index.readers.file import UnstructuredReader

load_dotenv()

def load_prompt(filepath):
    return Path(filepath).read_text(encoding="utf-8")

EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-m3")
RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-large")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-haiku-20240307")

ES_HOST = os.getenv("ES_HOST", "localhost")
ES_PORT = int(os.getenv("ES_PORT", "9200"))
ES_INDEX_CHUNKS = os.getenv("ES_INDEX_CHUNKS", "chunks")
ES_URL = f"http://{ES_HOST}:{ES_PORT}"

SANDBOX_CONTAINER_NAME = os.getenv("SANDBOX_CONTAINER_NAME", "rag-assistant-rag-sandbox-1")
ELASTICSEARCH_CONTAINER_NAME = os.getenv("ELASTICSEARCH_CONTAINER_NAME", "rag-assistant-elasticsearch-1")

REPOS_ROOT = Path("repos").resolve()
REPOS_SAFE_ROOT = Path("repos_safe").resolve()

LANG_BY_EXT = {
    ".py": "python", ".js": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "tsx",
    ".java": "java", ".kt": "kotlin",
    ".go": "go", ".rs": "rust",
    ".c": "c", ".h": "c",
    ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp", ".hh": "cpp",
    ".cs": "csharp", ".php": "php", ".rb": "ruby", ".swift": "swift",
    ".scala": "scala", ".groovy": "groovy", ".m": "objective_c", ".mm": "objective_cpp",
    ".sh": "bash", ".bash": "bash", ".zsh": "bash",
    ".cmd": "bash", ".bat": "bash",
    ".r": "r", ".lua": "lua",
    ".hs": "haskell",
    ".toml": "toml",
    ".sass": "sass", ".scss": "scss",
    ".jl": "julia",
    ".ps1": "powershell",
    ".sql": "sql", ".yaml": "yaml", ".yml": "yaml",
    ".xml": "xml", ".html": "html", ".htm": "html",
    ".json": "json",
}

def setup_logging(name: str, file: bool = True) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    if file:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        fh = logging.FileHandler(log_dir / f"{name}.log", encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    logger.propagate = False
    return logger

def message_for_log(text: str, max_size = 256) -> str:
    text = text.strip().replace("\n", " ").replace("\r", " ").replace("\t", " ")
    if len(text) <= max_size:
        return text
    half_size = max_size // 2
    return text[:half_size] + "..." + text[-half_size:]

def short_hash(s: str) -> str:
    d = hashlib.blake2s(s.encode(), digest_size=8).digest()
    return base64.urlsafe_b64encode(d).decode().rstrip("=")

def to_posix(p: str | Path) -> str:
    s = str(p).replace("\\", "/")
    while "//" in s:
        s = s.replace("//", "/")
    if s.startswith("./"):
        s = s[2:]
    return s

def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[\u200b\u200e\u200f\u202a-\u202e]", "", text)
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = re.sub(r"\s*\n\s*", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()

def file_hash(path, algo="sha256"):
    with open(path, "rb") as f:
        return hashlib.file_digest(f, algo).hexdigest()

IGNORE_FILE = Path(".ignore")
if not IGNORE_FILE.exists():
    raise FileNotFoundError(f"Файл .ignore не найден в {IGNORE_FILE.resolve()}")
IGNORE_SPEC = PathSpec.from_lines("gitwildmatch", IGNORE_FILE.read_text(encoding="utf-8").splitlines())

def is_ignored(rel_path: str) -> bool:
    return IGNORE_SPEC.match_file(rel_path)

def git_blob_oid(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()

def extract_binary_content(path: Path):
    with open(path, "rb") as f:
        file_bytes = f.read()
    ext = path.suffix.lower()
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

def execute_command(command: str) -> str:
    client = docker.from_env()
    container = client.containers.get(SANDBOX_CONTAINER_NAME)
    result = container.exec_run(
        cmd=["timeout", "30", "sh", "-c", command],
        user="nobody"
    )
    return result.output.decode('utf-8')
