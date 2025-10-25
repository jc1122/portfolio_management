#!/usr/bin/env python3
"""
Real Data Portfolio Visualization
==================================

This script demonstrates the portfolio management system on real historical data
from the long_history dataset (2005-2025, 100 stocks).

It compares three strategies:
1. Equal Weight (100 stocks) - Baseline
2. Momentum Only (30 stocks) - Factor-based selection
3. Combined + Membership (30 stocks) - Advanced with turnover control

Usage:
    python examples/real_data_visualization.py
"""

import sys
from pathlib import Path
from datetime import date
from decimal import Decimal

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from portfolio_management.backtesting.engine.backtest import BacktestEngine
from portfolio_management.backtesting.models import BacktestConfig, RebalanceFrequency
from portfolio_management.portfolio.strategies.risk_parity import RiskParityStrategy
from portfolio_management.portfolio.preselection import (
    Preselection,
    PreselectionConfig,
    PreselectionMethod,
)
from portfolio_management.portfolio.membership import MembershipPolicy

# Set plotting style
plt.style.use("seaborn-v0_8-darkgrid")
sns.set_palette("husl")


def load_real_data(prices_path, returns_path):
    """Load real historical data from CSV files."""
    print("\n📂 Loading real historical data...")

    # Load prices
    prices = pd.read_csv(prices_path, index_col=0, parse_dates=True)

    # Load returns
    returns = pd.read_csv(returns_path, index_col=0, parse_dates=True)

    print(f"✓ Loaded {len(prices.columns)} stocks")
    print(f"✓ Date range: {prices.index[0].date()} to {prices.index[-1].date()}")
    print(f"✓ Total days: {len(prices):,}")

    return prices, returns


def create_result_wrapper(equity_df, metrics, rebalance_events, alloc_history):
    """Create a result object wrapper for compatibility."""
    class Result:
        def __init__(self, equity_curve, metrics, rebalance_log, allocation_history):
            self.equity_curve = equity_curve
            self.metrics = metrics
            self.rebalance_log = rebalance_log
            self.trade_log = []
            self.allocation_history = allocation_history

    return Result(equity_df, metrics, rebalance_events, alloc_history)


def extract_allocation_history(engine):
    """Extract allocation history from backtest engine.

    Reconstructs portfolio weights at each rebalance date.
    """
    if not engine.rebalance_events:
        return pd.DataFrame()

    alloc_data = []
    holdings = {}

    for event in engine.rebalance_events:
        date = event.date

        # Apply trades
        for ticker, share_change in event.trades.items():
            holdings[ticker] = holdings.get(ticker, 0) + share_change
            if holdings[ticker] == 0:
                holdings.pop(ticker, None)

        # Get prices
        if date not in engine.prices.index:
            continue
        prices_at_date = engine.prices.loc[date]

        # Compute weights
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
        "Portfolio Equity Curves (2005-2025) - Real Data\nInitial Capital: $100,000",
        fontsize=14,
        fontweight="bold",
        pad=20,
    )
    ax.legend(loc="upper left", fontsize=11, frameon=True)
    ax.grid(True, alpha=0.3)

    # Format y-axis
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
        fontsize=9,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
    )

    plt.tight_layout()
    output_path = output_dir / "equity_curves_real.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"✓ Saved: {output_path}")


def plot_drawdowns(results_dict, output_dir):
    """Plot drawdown series."""
    print("\n📊 Creating drawdown plot...")

    fig, ax = plt.subplots(figsize=(14, 7))

    colors = ["#2E86AB", "#A23B72", "#F18F01"]

    for (name, result), color in zip(results_dict.items(), colors):
        equity = result.equity_curve
        running_max = equity.expanding().max()
        drawdown = (equity - running_max) / running_max

        ax.plot(
            drawdown.index,
            drawdown.values * 100,
            label=name,
            linewidth=2,
            color=color,
        )

    ax.set_xlabel("Date", fontsize=12, fontweight="bold")
    ax.set_ylabel("Drawdown (%)", fontsize=12, fontweight="bold")
    ax.set_title(
        "Portfolio Drawdowns (2005-2025) - Real Data",
        fontsize=14,
        fontweight="bold",
        pad=20,
    )
    ax.legend(loc="lower left", fontsize=11, frameon=True)
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color="black", linestyle="--", linewidth=0.8, alpha=0.5)

    plt.tight_layout()
    output_path = output_dir / "drawdowns_real.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"✓ Saved: {output_path}")


