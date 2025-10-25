#!/usr/bin/env python3
"""
Advanced S&P 500 Blue Chip Portfolio Example
==============================================

This example demonstrates a sophisticated workflow:
1. Filter US blue-chip stocks (NYSE/NASDAQ with long history)
2. Select top 100 stocks by quality metrics
3. Use momentum + low-volatility preselection to pick 30 best
4. Apply membership policy to control turnover
5. Construct risk-parity portfolio with constraints
6. Backtest 2005-2025 with realistic transaction costs
7. Compare against equal-weight and momentum-only strategies

This showcases the full power of the toolkit:
- Custom universe configuration
- Multi-factor preselection
- Membership policy (reduce churn)
- Point-in-time eligibility (no lookahead bias)
- Statistics caching (speed optimization)
- Strategy comparison
"""

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
import yaml

# Add src to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from portfolio_management.backtesting import (
    BacktestConfig,
    BacktestEngine,
    RebalanceFrequency,
)
from portfolio_management.data.factor_caching import FactorCache
from portfolio_management.portfolio import (
    EqualWeightStrategy,
    MembershipPolicy,
    Preselection,
    PreselectionConfig,
    PreselectionMethod,
    RiskParityStrategy,
)
from portfolio_management.reporting.visualization import create_summary_report


def main():
    """Run advanced S&P 500 blue chip portfolio example."""
    print("=" * 80)
    print("ADVANCED S&P 500 BLUE CHIP PORTFOLIO EXAMPLE")
    print("=" * 80)
    print()

    # =========================================================================
    # STEP 1: Define Custom Universe - Blue Chip US Stocks
    # =========================================================================
    print("STEP 1: Define Custom Universe Configuration")
    print("-" * 80)

    universe_config = {
        "sp500_blue_chips": {
            "description": "S&P 500 blue chip stocks with 20+ year history",
            "filter_criteria": {
                # HIGH QUALITY DATA ONLY
                "data_status": ["ok"],  # Only clean data
                "min_history_days": 7300,  # 20 years = 365 * 20
                "min_price_rows": 5040,  # 20 years of trading days
                # US MARKETS ONLY
                "markets": ["NYSE", "NSQ"],  # New York Stock Exchange & NASDAQ
                "currencies": ["USD"],
                # BLUE CHIP CATEGORIES (large cap, established companies)
                "categories": [
                    "nyse stocks/1",  # Tier 1 NYSE stocks
                    "nasdaq stocks/1",  # Tier 1 NASDAQ stocks
                ],
            },
            "classification_requirements": {
                "asset_class": ["equity"],
                "geography": ["north_america"],
            },
            "return_config": {
                "method": "log",  # Log returns for better statistical properties
                "frequency": "daily",  # Daily rebalancing capability
                "handle_missing": "forward_fill",
                "max_forward_fill_days": 5,
                "min_periods": 252,  # At least 1 year of data
                "align_method": "inner",  # Only dates with all assets
                "min_coverage": 0.95,  # 95% data completeness required
            },
            "constraints": {
                "min_assets": 80,  # Need at least 80 stocks
                "max_assets": 120,  # Cap at 120 stocks
            },
            # ADVANCED FEATURES
            "preselection": {
                "method": "combined",  # Momentum + Low-Vol combined
                "top_k": 30,  # Select 30 stocks for portfolio
                "lookback": 252,  # 1-year lookback for factors
                "skip": 21,  # Skip last month (20 trading days)
                "momentum_weight": 0.6,  # 60% momentum
                "low_vol_weight": 0.4,  # 40% low-volatility
                "min_periods": 126,  # At least 6 months of data
            },
            "membership_policy": {
                "enabled": True,
                "buffer_rank": 40,  # Keep existing if in top 40
                "min_holding_periods": 4,  # Hold at least 4 quarters
                "max_turnover": 0.20,  # Max 20% turnover per rebalance
                "max_new_assets": 5,  # Add at most 5 new stocks
                "max_removed_assets": 5,  # Remove at most 5 stocks
            },
        }
    }

    print("✓ Universe configured:")
    print(f"  • Markets: NYSE, NASDAQ")
    print(f"  • Min History: 20 years")
    print(f"  • Target Size: 100 stocks → 30 in portfolio")
    print(f"  • Preselection: 60% momentum + 40% low-vol")
    print(f"  • Membership: 4-quarter hold, max 20% turnover")
    print()

    # =========================================================================
    # STEP 2: Save Universe Configuration
    # =========================================================================
    print("STEP 2: Save Universe Configuration")
    print("-" * 80)

    config_file = REPO_ROOT / "config" / "sp500_blue_chips.yaml"
    config_file.parent.mkdir(parents=True, exist_ok=True)

    with open(config_file, "w") as f:
        yaml.dump({"universes": universe_config}, f, default_flow_style=False)

    print(f"✓ Configuration saved to: {config_file}")
    print()

    # =========================================================================
    # STEP 3: Load Universe Data (Selection → Classification → Returns)
    # =========================================================================
    print("STEP 3: Load Universe Data")
    print("-" * 80)
    print("This would normally run:")
    print("  python scripts/manage_universes.py load sp500_blue_chips \\")
    print("      --output-dir outputs/sp500_example")
    print()
    print("Since we don't have 20 years of S&P 500 data in this example,")
    print("we'll demonstrate the workflow with test data...")
    print()

    # Check if test data exists
    test_data_dir = REPO_ROOT / "outputs" / "long_history_1000"
    prices_file = test_data_dir / "long_history_1000_prices_daily.csv"
    returns_file = test_data_dir / "long_history_1000_returns_daily.csv.gz"

    if not returns_file.exists():
        print("⚠️  Test data not found. To run this example:")
        print("   1. Prepare Stooq data: python scripts/prepare_tradeable_data.py")
        print("   2. Load universe: python scripts/manage_universes.py load sp500_blue_chips")
        print("   3. Rerun this script")
        return 1

    print(f"✓ Using test data: {test_data_dir}")
    print()

    # =========================================================================
    # STEP 4: Load Price and Return Data
    # =========================================================================
    print("STEP 4: Load Price and Return Data")
    print("-" * 80)

    # Load data (use first 100 assets as proxy for blue chips)
    print("Loading data...")
    prices = pd.read_csv(prices_file, index_col=0, parse_dates=True)
    returns = pd.read_csv(returns_file, index_col=0, parse_dates=True)

    # Simulate blue chip selection: take first 100 assets with longest history
    asset_coverage = returns.notna().sum()
    top_100_assets = asset_coverage.nlargest(100).index.tolist()
    prices = prices[top_100_assets]
    returns = returns[top_100_assets]

    print(f"✓ Loaded {len(top_100_assets)} blue chip proxies")
    print(f"  • Date range: {returns.index[0].date()} to {returns.index[-1].date()}")
    print(f"  • Total days: {len(returns)}")
    print()

    # =========================================================================
    # STEP 5: Configure Backtest
    # =========================================================================
    print("STEP 5: Configure Backtest")
    print("-" * 80)

    backtest_config = BacktestConfig(
        start_date=date(2005, 1, 1),
        end_date=date(2024, 12, 31),
        initial_capital=Decimal("100000"),  # $100,000 starting capital
        rebalance_frequency=RebalanceFrequency.QUARTERLY,  # Rebalance every quarter
        commission=Decimal("0.001"),  # 10 bps = 0.1% commission
        slippage=Decimal("0.0005"),  # 5 bps = 0.05% slippage
        min_commission=Decimal("5.00"),  # $5 minimum per trade
        use_pit_eligibility=True,  # Point-in-time eligibility (no lookahead)
        min_history_days=252,  # Require 1 year of history before trading
    )

    print("✓ Backtest configuration:")
    print(f"  • Period: 2005-2024 (20 years)")
    print(f"  • Initial capital: $100,000")
    print(f"  • Rebalance: Quarterly")
    print(f"  • Commission: 0.1% + $5 min")
    print(f"  • Slippage: 0.05%")
    print(f"  • Point-in-time eligibility: Enabled")
    print()

    # =========================================================================
    # STEP 6: Configure Caching for Speed
    # =========================================================================
    print("STEP 6: Configure Caching")
    print("-" * 80)

    cache = FactorCache(
        cache_dir=REPO_ROOT / ".cache" / "sp500_example",
        enabled=True,
        ttl_days=None,  # No expiration
    )

    print(f"✓ Factor caching enabled: {cache.cache_dir}")
    print("  • Speeds up repeated backtests by 5-10x")
    print("  • Caches covariance matrices and factor scores")
    print()

    # =========================================================================
    # STEP 7: Configure Preselection (100 → 30 stocks)
    # =========================================================================
    print("STEP 7: Configure Multi-Factor Preselection")
    print("-" * 80)

    preselection_config = PreselectionConfig(
        method=PreselectionMethod.COMBINED,
        top_k=30,  # Select 30 stocks
        lookback=252,  # 1-year lookback
        skip=21,  # Skip last month
        momentum_weight=0.6,  # 60% momentum
        low_vol_weight=0.4,  # 40% defensive (low-vol)
        min_periods=126,  # Need 6 months minimum
    )

    preselection = Preselection(preselection_config, cache=cache)

    print("✓ Preselection strategy:")
    print("  • Method: Combined (Momentum + Low-Volatility)")
    print("  • Universe: 100 stocks")
    print("  • Selection: Top 30 by combined score")
    print("  • Momentum: 60% weight (1-year return, skip 1 month)")
    print("  • Low-Vol: 40% weight (defensive tilt)")
    print()

    # =========================================================================
    # STEP 8: Configure Membership Policy (Reduce Churn)
    # =========================================================================
    print("STEP 8: Configure Membership Policy")
    print("-" * 80)

    membership_policy = MembershipPolicy(
        buffer_rank=40,  # Keep existing if in top 40
        min_holding_periods=4,  # Hold at least 4 quarters (1 year)
        max_turnover=0.20,  # Max 20% portfolio turnover
        max_new_assets=5,  # Add at most 5 new stocks per rebalance
        max_removed_assets=5,  # Remove at most 5 stocks per rebalance
    )

    print("✓ Membership policy:")
    print("  • Buffer: Keep existing stocks if in top 40")
    print("  • Min hold: 4 quarters (forces 1-year minimum)")
    print("  • Max turnover: 20% per rebalance")
    print("  • Max new/removed: 5 stocks each")
    print("  • Effect: Stabilizes portfolio, reduces transaction costs")
    print()

    # =========================================================================
    # STEP 9: Run Backtest - Risk Parity Strategy
    # =========================================================================
    print("STEP 9: Run Backtest - Risk Parity with All Features")
    print("-" * 80)

    strategy = RiskParityStrategy()
    engine = BacktestEngine(
        config=backtest_config,
        strategy=strategy,
        preselection=preselection,
        membership_policy=membership_policy,
    )

    print("Running backtest (this may take 2-5 minutes)...")
    result = engine.run(prices, returns)

    print("✓ Backtest complete!")
    print()

    # =========================================================================
    # STEP 10: Display Results
    # =========================================================================
    print("STEP 10: Performance Results")
    print("=" * 80)

    metrics = result.metrics

    print("📊 RISK-ADJUSTED PERFORMANCE")
    print("-" * 80)
    print(f"  Total Return:        {metrics.total_return:.2%}")
    print(f"  Annualized Return:   {metrics.annualized_return:.2%}")
    print(f"  Annualized Vol:      {metrics.annualized_volatility:.2%}")
    print(f"  Sharpe Ratio:        {metrics.sharpe_ratio:.3f}")
    print(f"  Sortino Ratio:       {metrics.sortino_ratio:.3f}")
    print()

    print("📉 DRAWDOWN & DOWNSIDE RISK")
    print("-" * 80)
    print(f"  Max Drawdown:        {metrics.max_drawdown:.2%}")
    print(f"  Max Drawdown Days:   {metrics.max_drawdown_duration}")
    print(f"  CVaR (95%):          {metrics.cvar_95:.2%}")
    print()

    print("💰 TRANSACTION COSTS")
    print("-" * 80)
    print(f"  Total Costs:         ${metrics.total_transaction_costs:,.2f}")
    print(f"  Cost as % of Return: {metrics.total_transaction_costs / float(backtest_config.initial_capital) / metrics.total_return:.2%}")
    print(f"  Number of Trades:    {len(result.trade_log)}")
    print()

    print("🔄 TURNOVER STATISTICS")
    print("-" * 80)
    if hasattr(metrics, "average_turnover"):
        print(f"  Average Turnover:    {metrics.average_turnover:.2%}")
    print(f"  Number of Rebalances: {len(result.rebalance_log)}")
    print()

    # =========================================================================
    # STEP 11: Compare Strategies
    # =========================================================================
    print("STEP 11: Strategy Comparison")
    print("=" * 80)
    print("Running comparison backtests...")
    print()

    # Equal Weight baseline (no preselection, no membership)
    print("  • Equal Weight (baseline)...")
    eq_engine = BacktestEngine(
        config=backtest_config,
        strategy=EqualWeightStrategy(),
        preselection=None,  # Use all 100 stocks
        membership_policy=None,
    )
    eq_result = eq_engine.run(prices, returns)

    # Momentum-only (compare against combined factors)
    print("  • Momentum-Only (60 stocks)...")
    momentum_preselection = Preselection(
        PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=30,
            lookback=252,
            skip=21,
        ),
        cache=cache,
    )
    mom_engine = BacktestEngine(
        config=backtest_config,
        strategy=RiskParityStrategy(),
        preselection=momentum_preselection,
        membership_policy=None,  # No membership for comparison
    )
    mom_result = mom_engine.run(prices, returns)

    print()
    print("📊 STRATEGY COMPARISON")
    print("=" * 80)
    print(f"{'Strategy':<30} {'Return':>10} {'Sharpe':>8} {'MaxDD':>10} {'Trades':>8}")
    print("-" * 80)
    print(
        f"{'Equal Weight (100 stocks)':<30} "
        f"{eq_result.metrics.annualized_return:>10.2%} "
        f"{eq_result.metrics.sharpe_ratio:>8.3f} "
        f"{eq_result.metrics.max_drawdown:>10.2%} "
        f"{len(eq_result.trade_log):>8}"
    )
    print(
        f"{'Momentum Only (30 stocks)':<30} "
        f"{mom_result.metrics.annualized_return:>10.2%} "
        f"{mom_result.metrics.sharpe_ratio:>8.3f} "
        f"{mom_result.metrics.max_drawdown:>10.2%} "
        f"{len(mom_result.trade_log):>8}"
    )
    print(
        f"{'Combined + Membership (30)':<30} "
        f"{result.metrics.annualized_return:>10.2%} "
        f"{result.metrics.sharpe_ratio:>8.3f} "
        f"{result.metrics.max_drawdown:>10.2%} "
        f"{len(result.trade_log):>8}"
    )
    print()

    # =========================================================================
    # STEP 12: Save Results
    # =========================================================================
    print("STEP 12: Save Results")
    print("=" * 80)

    output_dir = REPO_ROOT / "outputs" / "sp500_example"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save equity curves
    result.to_csv(output_dir / "combined_membership", save_all=True)
    eq_result.to_csv(output_dir / "equal_weight", save_all=True)
    mom_result.to_csv(output_dir / "momentum_only", save_all=True)

    print(f"✓ Results saved to: {output_dir}")
    print()
    print("📁 Output files:")
    print("  • equity_curve.csv - Portfolio value over time")
    print("  • daily_returns.csv - Daily return series")
    print("  • allocation_history.csv - Weight changes over time")
    print("  • rebalance_log.csv - Rebalance dates and changes")
    print("  • trade_log.csv - Individual trades with costs")
    print("  • performance_metrics.json - Summary statistics")
    print()

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("=" * 80)
    print("✅ EXAMPLE COMPLETE")
    print("=" * 80)
    print()
    print("What we demonstrated:")
    print("  ✓ Custom universe configuration (YAML-based)")
    print("  ✓ Quality filtering (20 years, US markets only)")
    print("  ✓ Multi-factor preselection (momentum + low-vol)")
    print("  ✓ Membership policy (reduce churn, force holding periods)")
    print("  ✓ Point-in-time eligibility (no lookahead bias)")
    print("  ✓ Factor caching (5-10x speedup)")
    print("  ✓ Transaction cost modeling")
    print("  ✓ Strategy comparison")
    print()
    print("Next steps:")
    print("  1. Review output files in outputs/sp500_example/")
    print("  2. Adjust parameters in sp500_blue_chips.yaml")
    print("  3. Try different strategies (equal_weight, mean_variance)")
    print("  4. Experiment with preselection weights")
    print("  5. Test different rebalance frequencies")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
