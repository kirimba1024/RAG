import json
from typing import Dict, List, Optional, Any
from tree_sitter import Parser

try:
    # новый, поддерживаемый пакет
    from tree_sitter_language_pack import get_language, get_parser
except ImportError:
    # запасной вариант (устаревший пакет)
    from tree_sitter_languages import get_language, get_parser  # type: ignore

# Поддерживаемые языки
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
    "cmd": "cmd",
    "bat": "cmd",
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
    "json": "json"
}

# Какие типы узлов считать «важными» для каждого языка
NODE_KINDS = {
    "python": {
        "import": ["import_statement", "import_from_statement"],
        "class":  ["class_definition"],
        "func":   ["function_definition"],
        "method": ["function_definition"],  # методы тоже function_definition внутри class
    },
    "java": {
        "import": ["import_declaration"],
        "class":  ["class_declaration"],
        "interface": ["interface_declaration"],
        "method": ["method_declaration", "constructor_declaration"],
    },
    "javascript": {
        "import": ["import_declaration"],
        "class":  ["class_declaration"],
        "func":   ["function_declaration"],
        "method": ["method_definition"],
    },
    "typescript": {
        "import": ["import_declaration"],
        "class":  ["class_declaration"],
        "func":   ["function_declaration"],
        "method": ["method_signature", "method_definition"],
        "interface": ["interface_declaration"],
    },
    "go": {
        "import": ["import_declaration"],
        "type":   ["type_declaration", "type_spec"],
        "func":   ["function_declaration", "method_declaration"],
    },
    "rust": {
        "import": ["use_declaration"],
        "struct": ["struct_item"],
        "enum":   ["enum_item"],
        "impl":   ["impl_item"],
        "func":   ["function_item"],
    },
    "csharp": {
        "import": ["using_directive"],
        "namespace": ["namespace_declaration"],
        "class":  ["class_declaration"],
        "interface": ["interface_declaration"],
        "struct": ["struct_declaration"],
        "method": ["method_declaration", "constructor_declaration"],
    },
    "php": {
        "import": ["use_declaration", "namespace_use_declaration"],
        "namespace": ["namespace_definition"],
        "class": ["class_declaration"],
        "interface": ["interface_declaration"],
        "method": ["method_declaration", "function_definition"],
    },
    "ruby": {
        "import": ["require", "require_relative"],
        "module": ["module"],
        "class": ["class"],
        "method": ["method", "singleton_method"],
    },
    "swift": {
        "import": ["import_declaration"],
        "class": ["class_declaration"],
        "struct": ["struct_declaration"],
        "func": ["function_declaration"],
        "method": ["function_declaration"],
    },
    "dart": {
        "import": ["import_directive"],
        "class": ["class_declaration"],
        "func": ["function_declaration"],
        "method": ["method_declaration"],
    },
    "lua": {
        "import": ["require"],
        "func": ["function_definition"],
        "local_func": ["local_function"],
    },
    "bash": {
        "func": ["function_definition"],
    },
    "haskell": {
        "import": ["import_declaration"],
        "module": ["module"],
        "type": ["type_declaration"],
        "class": ["class_declaration"],
        "func": ["function_declaration"],
    },
    "toml": {
        "section": ["table", "array_table"],
        "key": ["pair"],
    },
    "yaml": {
        "key": ["block_mapping_pair", "flow_mapping_pair"],
    },
    "xml": {
        "tag": ["element"],
    },
    "html": {
        "tag": ["element"],
    },
    "sql": {
        "func": ["function_call"],
        "table": ["table_name"],
    },
    "json": {
        "key": ["pair"],
    },
}

