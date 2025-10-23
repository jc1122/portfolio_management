#!/usr/bin/env python3
"""Quick chart generator for backtest results."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def plot_equity_curve(output_dir: Path):
    """Plot equity curve from backtest results."""
    equity_file = output_dir / "viz_equity_curve.csv"
    if not equity_file.exists():
        print(f"Equity curve file not found: {equity_file}")
        return

    df = pd.read_csv(equity_file)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")

    plt.figure(figsize=(12, 6))
    plt.plot(df.index, df["equity"], linewidth=2, label="Portfolio Value")
    plt.title("Portfolio Equity Curve")
    plt.xlabel("Date")
    plt.ylabel("Portfolio Value ($)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()

    chart_file = output_dir / "equity_curve.png"
    plt.savefig(chart_file, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Chart saved to: {chart_file}")


def plot_drawdown(output_dir: Path):
    """Plot drawdown from backtest results."""
    drawdown_file = output_dir / "viz_drawdown.csv"
    if not drawdown_file.exists():
        print(f"Drawdown file not found: {drawdown_file}")
        return

    df = pd.read_csv(drawdown_file)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")

    plt.figure(figsize=(12, 6))
    plt.fill_between(
        df.index,
        df["drawdown_pct"],
        0,
        color="red",
        alpha=0.3,
        label="Drawdown",
    )
    plt.plot(df.index, df["drawdown_pct"], color="red", linewidth=1)
    plt.title("Portfolio Drawdown")
    plt.xlabel("Date")
    plt.ylabel("Drawdown (%)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()

    chart_file = output_dir / "drawdown.png"
    plt.savefig(chart_file, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Chart saved to: {chart_file}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python plot_charts.py <output_dir>")
        sys.exit(1)

    output_dir = Path(sys.argv[1])
    plot_equity_curve(output_dir)
    plot_drawdown(output_dir)
