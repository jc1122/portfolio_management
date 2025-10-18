#!/usr/bin/env python3
r"""Backtest CLI - Command-line interface for running portfolio backtests.

This script provides a user-friendly interface for executing backtests with
configurable parameters including strategy selection, date ranges, transaction
costs, and output options.

Examples:
    # Run equal-weight strategy with default settings
    python scripts/run_backtest.py equal_weight

    # Run risk parity with custom date range and costs
    python scripts/run_backtest.py risk_parity \\
        --start-date 2020-01-01 \\
        --end-date 2023-12-31 \\
        --commission 0.001 \\
        --slippage 0.0005

    # Run mean-variance with monthly rebalancing and save output
    python scripts/run_backtest.py mean_variance \\
        --rebalance-frequency monthly \\
        --output-dir results/backtest_2024

    # Run with custom universe and no visualization
    python scripts/run_backtest.py equal_weight \\
        --universe-file config/custom_universe.yaml \\
        --no-visualize

"""

import argparse
import json
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd
import yaml

from portfolio_management.backtest import (
    BacktestConfig,
    BacktestEngine,
    RebalanceFrequency,
    RebalanceTrigger,
    TransactionCostModel,
)
from portfolio_management.exceptions import (
    BacktestError,
    InsufficientHistoryError,
    InvalidBacktestConfigError,
)
from portfolio_management.portfolio import (
    EqualWeightStrategy,
    MeanVarianceStrategy,
    PortfolioStrategy,
    RiskParityStrategy,
)
from portfolio_management.visualization import (
    create_summary_report,
    prepare_drawdown_series,
    prepare_equity_curve,
    prepare_rolling_metrics,
    prepare_transaction_costs_summary,
)


