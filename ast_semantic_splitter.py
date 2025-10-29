"""
AST-aware semantic code splitter
Разбивает код по семантическим границам (функции, классы, методы)
на основе Tree-sitter AST
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from tree_sitter_language_pack import get_parser, get_language
from utils import TREE_SITTER_NAMES, setup_logging
from pathlib import Path

logger = setup_logging(Path(__file__).stem)

@dataclass
class SemanticChunk:
    """Семантический чанк кода"""
    text: str
    start_line: int
    end_line: int
    start_byte: int
    end_byte: int
    node_type: str
    node_name: Optional[str]
    file_path: str
    parent_type: Optional[str] = None
    parent_name: Optional[str] = None

class ASTSemanticSplitter:
    """Разбивает код по семантическим границам на основе AST"""
    
    # Семантические границы для разных языков
    SEMANTIC_BOUNDARIES = {
        'python': [
            'function_definition',
            'class_definition', 
            'method_definition',
            'async_function_definition',
            'module',
            'import_statement',
            'import_from_statement'
        ],
        'javascript': [
            'function_declaration',
            'function_expression',
            'class_declaration',
            'method_definition',
            'arrow_function',
            'import_statement',
            'export_statement'
        ],
        'typescript': [
            'function_declaration',
            'function_expression', 
            'class_declaration',
            'method_definition',
            'arrow_function',
            'interface_declaration',
            'type_alias_declaration',
            'import_statement',
            'export_statement'
        ],
        'java': [
            'class_declaration',
            'method_declaration',
            'constructor_declaration',
            'interface_declaration',
            'enum_declaration',
            'import_declaration',
            'package_declaration'
        ],
        'go': [
            'function_declaration',
            'method_declaration',
            'type_declaration',
            'var_declaration',
            'const_declaration',
            'import_declaration',
            'package_clause'
        ],
        'rust': [
            'function_item',
            'impl_item',
            'struct_item',
            'enum_item',
            'trait_item',
            'mod_item',
            'use_declaration'
        ]
    }
    
    def __init__(self, language: str):
        self.language = language
        self.parser = get_parser(language)
        self.semantic_boundaries = self.SEMANTIC_BOUNDARIES.get(language, [])
        
        if not self.parser:
            raise ValueError(f"Unsupported language: {language}")
    
    def split_code(self, source_code: str, file_path: str = "") -> List[SemanticChunk]:
        """Разбивает код на семантические чанки"""
        if not source_code.strip():
            return []
        
        try:
            tree = self.parser.parse(source_code.encode('utf-8'))
            chunks = []
            
            # Обходим AST дерево
            self._traverse_ast(tree.root_node, source_code, file_path, chunks)
            
            # Сортируем по позиции в коде
            chunks.sort(key=lambda x: x.start_byte)
            
            logger.info(f"Created {len(chunks)} semantic chunks for {file_path}")
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return []
    
    def _traverse_ast(self, node, source_code: str, file_path: str, chunks: List[SemanticChunk], 
                     parent_type: str = None, parent_name: str = None):
        """Рекурсивно обходит AST дерево"""
        
        # Проверяем, является ли узел семантической границей
        if self._is_semantic_boundary(node):
            chunk = self._create_chunk(node, source_code, file_path, parent_type, parent_name)
            if chunk:
                chunks.append(chunk)
        
        # Обходим детей
        for child in node.children:
            # Передаем информацию о родителе
            current_parent_type = node.type if self._is_semantic_boundary(node) else parent_type
            current_parent_name = self._get_node_name(node) if self._is_semantic_boundary(node) else parent_name
            
            self._traverse_ast(child, source_code, file_path, chunks, 
                             current_parent_type, current_parent_name)
    
    def _is_semantic_boundary(self, node) -> bool:
        """Проверяет, является ли узел семантической границей"""
        return node.type in self.semantic_boundaries
    
    def _get_node_name(self, node) -> Optional[str]:
        """Извлекает имя узла"""
        # Ищем поле 'name' или 'identifier'
        name_node = node.child_by_field_name('name') or node.child_by_field_name('identifier')
        if name_node:
            return self._get_text(name_node)
        
        # Ищем в детях
        for child in node.children:
            if 'identifier' in child.type or child.type.endswith('_identifier'):
                return self._get_text(child)
        
        # Если узел сам является идентификатором
        if node.type in ('identifier', 'type_identifier', 'property_identifier'):
            return self._get_text(node)
        
        return None
    
    def _get_text(self, node) -> str:
        """Извлекает текст узла"""
        return node.text.decode('utf-8') if hasattr(node, 'text') else ""
    
    def _create_chunk(self, node, source_code: str, file_path: str, 
                     parent_type: str = None, parent_name: str = None) -> Optional[SemanticChunk]:
        """Создает семантический чанк из AST узла"""
        
        # Извлекаем текст узла
        start_byte = node.start_byte
        end_byte = node.end_byte
        text = source_code[start_byte:end_byte]
        
        if not text.strip():
            return None
        
        # Вычисляем номера строк
        start_line = source_code[:start_byte].count('\n') + 1
        end_line = source_code[:end_byte].count('\n') + 1
        
        # Извлекаем имя узла
        node_name = self._get_node_name(node)
        
        return SemanticChunk(
            text=text,
            start_line=start_line,
            end_line=end_line,
            start_byte=start_byte,
            end_byte=end_byte,
            node_type=node.type,
            node_name=node_name,
            file_path=file_path,
            parent_type=parent_type,
            parent_name=parent_name
        )

def create_semantic_chunks(source_code: str, language: str, file_path: str = "") -> List[SemanticChunk]:
    """Создает семантические чанки для кода"""
    splitter = ASTSemanticSplitter(language)
    return splitter.split_code(source_code, file_path)

# Пример использования
if __name__ == "__main__":
    python_code = '''
def calculate_total(items):
    """Calculate total price of items"""
    total = 0
    for item in items:
        total += item.price
    return total

class ShoppingCart:
    def __init__(self):
        self.items = []
    
    def add_item(self, item):
        self.items.append(item)
    
    def get_total(self):
        return calculate_total(self.items)
'''
    
    chunks = create_semantic_chunks(python_code, 'python', 'test.py')
    
    for chunk in chunks:
        print(f"Type: {chunk.node_type}")
        print(f"Name: {chunk.node_name}")
        print(f"Lines: {chunk.start_line}-{chunk.end_line}")
        print(f"Text: {chunk.text[:100]}...")
        print("---")
