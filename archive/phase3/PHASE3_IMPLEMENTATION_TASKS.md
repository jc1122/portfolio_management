# Phase 3: Asset Selection - Detailed Implementation Tasks

## Overview

This document provides granular, step-by-step tasks for implementing Phase 3 (Asset Selection & Universe Management). Each task is designed to be completable in 30-90 minutes and includes specific deliverables, test requirements, and validation steps.

**Total Estimated Time:** 40-50 hours over 3 weeks
**Branch:** `portfolio-construction`
**Current Status:** Planning complete, ready for implementation

______________________________________________________________________

## Stage 1: Asset Selection Core (Week 1, Days 1-2)

### Task 1.1: Create Data Models for Selection (2 hours)

**File:** `src/portfolio_management/selection.py` (NEW)

**Steps:**

1. Create new file with module docstring
1. Add imports: `dataclasses`, `pandas`, `pathlib`, `datetime`, `typing`
1. Implement `FilterCriteria` dataclass with fields:
   - `data_status: list[str] = field(default_factory=lambda: ["ok"])`
   - `min_history_days: int = 252`
   - `max_gap_days: int = 10`
   - `min_price_rows: int = 252`
   - `zero_volume_severity: list[str] | None = None`
   - `markets: list[str] | None = None`
   - `regions: list[str] | None = None`
   - `currencies: list[str] | None = None`
   - `categories: list[str] | None = None`
   - `allowlist: set[str] | None = None`
   - `blocklist: set[str] | None = None`
1. Implement `SelectedAsset` dataclass with fields from match report:
   - `symbol: str`
   - `isin: str`
   - `name: str`
   - `market: str`
   - `region: str`
   - `currency: str`
   - `category: str`
   - `price_start: str` (date as string from CSV)
   - `price_end: str`
   - `price_rows: int`
   - `data_status: str`
   - `data_flags: str`
   - `stooq_path: str`
   - `resolved_currency: str`
   - `currency_status: str`
1. Add validation method to `FilterCriteria`: `validate() -> None`
   - Check `min_history_days > 0`
   - Check `min_price_rows > 0`
   - Check `max_gap_days >= 0`
   - Check `data_status` not empty
1. Add factory method: `FilterCriteria.default() -> FilterCriteria`
1. Add comprehensive docstrings with examples
1. Add type hints for all fields

**Deliverables:**

- `selection.py` with two dataclasses
- Docstrings explaining each field
- Validation logic

**Tests:** None yet (pure data models)

**Validation:**

```bash
python -c "from src.portfolio_management.selection import FilterCriteria, SelectedAsset; print('Models imported successfully')"
mypy src/portfolio_management/selection.py
```

______________________________________________________________________

### Task 1.2: Implement AssetSelector - Data Quality Filter (2 hours)

**File:** `src/portfolio_management/selection.py`

**Steps:**

1. Create `AssetSelector` class with docstring
1. Add `__init__` method (no parameters needed yet)
1. Implement `_filter_by_data_quality(df: pd.DataFrame, criteria: FilterCriteria) -> pd.DataFrame`:
   - Filter by `data_status` in criteria list
   - Parse `data_flags` column for zero_volume_severity
   - Extract severity from flags like: "zero_volume_severity=high"
   - Filter by severity if `criteria.zero_volume_severity` is not None
   - Return filtered DataFrame
1. Add helper method `_parse_severity(data_flags: str) -> str | None`:
   - Handle empty/NaN flags (return None)
   - Use regex or string parsing to extract severity value
   - Return None if not found
1. Add logging statements for diagnostics
1. Handle edge cases:
   - Empty input DataFrame
   - Missing columns
   - Invalid severity values

**Deliverables:**

- `_filter_by_data_quality` method
- `_parse_severity` helper
- Logging for filter statistics

**Tests:** Create `tests/test_selection.py`

- Test filtering by data_status (ok, warning, empty)
- Test filtering by severity (low, moderate, high)
- Test combined status + severity filtering
- Test edge cases (empty df, missing columns)

**Validation:**

```bash
pytest tests/test_selection.py::test_filter_by_data_quality -v
```

______________________________________________________________________

### Task 1.3: Implement AssetSelector - History Filter (1.5 hours)

**File:** `src/portfolio_management/selection.py`

**Steps:**

1. Implement `_filter_by_history(df: pd.DataFrame, criteria: FilterCriteria) -> pd.DataFrame`:
   - Convert `price_start` and `price_end` to datetime
   - Calculate history length in days: `(end - start).days`
   - Filter rows where `history_days >= criteria.min_history_days`
   - Filter by `price_rows >= criteria.min_price_rows`
   - Return filtered DataFrame
1. Add helper method `_calculate_history_days(row: pd.Series) -> int`:
   - Parse date strings safely
   - Handle invalid dates (return 0)
   - Return difference in days
1. Add logging for filtered counts
1. Handle edge cases:
   - Invalid date formats
   - Future dates
   - Negative history

**Deliverables:**

- `_filter_by_history` method
- Date parsing logic
- Error handling

**Tests:** Add to `tests/test_selection.py`

- Test min_history_days filtering
- Test min_price_rows filtering
- Test combined history + rows filtering
- Test invalid date handling
- Test edge dates (same start/end)

**Validation:**

```bash
pytest tests/test_selection.py::test_filter_by_history -v
```

______________________________________________________________________

### Task 1.4: Implement AssetSelector - Characteristics Filter (1.5 hours)

**File:** `src/portfolio_management/selection.py`

**Steps:**

1. Implement `_filter_by_characteristics(df: pd.DataFrame, criteria: FilterCriteria) -> pd.DataFrame`:
   - Filter by `markets` if not None: `df['market'].isin(criteria.markets)`
   - Filter by `regions` if not None: `df['region'].isin(criteria.regions)`
   - Filter by `currencies` if not None: `df['resolved_currency'].isin(criteria.currencies)`
   - Filter by `categories` if not None: `df['category'].isin(criteria.categories)`
   - Combine filters with AND logic
   - Return filtered DataFrame
1. Add logging for each filter stage
1. Handle None values (skip filter if None)
1. Handle case-insensitive matching option (add to criteria if needed)

**Deliverables:**

- `_filter_by_characteristics` method
- Multi-field filtering logic
- Logging

**Tests:** Add to `tests/test_selection.py`

- Test market filtering
- Test region filtering
- Test currency filtering
- Test category filtering
- Test combined characteristics
- Test None handling (no filter)

**Validation:**

```bash
pytest tests/test_selection.py::test_filter_by_characteristics -v
```

______________________________________________________________________

### Task 1.5: Implement AssetSelector - Allowlist/Blocklist (1 hour)

**File:** `src/portfolio_management/selection.py`

**Steps:**