def parse_date(date_str: str) -> date:
    """Parse date string in YYYY-MM-DD format."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as e:
        raise argparse.ArgumentTypeError(
            f"Invalid date format '{date_str}'. Use YYYY-MM-DD.",
        ) from e


def parse_decimal(value_str: str) -> Decimal:
    """Parse decimal value from string."""
    try:
        return Decimal(value_str)
    except Exception as e:
        raise argparse.ArgumentTypeError(
            f"Invalid decimal value '{value_str}'.",
        ) from e


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="Run portfolio backtest with specified strategy and parameters.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Required arguments
    parser.add_argument(
        "strategy",
        choices=["equal_weight", "risk_parity", "mean_variance"],
        help="Portfolio construction strategy to use",
    )

    # Date range
    parser.add_argument(
        "--start-date",
        type=parse_date,
        default="2020-01-01",
        help="Backtest start date (YYYY-MM-DD). Default: 2020-01-01",
    )
    parser.add_argument(
        "--end-date",
        type=parse_date,
        default=date.today().isoformat(),
        help="Backtest end date (YYYY-MM-DD). Default: today",
    )

    # Capital and costs
    parser.add_argument(
        "--initial-capital",
        type=parse_decimal,
        default=Decimal(100000),
        help="Initial portfolio capital. Default: 100000",
    )
    parser.add_argument(
        "--commission",
        type=parse_decimal,
        default=Decimal("0.001"),
        help="Commission rate (e.g., 0.001 = 0.1%%). Default: 0.001",
    )
    parser.add_argument(
        "--slippage",
        type=parse_decimal,
        default=Decimal("0.0005"),
        help="Slippage rate (e.g., 0.0005 = 0.05%%). Default: 0.0005",
    )
    parser.add_argument(
        "--min-commission",
        type=parse_decimal,
        default=Decimal("1.0"),
        help="Minimum commission per trade. Default: 1.0",
    )

    # Rebalancing
    parser.add_argument(
        "--rebalance-frequency",
        choices=["daily", "weekly", "monthly", "quarterly", "annual"],
        default="monthly",
        help="Rebalancing frequency. Default: monthly",
    )
    parser.add_argument(
        "--rebalance-trigger",
        choices=["scheduled", "opportunistic", "forced"],
        default="scheduled",
        help="Rebalancing trigger type. Default: scheduled",
    )
    parser.add_argument(
        "--drift-threshold",
        type=parse_decimal,
        default=Decimal("0.05"),
        help="Drift threshold for opportunistic rebalancing (e.g., 0.05 = 5%%). Default: 0.05",
    )

    # Data sources
    parser.add_argument(
        "--universe-file",
        type=Path,
        default=Path("config/universes.yaml"),
        help="Path to universe configuration file. Default: config/universes.yaml",
    )
    parser.add_argument(
        "--universe-name",
        type=str,
        default="default",
        help="Universe name in configuration file. Default: default",
    )
    parser.add_argument(
        "--prices-file",
        type=Path,
        default=Path("data/processed/prices.csv"),
        help="Path to prices CSV file. Default: data/processed/prices.csv",
    )
    parser.add_argument(
        "--returns-file",
        type=Path,
        default=Path("data/processed/returns.csv"),
        help="Path to returns CSV file. Default: data/processed/returns.csv",
    )

    # Strategy-specific parameters
    parser.add_argument(
        "--max-position-size",
        type=parse_decimal,
        default=Decimal("0.25"),
        help="Maximum position size (0-1). Default: 0.25",
    )
    parser.add_argument(
        "--min-position-size",
        type=parse_decimal,
        default=Decimal("0.01"),
        help="Minimum position size (0-1). Default: 0.01",
    )

    # Mean-variance specific
    parser.add_argument(
        "--target-return",
        type=parse_decimal,
        help="Target return for mean-variance strategy (annualized)",
    )
    parser.add_argument(
        "--risk-aversion",
        type=parse_decimal,
        default=Decimal("1.0"),
        help="Risk aversion parameter for mean-variance (higher = more conservative). Default: 1.0",
    )

    # Output options
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory for results. Default: results/backtest_TIMESTAMP",
    )
    parser.add_argument(
        "--no-visualize",
        action="store_true",
        help="Skip generating visualization data files",
    )
    parser.add_argument(
        "--save-trades",
        action="store_true",
        help="Save detailed trade history to CSV",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed progress information",
    )

    return parser


def load_universe(universe_file: Path, universe_name: str) -> list[str]:
    """Load asset universe from YAML configuration."""
    if not universe_file.exists():
        raise FileNotFoundError(f"Universe file not found: {universe_file}")

    with open(universe_file) as f:
        config = yaml.safe_load(f)

    if "universes" not in config:
        raise ValueError(f"No 'universes' section in {universe_file}")

    universes = config["universes"]
    if universe_name not in universes:
        available = ", ".join(universes.keys())
        raise ValueError(
            f"Universe '{universe_name}' not found. Available: {available}",
        )

    universe = universes[universe_name]
    if "assets" not in universe:
        raise ValueError(f"Universe '{universe_name}' has no 'assets' field")

    return universe["assets"]


def load_data(
    prices_file: Path,
    returns_file: Path,
    assets: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load prices and returns data for specified assets."""
    if not prices_file.exists():
        raise FileNotFoundError(f"Prices file not found: {prices_file}")
    if not returns_file.exists():
        raise FileNotFoundError(f"Returns file not found: {returns_file}")

    # Load prices
    prices = pd.read_csv(prices_file, index_col=0, parse_dates=True)
    if not all(asset in prices.columns for asset in assets):
        missing = [a for a in assets if a not in prices.columns]
        raise ValueError(f"Missing assets in prices file: {missing}")
    prices = prices[assets]

    # Load returns
    returns = pd.read_csv(returns_file, index_col=0, parse_dates=True)
    if not all(asset in returns.columns for asset in assets):
        missing = [a for a in assets if a not in returns.columns]
        raise ValueError(f"Missing assets in returns file: {missing}")
    returns = returns[assets]

    return prices, returns


def create_strategy(strategy_name: str) -> PortfolioStrategy:
    """Create portfolio strategy instance."""
    if strategy_name == "equal_weight":
        return EqualWeightStrategy()
    if strategy_name == "risk_parity":
        return RiskParityStrategy()
    if strategy_name == "mean_variance":
        return MeanVarianceStrategy()
    raise ValueError(f"Unknown strategy: {strategy_name}")


