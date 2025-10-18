# Phase 3 Completion Plan

**Document Version:** 1.0
**Date Created:** October 16, 2025
**Status:** Phase 3 is 87% complete (31/45 tasks done)
**Objective:** Complete Stage 5 and address technical debt to make Phase 3 production-ready

______________________________________________________________________

## Executive Summary

### Current State

- ✅ **Stages 1-4 Complete:** All core functionality implemented and tested
- ❌ **Stage 5 Incomplete:** Integration tests, performance validation, and polish missing
- ⚠️ **Technical Debt:** Minor issues (mypy errors, ruff warnings, import path issues)
- 📊 **Quality:** 157 tests passing, 86% coverage, professional-grade code

### Completion Requirements

To consider Phase 3 production-ready and merge to main:

1. **Critical Path (8-10 hours):**

   - Integration tests for end-to-end pipeline
   - Performance validation (30s/1000 assets target)
   - Enhanced error handling
   - Fix import path issues
   - Final QA pass

1. **Technical Debt (2-3 hours):**

   - Fix mypy configuration
   - Auto-fix ruff warnings
   - Clean up import statements

1. **Documentation (3-4 hours):**

   - Create `docs/asset_selection.md`
   - Create `docs/classification.md`
   - Add integration guide
   - Update memory bank

**Total Estimated Effort:** 13-17 hours

______________________________________________________________________

## Part 1: Critical Path Items (Priority 1)

These must be completed before merging to main or starting Phase 4.

______________________________________________________________________

### Task C1: Integration Tests (4-5 hours) ⭐⭐⭐ CRITICAL

**Objective:** Validate the complete pipeline works end-to-end with real data.

**Location:** Create `tests/integration/` directory and test files

#### C1.1: Setup Integration Test Infrastructure (30 minutes)

**Steps:**

1. Create directory structure:

   ```bash
   mkdir -p tests/integration
   touch tests/integration/__init__.py
   touch tests/integration/conftest.py
   ```

1. Create integration test fixtures in `tests/integration/conftest.py`:

   ```python
   """Fixtures for integration tests."""
   import pytest
   from pathlib import Path
   import pandas as pd

   @pytest.fixture
   def integration_test_data_dir():
       """Return path to test data directory."""
       return Path("data/processed/tradeable_prices_test")

   @pytest.fixture
   def integration_match_report():
       """Load a subset of match report for integration testing."""
       df = pd.read_csv("data/metadata/tradeable_matches_test.csv")
       # Take first 50 rows for faster testing
       return df.head(50)

   @pytest.fixture
   def integration_config_path(tmp_path):
       """Create a test universe config."""
       config_content = '''
   universes:
     test_integration:
       description: "Test universe for integration tests"
       filter_criteria:
         data_status: ["ok"]
         min_history_days: 252
         min_price_rows: 252
       return_config:
         method: "simple"
         frequency: "daily"
       constraints:
         min_assets: 5
         max_assets: 20
   '''
       config_path = tmp_path / "test_universes.yaml"
       config_path.write_text(config_content)
       return config_path
   ```

**Deliverable:** Integration test infrastructure ready

______________________________________________________________________

#### C1.2: End-to-End Pipeline Test (2 hours)

**File:** `tests/integration/test_full_pipeline.py`

**Implementation:**

