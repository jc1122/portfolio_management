# Phase 3: Asset Selection for Portfolio Construction

## Overview

This phase focuses on building the **asset selection pipeline** that filters and prepares the tradeable universe for portfolio construction. The goal is to create a robust, configurable system that selects appropriate instruments based on data quality, liquidity, diversification requirements, and investment objectives.

## Current State

**Data Available:**

- ✅ 5,560 matched instruments (tradeable universe → Stooq price data)
- ✅ 4,498 exported price files with historical data
- ✅ Comprehensive data quality flags (zero volume, empty files, date validation)
- ✅ Currency reconciliation (match, inferred_only, override)
- ✅ Market/category/region metadata for diversification

**Data Quality Summary:**

- **OK**: 3,956 instruments (71%)
- **Warning**: 1,602 instruments (29%) - mostly zero-volume issues
- **Empty**: 2 instruments (\<1%)
- Zero-volume severity levels: low, moderate, high

## Phase 3 Objectives

### 1. Asset Universe Filtering

Create a multi-stage filtering pipeline that:

- Filters by data quality (exclude empty, optionally handle warnings)
- Filters by liquidity criteria (minimum volume, zero-volume thresholds)
- Filters by data completeness (minimum history length, maximum gaps)
- Filters by asset characteristics (market, region, category, currency)
- Supports allowlist/blocklist for specific instruments

### 2. Portfolio Universe Definition

Define and manage multiple portfolio universes:

- **Core Universe**: High-quality, liquid instruments for core allocation
- **Satellite Universe**: Additional instruments for tactical tilts
- **Factor Universes**: Instruments grouped by factors (value, quality, momentum, size)
- **Defensive Universe**: Bonds, alternatives, cash equivalents

### 3. Asset Classification

Classify instruments for portfolio construction:

- **Asset Classes**: Equity, Fixed Income, Alternatives, Cash
- **Sub-Classes**: Large Cap, Small Cap, Growth, Value, Government Bonds, Corporate Bonds
- **Geography**: Developed Markets, Emerging Markets, Regional breakdowns
- **Sectors**: If derivable from metadata or manual tagging

### 4. Data Preparation for Optimization

Prepare price data for portfolio engines:

- Load and align price histories
- Calculate returns (simple, log, excess over risk-free)
- Handle missing data (forward fill, interpolation, exclusion)
- Resample to desired frequency (daily, weekly, monthly)
- Export to standardized format for strategy modules

### 5. Configuration & Orchestration

Build configuration system for:

- Filter criteria (YAML/JSON configuration)
- Universe definitions (core vs. satellite)
- Data preparation parameters (return calculation, resampling)
- CLI interface for universe selection and inspection

## Technical Design

### Module Structure

```
src/portfolio_management/
├── selection.py          # NEW: Asset filtering and universe management
├── classification.py     # NEW: Asset classification logic
├── returns.py           # NEW: Return calculation and alignment
├── universes.py         # NEW: Universe definitions and loading
└── config.py            # EXTEND: Add selection configuration
```

### Core Components

#### 1. `selection.py` - Asset Selection Pipeline

```python
@dataclass
class FilterCriteria:
    """Criteria for filtering tradeable instruments."""
    data_status: list[str] = field(default_factory=lambda: ["ok"])
    min_history_days: int = 252  # ~1 year
    max_gap_days: int = 10
    min_price_rows: int = 252
    zero_volume_severity: list[str] = field(default_factory=lambda: ["low", "moderate"])
    markets: list[str] | None = None  # None = all markets
    regions: list[str] | None = None
    currencies: list[str] | None = None
    allowlist: list[str] | None = None  # Explicit ISINs/symbols to include
    blocklist: list[str] | None = None  # Explicit ISINs/symbols to exclude

@dataclass
class SelectedAsset:
    """Asset that passed all filters."""
    symbol: str
    isin: str
    name: str
    market: str
    region: str
    currency: str
    price_start: date
    price_end: date
    price_rows: int
    data_status: str
    data_flags: str
    stooq_path: str

class AssetSelector:
    """Filter tradeable universe based on quality and criteria."""

    def select_assets(
        self,
        matches: pd.DataFrame,
        criteria: FilterCriteria,
    ) -> list[SelectedAsset]:
        """Apply multi-stage filtering to match report."""
        pass

    def _filter_by_data_quality(self, df: pd.DataFrame) -> pd.DataFrame:
        """Stage 1: Filter by data_status and severity."""
        pass

    def _filter_by_history(self, df: pd.DataFrame) -> pd.DataFrame:
        """Stage 2: Filter by history length and completeness."""
        pass

    def _filter_by_characteristics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Stage 3: Filter by market/region/currency."""
        pass

    def _apply_lists(self, df: pd.DataFrame) -> pd.DataFrame:
        """Stage 4: Apply allowlist/blocklist."""
        pass
```

