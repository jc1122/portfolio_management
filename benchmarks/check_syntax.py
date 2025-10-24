#!/usr/bin/env python3
"""Basic code validation for benchmark suite (no dependencies required).

This script validates the benchmark code structure and syntax without
requiring pandas or other dependencies to be installed.

Usage:
    python benchmarks/check_syntax.py
"""

import ast
import sys
from pathlib import Path


def check_python_syntax(filepath: Path) -> tuple[bool, str]:
    """Check if a Python file has valid syntax.
    
    Args:
        filepath: Path to Python file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        with open(filepath) as f:
            code = f.read()
        ast.parse(code)
        return True, ""
    except SyntaxError as e:
        return False, f"Syntax error at line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, str(e)


def check_file_structure(filepath: Path) -> tuple[bool, list[str]]:
    """Check file structure and organization.
    
    Args:
        filepath: Path to Python file
        
    Returns:
        Tuple of (is_valid, list of issues)
    """
    issues = []
    
    try:
        with open(filepath) as f:
            code = f.read()
        
        tree = ast.parse(code)
        
        # Check for docstring
        if not ast.get_docstring(tree):
            issues.append("Missing module docstring")
        
        # Check for shebang (for scripts)
        if not code.startswith("#!"):
            issues.append("Missing shebang line")
        
        # Check for imports
        has_imports = any(isinstance(node, (ast.Import, ast.ImportFrom)) 
                         for node in ast.walk(tree))
        if not has_imports:
            issues.append("No imports found")
        
        # Check for main guard
        has_main_guard = "__main__" in code
        if not has_main_guard:
            issues.append("Missing if __name__ == '__main__' guard")
        
        # Check for functions
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        if not functions:
            issues.append("No functions defined")
        
        # Check for classes (dataclasses for benchmarks)
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        
        return len(issues) == 0, issues
    
    except Exception as e:
        return False, [f"Error analyzing file: {e}"]


def check_benchmark_script():
    """Check the main benchmark script."""
    print("=" * 60)
    print("Checking benchmark_fast_io.py")
    print("=" * 60)
    
    script_path = Path(__file__).parent / "benchmark_fast_io.py"
    
    if not script_path.exists():
        print(f"❌ File not found: {script_path}")
        return False
    
    print(f"📄 File: {script_path}")
    print(f"📊 Size: {script_path.stat().st_size / 1024:.1f} KB")
    
    # Check syntax
    is_valid, error = check_python_syntax(script_path)
    if is_valid:
        print("✅ Valid Python syntax")
    else:
        print(f"❌ Syntax error: {error}")
        return False
    
    # Check structure
    is_valid, issues = check_file_structure(script_path)
    if is_valid:
        print("✅ Good file structure")
    else:
        print("⚠️  File structure issues:")
        for issue in issues:
            print(f"   - {issue}")
    
    # Count lines of code
    with open(script_path) as f:
        lines = f.readlines()
    
    code_lines = sum(1 for line in lines if line.strip() and not line.strip().startswith('#'))
    comment_lines = sum(1 for line in lines if line.strip().startswith('#'))
    blank_lines = sum(1 for line in lines if not line.strip())
    
    print(f"\n📈 Code Statistics:")
    print(f"   Total lines: {len(lines)}")
    print(f"   Code lines: {code_lines}")
    print(f"   Comment lines: {comment_lines}")
    print(f"   Blank lines: {blank_lines}")
    
    # Check for key components
    with open(script_path) as f:
        content = f.read()
    
    components = {
        'BenchmarkResult': '@dataclass' in content and 'BenchmarkResult' in content,
        'CSV benchmarks': 'benchmark_csv_read' in content,
        'Parquet benchmarks': 'benchmark_parquet' in content or 'parquet' in content.lower(),
        'Memory profiling': 'memory' in content.lower() and 'psutil' in content,
        'CLI interface': 'argparse' in content,
        'JSON output': 'json.dump' in content,
        'Result equivalence': 'equivalence' in content.lower(),
    }
    
    print(f"\n🔍 Key Components:")
    for component, present in components.items():
        status = "✅" if present else "❌"
        print(f"   {status} {component}")
    
    return all(components.values())


def check_validation_script():
    """Check the validation script."""
    print("\n" + "=" * 60)
    print("Checking validate_benchmark.py")
    print("=" * 60)
    
    script_path = Path(__file__).parent / "validate_benchmark.py"
    
    if not script_path.exists():
        print(f"❌ File not found: {script_path}")
        return False
    
    print(f"📄 File: {script_path}")
    
    # Check syntax
    is_valid, error = check_python_syntax(script_path)
    if is_valid:
        print("✅ Valid Python syntax")
    else:
        print(f"❌ Syntax error: {error}")
        return False
    
    # Check for validation functions
    with open(script_path) as f:
        content = f.read()
    
    checks = {
        'Import checking': 'check_imports' in content,
        'Backend checking': 'check_backend' in content,
        'Functionality test': 'test_basic' in content or 'test_functionality' in content,
    }
    
    print(f"\n🔍 Validation Checks:")
    for check, present in checks.items():
        status = "✅" if present else "❌"
        print(f"   {status} {check}")
    
    return all(checks.values())


def check_documentation():
    """Check documentation files."""
    print("\n" + "=" * 60)
    print("Checking Documentation")
    print("=" * 60)
    
    docs = [
        (Path(__file__).parent / "README.md", "Benchmark README"),
        (Path(__file__).parent.parent / "docs" / "performance" / "fast_io_benchmarks.md", 
         "Performance Documentation"),
    ]
    
    all_valid = True
    
    for doc_path, doc_name in docs:
        if not doc_path.exists():
            print(f"❌ {doc_name} not found: {doc_path}")
            all_valid = False
            continue
        
        size_kb = doc_path.stat().st_size / 1024
        
        with open(doc_path) as f:
            content = f.read()
        
        lines = content.count('\n')
        headers = content.count('#')
        code_blocks = content.count('```')
        
        print(f"\n📄 {doc_name}")
        print(f"   Location: {doc_path.name}")
        print(f"   Size: {size_kb:.1f} KB")
        print(f"   Lines: {lines}")
        print(f"   Headers: {headers}")
        print(f"   Code blocks: {code_blocks // 2}")  # Each block has opening and closing
        
        if lines < 100:
            print(f"   ⚠️  Documentation might be incomplete ({lines} lines)")
        else:
            print(f"   ✅ Comprehensive documentation")
    
    return all_valid


def main():
    """Run all code validation checks."""
    print("\n🔍 Benchmark Suite Code Validation")
    print("=" * 60)
    print("This validates code structure without requiring dependencies")
    print("=" * 60)
    
    results = {
        'benchmark_script': check_benchmark_script(),
        'validation_script': check_validation_script(),
        'documentation': check_documentation(),
    }
    
    # Summary
    print("\n" + "=" * 60)
    print("Validation Summary")
    print("=" * 60)
    
    for check, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check.replace('_', ' ').title()}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n✅ All code validation checks passed!")
        print("\n📚 Next Steps:")
        print("   1. Install dependencies: pip install pandas numpy polars pyarrow psutil")
        print("   2. Run validation: python benchmarks/validate_benchmark.py")
        print("   3. Run benchmarks: python benchmarks/benchmark_fast_io.py --all")
    else:
        print("\n❌ Some validation checks failed. Review output above.")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
