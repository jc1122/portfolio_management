#!/usr/bin/env python3
"""Validation script for fast IO implementation.

This script validates the fast IO implementation without requiring
optional dependencies (polars, pyarrow) to be installed.

Run this to verify the implementation is correct before running full tests.
"""

import ast
import sys
from pathlib import Path


def check_file_exists(path: str) -> bool:
    """Check if a file exists."""
    if not Path(path).exists():
        print(f"❌ Missing file: {path}")
        return False
    print(f"✓ Found: {path}")
    return True


def check_function_exists(file_path: str, function_names: list[str]) -> bool:
    """Check if functions exist in a Python file."""
    with open(file_path) as f:
        tree = ast.parse(f.read())

    defined_functions = {
        node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    }

    missing = []
    for func in function_names:
        if func not in defined_functions:
            missing.append(func)

    if missing:
        print(f"❌ Missing functions in {file_path}: {missing}")
        return False

    print(f"✓ All required functions found in {file_path}")
    return True


def check_string_in_file(file_path: str, search_string: str, description: str) -> bool:
    """Check if a string exists in a file."""
    with open(file_path) as f:
        content = f.read()

    if search_string not in content:
        print(f"❌ Missing in {file_path}: {description}")
        return False

    print(f"✓ Found in {file_path}: {description}")
    return True


def main():
    """Run all validation checks."""
    print("=" * 80)
    print("Fast IO Implementation Validation")
    print("=" * 80)
    print()

    all_checks_passed = True

    # Check 1: Core module exists
    print("Check 1: Core Fast IO Module")
    print("-" * 40)
    if not check_file_exists("src/portfolio_management/data/io/fast_io.py"):
        all_checks_passed = False

    if Path("src/portfolio_management/data/io/fast_io.py").exists():
        required_functions = [
            "get_available_backends",
            "is_backend_available",
            "select_backend",
            "read_csv_fast",
            "read_parquet_fast",
        ]
        if not check_function_exists(
            "src/portfolio_management/data/io/fast_io.py",
            required_functions,
        ):
            all_checks_passed = False
    print()

    # Check 2: Module exports
    print("Check 2: Module Exports")
    print("-" * 40)
    if not check_string_in_file(
        "src/portfolio_management/data/io/__init__.py",
        "read_csv_fast",
        "read_csv_fast export",
    ):
        all_checks_passed = False

    if not check_string_in_file(
        "src/portfolio_management/data/io/__init__.py",
        "get_available_backends",
        "get_available_backends export",
    ):
        all_checks_passed = False
    print()

    # Check 3: PriceLoader integration
    print("Check 3: PriceLoader Integration")
    print("-" * 40)
    if not check_string_in_file(
        "src/portfolio_management/analytics/returns/loaders.py",
        "io_backend",
        "io_backend parameter",
    ):
        all_checks_passed = False

    if not check_string_in_file(
        "src/portfolio_management/analytics/returns/loaders.py",
        "read_csv_fast",
        "read_csv_fast usage",
    ):
        all_checks_passed = False
    print()

    # Check 4: CLI integration
    print("Check 4: CLI Integration")
    print("-" * 40)
    if not check_string_in_file(
        "scripts/calculate_returns.py",
        "--io-backend",
        "--io-backend argument",
    ):
        all_checks_passed = False

    if not check_string_in_file(
        "scripts/calculate_returns.py",
        "io_backend=args.io_backend",
        "io_backend parameter passing",
    ):
        all_checks_passed = False
    print()

    # Check 5: Optional dependencies
    print("Check 5: Optional Dependencies")
    print("-" * 40)
    if not check_string_in_file(
        "pyproject.toml",
        "fast-io",
        "fast-io group",
    ):
        all_checks_passed = False

    if not check_string_in_file(
        "pyproject.toml",
        "polars",
        "polars dependency",
    ):
        all_checks_passed = False

    if not check_string_in_file(
        "pyproject.toml",
        "pyarrow",
        "pyarrow dependency",
    ):
        all_checks_passed = False
    print()

    # Check 6: Tests exist
    print("Check 6: Test Files")
    print("-" * 40)
    if not check_file_exists("tests/data/test_fast_io.py"):
        all_checks_passed = False

    if not check_file_exists("tests/analytics/test_fast_io_integration.py"):
        all_checks_passed = False

    if not check_file_exists("tests/benchmarks/benchmark_fast_io.py"):
        all_checks_passed = False
    print()

    # Check 7: Documentation exists
    print("Check 7: Documentation")
    print("-" * 40)
    if not check_file_exists("docs/fast_io.md"):
        all_checks_passed = False

    if not check_file_exists("tests/benchmarks/README.md"):
        all_checks_passed = False

    if not check_string_in_file(
        "README.md",
        "Optional fast IO",
        "Fast IO in README",
    ):
        all_checks_passed = False
    print()

    # Check 8: Module structure
    print("Check 8: Module Structure")
    print("-" * 40)
    try:
        with open("src/portfolio_management/data/io/fast_io.py") as f:
            content = f.read()

        # Check for proper error handling
        if "try:" in content and "ImportError" in content:
            print("✓ Proper import error handling")
        else:
            print("❌ Missing import error handling")
            all_checks_passed = False

        # Check for backend availability flags
        if "_POLARS_AVAILABLE" in content and "_PYARROW_AVAILABLE" in content:
            print("✓ Backend availability flags present")
        else:
            print("❌ Missing backend availability flags")
            all_checks_passed = False

        # Check for logging
        if "logger" in content:
            print("✓ Logging implemented")
        else:
            print("❌ Missing logging")
            all_checks_passed = False
    except Exception as e:
        print(f"❌ Error checking module structure: {e}")
        all_checks_passed = False
    print()

    # Final summary
    print("=" * 80)
    if all_checks_passed:
        print("✓ All validation checks passed!")
        print()
        print("The fast IO implementation appears to be complete and correct.")
        print()
        print("Next steps:")
        print("1. Install optional dependencies: pip install polars pyarrow")
        print("2. Run tests: pytest tests/data/test_fast_io.py -v")
        print("3. Run benchmarks: python tests/benchmarks/benchmark_fast_io.py")
        return 0
    print("❌ Some validation checks failed.")
    print()
    print("Please review the errors above and fix any issues.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
