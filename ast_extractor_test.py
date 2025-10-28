#!/usr/bin/env python3
"""
Минимальный тест AST extractor
Сравнивает 1:1 с expected результатами
"""

import os
from pathlib import Path
from ast_extractor import ASTExtractor

def test_ast_extraction():
    extractor = ASTExtractor()
    sources_dir = Path("test/ast-test/sources")
    expected_dir = Path("test/ast-test/expected")
    
    # Создаем expected папку если нет
    expected_dir.mkdir(exist_ok=True)
    
    # Маппинг языков
    lang_map = {
        '.py': 'python',
        '.java': 'java', 
        '.js': 'javascript',
        '.ts': 'typescript',
        '.cs': 'csharp',
        '.cpp': 'cpp',
        '.go': 'go',
        '.rs': 'rust',
        '.php': 'php',
        '.rb': 'ruby',
        '.xml': 'xml',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.html': 'html',
        '.sh': 'bash',
        '.zsh': 'bash',
        '.bat': 'bash',
        '.cmd': 'bash',
        '.hs': 'haskell',
        '.kt': 'kotlin',
        '.scala': 'scala',
        '.groovy': 'groovy',
        '.swift': 'swift',
        '.dart': 'dart',
        '.lua': 'lua',
        '.r': 'r',
        '.jl': 'julia',
        '.ps1': 'powershell',
        '.sass': 'sass',
        '.scss': 'scss',
        '.sql': 'sql',
        '.toml': 'toml',
        '.json': 'json'
    }
    
    results = []
    
    for source_file in sources_dir.glob("test_*"):
        # Используем ignore case для расширения
        suffix_lower = source_file.suffix.lower()
        if suffix_lower not in lang_map:
            continue
            
        print(f"🧪 Testing {source_file.name}...")
        
        # Читаем исходный файл
        with open(source_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Получаем язык
        language = lang_map[suffix_lower]
        
        # Генерируем результат
        result = extractor.outline_short(content, language)
        
        # Путь к expected файлу (используем полное имя файла для избежания конфликтов)
        expected_file = expected_dir / f"{source_file.name}.outline"
        
        if expected_file.exists():
            # Сравниваем с expected
            with open(expected_file, 'r', encoding='utf-8') as f:
                expected = f.read()
            
            if result.strip() == expected.strip():
                print(f"   ✅ PASS")
                results.append(('PASS', source_file.name))
            else:
                print(f"   ❌ FAIL - differs from expected")
                print(f"   Expected: {expected[:100]}...")
                print(f"   Got: {result[:100]}...")
                results.append(('FAIL', source_file.name))
        else:
            # Создаем expected файл
            with open(expected_file, 'w', encoding='utf-8') as f:
                f.write(result)
            print(f"   📝 Created expected file")
            results.append(('CREATED', source_file.name))
    
    # Итоги
    print(f"\n📊 SUMMARY:")
    for status, filename in results:
        print(f"  {status}: {filename}")
    
    passed = sum(1 for status, _ in results if status == 'PASS')
    total = len(results)
    print(f"\n🎯 {passed}/{total} tests passed")

if __name__ == "__main__":
    test_ast_extraction()