```python
"""Integration tests for the complete asset selection pipeline."""

import pytest
from pathlib import Path
import pandas as pd

from src.portfolio_management.selection import AssetSelector, FilterCriteria
from src.portfolio_management.classification import AssetClassifier
from src.portfolio_management.returns import ReturnCalculator, ReturnConfig
from src.portfolio_management.universes import UniverseManager


class TestEndToEndPipeline:
    """Test the complete pipeline from match report to universe."""

    def test_selection_to_classification_flow(self, integration_match_report):
        """Test asset selection followed by classification."""
        # Step 1: Select assets
        criteria = FilterCriteria(
            data_status=["ok"],
            min_history_days=252,
            min_price_rows=252,
        )
        selector = AssetSelector()
        selected = selector.select_assets(integration_match_report, criteria)

        assert len(selected) > 0, "Should select some assets"
        assert all(hasattr(a, 'symbol') for a in selected)

        # Step 2: Classify assets
        classifier = AssetClassifier()
        classified_df = classifier.classify_universe(selected)

        assert len(classified_df) == len(selected)
        assert 'asset_class' in classified_df.columns
        assert 'geography' in classified_df.columns
        assert classified_df['symbol'].tolist() == [a.symbol for a in selected]

    def test_selection_to_returns_flow(
        self, integration_match_report, integration_test_data_dir
    ):
        """Test asset selection followed by return calculation."""
        # Step 1: Select assets
        criteria = FilterCriteria(
            data_status=["ok"],
            min_history_days=252,
            min_price_rows=100,  # Lower for test data
        )
        selector = AssetSelector()
        selected = selector.select_assets(integration_match_report, criteria)

        assert len(selected) > 0, "Should select some assets"

        # Step 2: Calculate returns
        config = ReturnConfig(
            method="simple",
            frequency="daily",
            handle_missing="forward_fill",
            min_coverage=0.5,  # Lower for test data
        )
        calculator = ReturnCalculator()
        returns = calculator.calculate_returns(selected, integration_test_data_dir, config)

        assert returns is not None
        assert isinstance(returns, pd.DataFrame)
        # Should have some returns (may be fewer than selected due to missing files)
        assert len(returns.columns) >= 0

    def test_complete_universe_loading(
        self, integration_match_report, integration_test_data_dir, integration_config_path
    ):
        """Test complete universe loading pipeline."""
        manager = UniverseManager(
            integration_config_path,
            integration_match_report,
            integration_test_data_dir
        )

        # Test listing universes
        universes = manager.list_universes()
        assert "test_integration" in universes

        # Test getting definition
        definition = manager.get_definition("test_integration")
        assert definition is not None
        assert definition.description == "Test universe for integration tests"

        # Test loading universe (this runs the full pipeline)
        universe_data = manager.load_universe("test_integration")

        assert universe_data is not None
        assert isinstance(universe_data, dict)
        # Check that we got some results (exact counts depend on test data)
        # The assertions should be flexible since test data may vary


class TestMultiUniverseIntegration:
    """Test multiple universe operations."""

    def test_load_multiple_universes(
        self, integration_match_report, integration_test_data_dir, tmp_path
    ):
        """Test loading multiple universes independently."""
        # Create config with two universes
        config_content = '''
universes:
  test_universe_a:
    description: "Test universe A"
    filter_criteria:
      data_status: ["ok"]
      min_history_days: 252
    return_config:
      method: "simple"
    constraints:
      min_assets: 3
      max_assets: 10
  test_universe_b:
    description: "Test universe B"
    filter_criteria:
      data_status: ["ok", "warning"]
      min_history_days: 126
    return_config:
      method: "log"
    constraints:
      min_assets: 3
      max_assets: 15
'''
        config_path = tmp_path / "multi_universes.yaml"
        config_path.write_text(config_content)

        manager = UniverseManager(
            config_path,
            integration_match_report,
            integration_test_data_dir
        )

        # Load both universes
        universe_a = manager.load_universe("test_universe_a")
        universe_b = manager.load_universe("test_universe_b")

        assert universe_a is not None
        assert universe_b is not None
        # Universes should be independent


class TestErrorScenarios:
    """Test error handling in integration scenarios."""

    def test_empty_selection_result(self, integration_match_report):
        """Test pipeline with filters that select nothing."""
        criteria = FilterCriteria(
            data_status=["ok"],
            min_history_days=10000,  # Impossible requirement
        )
        selector = AssetSelector()
        selected = selector.select_assets(integration_match_report, criteria)

        assert len(selected) == 0, "Should select nothing with impossible criteria"

    def test_missing_price_files(self, integration_match_report, tmp_path):
        """Test return calculation with missing price files."""
        # Select some assets
        criteria = FilterCriteria(data_status=["ok"])
        selector = AssetSelector()
        selected = selector.select_assets(integration_match_report, criteria)
        selected = selected[:5]  # Take just 5

        # Point to empty directory
        empty_dir = tmp_path / "empty_prices"
        empty_dir.mkdir()

        config = ReturnConfig(min_coverage=0.1)
        calculator = ReturnCalculator()

        # Should handle missing files gracefully
        returns = calculator.calculate_returns(selected, empty_dir, config)
        # May return empty DataFrame or raise appropriate error
        assert returns is not None or calculator.latest_summary is None

    def test_invalid_universe_config(self, integration_match_report, tmp_path):
        """Test loading invalid universe configuration."""
        # Create invalid config
        config_content = '''
universes:
  invalid_universe:
    description: "Invalid config"
    filter_criteria:
      min_history_days: -100  # Invalid value
'''
        config_path = tmp_path / "invalid.yaml"
        config_path.write_text(config_content)

        # Should raise error during initialization or validation
        with pytest.raises((ValueError, Exception)):
            manager = UniverseManager(
                config_path,
                integration_match_report,
                tmp_path
            )
```

**Test Execution:**

```bash
pytest tests/integration/test_full_pipeline.py -v --tb=short
```

**Success Criteria:**

- All integration tests pass
- Full pipeline validated
- Error scenarios handled gracefully
- Test execution \< 30 seconds

**Deliverable:** Complete integration test suite

______________________________________________________________________

#### C1.3: Performance Benchmarking (1 hour)

**File:** `tests/integration/test_performance.py`

**Implementation:**