1. Implement `_apply_lists(df: pd.DataFrame, criteria: FilterCriteria) -> pd.DataFrame`:
   - If `criteria.blocklist` is not None:
     - Remove rows where `symbol` or `isin` in blocklist
   - If `criteria.allowlist` is not None:
     - Keep only rows where `symbol` or `isin` in allowlist
   - Log number of assets added/removed
   - Return filtered DataFrame
1. Add helper to check both symbol and isin: `_is_in_list(row: pd.Series, asset_list: set[str]) -> bool`
1. Handle interaction between allowlist and blocklist:
   - Blocklist takes precedence (if in both, exclude)
1. Add validation: warn if allowlist and blocklist overlap

**Deliverables:**

- `_apply_lists` method
- List checking logic
- Conflict handling

**Tests:** Add to `tests/test_selection.py`

- Test blocklist exclusion
- Test allowlist inclusion
- Test combined allowlist + blocklist
- Test symbol vs ISIN matching
- Test overlapping lists

**Validation:**

```bash
pytest tests/test_selection.py::test_apply_lists -v
```

______________________________________________________________________

### Task 1.6: Implement AssetSelector - Main Selection Method (2 hours)

**File:** `src/portfolio_management/selection.py`

**Steps:**

1. Implement `select_assets(matches_df: pd.DataFrame, criteria: FilterCriteria) -> list[SelectedAsset]`:
   - Validate input DataFrame has required columns
   - Validate criteria using `criteria.validate()`
   - Log initial asset count
   - Apply filters in sequence:
     - `_filter_by_data_quality`
     - `_filter_by_history`
     - `_filter_by_characteristics`
     - `_apply_lists`
   - Log count after each stage
   - Convert resulting DataFrame to list of `SelectedAsset` objects
   - Return list
1. Add helper: `_df_to_selected_assets(df: pd.DataFrame) -> list[SelectedAsset]`
   - Iterate rows and create SelectedAsset objects
   - Handle type conversions (int for price_rows)
   - Handle missing values gracefully
1. Add summary logging at the end:
   - Total selected
   - Percentage of original
   - Breakdown by market/region
1. Handle empty result gracefully (return empty list, log warning)

**Deliverables:**

- Complete `select_assets` public API
- DataFrame to object conversion
- Comprehensive logging
- Input validation

**Tests:** Add to `tests/test_selection.py`

- Test full pipeline with real match report fixture
- Test each filter stage separately
- Test empty result handling
- Test invalid input handling
- Test logging output

**Validation:**

```bash
pytest tests/test_selection.py::test_select_assets_full_pipeline -v
pytest tests/test_selection.py -v  # All tests
mypy src/portfolio_management/selection.py
```

______________________________________________________________________

### Task 1.7: Create Test Fixtures for Selection (1.5 hours)

**File:** `tests/fixtures/selection_test_data.csv` (NEW)

**Steps:**

1. Create synthetic test data CSV with ~50 rows covering:
   - Mix of data_status: ok (30), warning (15), empty (5)
   - Mix of severity: low, moderate, high, none
   - Various history lengths: \<1yr, 1-3yr, >3yr
   - Various price_rows: \<252, 252-756, >756
   - Multiple markets: LSE, XETRA, EURONEXT
   - Multiple regions: uk, de, fr
   - Multiple currencies: GBP, EUR, USD
   - Various categories: lse stocks, etf, bonds
1. Include edge cases:
   - Invalid dates
   - Zero price_rows
   - Empty data_flags
   - Symbols with special characters
1. Document the fixture in docstring
1. Create fixture loader in `tests/conftest.py`:
   ```python
   @pytest.fixture
   def selection_test_matches():
       return pd.read_csv("tests/fixtures/selection_test_data.csv")
   ```

**Deliverables:**

- `selection_test_data.csv` with diverse test cases
- Fixture loader in conftest.py
- Documentation

**Validation:**

```bash
python -c "import pandas as pd; df = pd.read_csv('tests/fixtures/selection_test_data.csv'); print(df.shape); print(df.columns.tolist())"
```

______________________________________________________________________

### Task 1.8: Add CLI Command for Asset Selection (2.5 hours)

**File:** `scripts/select_assets.py` (NEW)

**Steps:**

1. Create new CLI script with argparse
1. Add arguments:
   - `--match-report` (required): Path to tradeable_matches.csv
   - `--output`: Output CSV path (optional, prints to stdout if omitted)
   - `--data-status`: Comma-separated list (default: "ok")
   - `--min-history-days`: Integer (default: 252)
   - `--min-price-rows`: Integer (default: 252)
   - `--max-gap-days`: Integer (default: 10)
   - `--severity`: Comma-separated severity levels to exclude
   - `--markets`: Comma-separated market filter
   - `--regions`: Comma-separated region filter
   - `--currencies`: Comma-separated currency filter
   - `--allowlist`: Path to file with symbols/ISINs (one per line)
   - `--blocklist`: Path to file with symbols/ISINs (one per line)
   - `--verbose`: Enable detailed logging
1. Implement main function:
   - Load match report
   - Build FilterCriteria from arguments
   - Create AssetSelector
   - Run selection
   - Export results or print summary
1. Add summary statistics output:
   - Total selected
   - Breakdown by market
   - Breakdown by region
   - Breakdown by data_status
   - History range (min, max, median)
1. Add error handling and validation
1. Add --dry-run mode (show what would be selected)

**Deliverables:**

- `select_assets.py` CLI script
- Comprehensive argument parsing
- Summary statistics
- Error handling

**Tests:** Add to `tests/scripts/test_select_assets.py`

- Test CLI with various argument combinations
- Test output format
- Test error handling
- Test allowlist/blocklist file loading

**Validation:**

```bash
python scripts/select_assets.py --match-report data/metadata/tradeable_matches.csv --data-status ok --min-history-days 756 --output /tmp/test_selection.csv
wc -l /tmp/test_selection.csv
head /tmp/test_selection.csv
```

______________________________________________________________________

### Task 1.9: Document Selection Module (1 hour)

**Files:** `src/portfolio_management/selection.py`, `README.md`

**Steps:**

1. Add comprehensive module docstring to `selection.py`:
   - Purpose and overview
   - Usage examples
   - Key classes and functions
1. Add examples in docstrings:
   - Basic filtering
   - Advanced filtering with multiple criteria
   - Using allowlist/blocklist
1. Update README.md:
   - Add "Asset Selection" section
   - Document CLI usage with examples
   - Link to detailed docs
1. Create `docs/asset_selection.md` (optional):
   - Detailed guide
   - Filter strategy recommendations
   - Common use cases

**Deliverables:**

- Complete module documentation
- README updates
- Usage examples

**Validation:**

```bash
python -c "import src.portfolio_management.selection; help(src.portfolio_management.selection)"
```

______________________________________________________________________

## Stage 2: Asset Classification (Week 1-2, Days 3-4)

