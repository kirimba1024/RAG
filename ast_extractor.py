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
    "haskell": "haskell",
    "toml": "toml",
    "sass": "sass",
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

    def list_entity_names_grouped(self, code: str, language: str, limit_per_type: int = 200) -> str:
        """
        Группирует имена сущностей по точному node.type из Tree-sitter.
        Имя берём только из полей 'name' или 'identifier' самого узла (никаких глубоких сканов).
        Возвращает JSON: {"class_declaration":[...], "method_declaration":[...], ...}
        """
        if not code.strip():
            return json.dumps({})

        key = self._get_language_key(language) or ""
        parser = self.parsers.get(key) or (next(iter(self.parsers.values()), None))
        if not parser:
            return json.dumps({})

        buf = code.encode("utf8")
        root = parser.parse(buf).root_node
        def tx(n): return buf[n.start_byte:n.end_byte].decode("utf8", "ignore")

        def own_name(n):
            # только поля текущего узла — никакой «унификации»
            c = n.child_by_field_name("name") or n.child_by_field_name("identifier")
            return tx(c) if c else None

        groups: dict[str, list] = {}
        seen: dict[str, set] = {}
        stack = [root]
        while stack:
            n = stack.pop()
            nm = own_name(n)
            if nm:
                t = n.type
                if t not in groups:
                    groups[t], seen[t] = [], set()
                if nm not in seen[t] and len(groups[t]) < limit_per_type:
                    groups[t].append(nm)
                    seen[t].add(nm)
            # обычный DFS
            stack.extend(reversed(n.children))

        return json.dumps(groups, ensure_ascii=False, separators=(",",":"))

    def outline_short(self, code: str, language: str, limit: int = 120) -> str:
        """
        Короткий outline через list_entity_names_grouped.
        """
        groups_json = self.list_entity_names_grouped(code, language, limit)
        groups = json.loads(groups_json)
        
        out = []
        # Приоритетные типы для отображения
        priority_types = [
            "class_declaration", "interface_declaration", "struct_declaration",
            "function_declaration", "method_declaration", "constructor_declaration",
            "namespace_declaration", "module_declaration", "package_declaration",
            "using_directive", "import_declaration", "use_declaration"
        ]
        
        for t in priority_types:
            if t in groups and groups[t]:
                for name in groups[t][:10]:  # Ограничиваем количество
                    if t in ["method_declaration", "constructor_declaration"]:
                        out.append(f"method {name}()")
                    elif t in ["function_declaration"]:
                        out.append(f"func {name}()")
                    elif t in ["using_directive", "import_declaration", "use_declaration"]:
                        out.append(f"import {name}")
                    else:
                        out.append(f"{t.replace('_declaration', '')} {name}")
        
        # Добавляем остальные типы
        for t, names in groups.items():
            if t not in priority_types and names:
                for name in names[:5]:  # Меньше для остальных типов
                    out.append(f"{t.replace('_declaration', '')} {name}")
        
        return "\n".join(out[:limit])


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