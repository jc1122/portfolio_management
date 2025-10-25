#!/usr/bin/env python3
"""
Quick Portfolio Visualization Example
======================================

This example generates synthetic stock data and demonstrates:
1. Multi-factor preselection (100 → 30 stocks)
2. Membership policy
3. Portfolio construction
4. Backtest with visualizations

No real data required - generates synthetic returns.
"""

import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

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

# Set plot style
sns.set_style("whitegrid")
plt.rcParams["figure.figsize"] = (12, 6)


def generate_synthetic_data(
    n_assets=100,
    start_date="2003-01-01",  # Start earlier for buffer
    end_date="2024-12-31",    # Extend to 2024 for full backtest
    seed=42,
):
    """
    Generate synthetic price and return data for testing.

    Creates realistic-looking stock data with:
    - Market factor exposure (beta)
    - Momentum characteristics
    - Volatility clustering
    - Cross-sectional dispersion
    """
    np.random.seed(seed)

    # Generate date range (business days)
    dates = pd.date_range(start=start_date, end=end_date, freq="B")
    n_days = len(dates)

    # Generate asset identifiers
    assets = [f"STOCK_{i:03d}" for i in range(n_assets)]

    # Generate market returns (simulate S&P 500)
    market_returns = np.random.normal(0.0003, 0.01, n_days)  # ~8% annual return, 16% vol

    # Generate individual stock characteristics
    returns_data = []
    for i in range(n_assets):
        # Random characteristics
        beta = np.random.uniform(0.7, 1.3)
        momentum = np.random.uniform(-0.0002, 0.0005)  # Drift
        idio_vol = np.random.uniform(0.015, 0.03)  # Idiosyncratic volatility

        # Generate returns: beta * market + idiosyncratic
        idio_returns = np.random.normal(momentum, idio_vol, n_days)
        stock_returns = beta * market_returns + idio_returns

        returns_data.append(stock_returns)

    returns = pd.DataFrame(
        np.array(returns_data).T,
        index=dates,
        columns=assets,
    )

    # Generate prices from returns
    prices = (1 + returns).cumprod() * 100

    print(f"✓ Generated {n_assets} stocks, {n_days} days ({dates[0].date()} to {dates[-1].date()})")

    return prices, returns


def plot_equity_curves(results_dict, output_dir):
    """Plot equity curves for multiple strategies."""
    print("\n📊 Creating equity curve plot...")

    fig, ax = plt.subplots(figsize=(14, 7))

    colors = ["#2E86AB", "#A23B72", "#F18F01"]

    for (name, result), color in zip(results_dict.items(), colors):
        equity = result.equity_curve
        equity_normalized = equity / equity.iloc[0] * 100000
        ax.plot(
            equity_normalized.index,
            equity_normalized.values,
            label=name,
            linewidth=2,
            color=color,
        )

    ax.set_xlabel("Date", fontsize=12, fontweight="bold")
    ax.set_ylabel("Portfolio Value ($)", fontsize=12, fontweight="bold")
    ax.set_title(
        "Portfolio Equity Curves (2005-2024)\nInitial Capital: $100,000",
        fontsize=14,
        fontweight="bold",
        pad=20,
    )
    ax.legend(loc="upper left", fontsize=11, frameon=True)
    ax.grid(True, alpha=0.3)

    # Format y-axis as currency
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, p: f"${x:,.0f}")
    )

    # Add performance stats
    stats_text = []
    for name, result in results_dict.items():
        final_value = result.equity_curve.iloc[-1]
        total_return = (final_value / 100000 - 1) * 100
        stats_text.append(f"{name}: ${final_value:,.0f} (+{total_return:.1f}%)")

    ax.text(
        0.02, 0.98,
        "\n".join(stats_text),
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
    )

    plt.tight_layout()
    output_file = output_dir / "equity_curves.png"
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    print(f"✓ Saved: {output_file}")
    plt.close()


