# Advanced Portfolio Features Guide

**Comprehensive Tutorial: Filtering, Factor Selection, and Advanced Backtesting**

This guide demonstrates the sophisticated filtering and portfolio management capabilities available in this toolkit, using a real-world S&P 500 blue chip portfolio example.

______________________________________________________________________

## Table of Contents

1. [Universe Filtering](#universe-filtering)
1. [Multi-Factor Preselection](#multi-factor-preselection)
1. [Membership Policy (Turnover Control)](#membership-policy)
1. [Point-in-Time Eligibility](#point-in-time-eligibility)
1. [Statistics Caching](#statistics-caching)
1. [Complete Workflow Example](#complete-workflow-example)

______________________________________________________________________

## Universe Filtering

### Quality Filters

**Goal:** Select only high-quality assets with sufficient history and clean data.

```yaml
filter_criteria:
  # Data quality - "ok" = clean, "warning" = minor issues, "error" = problematic
  data_status: ["ok"]

  # History requirements
  min_history_days: 7300    # 20 years of calendar days
  min_price_rows: 5040      # 20 years of trading days

  # Market/geography filters
  markets: ["NYSE", "NSQ"]  # US exchanges only
  currencies: ["USD"]       # Dollar-denominated only

  # Category filters (data source structure)
  categories:
    - "nyse stocks/1"       # Tier 1 NYSE stocks (large caps)
    - "nasdaq stocks/1"     # Tier 1 NASDAQ stocks
```

**What This Does:**

- Eliminates penny stocks and small caps (via tier filtering)
- Ensures 20 years of history (survives 2000 dot-com, 2008 crisis, 2020 COVID)
- Only clean data (no gaps, missing dates, or quality issues)
- US-only (avoids currency risk)

### Allow/Blocklists

**Manual Control:** Override automatic selection for specific tickers.

```yaml
filter_criteria:
  allowlist:
    - AAPL        # Force include Apple
    - MSFT        # Force include Microsoft
    - GOOGL       # Force include Alphabet

  blocklist:
    - GME         # Exclude GameStop (too volatile)
    - AMC         # Exclude AMC (meme stock)
```

**Use Cases:**

- **Allowlist:** Force include stocks you know are high-quality
- **Blocklist:** Exclude stocks with known issues (bankruptcy risk, regulatory problems)

### Classification Requirements

**Goal:** Filter by asset type after selection.

```yaml
classification_requirements:
  asset_class: ["equity"]             # Stocks only (no bonds, commodities)
  sub_class: ["growth", "value"]      # Growth or value stocks
  geography: ["north_america"]        # US/Canada only
```

**Asset Classes Available:**

- `equity`, `bond`, `commodity`, `real_estate`, `cash`, `alternative`

**Sub-Classes for Equity:**

- `growth`, `value`, `small_cap`, `dividend`, `tech`, `financial`, `healthcare`

______________________________________________________________________

## Multi-Factor Preselection

### Why Preselection?

**Problem:** Large universes (100+ stocks) make optimization slow and unstable.

**Solution:** Use factor-based preselection to reduce universe size before optimization.

### Factor 1: Momentum

**Strategy:** Select stocks with highest past returns (trend-following).

```python
from portfolio_management.portfolio import PreselectionConfig, PreselectionMethod

config = PreselectionConfig(
    method=PreselectionMethod.MOMENTUM,
    top_k=30,           # Select 30 stocks
    lookback=252,       # Use 1-year return (252 trading days)
    skip=21,            # Skip last month (20 trading days)
    min_periods=126,    # Need 6 months minimum data
)
```

**Formula:**

```
Momentum Score = Cumulative Return over [t-252-21 to t-21]
               = (1+r₁) × (1+r₂) × ... × (1+rₙ) - 1
```

**Why Skip Last Month?**

- Short-term reversals are common (winners become losers)
- "12-1 momentum" (12 months minus 1 month) is empirically stronger
- Avoids trading on noise

**Example Scores:**

```
Stock A: +45% return (lookback period) → High score → Selected
Stock B: +5% return → Low score → Not selected
Stock C: -10% return → Negative → Not selected
```

### Factor 2: Low-Volatility

**Strategy:** Select stocks with lowest realized volatility (defensive).

```python
config = PreselectionConfig(
    method=PreselectionMethod.LOW_VOL,
    top_k=30,
    lookback=252,       # Use 1-year volatility
    min_periods=126,
)
```

**Formula:**

```
Low-Vol Score = 1 / std(returns)
```

Higher score = lower volatility = more attractive (defensive bias).

**Example:**

```
Stock A: 15% annual vol → Score = 1/0.15 = 6.67 → High score
Stock B: 40% annual vol → Score = 1/0.40 = 2.50 → Low score
```

### Factor 3: Combined (Multi-Factor)

**Strategy:** Combine momentum and low-vol using weighted Z-scores.

```python
config = PreselectionConfig(
    method=PreselectionMethod.COMBINED,
    top_k=30,
    lookback=252,
    skip=21,
    momentum_weight=0.6,    # 60% momentum
    low_vol_weight=0.4,     # 40% low-vol
    min_periods=126,
)
```

**Process:**

1. Calculate raw momentum scores for all stocks
1. Calculate raw low-vol scores for all stocks
1. Standardize each factor to Z-scores (mean=0, std=1)
1. Combine: `Combined = 0.6 × Momentum_Z + 0.4 × LowVol_Z`
1. Select top 30 stocks by combined score

**Intuition:**

- **60% momentum:** Emphasize trend-following (winners keep winning)
- **40% low-vol:** Add defensive tilt (reduce drawdowns)
- **Result:** Stocks that are both rising AND stable

**Example:**

```
Stock A: Momentum Z-score = +1.5, Low-Vol Z-score = +0.8
         Combined = 0.6×1.5 + 0.4×0.8 = 1.22 → Likely selected

Stock B: Momentum Z-score = +2.0, Low-Vol Z-score = -1.0
         Combined = 0.6×2.0 + 0.4×(-1.0) = 0.80 → Maybe selected

Stock C: Momentum Z-score = -0.5, Low-Vol Z-score = +1.5
         Combined = 0.6×(-0.5) + 0.4×1.5 = 0.30 → Probably not
```

### Deterministic Tie-Breaking

If two stocks have identical scores, tiebreaker is **alphabetical by ticker**.

**Why?** Ensures reproducible results across runs (critical for testing).

______________________________________________________________________

## Membership Policy (Turnover Control)

### Why Membership Policy?

**Problem:** Without controls, portfolios churn too much:

- High transaction costs
- Tax inefficiency (realized capital gains)
- Unstable allocations

**Solution:** Membership policy enforces holding periods and limits turnover.

### Configuration

```python
from portfolio_management.portfolio import MembershipPolicy

policy = MembershipPolicy(
    buffer_rank=40,              # Keep existing if in top 40
    min_holding_periods=4,       # Hold at least 4 rebalances
    max_turnover=0.20,           # Max 20% turnover per rebalance
    max_new_assets=5,            # Add at most 5 new stocks
    max_removed_assets=5,        # Remove at most 5 stocks
)
```

### How It Works

**Scenario:** Quarterly rebalancing, 30-stock portfolio.

**Current holdings:** Stocks ranked 1-30 at last rebalance.

**New rankings:** Preselection ranks all 100 stocks.

**Without membership policy:**

- Rebalance to top 30 (ranks 1-30)
- Could replace all 30 stocks (100% turnover!)

**With membership policy:**

1. **Buffer rank:** Keep existing stocks if ranked ≤40 (even if outside top 30)
1. **Min holding:** Can't remove stocks held \<4 quarters
1. **Max turnover:** Limit total weight change to 20%
1. **Max new/removed:** Add/remove at most 5 stocks

**Example:**

```
Existing Portfolio (30 stocks):
  A (rank 1), B (rank 5), C (rank 35), D (rank 50), ...

New Rankings:
  A (rank 1)  → Keep (top 30)
  B (rank 5)  → Keep (top 30)
  C (rank 35) → Keep (inside buffer rank 40)
  D (rank 50) → Remove (outside buffer, held 4+ periods)
  E (rank 45) → Remove (outside buffer, held 4+ periods)

New stocks to add:
  X (rank 10) → Add
  Y (rank 15) → Add
  Z (rank 20) → Add

But wait! max_new_assets=5, so only add top 3 new stocks.
Result: Net turnover ≈ 10% (well below 20% limit)
```

### Benefits

✅ **Lower transaction costs** (fewer trades)
✅ **Tax efficiency** (defer capital gains)
✅ **Stable allocations** (less portfolio drift)
✅ **Better long-term performance** (empirically proven)

______________________________________________________________________

## Point-in-Time Eligibility

### The Lookahead Bias Problem

**Bad Practice:**

```python
# At rebalance date 2020-01-01, use data from 2020-01-31
returns = returns.loc["2019-01-01":"2020-01-31"]  # WRONG!
```

This uses future information (data from January 2020 to make a decision on January 1, 2020).

**Result:** Unrealistic backtest performance (you can't trade on data you don't have yet).

### Point-in-Time Solution

```python
backtest_config = BacktestConfig(
    use_pit_eligibility=True,
    min_history_days=252,  # Require 1 year before trading
)
```

**What It Does:**

1. At each rebalance date, check each asset's data availability
1. Only include assets with ≥252 days of prior data
1. Exclude assets that:
   - IPO'd recently (insufficient history)
   - Delisted (no longer tradeable)
   - Have data gaps (quality issues)

**Example:**

```
Rebalance Date: 2020-01-01

Stock A: First data = 2018-01-01 → 2 years history → Eligible ✓
Stock B: First data = 2019-11-01 → 2 months history → Not eligible ✗
Stock C: Delisted 2019-12-15 → Not tradeable → Not eligible ✗
```

### Combined with Preselection

```python
# Point-in-time preselection
eligible_assets = pit_filter(returns, rebalance_date)  # Only past data
factor_scores = calculate_momentum(returns[eligible_assets])  # No lookahead
selected = factor_scores.nlargest(30)  # Top 30 from eligible only
```

**Result:** Realistic backtest that could have been executed in real-time.

______________________________________________________________________

## Statistics Caching

### The Performance Problem

**Without caching:**

- Monthly rebalancing requires calculating covariance matrix each month
- Overlapping windows: Jan-Dec, Feb-Jan, Mar-Feb, ...
- Recalculating same 252×252 covariance repeatedly is slow

**With caching:**

- Calculate once, store on disk
- Reuse cached result if inputs haven't changed
- 5-10x speedup for repeated backtests

### Configuration

```python
from portfolio_management.data.factor_caching import FactorCache

cache = FactorCache(
    cache_dir=Path(".cache/my_backtest"),
    enabled=True,
    ttl_days=None,  # No expiration
)
```

### What Gets Cached

1. **Factor scores** (momentum, low-vol)
1. **Covariance matrices** (for risk parity, mean-variance)
1. **Expected returns** (for mean-variance)
1. **PIT eligibility** (asset availability lookup)

### Cache Invalidation

Cache automatically rebuilds when:

- Input data changes (prices, returns)
- Configuration changes (lookback, skip, weights)
- Rebalance date changes

**Result:** Always correct results, but much faster on repeated runs.

### Example Performance

```
First backtest:     5 minutes (cold cache)
Second backtest:    30 seconds (warm cache)
Third backtest:     30 seconds (cached)

Speedup: 10x!
```

______________________________________________________________________

## Complete Workflow Example

### Scenario: S&P 500 Blue Chip Portfolio (2005-2025)

**Goal:** Build a 30-stock portfolio from S&P 500 blue chips using momentum + low-vol factors.

### Step 1: Define Universe

```yaml
# config/sp500_blue_chips.yaml
universes:
  sp500_blue_chips:
    description: "S&P 500 blue chips with 20+ year history"
    filter_criteria:
      data_status: ["ok"]
      min_history_days: 7300  # 20 years
      min_price_rows: 5040    # 20 years trading days
      markets: ["NYSE", "NSQ"]
      currencies: ["USD"]
      categories:
        - "nyse stocks/1"     # Tier 1 large caps
        - "nasdaq stocks/1"
    constraints:
      min_assets: 80
      max_assets: 120
```

### Step 2: Load Universe

```bash
python scripts/manage_universes.py load sp500_blue_chips \
    --output-dir outputs/sp500
```

**Output:** `outputs/sp500/sp500_blue_chips_returns.csv` (100 stocks × 5000+ days)

### Step 3: Configure Preselection

```python
preselection = Preselection(
    PreselectionConfig(
        method=PreselectionMethod.COMBINED,
        top_k=30,           # 100 → 30 stocks
        lookback=252,       # 1-year factors
        skip=21,            # Skip last month
        momentum_weight=0.6,
        low_vol_weight=0.4,
    ),
    cache=cache,
)
```

### Step 4: Configure Membership Policy

```python
membership = MembershipPolicy(
    buffer_rank=40,
    min_holding_periods=4,   # 1 year hold (quarterly rebalance)
    max_turnover=0.20,
)
```

### Step 5: Run Backtest

```python
engine = BacktestEngine(
    config=BacktestConfig(
        start_date=date(2005, 1, 1),
        end_date=date(2025, 1, 1),
        rebalance_frequency=RebalanceFrequency.QUARTERLY,
        use_pit_eligibility=True,
    ),
    strategy=RiskParityStrategy(),
    preselection=preselection,
    membership_policy=membership,
)

result = engine.run(prices, returns)
```

### Step 6: Review Results

```python
print(f"Annualized Return: {result.metrics.annualized_return:.2%}")
print(f"Sharpe Ratio: {result.metrics.sharpe_ratio:.3f}")
print(f"Max Drawdown: {result.metrics.max_drawdown:.2%}")
print(f"Total Trades: {len(result.trade_log)}")
```

**Expected Performance (20-year backtest):**

- Return: 10-15% annualized
- Sharpe: 0.8-1.2
- Max Drawdown: 30-40% (2008 crisis)
- Trades: 300-500 (quarterly rebalancing)

______________________________________________________________________

## Advanced Filtering Recipes

### 1. Conservative Dividend Portfolio

```yaml
filter_criteria:
  data_status: ["ok"]
  min_history_days: 3650  # 10 years
  markets: ["NYSE"]       # Blue chip exchange only

classification_requirements:
  sub_class: ["dividend"]

preselection:
  method: "low_vol"       # Defensive
  top_k: 20
```

### 2. Aggressive Growth Tech

```yaml
filter_criteria:
  data_status: ["ok", "warning"]  # Allow some risk
  min_history_days: 1260          # 5 years
  markets: ["NSQ"]                # NASDAQ = tech-heavy

classification_requirements:
  sub_class: ["growth", "tech"]

preselection:
  method: "momentum"              # Trend-following
  top_k: 30
  lookback: 126                   # 6-month momentum (aggressive)
  skip: 5                         # Skip 1 week only
```

### 3. International Diversification

```yaml
filter_criteria:
  markets: ["LSE", "NYSE", "NSQ"]  # US + UK
  currencies: ["GBP", "USD", "EUR"]

classification_requirements:
  geography: ["europe", "north_america", "asia"]

preselection:
  method: "combined"
  momentum_weight: 0.4            # Less momentum
  low_vol_weight: 0.6             # More defensive
```

______________________________________________________________________

## Running the Example

```bash
# Run the advanced S&P 500 example
python examples/sp500_blue_chips_advanced.py
```

**This demonstrates:**

- ✅ Custom universe with quality filters
- ✅ Multi-factor preselection (60% momentum + 40% low-vol)
- ✅ Membership policy (4-quarter hold, 20% max turnover)
- ✅ Point-in-time eligibility (no lookahead)
- ✅ Factor caching (5-10x speedup)
- ✅ Transaction cost modeling
- ✅ Strategy comparison

______________________________________________________________________

## Next Steps

1. **Experiment with factors:** Try different momentum/low-vol weights
1. **Adjust membership:** Test tighter/looser turnover limits
1. **Test strategies:** Compare equal-weight, risk-parity, mean-variance
1. **Add constraints:** Max sector exposure, max single-stock weight
1. **Long backtests:** Test 20+ years including 2000, 2008, 2020 crises

See `examples/sp500_blue_chips_advanced.py` for complete working code!