def save_results(
    output_dir: Path,
    config: BacktestConfig,
    equity_curve: list[tuple[date, float]],
    rebalance_events: list,
    metrics: dict[str, float],
    save_trades: bool,
    generate_viz: bool,
    verbose: bool,
) -> None:
    """Save backtest results to output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    if verbose:
        pass

    # Convert equity curve to DataFrame
    equity_df = pd.DataFrame(equity_curve, columns=["date", "equity"])
    equity_df = equity_df.set_index("date")

    # Save configuration
    config_dict = {
        "start_date": config.start_date.isoformat(),
        "end_date": config.end_date.isoformat(),
        "initial_capital": float(config.initial_capital),
        "rebalance_frequency": config.rebalance_frequency.name,
        "rebalance_trigger": config.rebalance_trigger.name,
        "commission_rate": float(config.commission_rate),
        "slippage_rate": float(config.slippage_rate),
        "min_commission": float(config.min_commission),
        "drift_threshold": float(config.drift_threshold),
    }
    with open(output_dir / "config.json", "w") as f:
        json.dump(config_dict, f, indent=2)
    if verbose:
        pass

    # Save metrics
    with open(output_dir / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    if verbose:
        pass

    # Save equity curve
    equity_df.to_csv(output_dir / "equity_curve.csv")
    if verbose:
        pass

    # Save trade history
    if save_trades and rebalance_events:
        trades = []
        for event in rebalance_events:
            for trade in event.trades:
                trades.append(
                    {
                        "date": event.date.isoformat(),
                        "asset": trade["asset"],
                        "shares": trade["shares"],
                        "price": trade["price"],
                        "value": trade["value"],
                        "commission": trade["commission"],
                        "slippage": trade["slippage"],
                        "total_cost": trade["total_cost"],
                    },
                )
        trades_df = pd.DataFrame(trades)
        trades_df.to_csv(output_dir / "trades.csv", index=False)
        if verbose:
            pass

    # Generate visualization data
    if generate_viz:
        # Equity curve with normalized values
        viz_equity = prepare_equity_curve(equity_df)
        viz_equity.to_csv(output_dir / "viz_equity_curve.csv")

        # Drawdown series
        viz_drawdown = prepare_drawdown_series(equity_df)
        viz_drawdown.to_csv(output_dir / "viz_drawdown.csv")

        # Rolling metrics
        viz_rolling = prepare_rolling_metrics(equity_df)
        viz_rolling.to_csv(output_dir / "viz_rolling_metrics.csv")

        # Transaction costs summary
        if rebalance_events:
            viz_costs = prepare_transaction_costs_summary(rebalance_events)
            viz_costs.to_csv(output_dir / "viz_transaction_costs.csv")

        # Summary report
        summary = create_summary_report(metrics, rebalance_events, equity_df)
        with open(output_dir / "summary_report.json", "w") as f:
            json.dump(summary, f, indent=2)

        if verbose:
            pass


def print_results(metrics: dict[str, float], verbose: bool) -> None:
    """Print backtest results to console."""
    if verbose:
        pass


def main() -> int:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    try:
        # Set up output directory
        if args.output_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            args.output_dir = Path(f"results/backtest_{timestamp}")

        if args.verbose:
            pass

        # Load universe
        if args.verbose:
            pass
        assets = load_universe(args.universe_file, args.universe_name)
        if args.verbose:
            pass

        # Load data
        if args.verbose:
            pass
        prices, returns = load_data(args.prices_file, args.returns_file, assets)
        if args.verbose:
            pass

        # Create strategy
        if args.verbose:
            pass
        strategy = create_strategy(args.strategy)
        if args.verbose:
            pass

        # Create transaction cost model
        cost_model = TransactionCostModel(
            commission_rate=args.commission,
            slippage_rate=args.slippage,
            min_commission=args.min_commission,
        )

        # Parse rebalance frequency and trigger
        freq_map = {
            "daily": RebalanceFrequency.DAILY,
            "weekly": RebalanceFrequency.WEEKLY,
            "monthly": RebalanceFrequency.MONTHLY,
            "quarterly": RebalanceFrequency.QUARTERLY,
            "annual": RebalanceFrequency.ANNUAL,
        }
        trigger_map = {
            "scheduled": RebalanceTrigger.SCHEDULED,
            "opportunistic": RebalanceTrigger.OPPORTUNISTIC,
            "forced": RebalanceTrigger.FORCED,
        }

        # Create backtest configuration
        config = BacktestConfig(
            start_date=args.start_date,
            end_date=args.end_date,
            initial_capital=args.initial_capital,
            rebalance_frequency=freq_map[args.rebalance_frequency],
            rebalance_trigger=trigger_map[args.rebalance_trigger],
            commission_rate=args.commission,
            slippage_rate=args.slippage,
            min_commission=args.min_commission,
            drift_threshold=args.drift_threshold,
        )

        # Run backtest
        if args.verbose:
            pass
        engine = BacktestEngine(
            config=config,
            strategy=strategy,
            cost_model=cost_model,
            prices=prices,
            returns=returns,
        )
        equity_curve, rebalance_events, metrics = engine.run()
        if args.verbose:
            pass

        # Print results
        print_results(metrics, args.verbose)

        # Save results
        save_results(
            args.output_dir,
            config,
            equity_curve,
            rebalance_events,
            metrics,
            args.save_trades,
            not args.no_visualize,
            args.verbose,
        )

        return 0

    except (
        BacktestError,
        InvalidBacktestConfigError,
        InsufficientHistoryError,
    ):
        return 1
    except FileNotFoundError:
        return 1
    except ValueError:
        return 1
    except Exception:
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