### Task 2.1: Design Classification Taxonomy (1.5 hours)

**File:** `src/portfolio_management/classification.py` (NEW)

**Steps:**

1. Create module with docstring
1. Define `AssetClass` enum:
   - `EQUITY = "equity"`
   - `FIXED_INCOME = "fixed_income"`
   - `ALTERNATIVE = "alternative"`
   - `CASH = "cash"`
   - `COMMODITY = "commodity"`
   - `REAL_ESTATE = "real_estate"`
   - `UNKNOWN = "unknown"`
1. Define `Geography` enum:
   - `DEVELOPED_MARKETS = "developed_markets"`
   - `EMERGING_MARKETS = "emerging_markets"`
   - `GLOBAL = "global"`
   - `NORTH_AMERICA = "north_america"`
   - `EUROPE = "europe"`
   - `ASIA_PACIFIC = "asia_pacific"`
   - `UNITED_KINGDOM = "united_kingdom"`
   - `UNKNOWN = "unknown"`
1. Define `SubClass` enum (20+ categories):
   - Equity: `LARGE_CAP`, `SMALL_CAP`, `VALUE`, `GROWTH`, `DIVIDEND`
   - Fixed Income: `GOVERNMENT`, `CORPORATE`, `HIGH_YIELD`, `INFLATION_LINKED`
   - Alternative: `GOLD`, `COMMODITIES`, `REIT`, `HEDGE_FUND`
1. Create `AssetClassification` dataclass:
   - `symbol: str`
   - `isin: str`
   - `asset_class: AssetClass`
   - `sub_class: str`
   - `geography: Geography`
   - `sector: str | None = None`
   - `confidence: float = 1.0` (classification confidence 0-1)
1. Document classification philosophy and limitations

**Deliverables:**

- Classification taxonomy with enums
- AssetClassification dataclass
- Documentation

**Validation:**

```bash
python -c "from src.portfolio_management.classification import AssetClass, Geography, AssetClassification; print(list(AssetClass))"
```

______________________________________________________________________

### Task 2.2: Implement Rule-Based Classification (3 hours)

**File:** `src/portfolio_management/classification.py`

**Steps:**

1. Create `AssetClassifier` class
1. Add classification rules as class constants:
   - `EQUITY_KEYWORDS = ["stock", "equity", "shares", "ETF"]`
   - `BOND_KEYWORDS = ["bond", "gilt", "treasury", "credit"]`
   - `COMMODITY_KEYWORDS = ["gold", "silver", "oil", "commodity"]`
   - `GEOGRAPHY_PATTERNS = {USA: ["US", "USA", "America"], UK: ["UK", "GBP", "British"], ...}`
1. Implement `_classify_by_name(asset: SelectedAsset) -> AssetClass`:
   - Search name for keywords (case-insensitive)
   - Return matched asset class or UNKNOWN
1. Implement `_classify_by_category(asset: SelectedAsset) -> AssetClass`:
   - Map category field to asset class
   - "lse stocks" → EQUITY
   - "etf" → depends on name
   - "bonds" → FIXED_INCOME
1. Implement `_classify_geography(asset: SelectedAsset) -> Geography`:
   - Use region field
   - Use currency as hint
   - Use name patterns
1. Implement `_classify_sub_class(asset: SelectedAsset, asset_class: AssetClass) -> str`:
   - Based on name keywords and asset class
   - Return string representation
1. Add confidence scoring based on:
   - Multiple confirming signals = high confidence
   - Single signal = medium confidence
   - Guessing = low confidence
1. Handle ambiguous cases (mark UNKNOWN, log warning)

**Deliverables:**

- Rule-based classification logic
- Confidence scoring
- Comprehensive keyword mappings

**Tests:** Create `tests/test_classification.py`

- Test classification by name
- Test classification by category
- Test geography classification
- Test sub-class classification
- Test confidence scoring
- Test ambiguous cases

**Validation:**

```bash
pytest tests/test_classification.py -v
```

______________________________________________________________________

### Task 2.3: Implement Manual Override System (1.5 hours)

**File:** `src/portfolio_management/classification.py`

**Steps:**

1. Create `ClassificationOverrides` class:
   - Load overrides from CSV or dict
   - Store by ISIN/symbol
1. Add CSV format: `isin,symbol,asset_class,sub_class,geography,sector`
1. Implement `load_overrides(path: Path) -> dict[str, dict]`:
   - Read CSV
   - Validate columns
   - Return lookup dict
1. Modify `AssetClassifier.__init__` to accept overrides:
   - `def __init__(self, overrides_path: Path | None = None)`
1. Modify classification methods to check overrides first:
   - If asset in overrides, use override values
   - Mark confidence = 1.0 for overrides
1. Add method to export current classifications for review:
   - `export_for_review(classifications: list[AssetClassification], path: Path)`
   - Creates CSV that can be edited and reloaded

**Deliverables:**

- Override loading system
- CSV format specification
- Export for review functionality

**Tests:** Add to `tests/test_classification.py`

- Test override loading
- Test override application
- Test override precedence
- Test export format

**Validation:**

```bash
# Create test override file
echo "isin,symbol,asset_class,sub_class,geography,sector" > /tmp/test_overrides.csv
echo "TEST123,TEST,equity,large_cap,united_kingdom,technology" >> /tmp/test_overrides.csv
pytest tests/test_classification.py::test_overrides -v
```

______________________________________________________________________

### Task 2.4: Implement Batch Classification (1 hour)

**File:** `src/portfolio_management/classification.py`

**Steps:**

1. Implement `classify_universe(assets: list[SelectedAsset]) -> pd.DataFrame`:
   - Iterate through assets
   - Call `classify_asset` for each
   - Collect results
   - Convert to DataFrame
   - Return with original asset metadata
1. Add progress logging for large batches
1. Add parallel processing option (optional):
   - Use `utils._run_in_parallel` if available
1. Add summary statistics:
   - Count by asset class
   - Count by geography
   - Low confidence classifications (\< 0.5)
1. Export results to CSV with all fields

**Deliverables:**

- Batch classification method
- Progress tracking
- Summary statistics

**Tests:** Add to `tests/test_classification.py`

- Test batch classification
- Test with empty list
- Test with large list (100+ items)
- Test summary statistics

**Validation:**

```bash
pytest tests/test_classification.py::test_classify_universe -v
```

______________________________________________________________________

### Task 2.5: Add CLI for Classification (2 hours)

**File:** `scripts/classify_assets.py` (NEW)

**Steps:**

1. Create CLI script with argparse
1. Add arguments:
   - `--input` (required): Path to selected assets CSV
   - `--output`: Path for classification results
   - `--overrides`: Path to manual overrides CSV
   - `--export-for-review`: Export template for manual review
   - `--summary`: Print classification summary
