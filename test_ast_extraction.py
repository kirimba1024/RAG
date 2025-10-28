#!/usr/bin/env python3
"""
Test script for AST extraction across all supported languages
"""

import os
import sys
from pathlib import Path
from ast_extractor import ASTExtractor

# Add current directory to path to import ast_extractor
sys.path.insert(0, str(Path(__file__).parent))

def test_ast_extraction():
    """Test AST extraction for all supported languages"""
    
    # Initialize extractor
    extractor = ASTExtractor()
    
    # Test files and their expected languages
    test_files = {
        'test_python.py': 'python',
        'test_java.java': 'java',
        'test_javascript.js': 'javascript',
        'test_typescript.ts': 'typescript',
        'test_go.go': 'go',
        'test_rust.rs': 'rust',
        'test_cpp.cpp': 'cpp',
        'test_csharp.cs': 'c_sharp',
        'test_php.php': 'php',
        'test_ruby.rb': 'ruby',
        'test_swift.swift': 'swift',
        'test_kotlin.kt': 'kotlin',
        'test_scala.scala': 'scala',
        'test_groovy.groovy': 'groovy',
        'test_r.R': 'r',
        'test_lua.lua': 'lua',
        'test_bash.sh': 'bash',
        'test_cmd.cmd': 'cmd',
        'test_haskell.hs': 'haskell',
        'test_toml.toml': 'toml',
        'test_sass.scss': 'scss',
        'test_julia.jl': 'julia',
        'test_powershell.ps1': 'powershell'
    }
    
    print("🧪 Testing AST extraction for all supported languages\n")
    print("=" * 80)
    
    results = {}
    
    for filename, language in test_files.items():
        filepath = Path(__file__).parent / "test" / "ast-test" / filename
        
        if not filepath.exists():
            print(f"❌ {filename}: File not found")
            results[filename] = "FILE_NOT_FOUND"
            continue
        
        try:
            # Read file content
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract AST structure
            ast_structure = extractor.extract_ast_structure(content, language)
            
            if ast_structure:
                print(f"✅ {filename} ({language}):")
                print(f"   📊 Extracted {len(ast_structure.splitlines())} lines of structure")
                
                # Show first few lines of structure
                lines = ast_structure.splitlines()
                for i, line in enumerate(lines[:5]):
                    print(f"   {line}")
                if len(lines) > 5:
                    print(f"   ... and {len(lines) - 5} more lines")
                
                results[filename] = "SUCCESS"
            else:
                print(f"⚠️  {filename} ({language}): No structure extracted")
                results[filename] = "NO_STRUCTURE"
            
        except Exception as e:
            print(f"❌ {filename} ({language}): Error - {str(e)}")
            results[filename] = f"ERROR: {str(e)}"
        
        print()
    
    # Summary
    print("=" * 80)
    print("📈 SUMMARY")
    print("=" * 80)
    
    success_count = sum(1 for result in results.values() if result == "SUCCESS")
    total_count = len(results)
    
    print(f"Total files tested: {total_count}")
    print(f"Successful extractions: {success_count}")
    print(f"Success rate: {success_count/total_count*100:.1f}%")
    print()
    
    # Detailed results
    print("📋 DETAILED RESULTS:")
    for filename, result in results.items():
        status_icon = "✅" if result == "SUCCESS" else "❌" if result.startswith("ERROR") else "⚠️"
        print(f"  {status_icon} {filename}: {result}")
    
    print()
    print("🎯 AST extraction test completed!")
    
    return results

def test_language_detection():
    """Test language detection from file extensions"""
    
    print("\n🔍 Testing language detection from file extensions")
    print("=" * 50)
    
    extractor = ASTExtractor()
    
    # Test various file extensions
    test_extensions = {
        '.py': 'python',
        '.java': 'java',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.go': 'go',
        '.rs': 'rust',
        '.cpp': 'cpp',
        '.cs': 'c_sharp',
        '.php': 'php',
        '.rb': 'ruby',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.scala': 'scala',
        '.groovy': 'groovy',
        '.r': 'r',
        '.lua': 'lua',
        '.sh': 'bash',
        '.cmd': 'cmd',
        '.hs': 'haskell',
        '.toml': 'toml',
        '.scss': 'scss',
        '.jl': 'julia',
        '.ps1': 'powershell'
    }
    
    # Import SUPPORTED_LANGUAGES from ast_extractor module
    from ast_extractor import SUPPORTED_LANGUAGES
    
    for ext, expected_lang in test_extensions.items():
        detected_lang = SUPPORTED_LANGUAGES.get(ext)
        status = "✅" if detected_lang == expected_lang else "❌"
        print(f"  {status} {ext} -> {detected_lang} (expected: {expected_lang})")
    
    print()

if __name__ == "__main__":
    print("🚀 Starting AST extraction tests...")
    print()
    
    # Test language detection
    test_language_detection()
    
    # Test AST extraction
    results = test_ast_extraction()
    
    # Exit with appropriate code
    success_count = sum(1 for result in results.values() if result == "SUCCESS")
    total_count = len(results)
    
    if success_count == total_count:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print(f"⚠️  {total_count - success_count} tests failed")
        sys.exit(1)