#### 2. `classification.py` - Asset Classification

```python
@dataclass
class AssetClass(Enum):
    EQUITY = "equity"
    FIXED_INCOME = "fixed_income"
    ALTERNATIVE = "alternative"
    CASH = "cash"

@dataclass
class AssetClassification:
    """Classification of an asset for portfolio construction."""
    symbol: str
    isin: str
    asset_class: AssetClass
    sub_class: str  # e.g., "large_cap_equity", "government_bond"
    geography: str  # e.g., "developed_markets", "emerging_markets"
    sector: str | None = None

class AssetClassifier:
    """Classify assets based on metadata and rules."""

    def classify_asset(self, asset: SelectedAsset) -> AssetClassification:
        """Classify single asset."""
        pass

    def classify_universe(self, assets: list[SelectedAsset]) -> pd.DataFrame:
        """Classify all assets in universe."""
        pass

    def _infer_asset_class(self, asset: SelectedAsset) -> AssetClass:
        """Infer asset class from name/market/category."""
        pass
```

#### 3. `returns.py` - Return Calculation

```python
@dataclass
class ReturnConfig:
    """Configuration for return calculation."""
    method: str = "simple"  # "simple", "log", "excess"
    frequency: str = "daily"  # "daily", "weekly", "monthly"
    risk_free_rate: float = 0.0  # Annual rate for excess returns
    handle_missing: str = "forward_fill"  # "forward_fill", "drop", "interpolate"
    max_forward_fill_days: int = 5

class ReturnCalculator:
    """Calculate and align returns for portfolio optimization."""

    def calculate_returns(
        self,
        prices: pd.DataFrame,
        config: ReturnConfig,
    ) -> pd.DataFrame:
        """Calculate returns from price data."""
        pass

    def align_returns(
        self,
        returns: pd.DataFrame,
        min_coverage: float = 0.8,
    ) -> pd.DataFrame:
        """Align returns across assets, handle missing data."""
        pass

    def load_and_prepare(
        self,
        assets: list[SelectedAsset],
        prices_dir: Path,
        config: ReturnConfig,
    ) -> pd.DataFrame:
        """Full pipeline: load prices → calculate returns → align."""
        pass
```

#### 4. `universes.py` - Universe Management

```python
@dataclass
class UniverseDefinition:
    """Definition of a portfolio universe."""
    name: str
    description: str
    filter_criteria: FilterCriteria
    classification_rules: dict[str, Any]
    min_assets: int = 10
    max_assets: int | None = None

class UniverseManager:
    """Manage multiple portfolio universes."""

    def __init__(self, config_path: Path):
        self.universes = self._load_universes(config_path)

    def get_universe(self, name: str) -> list[SelectedAsset]:
        """Load and filter assets for named universe."""
        pass

    def list_universes(self) -> list[str]:
        """List available universe names."""
        pass

    def validate_universe(self, name: str) -> dict[str, Any]:
        """Check universe meets minimum requirements."""
        pass
```

### Configuration Format

**config/universes.yaml:**