1. Implement main function:
   - Load selected assets
   - Load overrides if provided
   - Create classifier
   - Run classification
   - Export results
1. Add classification summary output:
   - Breakdown by asset class
   - Breakdown by geography
   - Low confidence assets (for review)
   - Unknown classifications
1. Add validation checks:
   - Warn about high % of UNKNOWN
   - Warn about low confidence classifications

**Deliverables:**

- Classification CLI
- Summary reporting
- Export for review

**Tests:** Add to `tests/scripts/test_classify_assets.py`

- Test CLI execution
- Test with/without overrides
- Test summary output
- Test export-for-review

**Validation:**

```bash
python scripts/classify_assets.py --input /tmp/test_selection.csv --output /tmp/test_classification.csv --summary
cat /tmp/test_classification.csv | head
```

______________________________________________________________________

### Task 2.6: Document Classification Module (1 hour)

**Files:** `src/portfolio_management/classification.py`, `README.md`

**Steps:**

1. Add comprehensive module docstring
1. Document classification rules and logic
1. Document override system usage
1. Add examples for common classifications
1. Update README.md with classification section
1. Document limitations and known issues
1. Provide recommendations for review

**Deliverables:**

- Complete documentation
- Usage examples
- README updates

**Validation:**

```bash
python -c "import src.portfolio_management.classification; help(src.portfolio_management.classification.AssetClassifier)"
```

______________________________________________________________________

## Stage 3: Return Calculation (Week 2, Days 5-7)

### Task 3.1: Create Return Configuration Model (1 hour)

**File:** `src/portfolio_management/returns.py` (NEW)

**Steps:**

1. Create module with docstring
1. Implement `ReturnConfig` dataclass:
   - `method: str = "simple"` # simple, log, excess
   - `frequency: str = "daily"` # daily, weekly, monthly
   - `risk_free_rate: float = 0.0` # annual rate for excess returns
   - `handle_missing: str = "forward_fill"` # forward_fill, drop, interpolate
   - `max_forward_fill_days: int = 5`
   - `min_periods: int = 2` # min periods for return calculation
   - `align_method: str = "outer"` # outer, inner for date alignment
1. Add validation method: `validate() -> None`
   - Check method in \["simple", "log", "excess"\]
   - Check frequency in \["daily", "weekly", "monthly"\]
   - Check handle_missing in \["forward_fill", "drop", "interpolate"\]
   - Check numeric values > 0
1. Add factory methods:
   - `default() -> ReturnConfig`
   - `monthly_simple() -> ReturnConfig`
   - `weekly_log() -> ReturnConfig`
1. Add comprehensive docstrings

**Deliverables:**

- ReturnConfig dataclass
- Validation logic
- Factory methods

**Validation:**

```bash
python -c "from src.portfolio_management.returns import ReturnConfig; cfg = ReturnConfig.default(); cfg.validate(); print('Valid')"
```

______________________________________________________________________

### Task 3.2: Implement Price Loading (2 hours)

**File:** `src/portfolio_management/returns.py`

**Steps:**

1. Create `PriceLoader` class
1. Implement `load_price_file(path: Path) -> pd.Series`:
   - Read CSV using pandas
   - Parse date column (assume format from Stooq)
   - Extract close price column
   - Set date as index
   - Return Series with dates and prices
1. Implement `load_multiple_prices(assets: list[SelectedAsset], prices_dir: Path) -> pd.DataFrame`:
   - Iterate through assets
   - Load each price file
   - Combine into DataFrame (columns = symbols)
   - Handle missing files (log warning, skip)
   - Handle loading errors (log, skip)
1. Add validation:
   - Check dates are sorted
   - Check prices are positive
   - Warn about gaps
1. Add progress logging for large batches
1. Add caching option (optional)

**Deliverables:**

- Price loading functionality
- Error handling
- Progress tracking

**Tests:** Create `tests/test_returns.py`

- Test single file loading
- Test multiple file loading
- Test missing file handling
- Test invalid data handling
- Use real fixtures from `data/processed/tradeable_prices_test/`

**Validation:**

```bash
pytest tests/test_returns.py::test_load_prices -v
```

______________________________________________________________________

### Task 3.3: Implement Return Calculation Methods (2.5 hours)

**File:** `src/portfolio_management/returns.py`

**Steps:**

1. Create `ReturnCalculator` class
1. Implement `_calculate_simple_returns(prices: pd.Series) -> pd.Series`:
   - `returns = prices.pct_change()`
   - Drop first NaN
   - Return Series
1. Implement `_calculate_log_returns(prices: pd.Series) -> pd.Series`:
   - `returns = np.log(prices / prices.shift(1))`
   - Drop first NaN
   - Return Series
1. Implement `_calculate_excess_returns(prices: pd.Series, risk_free_rate: float) -> pd.Series`:
   - Calculate simple returns
   - Convert annual risk_free_rate to daily: `(1 + rf)**(1/252) - 1`
   - Subtract daily risk_free from returns
   - Return Series
1. Implement `calculate_returns(prices: pd.DataFrame, config: ReturnConfig) -> pd.DataFrame`:
   - Dispatch to appropriate method based on config.method
   - Apply to all columns
   - Return DataFrame with same structure
1. Add validation:
   - Check for sufficient data (min_periods)
   - Warn about extreme returns (> 100%)
   - Handle zero prices

**Deliverables:**

- Three return calculation methods
- Dispatcher function
- Validation

**Tests:** Add to `tests/test_returns.py`

- Test simple returns calculation
- Test log returns calculation
- Test excess returns calculation
- Test with known data (verify correctness)
- Test edge cases (zero prices, single price)

**Validation:**

```bash
pytest tests/test_returns.py::test_calculate_returns -v
```

______________________________________________________________________

### Task 3.4: Implement Missing Data Handling (2 hours)

**File:** `src/portfolio_management/returns.py`

**Steps:**

1. Implement `_handle_missing_forward_fill(prices: pd.DataFrame, max_days: int) -> pd.DataFrame`:
   - Forward fill NaN values
   - Limit fill to max_days
   - Log fill statistics
   - Return filled DataFrame
1. Implement `_handle_missing_drop(prices: pd.DataFrame) -> pd.DataFrame`:
   - Drop rows with any NaN
   - Log dropped count
   - Return cleaned DataFrame
1. Implement `_handle_missing_interpolate(prices: pd.DataFrame) -> pd.DataFrame`:
   - Use linear interpolation
   - Limit interpolation gap
   - Log interpolated count
   - Return interpolated DataFrame
1. Implement `handle_missing_data(prices: pd.DataFrame, config: ReturnConfig) -> pd.DataFrame`:
   - Dispatch to appropriate handler
   - Return processed DataFrame
1. Add validation:
   - Check remaining NaN after handling
   - Warn if too much data dropped/filled

**Deliverables:**

- Three missing data handlers
- Dispatcher
- Statistics logging

