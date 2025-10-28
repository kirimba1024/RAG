#!/usr/bin/env python3
"""
Language-specific AST extraction tests
Tests each language individually with detailed validation
"""

import os
import sys
from pathlib import Path
from ast_extractor import ASTExtractor

# Add current directory to path to import ast_extractor
sys.path.insert(0, str(Path(__file__).parent))

class LanguageTester:
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
        
        # Expected elements in Python
        expected_elements = [
            'IMPORTS:', 'CLASS:', 'FUNCTION:', 'DATACLASS:', 'TYPE:'
        ]
        
        found_elements = [elem for elem in expected_elements if elem in ast_structure]
        
        print(f"   📊 Extracted {len(ast_structure.splitlines())} lines")
        print(f"   ✅ Found elements: {', '.join(found_elements)}")
        
        # Show sample structure
        lines = ast_structure.splitlines()[:8]
        for line in lines:
            print(f"   {line}")
        if len(ast_structure.splitlines()) > 8:
            print(f"   ... and {len(ast_structure.splitlines()) - 8} more lines")
        
        return {
            'success': len(found_elements) >= 3,
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
            'IMPORTS:', 'CLASS:', 'METHOD:', 'RETURNS:', 'PRIVATE:', 'PUBLIC:'
        ]
        
        found_elements = [elem for elem in expected_elements if elem in ast_structure]
        
        print(f"   📊 Extracted {len(ast_structure.splitlines())} lines")
        print(f"   ✅ Found elements: {', '.join(found_elements)}")
        
        # Show sample structure
        lines = ast_structure.splitlines()[:8]
        for line in lines:
            print(f"   {line}")
        if len(ast_structure.splitlines()) > 8:
            print(f"   ... and {len(ast_structure.splitlines()) - 8} more lines")
        
        return {
            'success': len(found_elements) >= 3,
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
            'CLASS:', 'FUNCTION:', 'IMPORTS:', 'EXPORT:'
        ]
        
        found_elements = [elem for elem in expected_elements if elem in ast_structure]
        
        print(f"   📊 Extracted {len(ast_structure.splitlines())} lines")
        print(f"   ✅ Found elements: {', '.join(found_elements)}")
        
        # Show sample structure
        lines = ast_structure.splitlines()[:5]
        for line in lines:
            print(f"   {line}")
        if len(ast_structure.splitlines()) > 5:
            print(f"   ... and {len(ast_structure.splitlines()) - 5} more lines")
        
        return {
            'success': len(found_elements) >= 2,
            'lines': len(ast_structure.splitlines()),
            'elements': found_elements
        }
    
    def test_typescript(self):
        """Test TypeScript AST extraction"""
        print("🔷 Testing TypeScript AST extraction...")
        
        file_path = self.test_dir / "test_typescript.ts"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast_structure = self.extractor.extract_ast_structure(content, 'typescript')
        
        # Expected elements in TypeScript
        expected_elements = [
            'IMPORTS:', 'CLASS:', 'INTERFACE:', 'FUNCTION:', 'TYPE:'
        ]
        
        found_elements = [elem for elem in expected_elements if elem in ast_structure]
        
        print(f"   📊 Extracted {len(ast_structure.splitlines())} lines")
        print(f"   ✅ Found elements: {', '.join(found_elements)}")
        
        # Show sample structure
        lines = ast_structure.splitlines()[:5]
        for line in lines:
            print(f"   {line}")
        if len(ast_structure.splitlines()) > 5:
            print(f"   ... and {len(ast_structure.splitlines()) - 5} more lines")
        
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
            'IMPORTS:', 'TYPE:', 'FUNCTION:', 'STRUCT:', 'METHOD:'
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
            'success': len(found_elements) >= 3,
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
            'IMPORTS:', 'TYPE:', 'FUNCTION:', 'STRUCT:', 'IMPL:', 'TEST:'
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
            'success': len(found_elements) >= 3,
            'lines': len(ast_structure.splitlines()),
            'elements': found_elements
        }
    
    def test_cpp(self):
        """Test C++ AST extraction"""
        print("⚙️ Testing C++ AST extraction...")
        
        file_path = self.test_dir / "test_cpp.cpp"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast_structure = self.extractor.extract_ast_structure(content, 'cpp')
        
        # Expected elements in C++
        expected_elements = [
            'INCLUDES:', 'CLASS:', 'FUNCTION:', 'NAMESPACE:', 'PRIVATE:', 'PUBLIC:'
        ]
        
        found_elements = [elem for elem in expected_elements if elem in ast_structure]
        
        print(f"   📊 Extracted {len(ast_structure.splitlines())} lines")
        print(f"   ✅ Found elements: {', '.join(found_elements)}")
        
        # Show sample structure
        lines = ast_structure.splitlines()[:8]
        for line in lines:
            print(f"   {line}")
        if len(ast_structure.splitlines()) > 8:
            print(f"   ... and {len(ast_structure.splitlines()) - 8} more lines")
        
        return {
            'success': len(found_elements) >= 3,
            'lines': len(ast_structure.splitlines()),
            'elements': found_elements
        }
    
    def test_csharp(self):
        """Test C# AST extraction"""
        print("🔷 Testing C# AST extraction...")
        
        file_path = self.test_dir / "test_csharp.cs"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast_structure = self.extractor.extract_ast_structure(content, 'c_sharp')
        
        # Expected elements in C#
        expected_elements = [
            'FUNCTION:', 'CLASS:', 'NAMESPACE:', 'USING:', 'PROPERTY:'
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
            'success': len(found_elements) >= 3,
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
            'IMPORTS:', 'CLASS:', 'FUNCTION:', 'NAMESPACE:', 'PRIVATE:', 'PUBLIC:'
        ]
        
        found_elements = [elem for elem in expected_elements if elem in ast_structure]
        
        print(f"   📊 Extracted {len(ast_structure.splitlines())} lines")
        print(f"   ✅ Found elements: {', '.join(found_elements)}")
        
        # Show sample structure
        lines = ast_structure.splitlines()[:8]
        for line in lines:
            print(f"   {line}")
        if len(ast_structure.splitlines()) > 8:
            print(f"   ... and {len(ast_structure.splitlines()) - 8} more lines")
        
        return {
            'success': len(found_elements) >= 3,
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
            'IMPORTS:', 'MODULE:', 'CLASS:', 'METHOD:', 'FUNCTION:'
        ]
        
        found_elements = [elem for elem in expected_elements if elem in ast_structure]
        
        print(f"   📊 Extracted {len(ast_structure.splitlines())} lines")
        print(f"   ✅ Found elements: {', '.join(found_elements)}")
        
        # Show sample structure
        lines = ast_structure.splitlines()[:8]
        for line in lines:
            print(f"   {line}")
        if len(ast_structure.splitlines()) > 8:
            print(f"   ... and {len(ast_structure.splitlines()) - 8} more lines")
        
        return {
            'success': len(found_elements) >= 3,
            'lines': len(ast_structure.splitlines()),
            'elements': found_elements
        }
    
    def test_swift(self):
        """Test Swift AST extraction"""
        print("🦉 Testing Swift AST extraction...")
        
        file_path = self.test_dir / "test_swift.swift"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast_structure = self.extractor.extract_ast_structure(content, 'swift')
        
        # Expected elements in Swift
        expected_elements = [
            'FUNCTION:', 'CLASS:', 'STRUCT:', 'IMPORT:', 'PROPERTY:'
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
            'success': len(found_elements) >= 3,
            'lines': len(ast_structure.splitlines()),
            'elements': found_elements
        }
    
    def test_kotlin(self):
        """Test Kotlin AST extraction"""
        print("🟣 Testing Kotlin AST extraction...")
        
        file_path = self.test_dir / "test_kotlin.kt"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast_structure = self.extractor.extract_ast_structure(content, 'kotlin')
        
        # Expected elements in Kotlin
        expected_elements = [
            'IMPORTS:', 'CLASS:', 'FUNCTION:', 'DATA_CLASS:', 'PRIVATE:', 'PUBLIC:'
        ]
        
        found_elements = [elem for elem in expected_elements if elem in ast_structure]
        
        print(f"   📊 Extracted {len(ast_structure.splitlines())} lines")
        print(f"   ✅ Found elements: {', '.join(found_elements)}")
        
        # Show sample structure
        lines = ast_structure.splitlines()[:4]
        for line in lines:
            print(f"   {line}")
        if len(ast_structure.splitlines()) > 4:
            print(f"   ... and {len(ast_structure.splitlines()) - 4} more lines")
        
        return {
            'success': len(found_elements) >= 2,
            'lines': len(ast_structure.splitlines()),
            'elements': found_elements
        }
    
    def test_scala(self):
        """Test Scala AST extraction"""
        print("🔴 Testing Scala AST extraction...")
        
        file_path = self.test_dir / "test_scala.scala"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast_structure = self.extractor.extract_ast_structure(content, 'scala')
        
        # Expected elements in Scala
        expected_elements = [
            'IMPORTS:', 'CLASS:', 'FUNCTION:', 'CASE_CLASS:', 'OBJECT:'
        ]
        
        found_elements = [elem for elem in expected_elements if elem in ast_structure]
        
        print(f"   📊 Extracted {len(ast_structure.splitlines())} lines")
        print(f"   ✅ Found elements: {', '.join(found_elements)}")
        
        # Show sample structure
        lines = ast_structure.splitlines()[:5]
        for line in lines:
            print(f"   {line}")
        if len(ast_structure.splitlines()) > 5:
            print(f"   ... and {len(ast_structure.splitlines()) - 5} more lines")
        
        return {
            'success': len(found_elements) >= 2,
            'lines': len(ast_structure.splitlines()),
            'elements': found_elements
        }
    
    def test_groovy(self):
        """Test Groovy AST extraction"""
        print("🟢 Testing Groovy AST extraction...")
        
        file_path = self.test_dir / "test_groovy.groovy"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast_structure = self.extractor.extract_ast_structure(content, 'groovy')
        
        # Expected elements in Groovy
        expected_elements = [
            'IMPORTS:', 'CLASS:', 'FUNCTION:', 'PACKAGE:'
        ]
        
        found_elements = [elem for elem in expected_elements if elem in ast_structure]
        
        print(f"   📊 Extracted {len(ast_structure.splitlines())} lines")
        print(f"   ✅ Found elements: {', '.join(found_elements)}")
        
        # Show sample structure
        lines = ast_structure.splitlines()[:5]
        for line in lines:
            print(f"   {line}")
        if len(ast_structure.splitlines()) > 5:
            print(f"   ... and {len(ast_structure.splitlines()) - 5} more lines")
        
        return {
            'success': len(found_elements) >= 2,
            'lines': len(ast_structure.splitlines()),
            'elements': found_elements
        }
    
    def test_r(self):
        """Test R AST extraction"""
        print("📊 Testing R AST extraction...")
        
        file_path = self.test_dir / "test_r.R"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast_structure = self.extractor.extract_ast_structure(content, 'r')
        
        # Expected elements in R
        expected_elements = [
            'IMPORTS:', 'VARIABLE:', 'FUNCTION:'
        ]
        
        found_elements = [elem for elem in expected_elements if elem in ast_structure]
        
        print(f"   📊 Extracted {len(ast_structure.splitlines())} lines")
        print(f"   ✅ Found elements: {', '.join(found_elements)}")
        
        # Show sample structure
        lines = ast_structure.splitlines()[:8]
        for line in lines:
            print(f"   {line}")
        if len(ast_structure.splitlines()) > 8:
            print(f"   ... and {len(ast_structure.splitlines()) - 8} more lines")
        
        return {
            'success': len(found_elements) >= 2,
            'lines': len(ast_structure.splitlines()),
            'elements': found_elements
        }
    
    def test_lua(self):
        """Test Lua AST extraction"""
        print("🌙 Testing Lua AST extraction...")
        
        file_path = self.test_dir / "test_lua.lua"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast_structure = self.extractor.extract_ast_structure(content, 'lua')
        
        # Expected elements in Lua
        expected_elements = [
            'FUNCTION:', 'LOCAL_FUNCTION:', 'IMPORTS:', 'MODULE:', 'TABLE:'
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
    
    def test_bash(self):
        """Test Bash AST extraction"""
        print("🐚 Testing Bash AST extraction...")
        
        file_path = self.test_dir / "test_bash.sh"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast_structure = self.extractor.extract_ast_structure(content, 'bash')
        
        # Expected elements in Bash
        expected_elements = [
            'FUNCTION:', 'IMPORTS:'
        ]
        
        found_elements = [elem for elem in expected_elements if elem in ast_structure]
        
        print(f"   📊 Extracted {len(ast_structure.splitlines())} lines")
        print(f"   ✅ Found elements: {', '.join(found_elements)}")
        
        # Show sample structure
        lines = ast_structure.splitlines()[:5]
        for line in lines:
            print(f"   {line}")
        if len(ast_structure.splitlines()) > 5:
            print(f"   ... and {len(ast_structure.splitlines()) - 5} more lines")
        
        return {
            'success': len(found_elements) >= 1,
            'lines': len(ast_structure.splitlines()),
            'elements': found_elements
        }
    
    def test_cmd(self):
        """Test CMD AST extraction"""
        print("💻 Testing CMD AST extraction...")
        
        file_path = self.test_dir / "test_cmd.cmd"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast_structure = self.extractor.extract_ast_structure(content, 'cmd')
        
        # Expected elements in CMD
        expected_elements = [
            'CALLS:', 'LABEL:'
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
    
    def test_haskell(self):
        """Test Haskell AST extraction"""
        print("🔷 Testing Haskell AST extraction...")
        
        file_path = self.test_dir / "test_haskell.hs"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast_structure = self.extractor.extract_ast_structure(content, 'haskell')
        
        # Expected elements in Haskell
        expected_elements = [
            'IMPORTS:', 'MODULE:', 'TYPE:', 'CLASS:', 'FUNCTION:'
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
            'success': len(found_elements) >= 3,
            'lines': len(ast_structure.splitlines()),
            'elements': found_elements
        }
    
    def test_toml(self):
        """Test TOML AST extraction"""
        print("📝 Testing TOML AST extraction...")
        
        file_path = self.test_dir / "test_toml.toml"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast_structure = self.extractor.extract_ast_structure(content, 'toml')
        
        # Expected elements in TOML
        expected_elements = [
            'SECTION:', 'KEY:'
        ]
        
        found_elements = [elem for elem in expected_elements if elem in ast_structure]
        
        print(f"   📊 Extracted {len(ast_structure.splitlines())} lines")
        print(f"   ✅ Found elements: {', '.join(found_elements)}")
        
        # Show sample structure
        lines = ast_structure.splitlines()[:8]
        for line in lines:
            print(f"   {line}")
        if len(ast_structure.splitlines()) > 8:
            print(f"   ... and {len(ast_structure.splitlines()) - 8} more lines")
        
        return {
            'success': len(found_elements) >= 2,
            'lines': len(ast_structure.splitlines()),
            'elements': found_elements
        }
    
    def test_sass_scss(self):
        """Test Sass/SCSS AST extraction"""
        print("🎨 Testing Sass/SCSS AST extraction...")
        
        # Test SCSS
        file_path = self.test_dir / "test_sass.scss"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast_structure = self.extractor.extract_ast_structure(content, 'scss')
        
        # Expected elements in Sass/SCSS
        expected_elements = [
            'SELECTOR:', 'MIXIN:', 'FUNCTION:', 'IMPORTS:'
        ]
        
        found_elements = [elem for elem in expected_elements if elem in ast_structure]
        
        print(f"   📊 SCSS: {len(ast_structure.splitlines())} lines")
        print(f"   ✅ Found elements: {', '.join(found_elements)}")
        
        # Test SASS
        file_path = self.test_dir / "test_sass.sass"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast_structure_sass = self.extractor.extract_ast_structure(content, 'sass')
        
        # Check SASS elements too
        sass_elements = ['SELECTOR:', 'MIXIN:', 'FUNCTION:', 'VARIABLE:']
        sass_found = [elem for elem in sass_elements if elem in ast_structure_sass]
        
        print(f"   📊 SASS: {len(ast_structure_sass.splitlines())} lines")
        print(f"   ✅ SASS elements: {', '.join(sass_found)}")
        
        # Success if either SCSS or SASS has enough elements
        scss_success = len(found_elements) >= 2
        sass_success = len(sass_found) >= 2
        
        return {
            'success': scss_success or sass_success,
            'lines': len(ast_structure.splitlines()),
            'elements': found_elements + sass_found
        }
    
    def test_julia(self):
        """Test Julia AST extraction"""
        print("🔬 Testing Julia AST extraction...")
        
        file_path = self.test_dir / "test_julia.jl"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast_structure = self.extractor.extract_ast_structure(content, 'julia')
        
        # Expected elements in Julia
        expected_elements = [
            'IMPORTS:', 'MODULE:', 'STRUCT:', 'FUNCTION:', 'MACRO:'
        ]
        
        found_elements = [elem for elem in expected_elements if elem in ast_structure]
        
        print(f"   📊 Extracted {len(ast_structure.splitlines())} lines")
        print(f"   ✅ Found elements: {', '.join(found_elements)}")
        
        # Show sample structure
        lines = ast_structure.splitlines()[:8]
        for line in lines:
            print(f"   {line}")
        if len(ast_structure.splitlines()) > 8:
            print(f"   ... and {len(ast_structure.splitlines()) - 8} more lines")
        
        return {
            'success': len(found_elements) >= 3,
            'lines': len(ast_structure.splitlines()),
            'elements': found_elements
        }
    
    def test_powershell(self):
        """Test PowerShell AST extraction"""
        print("💙 Testing PowerShell AST extraction...")
        
        file_path = self.test_dir / "test_powershell.ps1"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast_structure = self.extractor.extract_ast_structure(content, 'powershell')
        
        # Expected elements in PowerShell
        expected_elements = [
            'IMPORTS:', 'CLASS:', 'FUNCTION:', 'MODULE:'
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
            'TAG:', 'ATTRIBUTE:'
        ]
        
        found_elements = [elem for elem in expected_elements if elem in ast_structure]
        
        print(f"   📊 Extracted {len(ast_structure.splitlines())} lines")
        print(f"   ✅ Found elements: {', '.join(found_elements)}")
        
        # Show sample structure
        lines = ast_structure.splitlines()[:8]
        for line in lines:
            print(f"   {line}")
        if len(ast_structure.splitlines()) > 8:
            print(f"   ... and {len(ast_structure.splitlines()) - 8} more lines")
        
        return {
            'success': len(found_elements) >= 1,
            'lines': len(ast_structure.splitlines()),
            'elements': found_elements
        }
    
    def test_yaml(self):
        """Test YAML AST extraction"""
        print("📋 Testing YAML AST extraction...")
        
        # Test YAML
        file_path = self.test_dir / "test_yaml.yaml"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast_structure = self.extractor.extract_ast_structure(content, 'yaml')
        
        # Expected elements in YAML
        expected_elements = [
            'KEY:', 'VALUE:'
        ]
        
        found_elements = [elem for elem in expected_elements if elem in ast_structure]
        
        print(f"   📊 YAML: {len(ast_structure.splitlines())} lines")
        print(f"   ✅ Found elements: {', '.join(found_elements)}")
        
        # Test YML
        file_path = self.test_dir / "test_yml.yml"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast_structure_yml = self.extractor.extract_ast_structure(content, 'yaml')
        
        print(f"   📊 YML: {len(ast_structure_yml.splitlines())} lines")
        
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
            'TAG:', 'ATTRIBUTE:'
        ]
        
        found_elements = [elem for elem in expected_elements if elem in ast_structure]
        
        print(f"   📊 Extracted {len(ast_structure.splitlines())} lines")
        print(f"   ✅ Found elements: {', '.join(found_elements)}")
        
        # Show sample structure
        lines = ast_structure.splitlines()[:8]
        for line in lines:
            print(f"   {line}")
        if len(ast_structure.splitlines()) > 8:
            print(f"   ... and {len(ast_structure.splitlines()) - 8} more lines")
        
        return {
            'success': len(found_elements) >= 1,
            'lines': len(ast_structure.splitlines()),
            'elements': found_elements
        }
    
    def test_sql(self):
        """Test SQL AST extraction"""
        print("🗄️ Testing SQL AST extraction...")
        
        file_path = self.test_dir / "test_sql.sql"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast_structure = self.extractor.extract_ast_structure(content, 'sql')
        
        # Expected elements in SQL
        expected_elements = [
            'FUNCTION:', 'TABLE:', 'INDEX:', 'TRIGGER:'
        ]
        
        found_elements = [elem for elem in expected_elements if elem in ast_structure]
        
        print(f"   📊 Extracted {len(ast_structure.splitlines())} lines")
        print(f"   ✅ Found elements: {', '.join(found_elements)}")
        
        # Show sample structure
        lines = ast_structure.splitlines()[:8]
        for line in lines:
            print(f"   {line}")
        if len(ast_structure.splitlines()) > 8:
            print(f"   ... and {len(ast_structure.splitlines()) - 8} more lines")
        
        return {
            'success': len(found_elements) >= 1,
            'lines': len(ast_structure.splitlines()),
            'elements': found_elements
        }
    
    def test_dart(self):
        """Test Dart AST extraction"""
        print("🎯 Testing Dart AST extraction...")
        
        file_path = self.test_dir / "test_dart.dart"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast_structure = self.extractor.extract_ast_structure(content, 'dart')
        
        # Expected elements in Dart
        expected_elements = [
            'FUNCTION:', 'CLASS:', 'IMPORT:', 'EXTENSION:'
        ]
        
        found_elements = [elem for elem in expected_elements if elem in ast_structure]
        
        print(f"   📊 Extracted {len(ast_structure.splitlines())} lines")
        print(f"   ✅ Found elements: {', '.join(found_elements)}")
        
        # Show sample structure
        lines = ast_structure.splitlines()[:8]
        for line in lines:
            print(f"   {line}")
        if len(ast_structure.splitlines()) > 8:
            print(f"   ... and {len(ast_structure.splitlines()) - 8} more lines")
        
        return {
            'success': len(found_elements) >= 2,
            'lines': len(ast_structure.splitlines()),
            'elements': found_elements
        }
    
    def test_bat(self):
        """Test BAT AST extraction"""
        print("💻 Testing BAT AST extraction...")
        
        file_path = self.test_dir / "test_bat.bat"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast_structure = self.extractor.extract_ast_structure(content, 'cmd')
        
        # Expected elements in BAT
        expected_elements = [
            'CALLS:', 'LABEL:'
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
    
    def test_zsh(self):
        """Test ZSH AST extraction"""
        print("🐚 Testing ZSH AST extraction...")
        
        file_path = self.test_dir / "test_zsh.zsh"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast_structure = self.extractor.extract_ast_structure(content, 'bash')
        
        # Expected elements in ZSH
        expected_elements = [
            'FUNCTION:', 'IMPORTS:'
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
        """Run all language-specific tests"""
        print("🚀 Starting language-specific AST extraction tests...")
        print("=" * 80)
        
        # Define all test functions
        test_functions = [
            ('Python', self.test_python),
            ('Java', self.test_java),
            ('JavaScript', self.test_javascript),
            ('TypeScript', self.test_typescript),
            ('Go', self.test_go),
            ('Rust', self.test_rust),
            ('C++', self.test_cpp),
            ('C#', self.test_csharp),
            ('PHP', self.test_php),
            ('Ruby', self.test_ruby),
            ('Swift', self.test_swift),
            ('Kotlin', self.test_kotlin),
            ('Scala', self.test_scala),
            ('Groovy', self.test_groovy),
            ('R', self.test_r),
            ('Lua', self.test_lua),
            ('Bash', self.test_bash),
            ('CMD', self.test_cmd),
            ('Haskell', self.test_haskell),
            ('TOML', self.test_toml),
            ('Sass/SCSS', self.test_sass_scss),
            ('Julia', self.test_julia),
            ('PowerShell', self.test_powershell),
            ('XML', self.test_xml),
            ('YAML', self.test_yaml),
            ('HTML', self.test_html),
            ('SQL', self.test_sql),
            ('Dart', self.test_dart),
            ('BAT', self.test_bat),
            ('ZSH', self.test_zsh),
        ]
        
        results = {}
        
        for language_name, test_func in test_functions:
            try:
                print(f"\n{language_name}:")
                result = test_func()
                results[language_name] = result
                status = "✅ PASS" if result['success'] else "❌ FAIL"
                print(f"   {status}")
            except Exception as e:
                print(f"   ❌ ERROR: {str(e)}")
                results[language_name] = {'success': False, 'error': str(e)}
        
        # Summary
        print("\n" + "=" * 80)
        print("📈 SUMMARY")
        print("=" * 80)
        
        total_tests = len(test_functions)
        passed_tests = sum(1 for result in results.values() if result.get('success', False))
        
        print(f"Total languages tested: {total_tests}")
        print(f"Passed tests: {passed_tests}")
        print(f"Success rate: {passed_tests/total_tests*100:.1f}%")
        
        print("\n📋 DETAILED RESULTS:")
        for language_name, result in results.items():
            if result.get('success', False):
                elements = result.get('elements', [])
                lines = result.get('lines', 0)
                print(f"  ✅ {language_name}: {len(elements)} elements, {lines} lines")
            else:
                error = result.get('error', 'Failed validation')
                print(f"  ❌ {language_name}: {error}")
        
        print(f"\n🎯 Language-specific testing completed!")
        
        return results

if __name__ == "__main__":
    tester = LanguageTester()
    results = tester.run_all_tests()
    
    # Exit with appropriate code
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result.get('success', False))
    
    if passed_tests == total_tests:
        print("🎉 All language tests passed!")
        sys.exit(0)
    else:
        print(f"⚠️  {total_tests - passed_tests} language tests failed")
        sys.exit(1)