class ASTExtractor:
    def __init__(self):
        self.parsers: Dict[str, Parser] = {}
        self.languages: Dict[str, Any] = {}
        self._load_languages()

    def _load_languages(self):
        """Загружает парсеры для поддерживаемых языков"""
        for lang_key, ts_name in SUPPORTED_LANGUAGES.items():
            try:
                self.parsers[lang_key] = get_parser(ts_name)
                self.languages[lang_key] = get_language(ts_name)
            except Exception:
                # Если парсер недоступен, просто пропускаем
                continue

    def extract_ast_structure(self, code: str, language: str) -> str:
        """Извлекает AST структуру из кода для данного языка"""
        if not code.strip():
            return ""
        
        lang_key = self._get_language_key(language)
        if not lang_key or lang_key not in self.parsers:
            # Fallback: общий обход дерева
            return self._generic_tree_walk(code)
        
        try:
            return self._extract_with_tree_sitter(code, lang_key)
        except Exception:
            # Если что-то пошло не так, используем общий обход
            return self._generic_tree_walk(code)

    def _get_language_key(self, language: str) -> Optional[str]:
        """Преобразует название языка в ключ для поиска парсера"""
        lang_lower = language.lower().lstrip(".")
        return lang_lower if lang_lower in SUPPORTED_LANGUAGES else None

    def _extract_with_tree_sitter(self, code: str, lang_key: str) -> str:
        """Извлечение структуры с помощью Tree-sitter"""
        parser = self.parsers[lang_key]
        tree = parser.parse(code.encode("utf8"))
        root = tree.root_node
        kinds = NODE_KINDS.get(lang_key, {})
        by_kind: Dict[str, List[Dict[str, Any]]] = {}

        def node_text(n):
            """Извлекает текст узла"""
            b = n.start_byte
            e = n.end_byte
            return code.encode("utf8")[b:e].decode("utf8", errors="ignore")

        def name_of(n):
            """Извлекает имя узла"""
            # Многие грамматики используют поле 'name'
            for field in ("name", "identifier", "value"):
                child = n.child_by_field_name(field)
                if child:
                    return node_text(child)
            
            # Иногда имя — первый идентификатор внутри
            for ch in n.children:
                if ch.type in ("identifier", "type_identifier", "property_identifier", "shorthand_property_identifier"):
                    return node_text(ch)
            
            # Для некоторых узлов имя может быть в тексте самого узла
            if n.type in ("identifier", "type_identifier"):
                return node_text(n)
            
            return None

        # Обход дерева без regex
        stack = [root]
        while stack:
            n = stack.pop()
            stack.extend(reversed(n.children))

            for bucket, types in kinds.items():
                if n.type in types:
                    entry = {"type": n.type, "name": name_of(n)}
                    
                    # Для методов добавляем имя класса-владельца
                    if bucket in ("method",) and n.parent:
                        p = n.parent
                        while p and p.type not in ("class_declaration", "class_definition"):
                            p = p.parent
                        if p:
                            entry["in_class"] = name_of(p)
                    
                    # Для Python: разделяем функции и методы
                    if lang_key == "python" and bucket == "func":
                        # Проверяем, находится ли функция внутри класса
                        p = n.parent
                        while p and p.type not in ("class_definition", "function_definition"):
                            p = p.parent
                        if p and p.type == "class_definition":
                            # Это метод класса
                            entry["in_class"] = name_of(p)
                            by_kind.setdefault("method", []).append(entry)
                        else:
                            # Это обычная функция
                            by_kind.setdefault("func", []).append(entry)
                    else:
                        by_kind.setdefault(bucket, []).append(entry)

        # Форматируем результат в читаемый вид
        return self._format_structure(lang_key, by_kind)

    def _format_structure(self, lang_key: str, by_kind: Dict[str, List[Dict[str, Any]]]) -> str:
        """Форматирует структуру в читаемый текст"""
        result = []
        
        # Импорты
        if "import" in by_kind:
            result.append("IMPORTS:")
            for item in by_kind["import"][:10]:  # Ограничиваем количество
                result.append(f"  {item['name'] or item['type']}")
        
        # Namespace/Module
        for ns_type in ["namespace", "module"]:
            if ns_type in by_kind:
                result.append(f"{ns_type.upper()}:")
                for item in by_kind[ns_type]:
                    result.append(f"  {item['name'] or item['type']}")
        
        # Классы
        if "class" in by_kind:
            result.append("CLASS:")
            for item in by_kind["class"]:
                result.append(f"  {item['name'] or item['type']}")
        
        # Интерфейсы
        if "interface" in by_kind:
            result.append("INTERFACE:")
            for item in by_kind["interface"]:
                result.append(f"  {item['name'] or item['type']}")
        
        # Структуры
        if "struct" in by_kind:
            result.append("STRUCT:")
            for item in by_kind["struct"]:
                result.append(f"  {item['name'] or item['type']}")
        
        # Типы
        if "type" in by_kind:
            result.append("TYPE:")
            for item in by_kind["type"]:
                result.append(f"  {item['name'] or item['type']}")
        
        # Функции (только те, что не в классах)
        if "func" in by_kind:
            result.append("FUNC:")
            for item in by_kind["func"]:
                # Показываем только функции, которые не являются методами
                if "in_class" not in item:
                    result.append(f"  {item['name'] or item['type']}")
        
        # Методы (функции внутри классов)
        if "method" in by_kind:
            result.append("METHOD:")
            for item in by_kind["method"]:
                line = f"  {item['name'] or item['type']}"
                if "in_class" in item:
                    line += f" (IN_CLASS: {item['in_class']})"
                result.append(line)
        
        # Локальные функции
        if "local_func" in by_kind:
            result.append("LOCAL_FUNC:")
            for item in by_kind["local_func"]:
                line = f"  {item['name'] or item['type']}"
                if "in_class" in item:
                    line += f" (IN_CLASS: {item['in_class']})"
                result.append(line)
        
        # Специальные элементы для разных языков
        if lang_key == "toml":
            if "section" in by_kind:
                result.append("SECTION:")
                for item in by_kind["section"]:
                    result.append(f"  {item['name'] or item['type']}")
        
        if lang_key in ["yaml", "json"]:
            if "key" in by_kind:
                result.append("KEY:")
                for item in by_kind["key"][:20]:  # Ограничиваем для больших файлов
                    result.append(f"  {item['name'] or item['type']}")
        
        if lang_key in ["xml", "html"]:
            if "tag" in by_kind:
                result.append("TAG:")
                for item in by_kind["tag"][:20]:
                    result.append(f"  {item['name'] or item['type']}")
        
        return "\n".join(result) if result else ""

    def _generic_tree_walk(self, code: str) -> str:
        """Fallback: общий обход дерева без специфичных правил"""
        for lang_key in ["python", "java", "javascript", "typescript", "go", "rust", "csharp", "php"]:
            if lang_key in self.parsers:
                try:
                    parser = self.parsers[lang_key]
                    tree = parser.parse(code.encode("utf8"))
                    root = tree.root_node
                    out = []
                    
                    def node_text(n):
                        b = n.start_byte
                        e = n.end_byte
                        return code.encode("utf8")[b:e].decode("utf8", errors="ignore")
                    
                    # Берем только верхний уровень
                    for ch in root.children[:50]:
                        nm = ch.child_by_field_name("name")
                        out.append({
                            "node_type": ch.type,
                            "name": node_text(nm) if nm else None
                        })
                    
                    if out:
                        result = []
                        result.append(f"GENERIC_{lang_key.upper()}:")
                        for item in out:
                            if item["name"]:
                                result.append(f"  {item['node_type']}: {item['name']}")
                            else:
                                result.append(f"  {item['node_type']}")
                        return "\n".join(result)
                except Exception:
                    continue
        
        return "No parser available"