**Tests:** Add to `tests/test_returns.py`

- Test forward fill
- Test drop
- Test interpolation
- Test with various gap sizes
- Test statistics accuracy

**Validation:**

```bash
pytest tests/test_returns.py::test_handle_missing -v
```

______________________________________________________________________

### Task 3.5: Implement Date Alignment (2 hours)

**File:** `src/portfolio_management/returns.py`

**Steps:**

1. Implement `_align_dates(returns: pd.DataFrame, config: ReturnConfig) -> pd.DataFrame`:
   - Use pd.DataFrame join with method from config.align_method
   - Options: outer (keep all dates), inner (only common dates)
   - Reindex to business days if configured
   - Return aligned DataFrame
1. Implement `_resample_to_frequency(returns: pd.DataFrame, frequency: str) -> pd.DataFrame`:
   - Daily: no change
   - Weekly: `returns.resample('W').sum()` for simple returns
   - Monthly: `returns.resample('M').sum()` for simple returns
   - For log returns: use sum (additive)
   - Return resampled DataFrame
1. Add validation:
   - Check date continuity
   - Warn about large gaps
   - Check frequency makes sense for data
1. Add min_coverage parameter:
   - Drop assets with \< X% non-NaN values after alignment
   - Log dropped assets

**Deliverables:**

- Date alignment logic
- Frequency resampling
- Coverage filtering

**Tests:** Add to `tests/test_returns.py`

- Test outer alignment
- Test inner alignment
- Test resampling (daily→weekly, daily→monthly)
- Test coverage filtering
- Test with misaligned dates

**Validation:**

```bash
pytest tests/test_returns.py::test_align_dates -v
```

______________________________________________________________________

### Task 3.6: Implement Complete Pipeline (2 hours)

**File:** `src/portfolio_management/returns.py`

**Steps:**

1. Implement `load_and_prepare(assets: list[SelectedAsset], prices_dir: Path, config: ReturnConfig) -> pd.DataFrame`:
   - Load prices using PriceLoader
   - Handle missing data
   - Calculate returns
   - Align dates
   - Resample to frequency
   - Apply coverage filter
   - Return final DataFrame
1. Add comprehensive logging at each stage:
   - Assets loaded
   - Missing data handled
   - Returns calculated
   - Dates aligned
   - Final shape
1. Add summary statistics:
   - Mean return per asset
   - Volatility per asset
   - Correlation summary
1. Add export functionality:
   - `export_returns(returns: pd.DataFrame, path: Path)`
   - Save as CSV with proper formatting
1. Handle edge cases:
   - No valid assets after filters
   - All returns are NaN
   - Single asset only

**Deliverables:**

- Complete end-to-end pipeline
- Comprehensive logging
- Export functionality

**Tests:** Add to `tests/test_returns.py`

- Test full pipeline with real fixtures
- Test with different configs
- Test edge cases
- Test export format
- Integration test with 10+ assets

**Validation:**

```bash
pytest tests/test_returns.py::test_load_and_prepare_pipeline -v
pytest tests/test_returns.py -v  # All return tests
```

______________________________________________________________________

### Task 3.7: Add CLI for Return Calculation (2 hours)

**File:** `scripts/calculate_returns.py` (NEW)

**Steps:**

1. Create CLI script with argparse
1. Add arguments:
   - `--assets` (required): Path to selected/classified assets CSV
   - `--prices-dir` (required): Directory with price files
   - `--output`: Path for returns CSV
   - `--method`: Return calculation method (default: simple)
   - `--frequency`: Resampling frequency (default: daily)
   - `--risk-free-rate`: Annual risk-free rate (default: 0.0)
   - `--handle-missing`: Missing data strategy (default: forward_fill)
   - `--max-forward-fill`: Max days to forward fill (default: 5)
   - `--min-coverage`: Minimum non-NaN coverage (default: 0.8)
   - `--summary`: Print summary statistics
1. Implement main function:
   - Load asset list
   - Build ReturnConfig
   - Run pipeline
   - Export results
1. Add summary output:
   - Assets with returns: N
   - Date range: YYYY-MM-DD to YYYY-MM-DD
   - Return statistics (mean, std per asset)
   - Top/bottom performers
1. Add validation:
   - Warn if many assets dropped
   - Warn if extreme returns detected

**Deliverables:**

- Return calculation CLI
- Summary statistics
- Validation warnings

**Tests:** Add to `tests/scripts/test_calculate_returns.py`

- Test CLI execution
- Test different return methods
- Test different frequencies
- Test summary output

**Validation:**

```bash
python scripts/calculate_returns.py \
  --assets /tmp/test_selection.csv \
  --prices-dir data/processed/tradeable_prices \
  --output /tmp/test_returns.csv \
  --method simple \
  --frequency monthly \
  --summary
head /tmp/test_returns.csv
```

______________________________________________________________________

### Task 3.8: Document Returns Module (1 hour)

**Files:** `src/portfolio_management/returns.py`, `README.md`

**Steps:**

1. Add comprehensive module docstring
1. Document each return method with formulas
1. Document missing data strategies
1. Add usage examples
1. Update README.md with returns section
1. Document limitations:
   - Assumes adjusted prices
   - No dividend reinvestment tracking
   - No currency conversion
1. Add performance notes for large universes

**Deliverables:**

- Complete documentation
- Formula explanations
- Usage examples

**Validation:**

```bash
python -c "import src.portfolio_management.returns; help(src.portfolio_management.returns.ReturnCalculator)"
```

______________________________________________________________________

## Stage 4: Universe Management (Week 2-3, Days 8-10)

### Task 4.1: Design Universe Configuration Schema (1.5 hours)

**File:** `config/universes.yaml` (NEW), `src/portfolio_management/universes.py` (NEW)

**Steps:**

1. Create `config/` directory
1. Design YAML schema for universe definitions:
   ```yaml
   universes:
     universe_name:
       description: "Human-readable description"
       filter_criteria:
         data_status: ["ok"]
         min_history_days: 756
         # ... all FilterCriteria fields
       classification_requirements:
         asset_classes: ["equity", "fixed_income"]
         geographies: ["developed_markets"]
       return_config:
         method: "simple"
         frequency: "monthly"
         # ... ReturnConfig fields
       constraints:
         min_assets: 20
         max_assets: 50
         min_coverage: 0.8
   ```
1. Create example universes:
   - `core_global`: High quality, diversified
   - `satellite_factor`: Tactical tilts
   - `defensive`: Bonds and alternatives
   - `equity_only`: Pure equity exposure
1. Document schema with comments
1. Add validation rules

**Deliverables:**

- YAML schema design
- Example universe configurations
- Schema documentation

**Validation:**

```bash
cat config/universes.yaml
python -c "import yaml; yaml.safe_load(open('config/universes.yaml'))"
```

