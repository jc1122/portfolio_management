#!/usr/bin/env python3
"""Simple script to verify preselection module imports work correctly."""

import sys
from pathlib import Path

# Add src to path
repo_root = Path(__file__).resolve().parent
sys.path.insert(0, str(repo_root / "src"))

print("Testing preselection module imports...")

try:
    # Test basic imports
    from portfolio_management.portfolio.preselection import (
        Preselection,
        PreselectionConfig,
        PreselectionMethod,
        create_preselection_from_dict,
    )
    print("✓ Direct imports work")

    # Test package-level imports
    from portfolio_management.portfolio import (
        Preselection as Preselection2,
        PreselectionConfig as Config2,
        PreselectionMethod as Method2,
        create_preselection_from_dict as create2,
    )
    print("✓ Package-level imports work")

    # Test enum values
    assert PreselectionMethod.MOMENTUM.value == "momentum"
    assert PreselectionMethod.LOW_VOL.value == "low_vol"
    assert PreselectionMethod.COMBINED.value == "combined"
    print("✓ Enum values correct")

    # Test config creation
    config = PreselectionConfig(
        method=PreselectionMethod.MOMENTUM,
        top_k=10,
        lookback=252,
    )
    assert config.method == PreselectionMethod.MOMENTUM
    assert config.top_k == 10
    assert config.lookback == 252
    print("✓ Config creation works")

    # Test preselection creation
    preselection = Preselection(config)
    assert preselection.config.method == PreselectionMethod.MOMENTUM
    print("✓ Preselection creation works")

    # Test dict-based creation
    config_dict = {
        "method": "momentum",
        "top_k": 20,
        "lookback": 120,
    }
    preselection2 = create_preselection_from_dict(config_dict)
    assert preselection2 is not None
    assert preselection2.config.top_k == 20
    print("✓ Dict-based creation works")

    # Test disabled preselection
    disabled = create_preselection_from_dict({"top_k": 0})
    assert disabled is None
    print("✓ Disabled preselection returns None")

    # Test BacktestEngine import
    from portfolio_management.backtesting.engine.backtest import BacktestEngine
    print("✓ BacktestEngine imports work")

    # Test universe definition import
    from portfolio_management.assets.universes.universes import UniverseDefinition
    print("✓ UniverseDefinition imports work")

    print("\n✅ All import tests passed!")
    sys.exit(0)

except Exception as e:
    print(f"\n❌ Import test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
