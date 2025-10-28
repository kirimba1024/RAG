#!/usr/bin/env python3
"""
Tree-sitter AST extraction tests
Tests each language with Tree-sitter specific validation
"""

import os
import sys
from pathlib import Path
from ast_extractor import ASTExtractor

# Add current directory to path to import ast_extractor
sys.path.insert(0, str(Path(__file__).parent))

class TreeSitterTester:
    def __init__(self):
        self.extractor = ASTExtractor()
        self.test_dir = Path(__file__).parent / "test" / "ast-test"
        self.results = {}
    
    def test_python(self):
        """Test Python AST extraction"""
        print("🐍 Testing Python AST extraction...")
        
        file_path = self.test_dir / "test_python.py"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast_structure = self.extractor.extract_ast_structure(content, 'python')
        
        # Expected elements in Python (Tree-sitter format)
        expected_elements = [
            'IMPORTS:', 'CLASS:', 'FUNC:', 'METHOD:'
        ]
        
        found_elements = [elem for elem in expected_elements if elem in ast_structure]
        
        print(f"   📊 Extracted {len(ast_structure.splitlines())} lines")
        print(f"   ✅ Found elements: {', '.join(found_elements)}")
        
        # Show sample structure
        lines = ast_structure.splitlines()[:6]
        for line in lines:
            print(f"   {line}")
        if len(ast_structure.splitlines()) > 6:
            print(f"   ... and {len(ast_structure.splitlines()) - 6} more lines")
        
        return {
            'success': len(found_elements) >= 2,
            'lines': len(ast_structure.splitlines()),
            'elements': found_elements
        }

    def test_java(self):
        """Test Java AST extraction"""
        print("☕ Testing Java AST extraction...")
        
        file_path = self.test_dir / "test_java.java"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast_structure = self.extractor.extract_ast_structure(content, 'java')
        
        # Expected elements in Java
        expected_elements = [
            'IMPORTS:', 'CLASS:', 'METHOD:'
        ]
        
        found_elements = [elem for elem in expected_elements if elem in ast_structure]
        
        print(f"   📊 Extracted {len(ast_structure.splitlines())} lines")
        print(f"   ✅ Found elements: {', '.join(found_elements)}")
        
        # Show sample structure
        lines = ast_structure.splitlines()[:6]
        for line in lines:
            print(f"   {line}")
        if len(ast_structure.splitlines()) > 6:
            print(f"   ... and {len(ast_structure.splitlines()) - 6} more lines")
        
        return {
            'success': len(found_elements) >= 2,
            'lines': len(ast_structure.splitlines()),
            'elements': found_elements
        }

    def test_javascript(self):
        """Test JavaScript AST extraction"""
        print("🟨 Testing JavaScript AST extraction...")
        
        file_path = self.test_dir / "test_javascript.js"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast_structure = self.extractor.extract_ast_structure(content, 'javascript')
        
        # Expected elements in JavaScript
        expected_elements = [
            'CLASS:', 'FUNC:', 'METHOD:'
        ]
        
        found_elements = [elem for elem in expected_elements if elem in ast_structure]
        
        print(f"   📊 Extracted {len(ast_structure.splitlines())} lines")
        print(f"   ✅ Found elements: {', '.join(found_elements)}")
        
        # Show sample structure
        lines = ast_structure.splitlines()[:6]
        for line in lines:
            print(f"   {line}")
        if len(ast_structure.splitlines()) > 6:
            print(f"   ... and {len(ast_structure.splitlines()) - 6} more lines")
        
        return {
            'success': len(found_elements) >= 2,
            'lines': len(ast_structure.splitlines()),
            'elements': found_elements
        }

    def test_csharp(self):
        """Test C# AST extraction"""
        print("🔷 Testing C# AST extraction...")
        
        file_path = self.test_dir / "test_csharp.cs"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast_structure = self.extractor.extract_ast_structure(content, 'csharp')
        
        # Expected elements in C#
        expected_elements = [
            'IMPORTS:', 'NAMESPACE:', 'CLASS:', 'METHOD:'
        ]
        
        found_elements = [elem for elem in expected_elements if elem in ast_structure]
        
        print(f"   📊 Extracted {len(ast_structure.splitlines())} lines")
        print(f"   ✅ Found elements: {', '.join(found_elements)}")
        
        # Show sample structure
        lines = ast_structure.splitlines()[:6]
        for line in lines:
            print(f"   {line}")
        if len(ast_structure.splitlines()) > 6:
            print(f"   ... and {len(ast_structure.splitlines()) - 6} more lines")
        
        return {
            'success': len(found_elements) >= 2,
            'lines': len(ast_structure.splitlines()),
            'elements': found_elements
        }

    def test_go(self):
        """Test Go AST extraction"""
        print("🐹 Testing Go AST extraction...")
        
        file_path = self.test_dir / "test_go.go"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast_structure = self.extractor.extract_ast_structure(content, 'go')
        
        # Expected elements in Go
        expected_elements = [
            'IMPORTS:', 'TYPE:', 'FUNC:'
        ]
        
        found_elements = [elem for elem in expected_elements if elem in ast_structure]
        
        print(f"   📊 Extracted {len(ast_structure.splitlines())} lines")
        print(f"   ✅ Found elements: {', '.join(found_elements)}")
        
        # Show sample structure
        lines = ast_structure.splitlines()[:6]
        for line in lines:
            print(f"   {line}")
        if len(ast_structure.splitlines()) > 6:
            print(f"   ... and {len(ast_structure.splitlines()) - 6} more lines")
        
        return {
            'success': len(found_elements) >= 2,
            'lines': len(ast_structure.splitlines()),
            'elements': found_elements
        }

    def test_rust(self):
        """Test Rust AST extraction"""
        print("🦀 Testing Rust AST extraction...")
        
        file_path = self.test_dir / "test_rust.rs"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast_structure = self.extractor.extract_ast_structure(content, 'rust')
        
        # Expected elements in Rust
        expected_elements = [
            'IMPORTS:', 'STRUCT:', 'FUNC:'
        ]
        
        found_elements = [elem for elem in expected_elements if elem in ast_structure]
        
        print(f"   📊 Extracted {len(ast_structure.splitlines())} lines")
        print(f"   ✅ Found elements: {', '.join(found_elements)}")
        
        # Show sample structure
        lines = ast_structure.splitlines()[:6]
        for line in lines:
            print(f"   {line}")
        if len(ast_structure.splitlines()) > 6:
            print(f"   ... and {len(ast_structure.splitlines()) - 6} more lines")
        
        return {
            'success': len(found_elements) >= 2,
            'lines': len(ast_structure.splitlines()),
            'elements': found_elements
        }

    def test_php(self):
        """Test PHP AST extraction"""
        print("🐘 Testing PHP AST extraction...")
        
        file_path = self.test_dir / "test_php.php"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast_structure = self.extractor.extract_ast_structure(content, 'php')
        
        # Expected elements in PHP
        expected_elements = [
            'IMPORTS:', 'NAMESPACE:', 'CLASS:', 'METHOD:'
        ]
        
        found_elements = [elem for elem in expected_elements if elem in ast_structure]
        
        print(f"   📊 Extracted {len(ast_structure.splitlines())} lines")
        print(f"   ✅ Found elements: {', '.join(found_elements)}")
        
        # Show sample structure
        lines = ast_structure.splitlines()[:6]
        for line in lines:
            print(f"   {line}")
        if len(ast_structure.splitlines()) > 6:
            print(f"   ... and {len(ast_structure.splitlines()) - 6} more lines")
        
        return {
            'success': len(found_elements) >= 2,
            'lines': len(ast_structure.splitlines()),
            'elements': found_elements
        }

    def test_ruby(self):
        """Test Ruby AST extraction"""
        print("💎 Testing Ruby AST extraction...")
        
        file_path = self.test_dir / "test_ruby.rb"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast_structure = self.extractor.extract_ast_structure(content, 'ruby')
        
        # Expected elements in Ruby
        expected_elements = [
            'IMPORTS:', 'MODULE:', 'CLASS:', 'METHOD:'
        ]
        
        found_elements = [elem for elem in expected_elements if elem in ast_structure]
        
        print(f"   📊 Extracted {len(ast_structure.splitlines())} lines")
        print(f"   ✅ Found elements: {', '.join(found_elements)}")
        
        # Show sample structure
        lines = ast_structure.splitlines()[:6]
        for line in lines:
            print(f"   {line}")
        if len(ast_structure.splitlines()) > 6:
            print(f"   ... and {len(ast_structure.splitlines()) - 6} more lines")
        
        return {
            'success': len(found_elements) >= 2,
            'lines': len(ast_structure.splitlines()),
            'elements': found_elements
        }

    def test_xml(self):
        """Test XML AST extraction"""
        print("📄 Testing XML AST extraction...")
        
        file_path = self.test_dir / "test_xml.xml"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast_structure = self.extractor.extract_ast_structure(content, 'xml')
        
        # Expected elements in XML
        expected_elements = [
            'TAG:'
        ]
        
        found_elements = [elem for elem in expected_elements if elem in ast_structure]
        
        print(f"   📊 Extracted {len(ast_structure.splitlines())} lines")
        print(f"   ✅ Found elements: {', '.join(found_elements)}")
        
        # Show sample structure
        lines = ast_structure.splitlines()[:6]
        for line in lines:
            print(f"   {line}")
        if len(ast_structure.splitlines()) > 6:
            print(f"   ... and {len(ast_structure.splitlines()) - 6} more lines")
        
        return {
            'success': len(found_elements) >= 1,
            'lines': len(ast_structure.splitlines()),
            'elements': found_elements
        }

    def test_yaml(self):
        """Test YAML AST extraction"""
        print("📋 Testing YAML AST extraction...")
        
        file_path = self.test_dir / "test_yaml.yaml"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast_structure = self.extractor.extract_ast_structure(content, 'yaml')
        
        # Expected elements in YAML
        expected_elements = [
            'KEY:'
        ]
        
        found_elements = [elem for elem in expected_elements if elem in ast_structure]
        
        print(f"   📊 Extracted {len(ast_structure.splitlines())} lines")
        print(f"   ✅ Found elements: {', '.join(found_elements)}")
        
        # Show sample structure
        lines = ast_structure.splitlines()[:6]
        for line in lines:
            print(f"   {line}")
        if len(ast_structure.splitlines()) > 6:
            print(f"   ... and {len(ast_structure.splitlines()) - 6} more lines")
        
        return {
            'success': len(found_elements) >= 1,
            'lines': len(ast_structure.splitlines()),
            'elements': found_elements
        }

    def test_html(self):
        """Test HTML AST extraction"""
        print("🌐 Testing HTML AST extraction...")
        
        file_path = self.test_dir / "test_html.html"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast_structure = self.extractor.extract_ast_structure(content, 'html')
        
        # Expected elements in HTML
        expected_elements = [
            'TAG:'
        ]
        
        found_elements = [elem for elem in expected_elements if elem in ast_structure]
        
        print(f"   📊 Extracted {len(ast_structure.splitlines())} lines")
        print(f"   ✅ Found elements: {', '.join(found_elements)}")
        
        # Show sample structure
        lines = ast_structure.splitlines()[:6]
        for line in lines:
            print(f"   {line}")
        if len(ast_structure.splitlines()) > 6:
            print(f"   ... and {len(ast_structure.splitlines()) - 6} more lines")
        
        return {
            'success': len(found_elements) >= 1,
            'lines': len(ast_structure.splitlines()),
            'elements': found_elements
        }

    def run_all_tests(self):
        """Run all language tests"""
        print("🚀 Starting Tree-sitter AST extraction tests...")
        print("=" * 80)
        print()
        
        tests = [
            ('Python', self.test_python),
            ('Java', self.test_java),
            ('JavaScript', self.test_javascript),
            ('C#', self.test_csharp),
            ('Go', self.test_go),
            ('Rust', self.test_rust),
            ('PHP', self.test_php),
            ('Ruby', self.test_ruby),
            ('XML', self.test_xml),
            ('YAML', self.test_yaml),
            ('HTML', self.test_html),
        ]
        
        passed = 0
        total = len(tests)
        
        for name, test_func in tests:
            try:
                result = test_func()
                self.results[name] = result
                if result['success']:
                    passed += 1
                    print(f"   ✅ PASS")
                else:
                    print(f"   ❌ FAIL")
            except Exception as e:
                print(f"   ❌ ERROR: {e}")
                self.results[name] = {'success': False, 'error': str(e)}
            print()
        
        print("=" * 80)
        print("📈 SUMMARY")
        print("=" * 80)
        print(f"Total languages tested: {total}")
        print(f"Passed tests: {passed}")
        print(f"Success rate: {passed/total*100:.1f}%")
        print()
        
        print("📋 DETAILED RESULTS:")
        for name, result in self.results.items():
            if result['success']:
                elements = result.get('elements', [])
                lines = result.get('lines', 0)
                print(f"  ✅ {name}: {len(elements)} elements, {lines} lines")
            else:
                error = result.get('error', 'Failed validation')
                print(f"  ❌ {name}: {error}")
        
        print()
        print("🎯 Tree-sitter testing completed!")
        if passed < total:
            print(f"⚠️  {total - passed} language tests failed")
        else:
            print("🎉 All tests passed!")

if __name__ == "__main__":
    tester = TreeSitterTester()
    tester.run_all_tests()