______________________________________________________________________

### Task 4.2: Implement Universe Configuration Loader (2 hours)

**File:** `src/portfolio_management/universes.py`

**Steps:**

1. Create module with docstring
1. Implement `UniverseDefinition` dataclass:
   - All fields from YAML schema
   - Validation methods
1. Implement `UniverseConfigLoader`:
   - `load_config(path: Path) -> dict[str, UniverseDefinition]`
   - Parse YAML
   - Validate schema
   - Convert to UniverseDefinition objects
   - Return dict keyed by universe name
1. Add validation:
   - Required fields present
   - Valid enum values
   - Numeric constraints make sense
   - No duplicate universe names
1. Add helpful error messages for schema issues

**Deliverables:**

- Configuration loader
- Schema validation
- Error handling

**Tests:** Create `tests/test_universes.py`

- Test valid config loading
- Test invalid schema handling
- Test missing required fields
- Test duplicate names
- Create test config fixture

**Validation:**

```bash
pytest tests/test_universes.py::test_load_config -v
```

______________________________________________________________________

### Task 4.3: Implement UniverseManager Core (2.5 hours)

**File:** `src/portfolio_management/universes.py`

**Steps:**

1. Implement `UniverseManager` class:
   - `__init__(config_path: Path, matches_df: pd.DataFrame, prices_dir: Path)`
   - Store configuration, data sources
1. Implement `list_universes() -> list[str]`:
   - Return list of available universe names
1. Implement `get_definition(name: str) -> UniverseDefinition`:
   - Return definition for named universe
   - Raise error if not found
1. Implement `_select_assets(definition: UniverseDefinition) -> list[SelectedAsset]`:
   - Use AssetSelector with criteria from definition
   - Return selected assets
1. Implement `_classify_assets(assets: list[SelectedAsset]) -> pd.DataFrame`:
   - Use AssetClassifier
   - Return classified assets
1. Implement `_filter_by_classification(classified: pd.DataFrame, definition: UniverseDefinition) -> pd.DataFrame`:
   - Apply classification_requirements filters
   - Return filtered DataFrame
1. Implement `_calculate_returns(assets: list[SelectedAsset], definition: UniverseDefinition) -> pd.DataFrame`:
   - Use ReturnCalculator with return_config
   - Return returns DataFrame

**Deliverables:**

- UniverseManager core functionality
- Integration of selection, classification, returns

**Tests:** Add to `tests/test_universes.py`

- Test list_universes
- Test get_definition
- Test internal selection
- Test internal classification
- Test internal return calculation

**Validation:**

```bash
pytest tests/test_universes.py::test_universe_manager_core -v
```

______________________________________________________________________

### Task 4.4: Implement Universe Loading Pipeline (2 hours)

**File:** `src/portfolio_management/universes.py`

**Steps:**

1. Implement `load_universe(name: str) -> dict[str, pd.DataFrame]`:
   - Get universe definition
   - Select assets
   - Classify assets
   - Filter by classification
   - Calculate returns
   - Apply constraints (min/max assets)
   - Return dict with:
     - 'assets': Selected assets
     - 'classifications': Classifications
     - 'returns': Return data
     - 'metadata': Summary info
1. Add comprehensive logging for each stage
1. Add validation:
   - Check min_assets constraint
   - Check max_assets constraint (trim if exceeded)
   - Check min_coverage requirement
1. Add caching option:
   - Cache loaded universes
   - Invalidate on data changes

**Deliverables:**

- Complete universe loading pipeline
- Constraint enforcement
- Optional caching

**Tests:** Add to `tests/test_universes.py`

- Test full universe loading
- Test constraint enforcement
- Test with multiple universes
- Test caching behavior

**Validation:**

```bash
pytest tests/test_universes.py::test_load_universe -v
```

______________________________________________________________________

### Task 4.5: Implement Universe Comparison Tools (1.5 hours)

**File:** `src/portfolio_management/universes.py`

**Steps:**

1. Implement `compare_universes(names: list[str]) -> pd.DataFrame`:
   - Load each universe
   - Collect statistics:
     - Asset count
     - Asset class breakdown
     - Geography breakdown
     - Return statistics (mean, std)
     - Overlap between universes
   - Return comparison DataFrame
1. Implement `get_universe_overlap(name1: str, name2: str) -> set[str]`:
   - Load both universes
   - Return set of common symbols/ISINs
1. Implement `validate_universe(name: str) -> dict[str, Any]`:
   - Load universe
   - Check all constraints
   - Return validation report:
     - is_valid: bool
     - issues: list\[str\]
     - warnings: list\[str\]
     - statistics: dict

**Deliverables:**

- Comparison functionality
- Overlap analysis
- Validation reporting

**Tests:** Add to `tests/test_universes.py`

- Test universe comparison
- Test overlap calculation
- Test validation with valid universe
- Test validation with invalid universe

**Validation:**

```bash
pytest tests/test_universes.py::test_comparison_tools -v
```

______________________________________________________________________

### Task 4.6: Add CLI for Universe Management (2.5 hours)

**File:** `scripts/manage_universes.py` (NEW)

**Steps:**

1. Create CLI script with subcommands:
   - `list`: List available universes
   - `show <name>`: Show universe details
   - `load <name>`: Load and export universe
   - `compare <name1> <name2> ...`: Compare universes
   - `validate <name>`: Validate universe configuration
1. Implement `list` command:
   - Load config
   - Print universe names and descriptions
1. Implement `show` command:
   - Load universe definition
   - Print all configuration details
   - Print expected asset count (estimate)
1. Implement `load` command:
   - Load complete universe
   - Export assets, classifications, returns to files
   - Print summary statistics
1. Implement `compare` command:
   - Load multiple universes
   - Print comparison table
   - Show overlap percentages
1. Implement `validate` command:
   - Run validation
   - Print validation report
   - Exit with error code if invalid

**Deliverables:**

- Complete CLI with subcommands
- Rich output formatting
- Error handling

**Tests:** Add to `tests/scripts/test_manage_universes.py`

- Test each subcommand
- Test error handling
- Test output format

**Validation:**

```bash
python scripts/manage_universes.py list
python scripts/manage_universes.py show core_global
python scripts/manage_universes.py validate core_global
```

______________________________________________________________________

### Task 4.7: Create Predefined Universes (2 hours)

**File:** `config/universes.yaml`

**Steps:**

1. Design and document `core_global` universe:
   - High quality only (data_status: ok)
   - 3+ years history
   - Low zero-volume severity
   - Diversified asset classes
   - Target: 30-50 assets
1. Design `satellite_factor` universe:
   - Allow warnings
   - 2+ years history
   - Factor-oriented selection
   - Target: 20-30 assets
1. Design `defensive` universe:
   - Fixed income focus
   - Alternatives included
   - High quality
   - Target: 10-20 assets
