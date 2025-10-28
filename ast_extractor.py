from tree_sitter_language_pack import get_language, get_parser

SUPPORTED_LANGUAGES = {
    "java": "java",
    "python": "python",
    "javascript": "javascript",
    "typescript": "typescript",
    "kotlin": "kotlin",
    "scala": "scala",
    "groovy": "groovy",
    "cpp": "cpp",
    "csharp": "csharp",
    "go": "go",
    "rust": "rust",
    "php": "php",
    "ruby": "ruby",
    "swift": "swift",
    "dart": "dart",
    "r": "r",
    "lua": "lua",
    "bash": "bash",
    "sh": "bash",
    "zsh": "bash",
    "cmd": "bash",
    "bat": "bash",
    "hs": "haskell",
    "haskell": "haskell",
    "toml": "toml",
    "scss": "scss",
    "jl": "julia",
    "julia": "julia",
    "ps1": "powershell",
    "powershell": "powershell",
    "sql": "sql",
    "yaml": "yaml",
    "yml": "yaml",
    "xml": "xml",
    "html": "html",
    "json": "json",
}

class ASTExtractor:

    def __init__(self):
        self.parsers = {}
        self.languages = {}
        self._load_languages()

    def _load_languages(self) -> None:
        for lang_key, ts_name in SUPPORTED_LANGUAGES.items():
            self.parsers[lang_key] = get_parser(ts_name)
            self.languages[lang_key] = get_language(ts_name)

    def _get_language_key(self, language: str) -> str:
        key = language.lower().lstrip(".")
        if key not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {language}")
        return key