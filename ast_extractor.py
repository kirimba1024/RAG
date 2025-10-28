from tree_sitter_language_pack import get_language, get_parser
from pathlib import Path
from utils import setup_logging, TREE_SITTER_NAMES

logger = setup_logging(Path(__file__).stem)

class ASTExtractor:

    def __init__(self):
        self.parsers = {}
        self.languages = {}
        self._load_languages()

    def _load_languages(self) -> None:
        for lang_key, ts_name in TREE_SITTER_NAMES.items():
            try:
                self.parsers[lang_key] = get_parser(ts_name)
                self.languages[lang_key] = get_language(ts_name)
            except Exception as e:
                logger.warning(f"Failed to load language {lang_key} ({ts_name}): {e}")