def plot_drawdowns(results_dict, output_dir):
    """Plot drawdown series for multiple strategies."""
    print("\n📊 Creating drawdown plot...")

    fig, ax = plt.subplots(figsize=(14, 7))

    colors = ["#2E86AB", "#A23B72", "#F18F01"]

    for (name, result), color in zip(results_dict.items(), colors):
        equity = result.equity_curve
        cummax = equity.cummax()
        drawdown = (equity - cummax) / cummax

        ax.fill_between(
            drawdown.index,
            drawdown.values * 100,
            0,
            alpha=0.3,
            color=color,
            label=name,
        )
        ax.plot(
            drawdown.index,
            drawdown.values * 100,
            linewidth=1.5,
            color=color,
        )

    ax.set_xlabel("Date", fontsize=12, fontweight="bold")
    ax.set_ylabel("Drawdown (%)", fontsize=12, fontweight="bold")
    ax.set_title(
        "Portfolio Drawdowns (2005-2024)",
        fontsize=14,
        fontweight="bold",
        pad=20,
    )
    ax.legend(loc="lower right", fontsize=11, frameon=True)
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color="black", linestyle="-", linewidth=0.8)

    # Add max drawdown annotations
    for name, result in results_dict.items():
        max_dd = result.metrics.max_drawdown * 100
        ax.text(
            0.02, 0.02 + list(results_dict.keys()).index(name) * 0.05,
            f"{name} Max DD: {max_dd:.1f}%",
            transform=ax.transAxes,
            fontsize=10,
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
        )

    plt.tight_layout()
    output_file = output_dir / "drawdowns.png"
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    print(f"✓ Saved: {output_file}")
    plt.close()


def plot_returns_distribution(results_dict, output_dir):
    """Plot return distributions."""
    print("\n📊 Creating returns distribution plot...")

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    colors = ["#2E86AB", "#A23B72", "#F18F01"]

    for (name, result), ax, color in zip(results_dict.items(), axes, colors):
        returns = result.daily_returns.dropna()

        # Histogram
        ax.hist(
            returns * 100,
            bins=50,
            alpha=0.7,
            color=color,
            edgecolor="black",
            linewidth=0.5,
        )

        # Add normal distribution overlay
        mu, sigma = returns.mean() * 100, returns.std() * 100
        x = np.linspace(returns.min() * 100, returns.max() * 100, 100)
        from scipy import stats
        ax.plot(
            x,
            stats.norm.pdf(x, mu, sigma) * len(returns) * (returns.max() - returns.min()) * 100 / 50,
            'r-',
            linewidth=2,
            label='Normal',
        )

        ax.set_xlabel("Daily Return (%)", fontsize=11, fontweight="bold")
        ax.set_ylabel("Frequency", fontsize=11, fontweight="bold")
        ax.set_title(name, fontsize=12, fontweight="bold")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=9)

        # Add stats
        stats_text = f"Mean: {mu:.3f}%\nStd: {sigma:.2f}%\nSkew: {returns.skew():.2f}"
        ax.text(
            0.98, 0.98,
            stats_text,
            transform=ax.transAxes,
            fontsize=9,
            verticalalignment="top",
            horizontalalignment="right",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
        )

    plt.suptitle(
        "Daily Returns Distribution",
        fontsize=14,
        fontweight="bold",
        y=1.02,
    )
    plt.tight_layout()
    output_file = output_dir / "returns_distribution.png"
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    print(f"✓ Saved: {output_file}")
    plt.close()