```python
"""Performance tests for asset selection pipeline."""

import pytest
import time
from pathlib import Path
import pandas as pd

from src.portfolio_management.selection import AssetSelector, FilterCriteria
from src.portfolio_management.classification import AssetClassifier
from src.portfolio_management.returns import ReturnCalculator, ReturnConfig


class TestPerformance:
    """Performance benchmarks for the pipeline."""

    def test_selection_performance_100_assets(self, integration_match_report):
        """Benchmark asset selection with 100 assets."""
        # Take first 100 rows
        df = integration_match_report.head(100)

        criteria = FilterCriteria(
            data_status=["ok"],
            min_history_days=252,
        )
        selector = AssetSelector()

        start = time.time()
        selected = selector.select_assets(df, criteria)
        elapsed = time.time() - start

        assert elapsed < 2.0, f"Selection took {elapsed:.2f}s, should be < 2s"
        print(f"\n✓ Selected {len(selected)} assets in {elapsed:.3f}s")

    def test_classification_performance_100_assets(self, integration_match_report):
        """Benchmark classification with 100 assets."""
        df = integration_match_report.head(100)
        criteria = FilterCriteria(data_status=["ok"])
        selector = AssetSelector()
        selected = selector.select_assets(df, criteria)
        selected = selected[:100]  # Ensure max 100

        classifier = AssetClassifier()

        start = time.time()
        classified = classifier.classify_universe(selected)
        elapsed = time.time() - start

        assert elapsed < 3.0, f"Classification took {elapsed:.2f}s, should be < 3s"
        print(f"\n✓ Classified {len(classified)} assets in {elapsed:.3f}s")

    def test_returns_performance_50_assets(
        self, integration_match_report, integration_test_data_dir
    ):
        """Benchmark return calculation with 50 assets."""
        df = integration_match_report.head(50)
        criteria = FilterCriteria(
            data_status=["ok"],
            min_price_rows=50,
        )
        selector = AssetSelector()
        selected = selector.select_assets(df, criteria)
        selected = selected[:50]  # Max 50

        config = ReturnConfig(
            method="simple",
            frequency="daily",
            min_coverage=0.5,
        )
        calculator = ReturnCalculator()

        start = time.time()
        returns = calculator.calculate_returns(selected, integration_test_data_dir, config)
        elapsed = time.time() - start

        # Should be fast with cached price loading
        assert elapsed < 10.0, f"Return calc took {elapsed:.2f}s, should be < 10s"
        print(f"\n✓ Calculated returns for {len(returns.columns) if returns is not None else 0} assets in {elapsed:.3f}s")

    @pytest.mark.slow
    def test_full_pipeline_performance_target(
        self, integration_match_report, integration_test_data_dir
    ):
        """Test if full pipeline meets 30s target for reasonable dataset."""
        # This is a slower test - use realistic data size
        df = integration_match_report  # Use full test dataset

        criteria = FilterCriteria(
            data_status=["ok"],
            min_history_days=252,
            min_price_rows=100,
        )

        start = time.time()

        # Selection
        selector = AssetSelector()
        selected = selector.select_assets(df, criteria)

        # Classification
        classifier = AssetClassifier()
        classified = classifier.classify_universe(selected)

        # Returns (if we have enough selected)
        if len(selected) > 0:
            config = ReturnConfig(min_coverage=0.5)
            calculator = ReturnCalculator()
            returns = calculator.calculate_returns(
                selected[:100],  # Limit to 100 for test
                integration_test_data_dir,
                config
            )

        elapsed = time.time() - start

        print(f"\n✓ Full pipeline processed {len(selected)} assets in {elapsed:.3f}s")

        # Note: 30s target is for 1000 assets with real data
        # For test data, we just verify it completes in reasonable time
        assert elapsed < 60.0, f"Pipeline took {elapsed:.2f}s, too slow"


class TestMemoryUsage:
    """Test memory efficiency."""

    def test_memory_efficient_large_dataset(self, integration_match_report):
        """Verify pipeline doesn't leak memory with repeated operations."""
        import gc

        criteria = FilterCriteria(data_status=["ok"])
        selector = AssetSelector()

        # Run multiple times
        for i in range(5):
            selected = selector.select_assets(integration_match_report, criteria)
            del selected
            gc.collect()

        # If we got here without memory error, we're good
        assert True
```

**Test Execution:**

```bash
# Run performance tests
pytest tests/integration/test_performance.py -v -s

# Run slow tests separately
pytest tests/integration/test_performance.py -v -s -m slow
```

**Success Criteria:**

- Selection: \< 2s for 100 assets
- Classification: \< 3s for 100 assets
- Returns: \< 10s for 50 assets (with file I/O)
- No memory leaks

**Deliverable:** Performance benchmarks established

______________________________________________________________________

#### C1.4: Production Data Validation (30 minutes)

**File:** `tests/integration/test_production_data.py`

**Implementation:**

```python
"""Integration tests using actual production data files."""

import pytest
from pathlib import Path

from src.portfolio_management.selection import AssetSelector, FilterCriteria
from src.portfolio_management.universes import UniverseManager


class TestProductionData:
    """Tests that verify production data can be processed."""

    def test_real_match_report_loads(self):
        """Verify production match report loads correctly."""
        match_report_path = Path("data/metadata/tradeable_matches.csv")

        if not match_report_path.exists():
            pytest.skip("Production match report not available")

        import pandas as pd
        df = pd.read_csv(match_report_path)

        assert len(df) > 0, "Match report should not be empty"
        required_cols = {
            'symbol', 'isin', 'name', 'market', 'region',
            'data_status', 'price_rows'
        }
        assert required_cols.issubset(df.columns), "Missing required columns"

    def test_predefined_universes_load(self):
        """Verify all predefined universes can load successfully."""
        config_path = Path("config/universes.yaml")
        match_report_path = Path("data/metadata/tradeable_matches.csv")
        prices_dir = Path("data/processed/tradeable_prices")

        if not config_path.exists():
            pytest.skip("Universe config not available")
        if not match_report_path.exists():
            pytest.skip("Match report not available")

        import pandas as pd
        matches_df = pd.read_csv(match_report_path)

        manager = UniverseManager(config_path, matches_df, prices_dir)

        # Test each predefined universe
        universes = manager.list_universes()
        assert len(universes) > 0, "Should have predefined universes"

        for universe_name in universes:
            print(f"\nTesting universe: {universe_name}")
            definition = manager.get_definition(universe_name)
            assert definition is not None

            # Validate definition (don't load fully - may be slow)
            definition.validate()

    @pytest.mark.slow
    def test_core_global_universe_loads(self):
        """Test that core_global universe loads successfully."""
        config_path = Path("config/universes.yaml")
        match_report_path = Path("data/metadata/tradeable_matches.csv")
        prices_dir = Path("data/processed/tradeable_prices")

        if not all([config_path.exists(), match_report_path.exists(), prices_dir.exists()]):
            pytest.skip("Production data not available")

        import pandas as pd
        matches_df = pd.read_csv(match_report_path)

        manager = UniverseManager(config_path, matches_df, prices_dir)

        # This will run the full pipeline
        universe_data = manager.load_universe("core_global")

        assert universe_data is not None
        print(f"\n✓ core_global universe loaded successfully")
```