```yaml
universes:
  core_global:
    description: "High-quality global equity and bond ETFs"
    filter_criteria:
      data_status: ["ok"]
      min_history_days: 756  # ~3 years
      max_gap_days: 5
      zero_volume_severity: ["low"]
      markets: ["LSE", "XETRA", "EURONEXT"]
    classification_rules:
      asset_classes: ["equity", "fixed_income"]
    min_assets: 20
    max_assets: 50

  satellite_factor:
    description: "Factor-tilted instruments for tactical allocation"
    filter_criteria:
      data_status: ["ok", "warning"]
      min_history_days: 504  # ~2 years
      zero_volume_severity: ["low", "moderate"]
    classification_rules:
      factors: ["value", "quality", "momentum", "size"]
    min_assets: 10
    max_assets: 30

  defensive:
    description: "Bonds and alternatives for risk reduction"
    filter_criteria:
      data_status: ["ok"]
      min_history_days: 504
    classification_rules:
      asset_classes: ["fixed_income", "alternative"]
    min_assets: 5
```

## Implementation Plan

### Stage 1: Asset Selection Core (Week 1)

**Priority: HIGH**

1. **Implement FilterCriteria and SelectedAsset models** (2 hours)

   - Dataclasses for criteria and results
   - Validation logic for criteria

1. **Build AssetSelector with multi-stage filtering** (4 hours)

   - Data quality filtering (status, severity)
   - History filtering (length, gaps)
   - Characteristics filtering (market, region, currency)
   - Allowlist/blocklist logic

1. **Create comprehensive tests** (3 hours)

   - Test each filter stage independently
   - Test combined filtering pipeline
   - Edge cases (empty results, all excluded, etc.)
   - Use existing test fixtures

1. **CLI interface for inspection** (2 hours)

   - Command to list filtered assets
   - Summary statistics (count, quality breakdown)
   - Export filtered universe to CSV

**Deliverable:** Functional asset selector with CLI

### Stage 2: Asset Classification (Week 1-2)

**Priority: HIGH**

1. **Design classification taxonomy** (2 hours)

   - Define asset classes and sub-classes
   - Define geography categories
   - Research sector classification (if feasible)

1. **Implement AssetClassifier** (4 hours)

   - Rule-based classification from metadata
   - Handle edge cases (unknown/ambiguous)
   - Support manual overrides

1. **Create classification tests** (2 hours)

   - Test classification rules
   - Test edge cases
   - Validate classification coverage

1. **Integrate with selection pipeline** (2 hours)

   - Add classification to selection output
   - Update CLI to show classifications

**Deliverable:** Classification system integrated with selection

### Stage 3: Return Calculation (Week 2)

**Priority: HIGH**

1. **Implement ReturnConfig and ReturnCalculator** (3 hours)

   - Simple/log/excess return methods
   - Frequency resampling
   - Missing data handling

1. **Build price loading and alignment** (4 hours)

   - Load multiple price files efficiently
   - Align dates across assets
   - Handle missing data according to config
   - Memory-efficient for large universes

1. **Create return calculation tests** (3 hours)

   - Test return methods
   - Test alignment logic
   - Test missing data handling
   - Validate against known benchmarks

1. **CLI interface for return data** (2 hours)

   - Command to export returns for universe
   - Summary statistics (mean, volatility, correlation)

**Deliverable:** Return calculation pipeline with CLI

### Stage 4: Universe Management (Week 2-3)

**Priority: MEDIUM**

1. **Design universe configuration schema** (2 hours)

   - YAML/JSON format
   - Validation logic
   - Multiple universe definitions

1. **Implement UniverseManager** (3 hours)

   - Load configurations
   - Instantiate selectors with criteria
   - Cache results for performance

1. **Create predefined universes** (2 hours)

   - Core global (high quality)
   - Satellite factor (tactical)
   - Defensive (risk reduction)
   - Document rationale for each

1. **Build universe inspection tools** (2 hours)

   - List available universes
   - Show universe statistics
   - Compare universes

**Deliverable:** Universe management system with configurations

### Stage 5: Integration & Documentation (Week 3)

**Priority: MEDIUM**

1. **End-to-end integration tests** (3 hours)

   - Test full pipeline: selection → classification → returns
   - Test multiple universes
   - Test with production data