def plot_performance_metrics(results_dict, output_dir):
    """Plot performance metrics comparison."""
    print("\n📊 Creating performance metrics comparison...")

    # Extract metrics
    metrics_data = {
        "Strategy": [],
        "Annual Return": [],
        "Volatility": [],
        "Sharpe Ratio": [],
        "Max Drawdown": [],
        "Sortino Ratio": [],
    }

    for name, result in results_dict.items():
        m = result.metrics
        metrics_data["Strategy"].append(name)
        metrics_data["Annual Return"].append(m.annualized_return * 100)
        metrics_data["Volatility"].append(m.annualized_volatility * 100)
        metrics_data["Sharpe Ratio"].append(m.sharpe_ratio)
        metrics_data["Max Drawdown"].append(abs(m.max_drawdown) * 100)
        metrics_data["Sortino Ratio"].append(m.sortino_ratio)

    df = pd.DataFrame(metrics_data)

    # Create subplots
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    axes = axes.flatten()

    colors = ["#2E86AB", "#A23B72", "#F18F01"]

    metrics_to_plot = [
        ("Annual Return", "%", True),
        ("Volatility", "%", False),
        ("Sharpe Ratio", "", True),
        ("Max Drawdown", "%", False),
        ("Sortino Ratio", "", True),
    ]

    for i, (metric, unit, higher_better) in enumerate(metrics_to_plot):
        ax = axes[i]
        bars = ax.bar(df["Strategy"], df[metric], color=colors, alpha=0.7, edgecolor="black")
        ax.set_ylabel(f"{metric} ({unit})" if unit else metric, fontsize=11, fontweight="bold")
        ax.set_title(metric, fontsize=12, fontweight="bold")
        ax.grid(True, alpha=0.3, axis="y")

        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.,
                height,
                f"{height:.2f}",
                ha="center",
                va="bottom",
                fontsize=10,
                fontweight="bold",
            )

        # Rotate x labels
        ax.set_xticklabels(df["Strategy"], rotation=15, ha="right")

        # Highlight best performer
        if higher_better:
            best_idx = df[metric].idxmax()
        else:
            best_idx = df[metric].idxmin()
        bars[best_idx].set_alpha(1.0)
        bars[best_idx].set_edgecolor("darkgreen")
        bars[best_idx].set_linewidth(3)

    # Remove extra subplot
    fig.delaxes(axes[5])

    plt.suptitle(
        "Performance Metrics Comparison",
        fontsize=14,
        fontweight="bold",
        y=0.995,
    )
    plt.tight_layout()
    output_file = output_dir / "performance_metrics.png"
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    print(f"✓ Saved: {output_file}")
    plt.close()