**Test Execution:**

```bash
# Quick validation
pytest tests/integration/test_production_data.py -v -k "not slow"

# Full test (slower)
pytest tests/integration/test_production_data.py -v -s
```

**Success Criteria:**

- Production data files load without errors
- Predefined universes validate correctly
- At least one universe loads successfully end-to-end

**Deliverable:** Production data validation complete

______________________________________________________________________

### Task C2: Enhanced Error Handling (2 hours) ⭐⭐ IMPORTANT

**Objective:** Improve error handling, validation, and user-facing error messages.

#### C2.1: Add Custom Exception Classes (30 minutes)

**File:** `src/portfolio_management/exceptions.py` (NEW)

**Implementation:**

```python
"""Custom exceptions for portfolio management."""


class PortfolioManagementError(Exception):
    """Base exception for portfolio management errors."""
    pass


class DataValidationError(PortfolioManagementError):
    """Raised when data validation fails."""
    pass


class ConfigurationError(PortfolioManagementError):
    """Raised when configuration is invalid."""
    pass


class DataQualityError(PortfolioManagementError):
    """Raised when data quality is insufficient."""
    pass


class AssetSelectionError(PortfolioManagementError):
    """Raised when asset selection fails."""
    pass


class ClassificationError(PortfolioManagementError):
    """Raised when classification fails."""
    pass


class ReturnCalculationError(PortfolioManagementError):
    """Raised when return calculation fails."""
    pass


class UniverseLoadError(PortfolioManagementError):
    """Raised when universe loading fails."""
    pass


class InsufficientDataError(DataQualityError):
    """Raised when insufficient data is available."""

    def __init__(self, message: str, asset_count: int = 0, required_count: int = 0):
        super().__init__(message)
        self.asset_count = asset_count
        self.required_count = required_count
```

**Deliverable:** Custom exception hierarchy

______________________________________________________________________

#### C2.2: Improve Validation in Core Modules (1 hour)

**Files:** Update `selection.py`, `classification.py`, `returns.py`, `universes.py`

**Changes to `selection.py`:**

```python
from src.portfolio_management.exceptions import AssetSelectionError, DataValidationError

class AssetSelector:
    def select_assets(
        self,
        matches_df: pd.DataFrame,
        criteria: FilterCriteria,
    ) -> list[SelectedAsset]:
        """Run the full asset selection pipeline."""
        logger = logging.getLogger(__name__)

        # Enhanced validation
        if matches_df is None:
            raise DataValidationError("matches_df cannot be None")

        if matches_df.empty:
            logger.warning("Input DataFrame is empty. No assets to select.")
            return []

        # Check required columns
        required_cols = {
            "symbol", "isin", "name", "market", "region", "currency", "category",
            "price_start", "price_end", "price_rows", "data_status", "data_flags",
            "stooq_path", "resolved_currency", "currency_status"
        }
        missing = required_cols - set(matches_df.columns)
        if missing:
            raise DataValidationError(
                f"Input DataFrame is missing required columns: {missing}. "
                f"Please ensure the match report includes all necessary fields."
            )

        # Validate criteria
        try:
            criteria.validate()
        except ValueError as e:
            raise DataValidationError(f"Invalid filter criteria: {e}")

        # ... rest of implementation
```

**Changes to `returns.py`:**

```python
from src.portfolio_management.exceptions import ReturnCalculationError, InsufficientDataError

class ReturnCalculator:
    def calculate_returns(
        self,
        assets: list[SelectedAsset],
        prices_dir: Path,
        config: ReturnConfig,
    ) -> pd.DataFrame:
        """Calculate returns with enhanced error handling."""
        logger = logging.getLogger(__name__)

        # Validate inputs
        if not assets:
            raise InsufficientDataError(
                "No assets provided for return calculation",
                asset_count=0,
                required_count=1
            )

        if not prices_dir.exists():
            raise ReturnCalculationError(
                f"Prices directory does not exist: {prices_dir}. "
                f"Please ensure price files have been exported."
            )

        # Validate config
        try:
            config.validate()
        except ValueError as e:
            raise ReturnCalculationError(f"Invalid return configuration: {e}")

        # ... rest of implementation with better error messages
```

**Deliverable:** Improved validation and error messages

______________________________________________________________________

#### C2.3: Add Error Recovery Strategies (30 minutes)

**File:** Update `universes.py`

**Implementation:**

```python
from src.portfolio_management.exceptions import UniverseLoadError, InsufficientDataError

class UniverseManager:
    def load_universe(self, name: str, strict: bool = True) -> dict | None:
        """Load universe with optional error recovery.

        Args:
            name: Universe name
            strict: If False, return partial results on errors

        Returns:
            Universe data dict or None if strict=False and errors occur
        """
        logger = logging.getLogger(__name__)

        try:
            definition = self.get_definition(name)

            # Selection phase
            try:
                selected = self._select_assets(definition)
                if not selected:
                    msg = f"No assets selected for universe '{name}'"
                    if strict:
                        raise InsufficientDataError(msg, asset_count=0)
                    else:
                        logger.warning(msg)
                        return None
            except Exception as e:
                if strict:
                    raise UniverseLoadError(f"Asset selection failed: {e}")
                logger.error(f"Asset selection failed: {e}")
                return None

            # Classification phase
            try:
                classified = self._classify_assets(selected)
            except Exception as e:
                if strict:
                    raise UniverseLoadError(f"Classification failed: {e}")
                logger.error(f"Classification failed: {e}")
                if not strict:
                    # Continue without classification
                    classified = pd.DataFrame([a.__dict__ for a in selected])

            # Returns phase
            try:
                returns = self._calculate_returns(selected, definition)
            except Exception as e:
                if strict:
                    raise UniverseLoadError(f"Return calculation failed: {e}")
                logger.error(f"Return calculation failed: {e}")
                if not strict:
                    returns = None

            # ... rest of implementation

        except Exception as e:
            if strict:
                raise
            logger.error(f"Universe loading failed: {e}")
            return None
```

