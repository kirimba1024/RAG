#!/usr/bin/env python3
"""
Скрипт для обновления всех expected файлов в тестах AST экстрактора.
Запуск: python update_expected.py
"""

from ast_extractor import ASTExtractor, SUPPORTED_LANGUAGES
from pathlib import Path

def update_expected_files():
    """Обновляет все expected файлы новыми результатами."""
    extractor = ASTExtractor()
    sources_dir = Path('test/ast-test/sources')
    expected_dir = Path('test/ast-test/expected')
    
    # Создаем expected папку если нет
    expected_dir.mkdir(exist_ok=True)
    
    # Маппинг языков из ast_extractor.py
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
    
    # Проверяем, что все языки из маппинга поддерживаются
    unsupported_langs = []
    for ext, lang in lang_map.items():
        if lang not in SUPPORTED_LANGUAGES:
            unsupported_langs.append(f"{ext} -> {lang}")
    
    if unsupported_langs:
        print(f"⚠️  Предупреждение: следующие языки не поддерживаются в SUPPORTED_LANGUAGES:")
        for lang in unsupported_langs:
            print(f"   {lang}")
        print()
    
    updated_count = 0
    skipped_count = 0
    
    print("🔄 Обновление expected файлов...")
    print("=" * 50)
    
    for source_file in sorted(sources_dir.glob('test_*')):
        # Используем ignore case для расширения
        suffix_lower = source_file.suffix.lower()
        if suffix_lower not in lang_map:
            print(f"⏭️  Пропущен {source_file.name} (неизвестный язык)")
            skipped_count += 1
            continue
            
        print(f"📝 Обновляю {source_file.name}...")
        
        try:
            # Читаем исходный файл
            with open(source_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Получаем язык
            language = lang_map[suffix_lower]
            
            # Генерируем результат
            result = extractor.outline_short(content, language)
            
            # Путь к expected файлу (используем полное имя файла для избежания конфликтов)
            expected_file = expected_dir / f'{source_file.name}.outline'
            
            # Записываем новый результат
            with open(expected_file, 'w', encoding='utf-8') as f:
                f.write(result)
            
            print(f"   ✅ Обновлен: {expected_file.name}")
            updated_count += 1
            
        except Exception as e:
            print(f"   ❌ Ошибка при обработке {source_file.name}: {e}")
            skipped_count += 1
    
    print("=" * 50)
    print(f"📊 ИТОГИ:")
    print(f"   ✅ Обновлено: {updated_count} файлов")
    print(f"   ⏭️  Пропущено: {skipped_count} файлов")
    print(f"   📁 Всего обработано: {updated_count + skipped_count} файлов")
    
    if updated_count > 0:
        print(f"\n🎉 Все expected файлы успешно обновлены!")
        print(f"💡 Теперь можно запустить: python ast_extractor_test.py")

if __name__ == "__main__":
    update_expected_files()