def plot_allocation_heatmap(result, output_dir, name):
    """Plot allocation weights over time as heatmap."""
    print(f"\n📊 Creating allocation heatmap for {name}...")

    # Get allocation history
    alloc = result.allocation_history

    # Skip if empty or no allocations
    if alloc.empty:
        print(f"⚠️  No allocation history available for {name}, skipping heatmap")
        return

    # Ensure date index
    if not isinstance(alloc.index, pd.DatetimeIndex):
        print(f"⚠️  Invalid date index for {name}, skipping heatmap")
        return

    # Resample to monthly for better visualization
    alloc_monthly = alloc.resample("ME").last().fillna(0)

    # Select top 15 assets by average weight
    top_assets = alloc_monthly.mean().nlargest(15).index
    alloc_top = alloc_monthly[top_assets]

    # Create heatmap
    fig, ax = plt.subplots(figsize=(14, 8))

    sns.heatmap(
        alloc_top.T * 100,
        cmap="YlOrRd",
        cbar_kws={"label": "Weight (%)"},
        linewidths=0.5,
        linecolor="gray",
        ax=ax,
    )

    ax.set_xlabel("Date", fontsize=12, fontweight="bold")
    ax.set_ylabel("Asset", fontsize=12, fontweight="bold")
    ax.set_title(
        f"Portfolio Allocation Over Time - {name}\n(Top 15 Assets by Average Weight)",
        fontsize=14,
        fontweight="bold",
        pad=20,
    )

    # Format x-axis dates
    n_dates = len(alloc_top)
    step = max(n_dates // 10, 1)
    ax.set_xticks(range(0, n_dates, step))
    ax.set_xticklabels(
        [alloc_top.index[i].strftime("%Y-%m") for i in range(0, n_dates, step)],
        rotation=45,
        ha="right",
    )

    plt.tight_layout()
    output_file = output_dir / f"allocation_heatmap_{name.lower().replace(' ', '_')}.png"
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    print(f"✓ Saved: {output_file}")
    plt.close()


def create_result_wrapper(equity_df, metrics, rebalance_events, alloc_history):
    """Wrap backtest outputs into a convenient object."""
    class Result:
        def __init__(self, equity_df, metrics, rebalance_events, alloc_history):
            self.equity_curve = equity_df["equity"]
            self.daily_returns = self.equity_curve.pct_change()
            self.metrics = metrics
            self.rebalance_log = rebalance_events
            self.trade_log = []  # Simplified
            self.allocation_history = alloc_history

    return Result(equity_df, metrics, rebalance_events, alloc_history)


def extract_allocation_history(engine):
    """Extract allocation history from backtest engine.

    Reconstructs portfolio weights at each rebalance date by:
    1. Starting with empty holdings
    2. Applying each trade sequentially
    3. Computing weights from holdings * prices
    """
    if not engine.rebalance_events:
        return pd.DataFrame()

    alloc_data = []
    holdings = {}  # Track holdings evolution

    for event in engine.rebalance_events:
        date = event.date

        # Apply trades to holdings
        for ticker, share_change in event.trades.items():
            holdings[ticker] = holdings.get(ticker, 0) + share_change
            if holdings[ticker] == 0:
                holdings.pop(ticker, None)  # Remove if zero

        # Get prices at this date
        if date not in engine.prices.index:
            continue
        prices_at_date = engine.prices.loc[date]

        # Compute position values
        row_data = {"date": date}
        total_value = float(event.post_rebalance_value)

        for ticker, shares in holdings.items():
            if shares > 0 and ticker in prices_at_date:
                position_value = shares * float(prices_at_date[ticker])
                weight = position_value / total_value if total_value > 0 else 0.0
                row_data[ticker] = weight

        alloc_data.append(row_data)

    if alloc_data:
        alloc_df = pd.DataFrame(alloc_data).set_index("date")
        return alloc_df.fillna(0)
    return pd.DataFrame()


def main():
    """Run portfolio visualization example."""
    print("=" * 80)
    print("PORTFOLIO VISUALIZATION EXAMPLE")
    print("=" * 80)
    print()

    # Create output directory
    output_dir = REPO_ROOT / "outputs" / "visualization_example"
    output_dir.mkdir(parents=True, exist_ok=True)

    # =========================================================================
    # STEP 1: Generate Synthetic Data
    # =========================================================================
    prices, returns = generate_synthetic_data(
        n_assets=100,
        start_date="2003-01-01",  # Start earlier for warmup
        end_date="2024-12-31",    # Full period through 2024
    )

    # =========================================================================
    # STEP 2: Configure Backtest
    # =========================================================================
    print("\n⚙️  Configuring backtest...")

    backtest_config = BacktestConfig(
        start_date=date(2005, 1, 1),
        end_date=date(2018, 10, 1),  # Match available data
        initial_capital=Decimal("100000"),
        rebalance_frequency=RebalanceFrequency.QUARTERLY,
        commission_pct=0.001,  # 0.1% commission
        commission_min=5.0,  # $5 minimum
        slippage_bps=5.0,  # 5 bps = 0.05%
        use_pit_eligibility=True,
        min_history_days=252,
    )

    cache = FactorCache(
        cache_dir=REPO_ROOT / ".cache" / "viz_example",
        enabled=True,
    )

    # =========================================================================
    # STEP 3: Run Three Strategies
    # =========================================================================
    print("\n🚀 Running backtests...")

    results = {}

    # Strategy 1: Equal Weight (baseline)
    print("\n  1/3 Equal Weight (100 stocks, no filtering)...")
    eq_engine = BacktestEngine(
        config=backtest_config,
        strategy=EqualWeightStrategy(),
        prices=prices,
        returns=returns,
        preselection=None,
        membership_policy=None,
    )
    eq_equity, eq_metrics, eq_events = eq_engine.run()
    eq_alloc = extract_allocation_history(eq_engine)
    results["Equal Weight"] = create_result_wrapper(eq_equity, eq_metrics, eq_events, eq_alloc)

    # Strategy 2: Momentum Only (30 stocks)
    print("  2/3 Momentum Only (30 stocks, no membership)...")
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
        prices=prices,
        returns=returns,
        preselection=momentum_preselection,
        membership_policy=None,
    )
    mom_equity, mom_metrics, mom_events = mom_engine.run()
    mom_alloc = extract_allocation_history(mom_engine)
    results["Momentum Only"] = create_result_wrapper(mom_equity, mom_metrics, mom_events, mom_alloc)

    # Strategy 3: Combined + Membership (30 stocks)
    print("  3/3 Combined Factors + Membership (30 stocks)...")
    combined_preselection = Preselection(
        PreselectionConfig(
            method=PreselectionMethod.COMBINED,
            top_k=30,
            lookback=252,
            skip=21,
            momentum_weight=0.6,
            low_vol_weight=0.4,
        ),
        cache=cache,
    )
    membership_policy = MembershipPolicy(
        buffer_rank=40,
        min_holding_periods=4,
        max_turnover=0.20,
        max_new_assets=5,
        max_removed_assets=5,
    )
    combined_engine = BacktestEngine(
        config=backtest_config,
        strategy=RiskParityStrategy(),
        prices=prices,
        returns=returns,
        preselection=combined_preselection,
        membership_policy=membership_policy,
    )
    comb_equity, comb_metrics, comb_events = combined_engine.run()
    comb_alloc = extract_allocation_history(combined_engine)
    results["Combined + Membership"] = create_result_wrapper(comb_equity, comb_metrics, comb_events, comb_alloc)

    # =========================================================================
    # STEP 4: Display Results
    # =========================================================================
    print("\n" + "=" * 80)
    print("📊 PERFORMANCE RESULTS")
    print("=" * 80)

    print(f"\n{'Strategy':<25} {'Return':>10} {'Sharpe':>8} {'MaxDD':>10} {'Trades':>8}")
    print("-" * 80)
    for name, result in results.items():
        m = result.metrics
        print(
            f"{name:<25} "
            f"{m.annualized_return:>10.2%} "
            f"{m.sharpe_ratio:>8.3f} "
            f"{m.max_drawdown:>10.2%} "
            f"{len(result.trade_log):>8}"
        )

    # =========================================================================
    # STEP 5: Create Visualizations
    # =========================================================================
    print("\n" + "=" * 80)
    print("📈 CREATING VISUALIZATIONS")
    print("=" * 80)

    plot_equity_curves(results, output_dir)
    plot_drawdowns(results, output_dir)
    plot_returns_distribution(results, output_dir)
    plot_performance_metrics(results, output_dir)

    # Plot allocation heatmaps for filtered strategies
    plot_allocation_heatmap(results["Momentum Only"], output_dir, "Momentum Only")
    plot_allocation_heatmap(results["Combined + Membership"], output_dir, "Combined + Membership")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 80)
    print("✅ VISUALIZATION COMPLETE")
    print("=" * 80)
    print()
    print(f"📁 Output directory: {output_dir}")
    print()
    print("Generated plots:")
    print("  1. equity_curves.png - Portfolio value over time")
    print("  2. drawdowns.png - Drawdown series")
    print("  3. returns_distribution.png - Return histograms")
    print("  4. performance_metrics.png - Metrics comparison")
    print("  5. allocation_heatmap_momentum_only.png - Asset weights (Momentum)")
    print("  6. allocation_heatmap_combined_+_membership.png - Asset weights (Combined)")
    print()
    print("🎯 Key Findings:")

    best_sharpe = max(results.items(), key=lambda x: x[1].metrics.sharpe_ratio)
    best_return = max(results.items(), key=lambda x: x[1].metrics.annualized_return)
    best_drawdown = min(results.items(), key=lambda x: abs(x[1].metrics.max_drawdown))

    print(f"  • Best Sharpe Ratio: {best_sharpe[0]} ({best_sharpe[1].metrics.sharpe_ratio:.3f})")
    print(f"  • Highest Return: {best_return[0]} ({best_return[1].metrics.annualized_return:.2%})")
    print(f"  • Lowest Drawdown: {best_drawdown[0]} ({best_drawdown[1].metrics.max_drawdown:.2%})")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