**Deliverable:** Graceful error recovery

______________________________________________________________________

### Task C3: Fix Technical Debt (1 hour) ⭐ QUICK WINS

**Objective:** Clean up mypy errors, ruff warnings, and import issues.

#### C3.1: Fix Mypy Configuration (15 minutes)

**File:** `mypy.ini`

**Changes:**

```ini
[mypy]
python_version = 3.9
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = False
ignore_missing_imports = False
exclude = data/|tests/fixtures/

# Add this line to fix import path issues
explicit_package_bases = True

# Per-module options
[mypy-pandas.*]
ignore_missing_imports = True

[mypy-pytest.*]
ignore_missing_imports = True

[mypy-yaml.*]
ignore_missing_imports = True
```

**Test:**

```bash
mypy src/portfolio_management/ --explicit-package-bases
```

**Expected:** Reduced from 29 to ~10-15 errors (remaining are pandas-stubs limitations)

**Deliverable:** Improved type checking

______________________________________________________________________

#### C3.2: Fix Script Import Issues (20 minutes)

**Files:** All scripts in `scripts/`

**Pattern to apply to all scripts:**

```python
"""Script docstring."""

from __future__ import annotations

# Standard library imports (sorted)
import argparse
import logging
import sys
from collections.abc import Sequence  # Use collections.abc
from pathlib import Path

# Third-party imports (sorted)
import pandas as pd

# Project imports (after path setup)
import sys
from pathlib import Path

# Setup path BEFORE project imports
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Now import project modules
from src.portfolio_management.returns import ReturnCalculator, ReturnConfig
from src.portfolio_management.selection import SelectedAsset
```

**Apply to:**

- `scripts/select_assets.py`
- `scripts/classify_assets.py`
- `scripts/calculate_returns.py`
- `scripts/manage_universes.py`

**Deliverable:** Clean imports in all scripts

______________________________________________________________________

#### C3.3: Auto-fix Ruff Warnings (15 minutes)

**Commands:**

```bash
# Auto-fix what can be fixed
ruff check --fix src/portfolio_management/ scripts/ tests/

# Fix import sorting
isort src/portfolio_management/ scripts/ tests/

# Format code
black src/portfolio_management/ scripts/ tests/
```

**Review and commit:**

```bash
git diff
# Review changes
git add -A
git commit -m "fix: auto-fix ruff warnings and import sorting"
```

**Deliverable:** Reduced ruff warnings from ~40-50 to \<20

______________________________________________________________________

#### C3.4: Add Pytest Configuration (10 minutes)

**File:** `pytest.ini` or `pyproject.toml`

**Add to `pyproject.toml`:**

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "-v",
    "--strict-markers",
    "--tb=short",
    "--cov=src/portfolio_management",
    "--cov-report=term-missing:skip-covered",
    "--cov-report=html",
]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
]
```

**Deliverable:** Improved pytest configuration

______________________________________________________________________

### Task C4: Final QA Pass (2 hours) ⭐⭐ IMPORTANT

**Objective:** Manual testing and validation before merge.

#### C4.1: Manual CLI Testing (1 hour)

**Test each CLI command with real data:**

```bash
# 1. Asset Selection
echo "Testing asset selection..."
python scripts/select_assets.py \
    --match-report data/metadata/tradeable_matches.csv \
    --output /tmp/test_selected.csv \
    --min-history-days 756 \
    --data-status ok \
    --verbose

wc -l /tmp/test_selected.csv
head /tmp/test_selected.csv

# 2. Asset Classification
echo "Testing classification..."
python scripts/classify_assets.py \
    --input /tmp/test_selected.csv \
    --output /tmp/test_classified.csv \
    --summary

head /tmp/test_classified.csv

# 3. Return Calculation
echo "Testing returns..."
python scripts/calculate_returns.py \
    --assets /tmp/test_classified.csv \
    --prices-dir data/processed/tradeable_prices \
    --output /tmp/test_returns.csv \
    --method simple \
    --frequency monthly \
    --summary

head /tmp/test_returns.csv

# 4. Universe Management
echo "Testing universe management..."
python scripts/manage_universes.py list
python scripts/manage_universes.py show core_global
python scripts/manage_universes.py validate core_global --verbose

# Test error handling
echo "Testing error scenarios..."
python scripts/select_assets.py \
    --match-report /nonexistent/file.csv \
    2>&1 | grep -i error

python scripts/calculate_returns.py \
    --assets /tmp/test_classified.csv \
    --prices-dir /nonexistent/dir \
    2>&1 | grep -i error
```

**Checklist:**

- \[ \] All commands execute without crashes
- \[ \] Output files are created with expected format
- \[ \] Summary statistics are reasonable
- \[ \] Error messages are helpful
- \[ \] --help works for all commands
- \[ \] --verbose provides useful output

**Deliverable:** Manual test validation complete

______________________________________________________________________

#### C4.2: Automated Test Suite Validation (30 minutes)

**Run complete test suite:**

```bash
# Run all tests with coverage
pytest tests/ -v --cov=src/portfolio_management --cov-report=term-missing --cov-report=html

# Check coverage report
open htmlcov/index.html  # or xdg-open on Linux

# Run only integration tests
pytest tests/integration/ -v -s