1. **Performance optimization** (2 hours)

   - Profile price loading
   - Optimize alignment algorithm
   - Add caching where appropriate

1. **Documentation** (3 hours)

   - Module docstrings and type hints
   - User guide for universe configuration
   - Examples and tutorials
   - Update memory bank

1. **CLI polish** (2 hours)

   - Improve error messages
   - Add progress indicators
   - Add dry-run mode
   - Add verbose logging

**Deliverable:** Production-ready asset selection system

## Success Criteria

### Functional Requirements

- ✅ Filter tradeable universe by data quality, history, and characteristics
- ✅ Classify assets by asset class, geography, and other attributes
- ✅ Calculate aligned returns for portfolio optimization
- ✅ Manage multiple universe definitions via configuration
- ✅ CLI interface for universe inspection and export

### Quality Requirements

- ✅ Test coverage ≥80% for new modules
- ✅ Zero regressions in existing tests
- ✅ Type hints for all public APIs (mypy clean)
- ✅ Performance: Load and filter 5,000+ assets in \<30s
- ✅ Memory: Handle 500+ assets × 10 years daily data

### Documentation Requirements

- ✅ Comprehensive docstrings for all classes/functions
- ✅ User guide for universe configuration
- ✅ Examples demonstrating common use cases
- ✅ Memory bank updated with design decisions

## Risk Mitigation

### Risk: Classification Ambiguity

**Mitigation:** Start with simple rule-based classification, support manual overrides, document classification logic clearly

### Risk: Missing Data Handling

**Mitigation:** Multiple strategies (forward fill, drop, interpolate), configurable limits, clear diagnostics

### Risk: Performance with Large Universes

**Mitigation:** Lazy loading, efficient alignment algorithms, caching, progress indicators

### Risk: Configuration Complexity

**Mitigation:** Sensible defaults, validation with helpful errors, examples for common cases

## Next Steps After Phase 3

**Phase 4: Portfolio Construction Strategies**

- Implement equal-weight baseline
- Implement risk parity via `riskparityportfolio`
- Implement mean-variance via `PyPortfolioOpt`
- Strategy adapter interface

**Phase 5: Backtesting & Rebalancing**

- Historical portfolio simulation
- Rebalancing logic with transaction costs
- Opportunistic bands (±20%)
- Portfolio guardrails

**Phase 6: Performance Analytics & Reporting**

- Risk metrics (Sharpe, drawdown, ES)
- Factor exposure analysis
- Visualization (equity curves, allocations)
- Decision logs and compliance reports

## Open Questions

1. **Asset Classification Schema**: Should we use a standard taxonomy (GICS, ICB) or custom categories aligned with investment strategy?

1. **Return Calculation Frequency**: Should we support multiple frequencies simultaneously or force users to choose one?

1. **Universe Caching**: Should we cache filtered universes or always recompute from latest match report?

1. **Factor Attribution**: How should factor tilts (value, quality, momentum) be tagged? Manual labels, derived from name, or external data source?

1. **Benchmark Selection**: Should asset selection automatically identify benchmark instruments (e.g., S&P 500, AGG for bonds)?

1. **Currency Handling**: Should returns be calculated in local currency, converted to portfolio base currency (PLN/USD), or support both?

1. **Corporate Actions**: Do we need to handle splits, dividends, or assume adjusted prices from Stooq are sufficient?

## Resources

**Data Quality Reference:**

- Match report: `data/metadata/tradeable_matches.csv`
- Unmatched report: `data/metadata/tradeable_unmatched.csv`
- Price files: `data/processed/tradeable_prices/`

**Existing Codebase:**

- Models: `src/portfolio_management/models.py`
- I/O: `src/portfolio_management/io.py`
- Analysis: `src/portfolio_management/analysis.py`
- Config: `src/portfolio_management/config.py`

**External Libraries:**

- pandas: Data manipulation
- numpy: Numerical operations
- pyyaml: Configuration loading
- dataclasses: Type-safe models

**Testing:**

- pytest: Test framework
- Test fixtures: `tests/fixtures/`
- Conftest: `tests/conftest.py`