def plot_returns_distribution(results_dict, output_dir):
    """Plot return distributions."""
    print("\n📊 Creating returns distribution plot...")

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    colors = ["#2E86AB", "#A23B72", "#F18F01"]

    for ax, (name, result), color in zip(axes, results_dict.items(), colors):
        equity = result.equity_curve
        returns = equity.pct_change().dropna()

        ax.hist(returns * 100, bins=50, color=color, alpha=0.7, edgecolor="black")
        ax.axvline(returns.mean() * 100, color="red", linestyle="--", linewidth=2, label="Mean")
        ax.axvline(returns.median() * 100, color="green", linestyle="--", linewidth=2, label="Median")

        ax.set_xlabel("Daily Return (%)", fontsize=10, fontweight="bold")
        ax.set_ylabel("Frequency", fontsize=10, fontweight="bold")
        ax.set_title(name, fontsize=11, fontweight="bold")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    fig.suptitle(
        "Return Distributions (2005-2025) - Real Data",
        fontsize=14,
        fontweight="bold",
        y=1.02,
    )

    plt.tight_layout()
    output_path = output_dir / "returns_distribution_real.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"✓ Saved: {output_path}")


def plot_performance_metrics(results_dict, output_dir):
    """Plot performance metrics comparison."""
    print("\n📊 Creating performance metrics comparison...")

    # Extract metrics
    data = []
    for name, result in results_dict.items():
        m = result.metrics
        data.append({
            "Strategy": name,
            "Return (%)": m.annualized_return * 100,
            "Sharpe": m.sharpe_ratio,
            "Max DD (%)": abs(m.max_drawdown * 100),
            "Sortino": m.sortino_ratio,
            "Calmar": m.calmar_ratio,
        })

    df = pd.DataFrame(data)

    # Create subplots
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    axes = axes.flatten()

    metrics = ["Return (%)", "Sharpe", "Max DD (%)", "Sortino", "Calmar"]
    colors = ["#2E86AB", "#A23B72", "#F18F01"]

    for idx, metric in enumerate(metrics):
        ax = axes[idx]
        bars = ax.bar(df["Strategy"], df[metric], color=colors, edgecolor="black", linewidth=1.5)

        # Highlight best
        if metric == "Max DD (%)":
            best_idx = df[metric].idxmin()
        else:
            best_idx = df[metric].idxmax()
        bars[best_idx].set_edgecolor("gold")
        bars[best_idx].set_linewidth(3)

        ax.set_ylabel(metric, fontsize=11, fontweight="bold")
        ax.set_xticklabels(df["Strategy"], rotation=15, ha="right")
        ax.grid(True, alpha=0.3, axis="y")

        # Add values on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{height:.2f}",
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold",
            )

    # Remove extra subplot
    fig.delaxes(axes[5])

    fig.suptitle(
        "Performance Metrics Comparison (2005-2025) - Real Data",
        fontsize=14,
        fontweight="bold",
        y=0.98,
    )

    plt.tight_layout()
    output_path = output_dir / "performance_metrics_real.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"✓ Saved: {output_path}")