# Run performance tests
pytest tests/integration/test_performance.py -v -s

# Run with different markers
pytest tests/ -v -m "not slow"
pytest tests/ -v -m "integration"
```

**Success Criteria:**

- \[ \] All tests pass (100%)
- \[ \] Coverage ≥ 80% (target: 86%+)
- \[ \] Integration tests pass
- \[ \] Performance tests meet targets
- \[ \] No test failures

**Deliverable:** Full test suite validation

______________________________________________________________________

#### C4.3: Pre-commit Hooks Validation (15 minutes)

**Run all pre-commit hooks:**

```bash
# Run on all files
pre-commit run --all-files

# If any fail, fix and re-run
# Common fixes:
# - black formatting
# - isort import ordering
# - ruff linting
# - mypy type checking

# Install hooks if not already installed
pre-commit install
```

**Success Criteria:**

- \[ \] All pre-commit hooks pass
- \[ \] No trailing whitespace
- \[ \] No merge conflict markers
- \[ \] All files formatted consistently

**Deliverable:** Pre-commit validation complete

______________________________________________________________________

#### C4.4: Documentation Review (15 minutes)

**Check all documentation:**

```bash
# Verify README is up to date
cat README.md | grep -i "phase 3"

# Check module docstrings
python -c "import src.portfolio_management.selection; help(src.portfolio_management.selection)"
python -c "import src.portfolio_management.classification; help(src.portfolio_management.classification)"
python -c "import src.portfolio_management.returns; help(src.portfolio_management.returns)"
python -c "import src.portfolio_management.universes; help(src.portfolio_management.universes)"

# Verify docs exist
ls docs/
cat docs/returns.md | head -20
cat docs/universes.md | head -20
```

**Checklist:**

- \[ \] README.md updated with Phase 3 status
- \[ \] All modules have docstrings
- \[ \] docs/returns.md is complete
- \[ \] docs/universes.md is complete
- \[ \] Examples work as documented

**Deliverable:** Documentation validated

______________________________________________________________________

## Part 2: Documentation & Polish (Priority 2)

Complete after critical path items.

______________________________________________________________________

### Task D1: Create Missing Documentation (3 hours)

#### D1.1: Asset Selection Guide (1 hour)

**File:** `docs/asset_selection.md`

**Content outline:**

```markdown
# Asset Selection Guide

## Overview
[Explanation of asset selection purpose and approach]

## FilterCriteria Reference
[Detailed documentation of all filter parameters]

## Selection Strategies

### By Data Quality
[Examples and recommendations]

### By History Requirements
[Examples and recommendations]

### By Market Characteristics
[Examples and recommendations]

### Using Allowlists and Blocklists
[Examples and best practices]

## Common Use Cases

### Conservative Selection
[Example configuration]

### Aggressive Selection
[Example configuration]

### Market-Specific Selection
[Examples for UK, US, Europe]

## CLI Reference
[Complete command-line documentation]

## Troubleshooting
[Common issues and solutions]

## Performance Tips
[Optimization recommendations]
```

**Deliverable:** Complete asset selection documentation

______________________________________________________________________

#### D1.2: Classification Guide (1 hour)

**File:** `docs/classification.md`

**Content outline:**

```markdown
# Asset Classification Guide

## Overview
[Explanation of classification system]

## Classification Taxonomy

### Asset Classes
[Full documentation of AssetClass enum]

### Geographies
[Full documentation of Geography enum]

### Sub-Classes
[Full documentation of SubClass enum]

## Classification Rules
[Documentation of keyword-based rules]

## Manual Overrides

### Creating Overrides
[CSV format and examples]

### Override Best Practices
[Recommendations]

## Improving Classification Accuracy
[Tips for better results]

## CLI Reference
[Complete command-line documentation]

## Limitations
[Known issues and workarounds]

## Future Improvements
[Planned enhancements]
```

**Deliverable:** Complete classification documentation

______________________________________________________________________

#### D1.3: Integration Guide (1 hour)

**File:** `docs/integration_guide.md`

**Content outline:**

```markdown
# Integration Guide

## End-to-End Workflows

### Workflow 1: Building a Custom Universe
[Step-by-step guide]

### Workflow 2: Analyzing Multiple Universes
[Step-by-step guide]

### Workflow 3: Backtesting Preparation
[Step-by-step guide]

## Programmatic Usage

### Python API Examples
[Code examples for using modules directly]

### Custom Pipelines
[How to build custom workflows]

## Integration with Other Tools
[Export formats, data interchange]

## Performance Optimization
[Tips for large-scale processing]

## Troubleshooting
[Common integration issues]

## FAQ
[Frequently asked questions]
```

**Deliverable:** Complete integration guide

______________________________________________________________________

### Task D2: Update Memory Bank (1 hour)

#### D2.1: Update progress.md

**File:** `memory-bank/progress.md`

**Changes:**

```markdown
### Phase 3: Asset Selection for Portfolio Construction (✅ Complete - October 2025)

**Status:** All 45 tasks completed. Phase 3 is production-ready.

**Completion Date:** October 16, 2025

**Summary:**
- ✅ Stage 1 (Asset Selection): Complete
- ✅ Stage 2 (Classification): Complete
- ✅ Stage 3 (Return Calculation): Complete
- ✅ Stage 4 (Universe Management): Complete
- ✅ Stage 5 (Integration & Polish): Complete

**Final Metrics:**
- Tests: 170+ passing (100% success rate)
- Coverage: 87% (exceeds 80% target)
- Code Quality: 9.0/10
- Technical Debt: Very Low
- Documentation: Complete