1. Design `equity_only` universe:
   - Pure equity exposure
   - Geographic diversity
   - Quality focus
   - Target: 40-60 assets
1. Test each universe:
   - Validate configuration
   - Load successfully
   - Check asset counts
   - Review classifications
1. Document rationale and use cases for each

**Deliverables:**

- 4 predefined universes
- Documentation for each
- Validation testing

**Validation:**

```bash
python scripts/manage_universes.py validate core_global
python scripts/manage_universes.py validate satellite_factor
python scripts/manage_universes.py validate defensive
python scripts/manage_universes.py validate equity_only
python scripts/manage_universes.py compare core_global equity_only
```

______________________________________________________________________

### Task 4.8: Document Universe System (1.5 hours)

**Files:** `config/universes.yaml`, `README.md`, `docs/universes.md` (NEW)

**Steps:**

1. Add comprehensive comments to universes.yaml
1. Create `docs/universes.md`:
   - Schema reference
   - Configuration guide
   - Best practices
   - Example universes explained
1. Add usage examples:
   - Creating custom universe
   - Modifying existing universe
   - Common patterns
1. Update README.md:
   - Add universe management section
   - Link to detailed docs
   - Show CLI examples
1. Document limitations and considerations

**Deliverables:**

- Complete documentation
- User guide
- Configuration reference

**Validation:**

```bash
cat docs/universes.md
grep -i universe README.md
```

______________________________________________________________________

## Stage 5: Integration & Polish (Week 3, Days 11-15)

### Task 5.1: End-to-End Integration Tests (3 hours)

**File:** `tests/integration/test_full_pipeline.py` (NEW)

**Steps:**

1. Create integration test directory
1. Implement test for complete workflow:
   - Load real match report (test subset)
   - Select assets with FilterCriteria
   - Classify selected assets
   - Calculate returns
   - Validate all data flows correctly
1. Implement test for multiple universes:
   - Load 2+ universes
   - Verify independence
   - Check overlap analysis
1. Implement test with production data:
   - Use actual tradeable_matches.csv (first 100 rows)
   - Use actual price files from test directory
   - Verify no errors
1. Implement performance test:
   - Measure time for various operations
   - Ensure \< 30s for 1000 assets
1. Add stress tests:
   - Empty result handling
   - All assets filtered out
   - Missing price files
   - Corrupted data

**Deliverables:**

- Comprehensive integration tests
- Performance benchmarks
- Stress tests

**Validation:**

```bash
pytest tests/integration/test_full_pipeline.py -v --durations=10
```

______________________________________________________________________

### Task 5.2: Performance Optimization (2 hours)

**Files:** Various

**Steps:**

1. Profile key operations:
   - Price loading (bottleneck?)
   - Return calculation
   - Classification
   - Universe loading
1. Optimize price loading:
   - Consider parallel loading
   - Add progress bar for user feedback
   - Cache loaded prices
1. Optimize return calculation:
   - Vectorize operations
   - Use numpy where possible
   - Avoid loops
1. Optimize classification:
   - Pre-compile regex patterns
   - Cache keyword lookups
1. Add caching layer:
   - Cache universe loads
   - Cache return calculations
   - Invalidate on data changes
1. Test performance improvements:
   - Measure before/after
   - Target: 5000 assets in \< 30s

**Deliverables:**

- Performance improvements
- Caching implementation
- Benchmarks

**Validation:**

```bash
python -m cProfile -o /tmp/profile.stats scripts/manage_universes.py load core_global
python -c "import pstats; p = pstats.Stats('/tmp/profile.stats'); p.sort_stats('cumulative'); p.print_stats(20)"
```

______________________________________________________________________

### Task 5.3: Error Handling & Validation (2 hours)

**Files:** All modules

**Steps:**

1. Review all error cases:
   - Missing files
   - Invalid data
   - Configuration errors
   - Constraint violations
1. Add custom exceptions:
   - `UniverseError`
   - `ClassificationError`
   - `ReturnCalculationError`
1. Improve error messages:
   - Clear, actionable messages
   - Include context (which file, which asset)
   - Suggest fixes
1. Add validation at boundaries:
   - CLI argument validation
   - Configuration validation
   - Data validation
1. Add defensive checks:
   - Non-None assertions
   - Type checks where critical
   - Range checks for numerics
1. Test error paths:
   - Add tests for each error type
   - Verify error messages

**Deliverables:**

- Custom exceptions
- Improved error handling
- Validation tests

**Validation:**

```bash
pytest tests/ -v -k "error or invalid or exception"
```

______________________________________________________________________

### Task 5.4: Logging & Diagnostics (1.5 hours)

**Files:** All modules

**Steps:**

1. Standardize logging:
   - Use Python logging module
   - Consistent format
   - Appropriate log levels
1. Add diagnostic logging:
   - Start/end of major operations
   - Input/output sizes
   - Time taken
   - Resources used
1. Add verbose mode support:
   - CLI --verbose flag
   - Detailed logging when enabled
   - Silent mode for production
1. Add progress indicators:
   - Progress bars for long operations
   - Percentage complete
   - ETA if possible
1. Add logging configuration:
   - Control via config file
   - Set log level
   - Set log destination

**Deliverables:**

- Standardized logging
- Progress indicators
- Configurable logging

**Validation:**

```bash
python scripts/manage_universes.py load core_global --verbose
python scripts/manage_universes.py load core_global --quiet
```

______________________________________________________________________

### Task 5.5: CLI Polish & User Experience (2 hours)

**Files:** All scripts in `scripts/`

**Steps:**

1. Improve CLI help messages:
   - Clear descriptions
   - Usage examples
   - Default value indicators
1. Add input validation:
   - Check file exists before processing
   - Validate argument combinations
   - Provide suggestions for typos
1. Add dry-run mode to all commands:
   - Show what would happen
   - Don't modify anything
1. Add confirmation prompts:
   - Before overwriting files
   - Before long operations
   - Optional --yes flag to skip
1. Improve output formatting:
   - Tables for comparisons
   - Color coding (optional)
   - Clear section headers
1. Add examples to help:
   - Common use cases
   - Quick start guide

**Deliverables:**

- Polished CLI experience
- Better help messages
- Validation and safety

**Validation:**

```bash
python scripts/manage_universes.py --help
python scripts/select_assets.py --help
python scripts/classify_assets.py --help
python scripts/calculate_returns.py --help
```

______________________________________________________________________

### Task 5.6: Comprehensive Documentation (3 hours)

**Files:** `README.md`, `docs/` directory

**Steps:**

1. Update README.md:
   - Add Phase 3 completion status
   - Update feature list
   - Add usage examples for new features
   - Update repository structure
1. Create `docs/phase3_guide.md`:
   - Complete user guide
   - Step-by-step tutorials
   - Configuration examples
   - Troubleshooting section