def main():
    """Run the real data visualization example."""
    print("=" * 80)
    print("PORTFOLIO VISUALIZATION - REAL HISTORICAL DATA")
    print("=" * 80)

    # Paths
    data_dir = Path(__file__).parent.parent / "data" / "processed"
    output_dir = Path(__file__).parent.parent / "outputs" / "real_data_example"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load real data
    prices, returns = load_real_data(
        data_dir / "long_history_prices_daily.csv",
        data_dir / "long_history_returns_daily.csv",
    )

    # Configure backtest
    print("\n⚙️  Configuring backtest...")

    config = BacktestConfig(
        start_date=date(2005, 1, 3),
        end_date=date(2024, 12, 31),  # Use through 2024
        initial_capital=Decimal("100000.00"),
        rebalance_frequency=RebalanceFrequency.QUARTERLY,
        commission_pct=0.001,  # 0.1%
        commission_min=1.0,
        slippage_bps=5.0,
        cash_reserve_pct=0.02,
    )

    # Run backtests
    print("\n🚀 Running backtests...")
    results = {}

    # Strategy 1: Equal Weight (100 stocks)
    print("\n  1/3 Equal Weight (100 stocks, no filtering)...")
    eq_engine = BacktestEngine(
        prices=prices,
        returns=returns,
        config=config,
        strategy=RiskParityStrategy(),
    )
    eq_equity_df, eq_metrics, eq_rebalance_events = eq_engine.run()
    eq_alloc = extract_allocation_history(eq_engine)
    results["Equal Weight"] = create_result_wrapper(
        eq_equity_df["equity"], eq_metrics, eq_rebalance_events, eq_alloc
    )

    # Strategy 2: Momentum Only (30 stocks)
    print("  2/3 Momentum Only (30 stocks, no membership)...")
    mom_config = PreselectionConfig(
        method=PreselectionMethod.COMBINED,
        top_k=30,
        lookback=252,
        skip=21,  # Skip ~1 month to avoid short-term reversal
        momentum_weight=0.6,
        low_vol_weight=0.4,
    )
    mom_presel = Preselection(config=mom_config)
    mom_engine = BacktestEngine(
        prices=prices,
        returns=returns,
        config=config,
        strategy=RiskParityStrategy(),
        preselection=mom_presel,
    )
    mom_equity_df, mom_metrics, mom_rebalance_events = mom_engine.run()
    mom_alloc = extract_allocation_history(mom_engine)
    results["Momentum Only"] = create_result_wrapper(
        mom_equity_df["equity"], mom_metrics, mom_rebalance_events, mom_alloc
    )

    # Strategy 3: Combined + Membership (30 stocks)
    print("  3/3 Combined Factors + Membership (30 stocks)...")
    comb_config = PreselectionConfig(
        method=PreselectionMethod.COMBINED,
        top_k=30,
        lookback=252,
        skip=21,
        momentum_weight=0.6,
        low_vol_weight=0.4,
    )
    comb_presel = Preselection(config=comb_config)
    comb_membership = MembershipPolicy(
        min_holding_periods=4,
        max_turnover=0.20,
    )
    comb_engine = BacktestEngine(
        prices=prices,
        returns=returns,
        config=config,
        strategy=RiskParityStrategy(),
        preselection=comb_presel,
        membership_policy=comb_membership,
    )
    comb_equity_df, comb_metrics, comb_rebalance_events = comb_engine.run()
    comb_alloc = extract_allocation_history(comb_engine)
    results["Combined + Membership"] = create_result_wrapper(
        comb_equity_df["equity"], comb_metrics, comb_rebalance_events, comb_alloc
    )

    # Print results
    print("\n" + "=" * 80)
    print("📊 PERFORMANCE RESULTS - REAL DATA (2005-2024)")
    print("=" * 80)
    print()
    print(f"{'Strategy':<30} {'Return':>8} {'Sharpe':>8} {'Max DD':>8} {'Trades':>8}")
    print("-" * 80)

    for name, result in results.items():
        m = result.metrics
        n_trades = len(result.rebalance_log)
        print(
            f"{name:<30} {m.annualized_return*100:>7.2f}% "
            f"{m.sharpe_ratio:>8.3f} {m.max_drawdown*100:>7.2f}% "
            f"{n_trades:>8}"
        )

    # Create visualizations
    print("\n" + "=" * 80)
    print("📈 CREATING VISUALIZATIONS")
    print("=" * 80)

    plot_equity_curves(results, output_dir)
    plot_drawdowns(results, output_dir)
    plot_returns_distribution(results, output_dir)
    plot_performance_metrics(results, output_dir)

    # Summary
    print("\n" + "=" * 80)
    print("✅ VISUALIZATION COMPLETE - REAL DATA")
    print("=" * 80)
    print(f"\n📁 Output directory: {output_dir}")
    print("Generated plots:")
    print("  1. equity_curves_real.png - Portfolio value over time")
    print("  2. drawdowns_real.png - Drawdown series")
    print("  3. returns_distribution_real.png - Return histograms")
    print("  4. performance_metrics_real.png - Metrics comparison")

    # Key findings
    best_strategy = max(results.items(), key=lambda x: x[1].metrics.sharpe_ratio)
    best_return = max(results.items(), key=lambda x: x[1].metrics.annualized_return)
    best_dd = min(results.items(), key=lambda x: x[1].metrics.max_drawdown)

    print("\n🎯 Key Findings:")
    print(f"  • Best Sharpe Ratio: {best_strategy[0]} ({best_strategy[1].metrics.sharpe_ratio:.3f})")
    print(f"  • Highest Return: {best_return[0]} ({best_return[1].metrics.annualized_return*100:.2f}%)")
    print(f"  • Lowest Drawdown: {best_dd[0]} ({best_dd[1].metrics.max_drawdown*100:.2f}%)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
