# Preselection Edge Cases and Robustness

This document describes the edge case handling, tie-breaking rules, and known limitations of the preselection factor computation system.

## Tie-Breaking Rules

The preselection system uses **deterministic tie-breaking** to ensure consistent, reproducible results across runs.

### Primary Rule: Score-Based Ranking

Assets are ranked primarily by their factor score (momentum, low-volatility, or combined).

### Secondary Rule: Alphabetical Tie-Breaking

When multiple assets have identical scores (or scores within numerical precision), ties are broken **alphabetically by asset symbol**.

**Example:**

```python
# Three assets with identical momentum scores
"ASSET_A": 0.001  # Rank 1 (alphabetically first)
"ASSET_C": 0.001  # Rank 2
"ASSET_B": 0.001  # Rank 3

# If top_k=2, selected assets are: ["ASSET_A", "ASSET_B"]
```

### Tie-Breaking at Selection Boundary

When ties occur at the selection boundary (e.g., ranks 29-32 tied when top_k=30), the system selects the first k assets alphabetically from the tied group.

**Example:**

```python
# 5 assets tied at boundary (ranks 28-32) when top_k=30
"TIE_Z": 0.002  # Not selected (alphabetically last)
"TIE_A": 0.002  # Selected (alphabetically 1st)
"TIE_M": 0.002  # Selected (alphabetically 3rd)
"TIE_B": 0.002  # Selected (alphabetically 2nd)
"TIE_Y": 0.002  # Not selected (alphabetically 4th)

# Top 27 assets with higher scores all selected
# From tied group, selects: ["TIE_A", "TIE_B", "TIE_M"]
```

### Numerical Precision Handling

The system treats values that differ by less than ~1e-10 as potentially identical due to floating-point arithmetic. The deterministic tie-breaking ensures consistent ordering even with numerical precision issues.

## Edge Case Behavior

### Empty or Minimal Result Sets

#### No Assets Meet Criteria

- **Behavior**: Raises `InsufficientDataError` if no data meets `min_periods` requirement
- **Use Case**: Early universe construction with limited history

#### All Assets Have Insufficient Data

- **Behavior**: Filters to only assets with valid scores; may return fewer than top_k assets
- **Use Case**: Sparse data scenarios

#### Single Asset Selection (top_k=1)

- **Behavior**: Selects exactly one asset deterministically
- **Guaranteed**: Same config + same data = same asset selected

#### Result Set Smaller Than top_k

- **Behavior**: Returns all valid assets (fewer than requested)
- **Example**: Request top_k=10, only 3 assets have valid data → returns 3 assets

### Combined Factor Edge Cases

#### One Factor All NaN

- **Behavior**: Standardization returns neutral scores (zeros) for NaN factor
- **Impact**: Selection driven primarily by the valid factor
- **Example**: All-zero returns → momentum=0 for all, selection based on volatility

#### Both Factors All NaN

- **Behavior**: Standardization returns zeros (neutral scores) for all assets
- **Selection**: Tie-breaking by symbol (alphabetically first assets selected)
- **Note**: No crash; deterministic behavior maintained

#### Extreme Weight Ratios

- **Supported**: Weights from 0.01/0.99 to 0.99/0.01
- **Behavior**: Gracefully handles weights heavily skewed toward one factor
- **Validation**: Weights must sum to 1.0 (±1e-6 tolerance)

### Data Quality Issues

#### All-Zero Returns

- **Behavior**: Momentum = 0 for all assets; volatility may be zero or very low
- **Selection**: Tie-breaking by symbol when all scores identical
- **Use Case**: Stable price periods or testing scenarios

#### All NaN in Lookback Window

- **Behavior**: Filters to data before NaN window; may use shorter effective lookback
- **Fallback**: Uses available data if `min_periods` satisfied

#### Extreme Outliers (±50% daily)

- **Behavior**: Outliers included in calculations without special handling
- **Impact**: High volatility → low score for low-vol method; may dominate momentum
- **Note**: No automated outlier detection or removal

#### Mixed Valid/Invalid Data

- **Behavior**: Computes scores on available data; NaN values propagate appropriately
- **Selection**: Only assets with valid (non-NaN) scores are selected

### Configuration Boundaries

#### lookback = min_periods

- **Behavior**: Valid configuration; uses exact minimum required data
- **Use Case**: Aggressive early-stage filtering

#### skip = lookback - 1

- **Behavior**: Valid configuration; uses only 1 period for momentum
- **Result**: Effectively single-period return momentum
- **Note**: Numerically valid but may be very noisy

#### top_k = 0

- **Behavior**: Preselection disabled; returns **all** assets (sorted alphabetically)
- **Use Case**: Bypass preselection while keeping same code path

#### top_k > universe size

- **Behavior**: Returns all valid assets (fewer than top_k)
- **Use Case**: "Select best available" without hard limit