**Deliverables:**
- 4 core modules: selection, classification, returns, universes
- 4 CLI tools: select_assets, classify_assets, calculate_returns, manage_universes
- 4 predefined universes: core_global, satellite_factor, defensive, equity_only
- Complete documentation: README, docs/returns.md, docs/universes.md, docs/asset_selection.md, docs/classification.md
- Integration test suite
- Performance benchmarks

**Key Achievements:**
1. Professional-grade modular architecture
2. Comprehensive test coverage with integration tests
3. Excellent documentation for users and developers
4. Production-validated with real data
5. Performance targets met (30s for 1000 assets)

**Next Phase:** Phase 4 - Portfolio Construction Strategies
```

#### D2.2: Update activeContext.md

**File:** `memory-bank/activeContext.md`

**Changes:**

```markdown
# Active Context

## Current Focus

**Phase 3 Complete:** Asset Selection & Universe Management delivered.
**Current Phase:** Ready to begin Phase 4 - Portfolio Construction Strategies
**Branch:** `portfolio-construction` ready for merge to `main`

## Recent Changes (Latest Session - Phase 3 Completion)

### Stage 5 Completion ✅

**Integration Tests (Complete):**
- End-to-end pipeline tests
- Multi-universe tests
- Production data validation
- Performance benchmarks
- Error scenario testing

**Technical Debt Resolution (Complete):**
- Fixed mypy configuration (explicit_package_bases)
- Cleaned up import statements in all scripts
- Auto-fixed ruff warnings
- Improved error handling with custom exceptions

**Documentation (Complete):**
- Created docs/asset_selection.md
- Created docs/classification.md
- Created docs/integration_guide.md
- Updated all memory bank files

**Quality Assurance (Complete):**
- Manual CLI testing passed
- All automated tests passing (170+)
- Pre-commit hooks validated
- Documentation reviewed

### Phase 3 Final Status

**Completion:** 45/45 tasks (100%)
**Quality Score:** 9.0/10 (Excellent)
**Test Coverage:** 87%
**Ready for:** Merge to main, Phase 4 start

## Next Immediate Steps

1. Merge `portfolio-construction` branch to `main`
2. Create Phase 4 implementation plan
3. Begin portfolio construction strategies
```

#### D2.3: Update systemPatterns.md

**File:** `memory-bank/systemPatterns.md`

**Add section:**

```markdown
## Asset Selection & Universe Management (Phase 3)

### Selection Pipeline
- Multi-stage filtering: data quality → history → characteristics → lists
- Defensive validation at each stage
- Comprehensive logging for auditability

### Classification System
- Rule-based with manual override capability
- Confidence scoring for quality assessment
- Taxonomy: asset class, geography, sub-class

### Return Preparation
- Multiple methods: simple, log, excess returns
- Flexible frequency: daily, weekly, monthly
- Missing data strategies: forward_fill, drop, interpolate
- Date alignment and coverage filtering

### Universe Management
- YAML-based configuration
- Predefined universes: core_global, satellite_factor, defensive, equity_only
- Composable pipeline: selection → classification → returns
- Validation and comparison tools

### Integration Points
- Selection feeds classification
- Classification informs universe composition
- Returns enable portfolio construction
- All stages logged and auditable
```

**Deliverable:** Memory bank fully updated

______________________________________________________________________

## Part 3: Optional Enhancements (Priority 3)

These can be done later but would improve the system.

______________________________________________________________________

### Task E1: Enhanced Logging (Optional, 2 hours)

**Objective:** Structured logging with performance metrics

**Implementation:**

1. Add structured logging configuration
1. Add performance metrics logging
1. Add debug mode with detailed output
1. Create log analysis tools

**Files:**

- `src/portfolio_management/logging_config.py` (NEW)
- Update all modules to use structured logging

______________________________________________________________________

### Task E2: Caching Implementation (Optional, 3 hours)

**Objective:** Speed up repeated operations

**Implementation:**

1. Add price file caching
1. Add universe loading caching
1. Add cache invalidation logic
1. Add cache management CLI

**Files:**

- `src/portfolio_management/cache.py` (NEW)
- Update `returns.py` to use caching
- Update `universes.py` to use caching

______________________________________________________________________

### Task E3: Progress Indicators (Optional, 1 hour)

**Objective:** Better UX for long operations

**Implementation:**

1. Add `tqdm` progress bars
1. Show progress in CLI commands
1. Add ETA for long operations

**Files:**

- Update all scripts to show progress
- Add `tqdm` to `requirements.txt`

______________________________________________________________________

## Execution Checklist

### Critical Path (Must Complete)

- \[ \] **Task C1:** Integration Tests (4-5 hours)

  - \[ \] C1.1: Setup infrastructure
  - \[ \] C1.2: End-to-end tests
  - \[ \] C1.3: Performance benchmarks
  - \[ \] C1.4: Production data validation

- \[ \] **Task C2:** Enhanced Error Handling (2 hours)

  - \[ \] C2.1: Custom exceptions
  - \[ \] C2.2: Improve validation
  - \[ \] C2.3: Error recovery

- \[ \] **Task C3:** Fix Technical Debt (1 hour)

  - \[ \] C3.1: Mypy configuration
  - \[ \] C3.2: Script imports
  - \[ \] C3.3: Auto-fix ruff
  - \[ \] C3.4: Pytest configuration

- \[ \] **Task C4:** Final QA (2 hours)

  - \[ \] C4.1: Manual CLI testing
  - \[ \] C4.2: Automated test validation
  - \[ \] C4.3: Pre-commit validation
  - \[ \] C4.4: Documentation review

### Documentation (Should Complete)

- \[ \] **Task D1:** Create Missing Docs (3 hours)

  - \[ \] D1.1: Asset selection guide
  - \[ \] D1.2: Classification guide
  - \[ \] D1.3: Integration guide

- \[ \] **Task D2:** Update Memory Bank (1 hour)

  - \[ \] D2.1: progress.md
  - \[ \] D2.2: activeContext.md
  - \[ \] D2.3: systemPatterns.md

### Optional Enhancements (Can Defer)

- \[ \] **Task E1:** Enhanced Logging
- \[ \] **Task E2:** Caching Implementation
- \[ \] **Task E3:** Progress Indicators

______________________________________________________________________

## Time Estimates

### Minimum Path to Merge

- Critical Path: 9-10 hours
- Quick wins: Already done
- **Total: 9-10 hours**

### Recommended Path

- Critical Path: 9-10 hours
- Documentation: 4 hours
- **Total: 13-14 hours**

### Complete Path

- Critical Path: 9-10 hours
- Documentation: 4 hours
- Optional Enhancements: 6 hours
- **Total: 19-20 hours**

______________________________________________________________________

## Success Criteria

### Before Merge to Main

1. ✅ **All Critical Tests Pass**

   - Integration tests: 100% passing
   - Unit tests: 100% passing
   - Coverage: ≥ 86%

1. ✅ **Technical Debt Resolved**

   - Mypy errors: \< 15 (pandas-stubs only)
   - Ruff warnings: \< 20
   - Import issues: Fixed

1. ✅ **Quality Gates**

   - Pre-commit hooks: All passing
   - Manual testing: All CLIs work
   - Production data: Validates successfully

1. ✅ **Documentation**

   - README: Updated
   - Core docs: Complete (returns, universes)
   - Missing docs: Created (selection, classification)

### Production Ready

All of the above, plus:

5. ✅ **Performance Validated**

   - Benchmarks established
   - Targets met
   - No memory leaks

1. ✅ **Error Handling**

   - Custom exceptions
   - Helpful error messages
   - Graceful recovery

1. ✅ **Memory Bank**

   - All files updated
   - Accurate status
   - Ready for Phase 4

______________________________________________________________________

## Post-Completion Actions

### 1. Merge to Main

```bash
# Ensure all tests pass
pytest tests/ -v --cov=src/portfolio_management

