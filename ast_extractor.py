import tree_sitter
from tree_sitter import Language, Parser
from pathlib import Path
from typing import Dict, List, Optional, Any
import json

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
    "csharp": "c_sharp",
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
    "html": "html"
}

class ASTExtractor:
    def __init__(self):
        self.parsers = {}
        self._load_languages()
    
    def _load_languages(self):
        """Загружает парсеры для поддерживаемых языков"""
        try:
            # Попытка загрузить tree-sitter языки
            for lang_name, tree_sitter_name in SUPPORTED_LANGUAGES.items():
                try:
                    # Здесь нужно будет установить соответствующие языки
                    # Пока создаем заглушки
                    self.parsers[lang_name] = None
                except Exception:
                    continue
        except Exception:
            pass
    
    def extract_ast_structure(self, code: str, language: str) -> str:
        """Извлекает AST структуру из кода"""
        if not code.strip():
            return ""
        
        lang_key = self._get_language_key(language)
        if not lang_key or lang_key not in self.parsers:
            return self._fallback_extraction(code, language)
        
        try:
            return self._extract_with_tree_sitter(code, lang_key)
        except Exception:
            return self._fallback_extraction(code, language)
    
    def _get_language_key(self, language: str) -> Optional[str]:
        """Определяет ключ языка из расширения или имени"""
        lang_lower = language.lower()
        for key in SUPPORTED_LANGUAGES:
            if lang_lower in [key, f".{key}"]:
                return key
        return None
    
    def _extract_with_tree_sitter(self, code: str, language: str) -> str:
        """Извлечение с помощью tree-sitter"""
        # TODO: Реализовать когда установим tree-sitter языки
        return self._fallback_extraction(code, language)
    
    def _fallback_extraction(self, code: str, language: str) -> str:
        """Fallback извлечение через простые паттерны"""
        if language in ["java", "kotlin", "scala", "groovy"]:
            return self._extract_java_like(code)
        elif language in ["python"]:
            return self._extract_python_like(code)
        elif language in ["javascript", "typescript"]:
            return self._extract_js_like(code)
        elif language in ["cpp"]:
            return self._extract_cpp_like(code)
        elif language in ["csharp"]:
            return self._extract_csharp_like(code)
        elif language in ["go", "rust"]:
            return self._extract_go_rust_like(code)
        elif language in ["php"]:
            return self._extract_php_like(code)
        elif language in ["ruby"]:
            return self._extract_ruby_like(code)
        elif language in ["swift"]:
            return self._extract_swift_like(code)
        elif language in ["dart"]:
            return self._extract_dart_like(code)
        elif language in ["r"]:
            return self._extract_r_like(code)
        elif language in ["lua"]:
            return self._extract_lua_like(code)
        elif language in ["bash", "sh", "zsh"]:
            return self._extract_shell_like(code)
        elif language in ["cmd", "bat"]:
            return self._extract_cmd_like(code)
        elif language in ["haskell"]:
            return self._extract_haskell_like(code)
        elif language in ["toml"]:
            return self._extract_toml_like(code)
        elif language in ["sass", "scss"]:
            return self._extract_sass_like(code)
        elif language in ["julia"]:
            return self._extract_julia_like(code)
        elif language in ["powershell"]:
            return self._extract_powershell_like(code)
        elif language in ["yaml", "xml", "html"]:
            return self._extract_markup_like(code, language)
        else:
            return self._extract_generic(code)
    
    def _extract_java_like(self, code: str) -> str:
        """Извлечение для Java-подобных языков"""
        lines = code.split('\n')
        structure = []
        current_class = None
        current_method = None
        imports = []
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('//'):
                continue
                
            # Импорты
            if line.startswith('import '):
                imports.append(line)
            
            # Классы
            elif 'class ' in line and '{' in line:
                class_name = self._extract_class_name(line)
                if class_name:
                    current_class = class_name
                    extends = self._extract_extends(line)
                    implements = self._extract_implements(line)
                    structure.append(f"CLASS: {class_name}")
                    if extends:
                        structure.append(f"  EXTENDS: {extends}")
                    if implements:
                        structure.append(f"  IMPLEMENTS: {implements}")
            
            # Интерфейсы
            elif 'interface ' in line and '{' in line:
                interface_name = self._extract_interface_name(line)
                if interface_name:
                    structure.append(f"INTERFACE: {interface_name}")
            
            # Методы
            elif current_class and ('public ' in line or 'private ' in line or 'protected ' in line) and '(' in line and ')' in line:
                method_name = self._extract_method_name(line)
                if method_name:
                    current_method = method_name
                    return_type = self._extract_return_type(line)
                    structure.append(f"  METHOD: {method_name}")
                    if return_type:
                        structure.append(f"    RETURNS: {return_type}")
            
            # Вызовы методов
            elif current_method and '.' in line and '(' in line:
                calls = self._extract_method_calls(line)
                for call in calls:
                    structure.append(f"    CALLS: {call}")
        
        if imports:
            structure.insert(0, "IMPORTS:")
            for imp in imports[:10]:  # Ограничиваем количество
                structure.append(f"  {imp}")
        
        return '\n'.join(structure) if structure else ""
    
    def _extract_python_like(self, code: str) -> str:
        """Извлечение для Python"""
        lines = code.split('\n')
        structure = []
        current_class = None
        imports = []
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Импорты
            if line.startswith(('import ', 'from ')):
                imports.append(line)
            
            # Классы
            elif line.startswith('class '):
                class_name = self._extract_python_class_name(line)
                if class_name:
                    current_class = class_name
                    bases = self._extract_python_bases(line)
                    structure.append(f"CLASS: {class_name}")
                    if bases:
                        structure.append(f"  INHERITS: {bases}")
            
            # Функции
            elif line.startswith('def '):
                func_name = self._extract_python_function_name(line)
                if func_name:
                    structure.append(f"FUNCTION: {func_name}")
                    if current_class:
                        structure.append(f"  IN_CLASS: {current_class}")
            
            # Переменные класса
            elif current_class and '=' in line and not line.startswith(' '):
                var_name = self._extract_python_variable_name(line)
                if var_name:
                    structure.append(f"  VARIABLE: {var_name}")
        
        if imports:
            structure.insert(0, "IMPORTS:")
            for imp in imports[:10]:
                structure.append(f"  {imp}")
        
        return '\n'.join(structure) if structure else ""
    
    def _extract_js_like(self, code: str) -> str:
        """Извлечение для JavaScript/TypeScript"""
        lines = code.split('\n')
        structure = []
        imports = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('//'):
                continue
            
            # Импорты
            if line.startswith(('import ', 'const ', 'let ', 'var ')) and 'from ' in line:
                imports.append(line)
            
            # Классы
            elif 'class ' in line:
                class_name = self._extract_js_class_name(line)
                if class_name:
                    structure.append(f"CLASS: {class_name}")
            
            # Функции
            elif line.startswith(('function ', 'const ', 'let ', 'var ')) and '(' in line:
                func_name = self._extract_js_function_name(line)
                if func_name:
                    structure.append(f"FUNCTION: {func_name}")
        
        if imports:
            structure.insert(0, "IMPORTS:")
            for imp in imports[:10]:
                structure.append(f"  {imp}")
        
        return '\n'.join(structure) if structure else ""
    
    def _extract_cpp_like(self, code: str) -> str:
        """Извлечение для C++/C#"""
        lines = code.split('\n')
        structure = []
        imports = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('//'):
                continue
            
            # Включения
            if line.startswith('#include') or line.startswith('using '):
                imports.append(line)
            
            # Классы
            elif 'class ' in line and '{' in line:
                class_name = self._extract_cpp_class_name(line)
                if class_name:
                    structure.append(f"CLASS: {class_name}")
            
            # Функции
            elif ('(' in line and ')' in line and 
                  ('void ' in line or 'int ' in line or 'string ' in line or 'bool ' in line)):
                func_name = self._extract_cpp_function_name(line)
                if func_name:
                    structure.append(f"FUNCTION: {func_name}")
        
        if imports:
            structure.insert(0, "INCLUDES:")
            for imp in imports[:10]:
                structure.append(f"  {imp}")
        
        return '\n'.join(structure) if structure else ""
    
    def _extract_go_rust_like(self, code: str) -> str:
        """Извлечение для Go/Rust"""
        lines = code.split('\n')
        structure = []
        imports = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('//'):
                continue
            
            # Импорты
            if line.startswith(('import ', 'use ')):
                imports.append(line)
            
            # Структуры/типы
            elif ('struct ' in line or 'type ' in line) and '{' in line:
                type_name = self._extract_type_name(line)
                if type_name:
                    structure.append(f"TYPE: {type_name}")
            
            # Функции
            elif line.startswith(('func ', 'fn ')):
                func_name = self._extract_go_rust_function_name(line)
                if func_name:
                    structure.append(f"FUNCTION: {func_name}")
        
        if imports:
            structure.insert(0, "IMPORTS:")
            for imp in imports[:10]:
                structure.append(f"  {imp}")
        
        return '\n'.join(structure) if structure else ""
    
    def _extract_markup_like(self, code: str, language: str) -> str:
        """Извлечение для YAML/XML/HTML"""
        if language == "yaml":
            return self._extract_yaml_structure(code)
        elif language in ["xml", "html"]:
            return self._extract_xml_html_structure(code)
        return ""
    
    def _extract_yaml_structure(self, code: str) -> str:
        """Извлечение структуры YAML"""
        lines = code.split('\n')
        structure = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if ':' in line and not line.startswith('-'):
                key = line.split(':')[0].strip()
                structure.append(f"KEY: {key}")
        
        return '\n'.join(structure) if structure else ""
    
    def _extract_xml_html_structure(self, code: str) -> str:
        """Извлечение структуры XML/HTML"""
        lines = code.split('\n')
        structure = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('<!--'):
                continue
            
            if line.startswith('<') and '>' in line:
                tag = self._extract_tag_name(line)
                if tag:
                    structure.append(f"TAG: {tag}")
        
        return '\n'.join(structure) if structure else ""
    
    def _extract_generic(self, code: str) -> str:
        """Общее извлечение для неизвестных языков"""
        lines = code.split('\n')
        structure = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Ищем функции
            if '(' in line and ')' in line and not line.startswith('#'):
                func_name = self._extract_generic_function_name(line)
                if func_name:
                    structure.append(f"FUNCTION: {func_name}")
        
        return '\n'.join(structure) if structure else ""
    
    # Вспомогательные методы для извлечения имен
    def _extract_class_name(self, line: str) -> Optional[str]:
        """Извлекает имя класса из строки"""
        import re
        match = re.search(r'class\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_interface_name(self, line: str) -> Optional[str]:
        """Извлекает имя интерфейса"""
        import re
        match = re.search(r'interface\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_extends(self, line: str) -> Optional[str]:
        """Извлекает родительский класс"""
        import re
        match = re.search(r'extends\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_implements(self, line: str) -> Optional[str]:
        """Извлекает реализуемые интерфейсы"""
        import re
        match = re.search(r'implements\s+([^{]+)', line)
        return match.group(1).strip() if match else None
    
    def _extract_method_name(self, line: str) -> Optional[str]:
        """Извлекает имя метода"""
        import re
        match = re.search(r'(\w+)\s*\(', line)
        return match.group(1) if match else None
    
    def _extract_return_type(self, line: str) -> Optional[str]:
        """Извлекает тип возвращаемого значения"""
        import re
        match = re.search(r'(public|private|protected)\s+(\w+)', line)
        return match.group(2) if match else None
    
    def _extract_method_calls(self, line: str) -> List[str]:
        """Извлекает вызовы методов"""
        import re
        calls = re.findall(r'(\w+\.\w+)\s*\(', line)
        return calls
    
    def _extract_python_class_name(self, line: str) -> Optional[str]:
        """Извлекает имя класса Python"""
        import re
        match = re.search(r'class\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_python_bases(self, line: str) -> Optional[str]:
        """Извлекает базовые классы Python"""
        import re
        match = re.search(r'class\s+\w+\s*\(([^)]+)\)', line)
        return match.group(1).strip() if match else None
    
    def _extract_python_function_name(self, line: str) -> Optional[str]:
        """Извлекает имя функции Python"""
        import re
        match = re.search(r'def\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_python_variable_name(self, line: str) -> Optional[str]:
        """Извлекает имя переменной Python"""
        import re
        match = re.search(r'(\w+)\s*=', line)
        return match.group(1) if match else None
    
    def _extract_js_class_name(self, line: str) -> Optional[str]:
        """Извлекает имя класса JS/TS"""
        import re
        match = re.search(r'class\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_js_function_name(self, line: str) -> Optional[str]:
        """Извлекает имя функции JS/TS"""
        import re
        if line.startswith('function '):
            match = re.search(r'function\s+(\w+)', line)
        else:
            match = re.search(r'(?:const|let|var)\s+(\w+)\s*=', line)
        return match.group(1) if match else None
    
    def _extract_cpp_class_name(self, line: str) -> Optional[str]:
        """Извлекает имя класса C++/C#"""
        import re
        match = re.search(r'class\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_cpp_function_name(self, line: str) -> Optional[str]:
        """Извлекает имя функции C++/C#"""
        import re
        match = re.search(r'(\w+)\s*\(', line)
        return match.group(1) if match else None
    
    def _extract_type_name(self, line: str) -> Optional[str]:
        """Извлекает имя типа Go/Rust"""
        import re
        match = re.search(r'(?:struct|type)\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_go_rust_function_name(self, line: str) -> Optional[str]:
        """Извлекает имя функции Go/Rust"""
        import re
        match = re.search(r'(?:func|fn)\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_tag_name(self, line: str) -> Optional[str]:
        """Извлекает имя тега XML/HTML"""
        import re
        match = re.search(r'<(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_generic_function_name(self, line: str) -> Optional[str]:
        """Общее извлечение имени функции"""
        import re
        match = re.search(r'(\w+)\s*\(', line)
        return match.group(1) if match else None
    
    def _extract_php_like(self, code: str) -> str:
        """Извлечение для PHP"""
        lines = code.split('\n')
        structure = []
        imports = []
        current_class = None
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('//') or line.startswith('#'):
                continue
            
            # Импорты
            if line.startswith(('use ', 'require ', 'include ', 'require_once ', 'include_once ')):
                imports.append(line)
            
            # Namespace
            elif line.startswith('namespace '):
                namespace = self._extract_php_namespace(line)
                if namespace:
                    structure.append(f"NAMESPACE: {namespace}")
            
            # Классы (включая внутри namespace)
            elif 'class ' in line and ('{' in line or ':' in line):
                class_name = self._extract_php_class_name(line)
                if class_name:
                    current_class = class_name
                    extends = self._extract_php_extends(line)
                    implements = self._extract_php_implements(line)
                    structure.append(f"CLASS: {class_name}")
                    if extends:
                        structure.append(f"  EXTENDS: {extends}")
                    if implements:
                        structure.append(f"  IMPLEMENTS: {implements}")
            
            # Интерфейсы
            elif 'interface ' in line and '{' in line:
                interface_name = self._extract_php_interface_name(line)
                if interface_name:
                    structure.append(f"INTERFACE: {interface_name}")
            
            # Функции
            elif 'function ' in line and '(' in line:
                func_name = self._extract_php_function_name(line)
                if func_name:
                    structure.append(f"FUNCTION: {func_name}")
                    if current_class:
                        structure.append(f"  IN_CLASS: {current_class}")
        
        if imports:
            structure.insert(0, "IMPORTS:")
            for imp in imports[:10]:
                structure.append(f"  {imp}")
        
        return '\n'.join(structure) if structure else ""
    
    def _extract_ruby_like(self, code: str) -> str:
        """Извлечение для Ruby"""
        lines = code.split('\n')
        structure = []
        imports = []
        current_class = None
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Импорты
            if line.startswith(('require ', 'require_relative ', 'load ')):
                imports.append(line)
            
            # Классы
            elif line.startswith('class '):
                class_name = self._extract_ruby_class_name(line)
                if class_name:
                    current_class = class_name
                    inheritance = self._extract_ruby_inheritance(line)
                    structure.append(f"CLASS: {class_name}")
                    if inheritance:
                        structure.append(f"  INHERITS: {inheritance}")
            
            # Модули
            elif line.startswith('module '):
                module_name = self._extract_ruby_module_name(line)
                if module_name:
                    structure.append(f"MODULE: {module_name}")
            
            # Методы
            elif line.startswith('def '):
                method_name = self._extract_ruby_method_name(line)
                if method_name:
                    structure.append(f"METHOD: {method_name}")
                    if current_class:
                        structure.append(f"  IN_CLASS: {current_class}")
        
        if imports:
            structure.insert(0, "IMPORTS:")
            for imp in imports[:10]:
                structure.append(f"  {imp}")
        
        return '\n'.join(structure) if structure else ""
    
    def _extract_r_like(self, code: str) -> str:
        """Извлечение для R"""
        lines = code.split('\n')
        structure = []
        imports = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Импорты
            if line.startswith(('library(', 'require(', 'source(')):
                imports.append(line)
            
            # Функции
            elif 'function(' in line or 'function (' in line:
                func_name = self._extract_r_function_name(line)
                if func_name:
                    structure.append(f"FUNCTION: {func_name}")
            
            # Переменные
            elif '<-' in line or '=' in line:
                var_name = self._extract_r_variable_name(line)
                if var_name:
                    structure.append(f"VARIABLE: {var_name}")
        
        if imports:
            structure.insert(0, "IMPORTS:")
            for imp in imports[:10]:
                structure.append(f"  {imp}")
        
        return '\n'.join(structure) if structure else ""
    
    def _extract_lua_like(self, code: str) -> str:
        """Извлечение для Lua"""
        lines = code.split('\n')
        structure = []
        imports = []
        current_module = None
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('--'):
                continue
            
            # Импорты
            if line.startswith('require('):
                imports.append(line)
            
            # Модули (module() или таблицы как модули)
            elif line.startswith('module(') or (line.startswith('local ') and '=' in line and '{' in line):
                if line.startswith('module('):
                    module_name = self._extract_lua_module_name(line)
                else:
                    module_name = self._extract_lua_table_name(line)
                if module_name:
                    current_module = module_name
                    structure.append(f"MODULE: {module_name}")
            
            # Функции
            elif line.startswith('function '):
                func_name = self._extract_lua_function_name(line)
                if func_name:
                    structure.append(f"FUNCTION: {func_name}")
                    if current_module:
                        structure.append(f"  IN_MODULE: {current_module}")
            
            # Локальные функции
            elif 'local function ' in line:
                func_name = self._extract_lua_local_function_name(line)
                if func_name:
                    structure.append(f"LOCAL_FUNCTION: {func_name}")
                    if current_module:
                        structure.append(f"  IN_MODULE: {current_module}")
            
            # Таблицы
            elif line.startswith('local ') and '=' in line and '{' in line:
                table_name = self._extract_lua_table_name(line)
                if table_name:
                    structure.append(f"TABLE: {table_name}")
                    if current_module:
                        structure.append(f"  IN_MODULE: {current_module}")
        
        if imports:
            structure.insert(0, "IMPORTS:")
            for imp in imports[:10]:
                structure.append(f"  {imp}")
        
        return '\n'.join(structure) if structure else ""
    
    def _extract_shell_like(self, code: str) -> str:
        """Извлечение для Shell/Bash/Zsh"""
        lines = code.split('\n')
        structure = []
        imports = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Импорты
            if line.startswith(('source ', '. ', 'export ')):
                imports.append(line)
            
            # Функции
            elif line.startswith(('function ', 'function_')) or ('()' in line and '{' in line):
                func_name = self._extract_shell_function_name(line)
                if func_name:
                    structure.append(f"FUNCTION: {func_name}")
        
        if imports:
            structure.insert(0, "IMPORTS:")
            for imp in imports[:10]:
                structure.append(f"  {imp}")
        
        return '\n'.join(structure) if structure else ""
    
    def _extract_cmd_like(self, code: str) -> str:
        """Извлечение для CMD/BAT"""
        lines = code.split('\n')
        structure = []
        imports = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('REM ') or line.startswith('::'):
                continue
            
            # Импорты
            if line.startswith(('call ', '@call ', 'start ')):
                imports.append(line)
            
            # Метки
            elif line.startswith(':') and not line.startswith('::'):
                label_name = self._extract_cmd_label_name(line)
                if label_name:
                    structure.append(f"LABEL: {label_name}")
        
        if imports:
            structure.insert(0, "CALLS:")
            for imp in imports[:10]:
                structure.append(f"  {imp}")
        
        return '\n'.join(structure) if structure else ""
    
    # Вспомогательные методы для новых языков
    def _extract_php_class_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'class\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_php_extends(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'extends\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_php_implements(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'implements\s+([^{]+)', line)
        return match.group(1).strip() if match else None
    
    def _extract_php_interface_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'interface\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_php_function_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'function\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_php_namespace(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'namespace\s+([^;]+)', line)
        return match.group(1).strip() if match else None
    
    def _extract_ruby_class_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'class\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_ruby_inheritance(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'class\s+\w+\s*<\s*(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_ruby_module_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'module\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_ruby_method_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'def\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_r_function_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'(\w+)\s*<-\s*function', line)
        return match.group(1) if match else None
    
    def _extract_r_variable_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'(\w+)\s*[<\-=]', line)
        return match.group(1) if match else None
    
    def _extract_lua_function_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'function\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_lua_local_function_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'local\s+function\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_lua_module_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'module\s*\(\s*["\'](\w+)["\']', line)
        return match.group(1) if match else None
    
    def _extract_lua_table_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'local\s+(\w+)\s*=', line)
        return match.group(1) if match else None
    
    def _extract_shell_function_name(self, line: str) -> Optional[str]:
        import re
        if line.startswith('function '):
            match = re.search(r'function\s+(\w+)', line)
        else:
            match = re.search(r'(\w+)\s*\(\)', line)
        return match.group(1) if match else None
    
    def _extract_cmd_label_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r':(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_haskell_like(self, code: str) -> str:
        """Извлечение для Haskell"""
        lines = code.split('\n')
        structure = []
        imports = []
        current_module = None
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('--'):
                continue
            
            # Импорты
            if line.startswith('import '):
                imports.append(line)
            
            # Модули
            elif line.startswith('module '):
                module_name = self._extract_haskell_module_name(line)
                if module_name:
                    current_module = module_name
                    structure.append(f"MODULE: {module_name}")
            
            # Типы данных
            elif line.startswith('data ') or line.startswith('newtype '):
                type_name = self._extract_haskell_type_name(line)
                if type_name:
                    structure.append(f"TYPE: {type_name}")
            
            # Классы типов
            elif line.startswith('class '):
                class_name = self._extract_haskell_class_name(line)
                if class_name:
                    structure.append(f"CLASS: {class_name}")
            
            # Функции
            elif '::' in line and '=' in line:
                func_name = self._extract_haskell_function_name(line)
                if func_name:
                    structure.append(f"FUNCTION: {func_name}")
        
        if imports:
            structure.insert(0, "IMPORTS:")
            for imp in imports[:10]:
                structure.append(f"  {imp}")
        
        return '\n'.join(structure) if structure else ""
    
    def _extract_toml_like(self, code: str) -> str:
        """Извлечение для TOML"""
        lines = code.split('\n')
        structure = []
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Секции
            if line.startswith('[') and line.endswith(']'):
                section_name = line[1:-1]
                current_section = section_name
                structure.append(f"SECTION: {section_name}")
            
            # Ключи
            elif '=' in line and current_section:
                key = line.split('=')[0].strip()
                structure.append(f"  KEY: {key}")
        
        return '\n'.join(structure) if structure else ""
    
    def _extract_sass_like(self, code: str) -> str:
        """Извлечение для Sass/SCSS"""
        lines = code.split('\n')
        structure = []
        current_selector = None
        imports = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('//') or line.startswith('/*'):
                continue
            
            # Импорты
            if line.startswith('@import ') or line.startswith('@use '):
                imports.append(line)
            
            # Селекторы (SCSS и SASS)
            elif (line.startswith('.') or line.startswith('#') or line.startswith('@') or 
                  line.startswith('&') or line.startswith('*') or 
                  (not line.startswith('@') and ':' in line and not line.startswith(' '))):
                selector = self._extract_sass_selector(line)
                if selector:
                    current_selector = selector
                    structure.append(f"SELECTOR: {selector}")
            
            # Миксины (SCSS @mixin или SASS =)
            elif line.startswith('@mixin ') or line.startswith('='):
                if line.startswith('@mixin '):
                    mixin_name = self._extract_sass_mixin_name(line)
                else:
                    mixin_name = self._extract_sass_sass_mixin_name(line)
                if mixin_name:
                    structure.append(f"MIXIN: {mixin_name}")
            
            # Функции
            elif line.startswith('@function '):
                func_name = self._extract_sass_function_name(line)
                if func_name:
                    structure.append(f"FUNCTION: {func_name}")
            
            # Переменные
            elif line.startswith('$'):
                var_name = self._extract_sass_variable_name(line)
                if var_name:
                    structure.append(f"VARIABLE: {var_name}")
            
            # Вложенные селекторы (SASS)
            elif line.startswith('  ') and (line.strip().startswith('.') or line.strip().startswith('#') or line.strip().startswith('&')):
                selector = self._extract_sass_selector(line.strip())
                if selector:
                    structure.append(f"  NESTED_SELECTOR: {selector}")
        
        if imports:
            structure.insert(0, "IMPORTS:")
            for imp in imports[:10]:
                structure.append(f"  {imp}")
        
        return '\n'.join(structure) if structure else ""
    
    def _extract_julia_like(self, code: str) -> str:
        """Извлечение для Julia"""
        lines = code.split('\n')
        structure = []
        imports = []
        current_module = None
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Импорты
            if line.startswith(('using ', 'import ')):
                imports.append(line)
            
            # Модули
            elif line.startswith('module '):
                module_name = self._extract_julia_module_name(line)
                if module_name:
                    current_module = module_name
                    structure.append(f"MODULE: {module_name}")
            
            # Структуры
            elif line.startswith('struct ') or line.startswith('mutable struct '):
                struct_name = self._extract_julia_struct_name(line)
                if struct_name:
                    structure.append(f"STRUCT: {struct_name}")
            
            # Функции
            elif line.startswith('function '):
                func_name = self._extract_julia_function_name(line)
                if func_name:
                    structure.append(f"FUNCTION: {func_name}")
            
            # Макросы
            elif line.startswith('macro '):
                macro_name = self._extract_julia_macro_name(line)
                if macro_name:
                    structure.append(f"MACRO: {macro_name}")
        
        if imports:
            structure.insert(0, "IMPORTS:")
            for imp in imports[:10]:
                structure.append(f"  {imp}")
        
        return '\n'.join(structure) if structure else ""
    
    def _extract_powershell_like(self, code: str) -> str:
        """Извлечение для PowerShell"""
        lines = code.split('\n')
        structure = []
        imports = []
        current_module = None
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Импорты
            if line.startswith(('Import-Module ', 'using module ')):
                imports.append(line)
            
            # Модули
            elif line.startswith('module '):
                module_name = self._extract_powershell_module_name(line)
                if module_name:
                    current_module = module_name
                    structure.append(f"MODULE: {module_name}")
            
            # Функции
            elif line.startswith('function '):
                func_name = self._extract_powershell_function_name(line)
                if func_name:
                    structure.append(f"FUNCTION: {func_name}")
            
            # Классы
            elif line.startswith('class '):
                class_name = self._extract_powershell_class_name(line)
                if class_name:
                    structure.append(f"CLASS: {class_name}")
        
        if imports:
            structure.insert(0, "IMPORTS:")
            for imp in imports[:10]:
                structure.append(f"  {imp}")
        
        return '\n'.join(structure) if structure else ""
    
    def _extract_csharp_like(self, code: str) -> str:
        """Извлечение для C#"""
        lines = code.split('\n')
        structure = []
        imports = []
        current_class = None
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('//') or line.startswith('/*'):
                continue
            
            # Импорты
            if line.startswith('using '):
                imports.append(line)
            
            # Namespace
            elif line.startswith('namespace '):
                namespace = self._extract_csharp_namespace(line)
                if namespace:
                    structure.append(f"NAMESPACE: {namespace}")
            
            # Классы (включая внутри namespace)
            elif 'class ' in line:
                class_name = self._extract_csharp_class_name(line)
                if class_name:
                    current_class = class_name
                    structure.append(f"CLASS: {class_name}")
                    # Наследование
                    inheritance = self._extract_csharp_inheritance(line)
                    if inheritance:
                        structure.append(f"  INHERITS: {inheritance}")
            
            # Интерфейсы (включая внутри namespace)
            elif 'interface ' in line:
                interface_name = self._extract_csharp_interface_name(line)
                if interface_name:
                    structure.append(f"INTERFACE: {interface_name}")
            
            
            # Функции/методы
            elif ('(' in line and ')' in line and '{' in line) and not ('class ' in line or 'interface ' in line or 'namespace ' in line):
                func_name = self._extract_csharp_function_name(line)
                if func_name:
                    structure.append(f"FUNCTION: {func_name}")
                    if current_class:
                        structure.append(f"  IN_CLASS: {current_class}")
            
            # Свойства
            elif ('get;' in line or 'set;' in line) and '{' in line:
                prop_name = self._extract_csharp_property_name(line)
                if prop_name:
                    structure.append(f"PROPERTY: {prop_name}")
                    if current_class:
                        structure.append(f"  IN_CLASS: {current_class}")
        
        if imports:
            structure.insert(0, "USING:")
            for imp in imports[:10]:
                structure.append(f"  {imp}")
        
        return '\n'.join(structure) if structure else ""
    
    def _extract_swift_like(self, code: str) -> str:
        """Извлечение для Swift"""
        lines = code.split('\n')
        structure = []
        imports = []
        current_class = None
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('//'):
                continue
            
            # Импорты
            if line.startswith('import '):
                imports.append(line)
            
            # Классы
            elif 'class ' in line and '{' in line:
                class_name = self._extract_swift_class_name(line)
                if class_name:
                    current_class = class_name
                    structure.append(f"CLASS: {class_name}")
                    # Наследование
                    inheritance = self._extract_swift_inheritance(line)
                    if inheritance:
                        structure.append(f"  INHERITS: {inheritance}")
            
            # Структуры
            elif 'struct ' in line and '{' in line:
                struct_name = self._extract_swift_struct_name(line)
                if struct_name:
                    structure.append(f"STRUCT: {struct_name}")
            
            # Протоколы
            elif 'protocol ' in line and '{' in line:
                protocol_name = self._extract_swift_protocol_name(line)
                if protocol_name:
                    structure.append(f"PROTOCOL: {protocol_name}")
            
            # Функции
            elif 'func ' in line and '(' in line:
                func_name = self._extract_swift_function_name(line)
                if func_name:
                    structure.append(f"FUNCTION: {func_name}")
                    if current_class:
                        structure.append(f"  IN_CLASS: {current_class}")
            
            # Свойства
            elif ('var ' in line or 'let ' in line) and ':' in line:
                prop_name = self._extract_swift_property_name(line)
                if prop_name:
                    structure.append(f"PROPERTY: {prop_name}")
                    if current_class:
                        structure.append(f"  IN_CLASS: {current_class}")
        
        if imports:
            structure.insert(0, "IMPORTS:")
            for imp in imports[:10]:
                structure.append(f"  {imp}")
        
        return '\n'.join(structure) if structure else ""
    
    def _extract_dart_like(self, code: str) -> str:
        """Извлечение для Dart"""
        lines = code.split('\n')
        structure = []
        imports = []
        current_class = None
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('//'):
                continue
            
            # Импорты
            if line.startswith('import '):
                imports.append(line)
            
            # Классы
            elif 'class ' in line and '{' in line:
                class_name = self._extract_dart_class_name(line)
                if class_name:
                    current_class = class_name
                    structure.append(f"CLASS: {class_name}")
                    # Наследование
                    inheritance = self._extract_dart_inheritance(line)
                    if inheritance:
                        structure.append(f"  INHERITS: {inheritance}")
            
            # Миксины
            elif 'mixin ' in line and '{' in line:
                mixin_name = self._extract_dart_mixin_name(line)
                if mixin_name:
                    structure.append(f"MIXIN: {mixin_name}")
            
            # Расширения
            elif 'extension ' in line and '{' in line:
                extension_name = self._extract_dart_extension_name(line)
                if extension_name:
                    structure.append(f"EXTENSION: {extension_name}")
            
            # Функции
            elif ('(' in line and ')' in line and '{' in line) and not (line.startswith('class ') or line.startswith('mixin ') or line.startswith('extension ')):
                func_name = self._extract_dart_function_name(line)
                if func_name:
                    structure.append(f"FUNCTION: {func_name}")
                    if current_class:
                        structure.append(f"  IN_CLASS: {current_class}")
        
        if imports:
            structure.insert(0, "IMPORTS:")
            for imp in imports[:10]:
                structure.append(f"  {imp}")
        
        return '\n'.join(structure) if structure else ""
    
    # Вспомогательные методы для новых языков
    def _extract_haskell_module_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'module\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_haskell_type_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'(?:data|newtype)\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_haskell_class_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'class\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_haskell_function_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'(\w+)\s*::', line)
        return match.group(1) if match else None
    
    def _extract_sass_selector(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'^([.#@\w\s-]+)', line)
        return match.group(1).strip() if match else None
    
    def _extract_sass_mixin_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'@mixin\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_sass_function_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'@function\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_sass_variable_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'\$(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_sass_sass_mixin_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'=(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_julia_module_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'module\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_julia_struct_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'(?:mutable\s+)?struct\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_julia_function_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'function\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_julia_macro_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'macro\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_powershell_module_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'module\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_powershell_function_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'function\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_powershell_class_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'class\s+(\w+)', line)
        return match.group(1) if match else None
    
    # Вспомогательные методы для C#
    def _extract_csharp_namespace(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'namespace\s+([^{]+)', line)
        return match.group(1).strip() if match else None
    
    def _extract_csharp_class_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'class\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_csharp_inheritance(self, line: str) -> Optional[str]:
        import re
        match = re.search(r':\s*(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_csharp_interface_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'interface\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_csharp_function_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'(\w+)\s*\(', line)
        return match.group(1) if match else None
    
    def _extract_csharp_property_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'(\w+)\s*\{', line)
        return match.group(1) if match else None
    
    # Вспомогательные методы для Swift
    def _extract_swift_class_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'class\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_swift_inheritance(self, line: str) -> Optional[str]:
        import re
        match = re.search(r':\s*(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_swift_struct_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'struct\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_swift_protocol_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'protocol\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_swift_function_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'func\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_swift_property_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'(?:var|let)\s+(\w+)', line)
        return match.group(1) if match else None
    
    # Вспомогательные методы для Dart
    def _extract_dart_class_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'class\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_dart_inheritance(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'extends\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_dart_mixin_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'mixin\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_dart_extension_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'extension\s+(\w+)', line)
        return match.group(1) if match else None
    
    def _extract_dart_function_name(self, line: str) -> Optional[str]:
        import re
        match = re.search(r'(?:(?:static|final|const|void|dynamic|\w+)\s+)?(\w+)\s*\(', line)
        return match.group(1) if match else None