### Z-Score Edge Cases

#### All Assets Identical (Zero Std Dev)

- **Behavior**: Returns neutral scores (zeros) for all assets
- **Selection**: Tie-breaking by symbol
- **Formula**: When std ≈ 0, all z-scores set to 0.0

#### Extreme Outlier (|z-score| > 3)

- **Behavior**: Outlier included in ranking without capping
- **Impact**: Extreme scores may dominate combined factor
- **Note**: No automated outlier trimming

#### Empty Factor Result

- **Behavior**: Handles all-NaN gracefully via neutral scoring
- **No Crash**: System doesn't fail on degenerate inputs

## Determinism Guarantees

### Same Config = Same Order

- **Guarantee**: Identical configuration + identical data → identical selected assets in identical order
- **Implementation**: Deterministic sorting by (score descending, symbol ascending)
- **Validation**: Tested with 20+ repeated runs in test suite

### Output Ordering

- **Guarantee**: Selected assets **always** returned in alphabetical order
- **Rationale**: Consistent downstream processing and user display
- **Implementation**: Final `sorted()` call on selected asset list

### No Silent Failures

- **Guarantee**: Edge cases either:
  1. Return valid results with deterministic behavior, or
  1. Raise explicit exception (e.g., `InsufficientDataError`)
- **No Silent Failures**: System doesn't return incorrect results without warning

## Known Limitations

### 1. No Outlier Detection

- **Limitation**: System includes extreme values without automated detection/trimming
- **Impact**: Single extreme outlier can dominate factor scores
- **Mitigation**: Pre-process data externally if outlier handling required

### 2. No Missing Data Imputation

- **Limitation**: NaN values propagate through calculations
- **Impact**: Assets with sparse data may have NaN scores and be excluded
- **Mitigation**: Ensure sufficient data density or pre-impute missing values

### 3. No Stability Constraints

- **Limitation**: No built-in portfolio turnover or stability constraints
- **Impact**: Small score changes can cause selection changes
- **Mitigation**: Use `MembershipPolicy` for turnover management (separate module)

### 4. Fixed Ranking Factors

- **Limitation**: Only momentum and low-volatility factors available
- **Impact**: Cannot rank by value, quality, or other factors
- **Extension**: Use custom factor computation + external ranking

### 5. No Multi-Period Optimization

- **Limitation**: Each selection period is independent
- **Impact**: No consideration of historical selection stability
- **Mitigation**: Use lookahead periods or stability overlays externally

### 6. Lookback Window Constraints

- **Limitation**: Single fixed lookback window per run
- **Impact**: Cannot use multiple timescales simultaneously
- **Workaround**: Run multiple preselections with different configs and combine

### 7. Equal Weighting Within Selection

- **Limitation**: Top-k selection treats all selected assets equally
- **Impact**: No "soft" weighting based on score magnitude
- **Mitigation**: Use scores in downstream portfolio construction

### 8. No Cross-Sectional Normalization Options

- **Limitation**: Z-score standardization only; no rank-based or percentile methods
- **Impact**: Outliers affect standardization
- **Workaround**: Pre-transform scores externally if needed

## Best Practices

### Handling Ties

1. **Accept alphabetical tie-breaking** as standard behavior
1. **Verify determinism** in critical applications with repeated runs
1. **Document assumption** when tie-breaking affects >5% of universe

### Data Quality

1. **Validate min_periods** matches your data availability
1. **Pre-filter** assets with insufficient history before preselection
1. **Monitor** NaN score rates in production

### Configuration

1. **Start conservative**: Use validated defaults (lookback=252, skip=1)
1. **Test edge values**: Verify behavior at boundaries before production
1. **Document rationale**: Record why specific config values chosen

### Production Deployment

1. **Monitor factor distributions** to detect data issues
1. **Log selection changes** between periods for audit trail
1. **Test with synthetic edge cases** matching your data characteristics
1. **Implement alerting** for unexpected empty selections

## Testing Coverage

The edge case test suite (`tests/integration/test_preselection_edge_cases.py`) validates:

- ✅ Ranking ties (5 tests)
- ✅ Empty/minimal results (5 tests)
- ✅ Combined factor edge cases (4 tests)
- ✅ Data quality issues (5 tests)
- ✅ Configuration boundaries (5 tests)
- ✅ Z-score edge cases (4 tests)
- ✅ Validation and determinism (3 tests)

**Total: 31 edge case tests** ensuring robust behavior across scenarios.

## References

- **Implementation**: `src/portfolio_management/portfolio/preselection.py`
- **Unit Tests**: `tests/portfolio/test_preselection.py` (29 tests)
- **Edge Case Tests**: `tests/integration/test_preselection_edge_cases.py` (31 tests)
- **Related**: MembershipPolicy for turnover constraints