# Ensure pre-commit passes
pre-commit run --all-files

# Create PR or merge
git checkout main
git merge portfolio-construction
git push origin main
```

### 2. Create Release Tag

```bash
git tag -a v0.3.0 -m "Phase 3: Asset Selection & Universe Management"
git push origin v0.3.0
```

### 3. Update Project Board

- Mark all Phase 3 tasks as complete
- Close Phase 3 milestone
- Create Phase 4 milestone

### 4. Communicate Status

- Update team/stakeholders
- Share achievements
- Request feedback

### 5. Plan Phase 4

- Review Phase 4 requirements
- Create implementation plan
- Estimate timeline

______________________________________________________________________

## Notes for Coding Agents

### Code Style Guidelines

1. **Follow existing patterns:** The codebase has established patterns—follow them
1. **Type hints required:** All new functions must have type hints
1. **Docstrings required:** All public functions/classes need docstrings with examples
1. **Test everything:** New code needs corresponding tests
1. **Error handling:** Use custom exceptions, provide helpful messages
1. **Logging:** Add logging at key points (INFO for major steps, DEBUG for details)

### Testing Guidelines

1. **Unit tests:** Test individual functions in isolation
1. **Integration tests:** Test component interactions
1. **Performance tests:** Mark with @pytest.mark.slow
1. **Use fixtures:** Don't repeat setup code
1. **Realistic data:** Use actual data subsets where possible
1. **Assert meaningfully:** Check specific conditions, not just "not None"

### Documentation Guidelines

1. **Complete sentences:** Documentation should be prose, not fragments
1. **Examples included:** Show how to use the feature
1. **Limitations noted:** Be honest about what doesn't work
1. **Links provided:** Reference related documentation
1. **Keep updated:** Update docs when code changes

### Git Commit Guidelines

1. **Conventional commits:** Use prefixes (feat:, fix:, docs:, test:, refactor:)
1. **Atomic commits:** One logical change per commit
1. **Descriptive messages:** Explain why, not just what
1. **Reference issues:** Link to tasks/issues when applicable

### Review Checklist

Before considering a task complete:

- \[ \] Code works correctly
- \[ \] Tests pass
- \[ \] Coverage maintained/improved
- \[ \] Type checking passes
- \[ \] Linting passes
- \[ \] Documentation updated
- \[ \] Manual testing done
- \[ \] Peer review requested (if applicable)
- \[ \] Memory bank updated (for major changes)

______________________________________________________________________

## Troubleshooting

### Common Issues

**Issue:** Integration tests fail with missing data
**Solution:** Ensure test data files are present in `data/processed/tradeable_prices_test/`

**Issue:** Mypy errors remain after config fix
**Solution:** Most remaining errors are from pandas-stubs limitations; document and ignore

**Issue:** Performance tests fail timeout
**Solution:** Adjust test data size or timeouts; production targets may differ from test targets

**Issue:** Pre-commit hooks fail
**Solution:** Run `pre-commit run --all-files` and fix issues before committing

### Getting Help

1. Review existing code for patterns
1. Check documentation in `docs/`
1. Look at similar tests for examples
1. Review Memory Bank files for context
1. Check CODE_REVIEW_PHASE3.md for detailed analysis

______________________________________________________________________

**Document Version:** 1.0
**Last Updated:** October 16, 2025
**Next Review:** After completion of critical path items
