#!/usr/bin/env python3
"""Validation script for fast IO benchmark suite.

This script performs basic validation checks on the benchmark implementation
to ensure everything is set up correctly before running full benchmarks.

Usage:
    python benchmarks/validate_benchmark.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def check_imports():
    """Check that all required modules can be imported."""
    print("=" * 60)
    print("Checking Imports")
    print("=" * 60)
    
    errors = []
    
    # Core dependencies
    try:
        import pandas as pd
        print(f"✅ pandas {pd.__version__}")
    except ImportError as e:
        print(f"❌ pandas: {e}")
        errors.append("pandas")
    
    try:
        import numpy as np
        print(f"✅ numpy {np.__version__}")
    except ImportError as e:
        print(f"❌ numpy: {e}")
        errors.append("numpy")
    
    # Fast IO module
    try:
        from portfolio_management.data.io.fast_io import (
            get_available_backends,
            read_csv_fast,
            read_parquet_fast,
        )
        print("✅ fast_io module")
    except ImportError as e:
        print(f"❌ fast_io module: {e}")
        errors.append("fast_io")
    
    # Optional dependencies
    try:
        import polars as pl
        print(f"✅ polars {pl.__version__}")
    except ImportError:
        print("⚠️  polars (optional, recommended for speed)")
    
    try:
        import pyarrow as pa
        print(f"✅ pyarrow {pa.__version__}")
    except ImportError:
        print("⚠️  pyarrow (optional, recommended for Parquet)")
    
    try:
        import psutil
        print(f"✅ psutil {psutil.__version__}")
    except ImportError:
        print("⚠️  psutil (optional, for memory profiling)")
    
    return errors


def check_backend_availability():
    """Check which IO backends are available."""
    print("\n" + "=" * 60)
    print("Backend Availability")
    print("=" * 60)
    
    try:
        from portfolio_management.data.io.fast_io import (
            get_available_backends,
            is_backend_available,
        )
        
        available = get_available_backends()
        print(f"Available backends: {', '.join(available)}")
        
        for backend in ['pandas', 'polars', 'pyarrow']:
            status = "✅" if is_backend_available(backend) else "❌"
            print(f"{status} {backend}")
        
        if len(available) == 1:
            print("\n⚠️  Only pandas available. Install optional backends:")
            print("    pip install polars pyarrow")
        
        return len(available) > 1
    
    except Exception as e:
        print(f"❌ Error checking backends: {e}")
        return False


def check_benchmark_script():
    """Check that the benchmark script is accessible."""
    print("\n" + "=" * 60)
    print("Benchmark Script")
    print("=" * 60)
    
    script_path = Path(__file__).parent / "benchmark_fast_io.py"
    
    if script_path.exists():
        print(f"✅ Found: {script_path}")
        
        # Check if executable
        if script_path.stat().st_mode & 0o111:
            print("✅ Script is executable")
        else:
            print("⚠️  Script is not executable (chmod +x to make executable)")
        
        return True
    else:
        print(f"❌ Not found: {script_path}")
        return False


def check_documentation():
    """Check that documentation exists."""
    print("\n" + "=" * 60)
    print("Documentation")
    print("=" * 60)
    
    docs = [
        Path(__file__).parent.parent / "docs" / "performance" / "fast_io_benchmarks.md",
        Path(__file__).parent / "README.md",
    ]
    
    all_exist = True
    for doc in docs:
        if doc.exists():
            size_kb = doc.stat().st_size / 1024
            print(f"✅ {doc.name} ({size_kb:.1f} KB)")
        else:
            print(f"❌ {doc.name} not found")
            all_exist = False
    
    return all_exist


def test_basic_functionality():
    """Test basic fast IO functionality."""
    print("\n" + "=" * 60)
    print("Functionality Test")
    print("=" * 60)
    
    try:
        import pandas as pd
        import numpy as np
        from tempfile import TemporaryDirectory
        from portfolio_management.data.io.fast_io import read_csv_fast
        
        with TemporaryDirectory() as tmpdir:
            # Create test CSV
            test_csv = Path(tmpdir) / "test.csv"
            df_original = pd.DataFrame({
                'date': pd.date_range('2020-01-01', periods=100),
                'value': np.random.randn(100),
            })
            df_original.to_csv(test_csv, index=False)
            print(f"✅ Created test CSV ({len(df_original)} rows)")
            
            # Test reading with available backends
            from portfolio_management.data.io.fast_io import get_available_backends
            
            for backend in get_available_backends():
                try:
                    df = read_csv_fast(test_csv, backend=backend)
                    if len(df) == len(df_original):
                        print(f"✅ {backend}: Read {len(df)} rows")
                    else:
                        print(f"❌ {backend}: Row count mismatch ({len(df)} vs {len(df_original)})")
                except Exception as e:
                    print(f"❌ {backend}: {e}")
        
        return True
    
    except Exception as e:
        print(f"❌ Functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def print_recommendations():
    """Print recommendations based on validation results."""
    print("\n" + "=" * 60)
    print("Recommendations")
    print("=" * 60)
    
    from portfolio_management.data.io.fast_io import get_available_backends
    available = get_available_backends()
    
    if len(available) == 1:
        print("\n⚠️  Limited Performance")
        print("Only pandas is available. To unlock fast IO:")
        print("  pip install polars      # 4-5x speedup")
        print("  pip install pyarrow     # 2-3x speedup")
    elif 'polars' in available:
        print("\n✅ Optimal Configuration")
        print("All fast backends available. Run benchmarks with:")
        print("  python benchmarks/benchmark_fast_io.py --all")
    else:
        print("\n⚠️  Partial Configuration")
        print("Some backends available. For maximum speed:")
        print("  pip install polars      # 4-5x speedup")
    
    print("\n📚 Next Steps:")
    print("  1. Run validation: python benchmarks/validate_benchmark.py")
    print("  2. Run benchmarks: python benchmarks/benchmark_fast_io.py --all")
    print("  3. Review results: docs/performance/fast_io_benchmarks.md")


def main():
    """Run all validation checks."""
    print("\n🔍 Fast IO Benchmark Validation")
    print("=" * 60)
    
    results = {
        'imports': True,
        'backends': True,
        'script': True,
        'docs': True,
        'functionality': True,
    }
    
    # Run checks
    import_errors = check_imports()
    results['imports'] = len(import_errors) == 0
    
    if not results['imports']:
        print("\n❌ Cannot proceed - core dependencies missing:")
        for error in import_errors:
            print(f"   - {error}")
        print("\nInstall with: pip install pandas numpy")
        return 1
    
    results['backends'] = check_backend_availability()
    results['script'] = check_benchmark_script()
    results['docs'] = check_documentation()
    results['functionality'] = test_basic_functionality()
    
    # Summary
    print("\n" + "=" * 60)
    print("Validation Summary")
    print("=" * 60)
    
    for check, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check.replace('_', ' ').title()}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n✅ All checks passed! Ready to run benchmarks.")
    else:
        print("\n⚠️  Some checks failed. Review output above.")
    
    print_recommendations()
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
