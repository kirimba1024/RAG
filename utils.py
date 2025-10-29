import os
from pathlib import Path
import hashlib, base64
import logging
import re
import unicodedata
from dotenv import load_dotenv

load_dotenv()

def load_prompt(filepath):
    return Path(filepath).read_text(encoding="utf-8")

EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-m3")
RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-large")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-haiku-20240307")

NEO4J_HOST = os.getenv("NEO4J_HOST", "localhost")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASS", "neo4jpass")
NEO4J_BOLT_PORT = os.getenv("NEO4J_BOLT_PORT", "7687")
NEO4J_BOLT_URL = f"bolt://{NEO4J_HOST}:{NEO4J_BOLT_PORT}"

ES_HOST = os.getenv("ES_HOST", "localhost")
ES_PORT = int(os.getenv("ES_PORT", "9200"))
ES_INDEX = os.getenv("ES_INDEX", "rag")
ES_MANIFEST_INDEX = os.getenv("ES_MANIFEST_INDEX", "manifest")
ES_URL = f"http://{ES_HOST}:{ES_PORT}"

KNOWLEDGE_ROOT = Path("knowledge").resolve()

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

def setup_logging(name: str) -> logging.Logger:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
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


def calc_hash(data) -> str:
    if isinstance(data, (bytes, bytearray, memoryview)):
        b = bytes(data)
    else:
        b = str(data).encode("utf-8", errors="ignore")
    return hashlib.sha256(b).hexdigest()

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
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[\u200b\u200e\u200f\u202a-\u202e]", "", text)
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = re.sub(r"\s*\n\s*", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()

def file_hash(path, algo="sha256"):
    import hashlib
    with open(path, "rb") as f:
        return hashlib.file_digest(f, algo).hexdigest()