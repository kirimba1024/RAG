import json
from typing import Dict, Optional, Any
from tree_sitter import Parser

try:
    # Рекомендуемый современный пакет с готовыми грамматиками
    from tree_sitter_language_pack import get_language, get_parser
except ImportError:
    # Запасной вариант (аналогичный пакет; может быть устаревшим в вашей среде)
    from tree_sitter_languages import get_language, get_parser  # type: ignore

# Поддерживаемые языки (ключ -> имя грамматики в пакете)
SUPPORTED_LANGUAGES: Dict[str, str] = {
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
    "cmd": "bash",   # нет отдельной грамматики cmd.exe — опциональный маппинг
    "bat": "bash",   # как и выше
    "hs": "haskell",
    "toml": "toml",
    "sass": "sass",
    "scss": "scss",
    "jl": "julia",
    "ps1": "powershell",
    "sql": "sql",
    "yaml": "yaml",
    "yml": "yaml",
    "xml": "xml",
    "html": "html",
    "json": "json",
}

class ASTExtractor:
    """
    Универсальный извлекатель текстового представления AST (точнее CST Tree-sitter)
    без регулярных выражений. Возвращает S-expression дерева.
    """

    def __init__(self):
        self.parsers: Dict[str, Parser] = {}
        self.languages: Dict[str, Any] = {}
        self._load_languages()

    def _load_languages(self) -> None:
        """Загружает парсеры для поддерживаемых языков (мягко игнорируя отсутствующие)."""
        for lang_key, ts_name in SUPPORTED_LANGUAGES.items():
            try:
                self.parsers[lang_key] = get_parser(ts_name)
                self.languages[lang_key] = get_language(ts_name)
            except Exception:
                # Если конкретной грамматики нет в пакете/платформе — просто пропускаем
                continue

    def extract_ast_structure(self, code: str, language: str, format_type: str = "readable") -> str:
        """
        Возвращает строковое представление AST/CST.
        
        Args:
            code: Исходный код
            language: Язык программирования
            format_type: "sexp" для S-expression, "readable" для читаемого формата
        
        Если указанный язык недоступен, выполняется «наилучший доступный» парсинг
        первым попавшимся парсером (может дать дерево с ERROR-узлами) — либо пустая строка.
        """
        if not code or not code.strip():
            return ""

        lang_key = self._get_language_key(language)
        if lang_key and lang_key in self.parsers:
            try:
                if format_type == "sexp":
                    return self._to_sexp(self.parsers[lang_key], code)
                else:
                    return self._to_readable(self.parsers[lang_key], code)
            except Exception:
                # Падать не хотим: попробуем общий путь ниже
                pass

        # Fallback: пробуем любые доступные парсеры (на случай неизвестного/неподдержанного языка)
        return self._generic_best_effort(code, format_type)

    def _get_language_key(self, language: str) -> Optional[str]:
        """Преобразует название/расширение в ключ ('.py' -> 'python', 'Python' -> 'python')."""
        key = language.lower().lstrip(".")
        return key if key in SUPPORTED_LANGUAGES else None

    @staticmethod
    def _to_sexp(parser: Parser, code: str) -> str:
        """
        Возвращает S-expression всего дерева.
        Новые биндинги печатают S-expr через str(node); старые — через node.sexp().
        Делаем совместимо с обеими версиями.
        """
        tree = parser.parse(code.encode("utf8"))
        root = tree.root_node
        # Предпочтём современный путь, но гарантируем совместимость
        try:
            s = str(root)
            # В большинстве актуальных версий это уже S-expression
            if "(" in s and ")" in s:
                return s
        except Exception:
            pass
        # Старые биндинги или непредвиденные случаи
        try:
            return root.sexp()  # type: ignore[attr-defined]
        except Exception:
            return ""

    def _generic_best_effort(self, code: str) -> str:
        """Пытается распарсить код любым доступным парсером и вернуть дерево; иначе пустая строка."""
        for parser in self.parsers.values():
            try:
                s = self._to_sexp(parser, code)
                if s:
                    return s
            except Exception:
                continue
        return ""

    def outline_short(self, code: str, language: str, limit: int = 120) -> str:
        """
        Короткий универсальный outline: import/class/interface/struct/enum/func + методы классов.
        Без regex. Если язык не найден — пробует любой доступный парсер.
        """
        if not code.strip():
            return ""

        key = self._get_language_key(language) or ""
        parser = self.parsers.get(key) or (next(iter(self.parsers.values()), None))
        if not parser:
            return ""

        tree = parser.parse(code.encode("utf8"))
        root = tree.root_node
        buf = code.encode("utf8")

        def text(n):
            return buf[n.start_byte:n.end_byte].decode("utf8", "ignore")

        def name(n):
            for fld in ("name", "identifier"):
                c = n.child_by_field_name(fld)
                if c:
                    return text(c)
            for ch in n.children:
                if "identifier" in ch.type or ch.type.endswith("_identifier"):
                    return text(ch)
            if n.type in ("identifier", "type_identifier"):
                return text(n)
            return None

        out = []

        # 1) верхний уровень
        for n in root.children:
            t, nm = n.type, name(n)
            if "import" in t or t in ("using_directive", "use_declaration", "namespace_use_declaration"):
                out.append(f"import {nm or '…'}")
            elif "class" in t and nm:
                out.append(f"class {nm}")
            elif "interface" in t and nm:
                out.append(f"interface {nm}")
            elif "struct" in t and nm:
                out.append(f"struct {nm}")
            elif "enum" in t and nm:
                out.append(f"enum {nm}")
            elif "function" in t and nm:
                out.append(f"func {nm}()")

        # 2) методы внутри классов (короткий глубокий обход)
        def collect_methods(cls):
            cname = name(cls) or "<?>"
            stack = [cls]
            while stack:
                cur = stack.pop()
                for ch in cur.children:
                    tt, nm2 = ch.type, name(ch)
                    if nm2 and ("method" in tt or "function" in tt):
                        out.append(f"method {cname}.{nm2}()")
                    stack.append(ch)

        for n in root.children:
            if "class" in n.type:
                collect_methods(n)

        # dedupe + лимит
        seen, uniq = set(), []
        for ln in out:
            if ln not in seen:
                uniq.append(ln); seen.add(ln)
            if len(uniq) >= limit:
                break

        # если совсем пусто — компактный s-expression
        if not uniq:
            try:
                return str(root)[:4000]
            except Exception:
                try:
                    return root.sexp()[:4000]  # type: ignore[attr-defined]
                except Exception:
                    return ""

        return "\n".join(uniq)


if __name__ == "__main__":
    # Небольшой CLI для быстрого теста:
    import sys
    if len(sys.argv) < 3:
        print("Usage: python ast_extractor.py <language> <path-to-source-file>")
        sys.exit(1)
    lang = sys.argv[1]
    path = sys.argv[2]
    with open(path, "r", encoding="utf-8") as f:
        code_text = f.read()
    extractor = ASTExtractor()
    print(extractor.extract_ast_structure(code_text, lang))