1. Create `docs/api_reference.md`:
   - Document all public classes
   - Document all public methods
   - Include examples
1. Create `docs/architecture.md`:
   - System design overview
   - Module relationships
   - Data flow diagrams
1. Add docstring examples to all modules:
   - Usage examples in docstrings
   - Include in help() output
1. Create Jupyter notebook examples:
   - `examples/asset_selection.ipynb`
   - `examples/universe_management.ipynb`
   - `examples/custom_universe.ipynb`

**Deliverables:**

- Updated README
- Comprehensive documentation
- API reference
- Example notebooks

**Validation:**

```bash
grep -i "Phase 3" README.md
ls docs/*.md
cat docs/phase3_guide.md | head -50
```

______________________________________________________________________

### Task 5.7: Update Memory Bank (1 hour)

**Files:** `memory-bank/*.md`

**Steps:**

1. Update `progress.md`:
   - Mark Phase 3 as complete
   - Update metrics table
   - Document achievements
   - Add Phase 4 preview
1. Update `activeContext.md`:
   - Current status
   - Recent changes
   - Next focus
1. Update `systemPatterns.md`:
   - Add asset selection patterns
   - Document universe management approach
   - Update component relationships
1. Update `techContext.md`:
   - Add new dependencies
   - Update stack summary
1. Review and update other memory bank files as needed

**Deliverables:**

- Updated memory bank
- Accurate status
- Ready for next phase

**Validation:**

```bash
grep "Phase 3" memory-bank/progress.md
grep "asset selection" memory-bank/systemPatterns.md
```

______________________________________________________________________

### Task 5.8: Final Testing & Quality Assurance (3 hours)

**Steps:**

1. Run complete test suite:
   ```bash
   pytest tests/ -v --cov=src/portfolio_management --cov-report=term-missing
   ```
1. Check test coverage:
   - Target: ≥80% for new modules
   - Identify untested code paths
   - Add missing tests
1. Run type checking:
   ```bash
   mypy src/portfolio_management/
   ```
1. Run linting:
   ```bash
   ruff check src/portfolio_management/ scripts/ tests/
   ```
1. Run formatting:
   ```bash
   black --check src/portfolio_management/ scripts/ tests/
   isort --check src/portfolio_management/ scripts/ tests/
   ```
1. Run all CLI commands manually:
   - Test each script with real data
   - Verify outputs
   - Check error handling
1. Run pre-commit hooks:
   ```bash
   pre-commit run --all-files
   ```
1. Fix any issues found

**Deliverables:**

- 100% passing tests
- ≥80% coverage
- Clean type checking
- Clean linting
- All pre-commit hooks passing

**Validation:**

```bash
pytest tests/ -v --cov=src/portfolio_management --cov-report=term-missing
mypy src/portfolio_management/
ruff check src/portfolio_management/ scripts/ tests/
pre-commit run --all-files
```

______________________________________________________________________

## Summary Checklist

### Stage 1: Asset Selection Core ✓

- \[x\] Task 1.1: Data models (FilterCriteria, SelectedAsset)
- \[x\] Task 1.2: Data quality filter
- \[x\] Task 1.3: History filter
- \[x\] Task 1.4: Characteristics filter
- \[x\] Task 1.5: Allowlist/blocklist
- \[x\] Task 1.6: Main selection method
- \[x\] Task 1.7: Test fixtures
- \[x\] Task 1.8: CLI command
- \[x\] Task 1.9: Documentation

### Stage 2: Asset Classification ✓

- \[x\] Task 2.1: Classification taxonomy
- \[x\] Task 2.2: Rule-based classification
- \[x\] Task 2.3: Manual override system
- \[x\] Task 2.4: Batch classification
- \[x\] Task 2.5: CLI command
- \[x\] Task 2.6: Documentation

### Stage 3: Return Calculation ✓

- \[x\] Task 3.1: Return configuration model
- \[x\] Task 3.2: Price loading
- \[x\] Task 3.3: Return calculation methods
- \[x\] Task 3.4: Missing data handling
- \[x\] Task 3.5: Date alignment
- \[x\] Task 3.6: Complete pipeline
- \[x\] Task 3.7: Add CLI for Return Calculation
- \[x\] Task 3.8: Documentation

### Stage 4: Universe Management ✓

- \[x\] Task 4.1: Configuration schema
- \[x\] Task 4.2: Configuration loader
- \[x\] Task 4.3: UniverseManager core
- \[x\] Task 4.4: Universe loading pipeline
- \[x\] Task 4.5: Comparison tools
- \[x\] Task 4.6: CLI command
- \[x\] Task 4.7: Predefined universes
- \[x\] Task 4.8: Documentation

### Stage 5: Integration & Polish ✓

- \[ \] Task 5.1: Integration tests
- \[ \] Task 5.2: Performance optimization
- \[ \] Task 5.3: Error handling
- \[ \] Task 5.4: Logging & diagnostics
- \[ \] Task 5.5: CLI polish
- \[ \] Task 5.6: Comprehensive documentation
- \[ \] Task 5.7: Update memory bank
- \[ \] Task 5.8: Final QA

______________________________________________________________________

## Success Criteria

- \[ \] All 45 tasks completed
- \[ \] Test coverage ≥80% for new modules
- \[ \] All tests passing (target: 70+ total tests)
- \[ \] Zero mypy errors in new modules
- \[ \] All CLI commands functional
- \[ \] Documentation complete
- \[ \] Memory bank updated
- \[ \] Pre-commit hooks passing
- \[ \] Can load and process 1000+ assets in \<30s
- \[ \] Ready for Phase 4 (Portfolio Construction Strategies)

______________________________________________________________________

## Time Tracking

| Stage | Estimated | Actual | Notes |
|-------|-----------|--------|-------|
| Stage 1 | 14.5 hours | | |
| Stage 2 | 10 hours | | |
| Stage 3 | 13.5 hours | | |
| Stage 4 | 14.5 hours | | |
| Stage 5 | 16.5 hours | | |
| **Total** | **69 hours** | | ~3 weeks @ 20-25 hrs/week |

______________________________________________________________________

## Next Steps After Completion

Once Phase 3 is complete:

1. **Update project status**

   - Mark Phase 3 complete in all documentation
   - Update CODE_REVIEW.md with Phase 3 assessment
   - Celebrate milestone! 🎉

1. **Plan Phase 4: Portfolio Construction Strategies**

   - Strategy interface design
   - Equal-weight implementation
   - Risk parity implementation
   - Mean-variance implementation

1. **Plan Phase 5: Backtesting & Rebalancing**

   - Historical simulation
   - Transaction costs
   - Rebalancing logic
   - Performance analytics

1. **Consider optional enhancements**

   - Web UI for universe management
   - Advanced factor models
   - Optimization constraints
   - Real-time data integration
