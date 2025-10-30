import os
from pathlib import Path
import hashlib, base64
import logging
import re
import unicodedata
import requests
import subprocess
from dotenv import load_dotenv
from pathspec import PathSpec
from mask import SECRET_PATTERNS

load_dotenv()

def load_prompt(filepath):
    return Path(filepath).read_text(encoding="utf-8")

EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-m3")
RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-large")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-haiku-20240307")

ES_HOST = os.getenv("ES_HOST", "localhost")
ES_PORT = int(os.getenv("ES_PORT", "9200"))
ES_INDEX = os.getenv("ES_INDEX", "rag")
ES_MANIFEST_INDEX = os.getenv("ES_MANIFEST_INDEX", "manifest")
ES_URL = f"http://{ES_HOST}:{ES_PORT}"

SOURCEGRAPH_URL = os.getenv("SOURCEGRAPH_URL", "http://localhost:3080")
SOURCEGRAPH_TOKEN = os.getenv("SOURCEGRAPH_TOKEN", "")

REPOS_ROOT = Path("repos").resolve()

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

logger = setup_logging("utils")

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
IGNORE_SPEC = PathSpec.from_lines("gitwildmatch", IGNORE_FILE.read_text(encoding="utf-8").splitlines())

def is_ignored(rel_path: Path) -> bool:
    return IGNORE_SPEC.match_file(to_posix(rel_path))

EMOJI_MAP = [
    (['private key', 'pem', 'pgp', 'certificate'], '🔐'),
    (['password', 'passwd', 'pwd'], '🔑'),
    (['token', 'bearer', 'jwt'], '🎫'),
    (['api', 'key', 'secret'], '🗝️'),
    (['jdbc', 'mongodb', 'postgres', 'mysql', 'redis'], '🗄️'),
    (['aws', 'vault', 'keycloak'], '☁️'),
]

def classify_secret_type(pattern: str) -> str:
    pattern_lower = pattern.lower()
    for keywords, emoji in EMOJI_MAP:
        if any(k in pattern_lower for k in keywords):
            return emoji
    return '⚠️'

def check_secrets_in_text(text: str) -> list[dict]:
    findings = []
    for pat, _ in SECRET_PATTERNS:
        for match in pat.finditer(text):
            match_text = match.group(0)
            findings.append({
                'match': match_text if len(match_text) <= 120 else match_text[:120] + '...',
                'line': text[:match.start()].count('\n') + 1,
                'type': classify_secret_type(pat.pattern)
            })
    return findings