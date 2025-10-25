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
from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from portfolio_management.analytics.indicators import (
    FilterHook,
    IndicatorConfig,
    NoOpIndicatorProvider,
)
from portfolio_management.backtesting import (
    BacktestConfig,
    RebalanceFrequency,
)
from portfolio_management.config.validation import (
    ValidationWarning,
    check_dependencies,
    check_optimality_warnings,
    get_sensible_defaults,
    validate_cache_config,
    validate_feature_compatibility,
    validate_membership_config,
    validate_pit_config,
    validate_preselection_config,
)
from portfolio_management.core.exceptions import (
    BacktestError,
    ConfigurationError,
    InsufficientHistoryError,
    InvalidBacktestConfigError,
)
from portfolio_management.portfolio import (
    EqualWeightStrategy,
    MeanVarianceStrategy,
    PortfolioStrategy,
    RiskParityStrategy,
)
from portfolio_management.reporting.visualization import (
    create_summary_report,
    prepare_drawdown_series,
    prepare_equity_curve,
    prepare_rolling_metrics,
    prepare_transaction_costs_summary,
)
from portfolio_management.services import BacktestRequest, BacktestService


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
        default=date(2020, 1, 1),
        help="Backtest start date (YYYY-MM-DD). Default: 2020-01-01",
    )
    parser.add_argument(
        "--end-date",
        type=parse_date,
        default=date.today(),
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
        "--drift-threshold",
        type=parse_decimal,
        default=Decimal("0.05"),
        help="Drift threshold for opportunistic rebalancing (e.g., 0.05 = 5%%). Default: 0.05",
    )
    parser.add_argument(
        "--lookback-periods",
        type=int,
        default=252,
        help="Rolling lookback window for parameter estimation (days). Default: 252 (1 year)",
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

    # Preselection options
    parser.add_argument(
        "--preselect-method",
        choices=["momentum", "low_vol", "combined"],
        help="Preselection method (momentum, low_vol, or combined)",
    )
    parser.add_argument(
        "--preselect-top-k",
        type=int,
        help="Number of assets to select via preselection (0 or None to disable)",
    )
    parser.add_argument(
        "--preselect-lookback",
        type=int,
        default=252,
        help="Lookback period for preselection factors (days). Default: 252",
    )
    parser.add_argument(
        "--preselect-skip",
        type=int,
        default=1,
        help="Skip most recent N days for momentum calculation. Default: 1",
    )
    parser.add_argument(
        "--preselect-momentum-weight",
        type=float,
        default=0.5,
        help="Weight for momentum in combined preselection (0-1). Default: 0.5",
    )
    parser.add_argument(
        "--preselect-low-vol-weight",
        type=float,
        default=0.5,
        help="Weight for low-volatility in combined preselection (0-1). Default: 0.5",
    )

    # Technical indicators
    parser.add_argument(
        "--enable-indicators",
        action="store_true",
        help="Enable technical indicator filtering (currently no-op stub)",
    )
    parser.add_argument(
        "--indicator-provider",
        type=str,
        default="noop",
        choices=["noop"],
        help="Indicator provider to use. Default: noop (currently only option)",
    )

    # Membership policy
    parser.add_argument(
        "--membership-enabled",
        action="store_true",
        help="Enable membership policy to control asset churn during rebalancing",
    )
    parser.add_argument(
        "--membership-buffer-rank",
        type=int,
        default=5,
        help="Rank buffer to protect existing holdings (higher = more stable). Default: 5",
    )
    parser.add_argument(
        "--membership-min-hold",
        type=int,
        default=3,
        help="Minimum rebalance periods to hold an asset. Default: 3",
    )
    parser.add_argument(
        "--membership-max-turnover",
        type=parse_decimal,
        help="Maximum portfolio turnover per rebalancing (0-1, e.g., 0.3 = 30%%)",
    )
    parser.add_argument(
        "--membership-max-new",
        type=int,
        help="Maximum number of new assets to add per rebalancing",
    )
    parser.add_argument(
        "--membership-max-removed",
        type=int,
        help="Maximum number of assets to remove per rebalancing",
    )

    # Point-in-time (PIT) eligibility
    parser.add_argument(
        "--use-pit-eligibility",
        action="store_true",
        help="Enable point-in-time eligibility filtering to avoid lookahead bias",
    )
    parser.add_argument(
        "--min-history-days",
        type=int,
        default=252,
        help="Minimum days of history for PIT eligibility (default: 252 = 1 year)",
    )
    parser.add_argument(
        "--min-price-rows",
        type=int,
        default=252,
        help="Minimum price rows for PIT eligibility (default: 252)",
    )

    # Caching options
    parser.add_argument(
        "--enable-cache",
        action="store_true",
        help="Enable on-disk caching for factor scores and PIT eligibility",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        help="Directory for cache storage. Default: .cache/backtest",
    )
    parser.add_argument(
        "--cache-max-age-days",
        type=int,
        help="Maximum age of cache entries in days (optional, no limit if not set)",
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

    # Validation options
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat configuration warnings as errors (strict validation mode)",
    )
    parser.add_argument(
        "--ignore-warnings",
        action="store_true",
        help="Suppress configuration warnings (not recommended)",
    )
    parser.add_argument(
        "--show-defaults",
        action="store_true",
        help="Display sensible default values and exit",
    )

    return parser


def load_universe(universe_file: Path, universe_name: str) -> tuple[list[str], dict]:
    """Load asset universe and configuration from YAML.

    Returns:
        Tuple of (assets list, universe config dict with preselection/membership/pit blocks)

    """
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

    return universe["assets"], universe


def load_data(
    prices_file: Path,
    returns_file: Path,
    assets: list[str],
    start_date: date | None = None,
    end_date: date | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load prices and returns data for specified assets and date range.

    This function optimizes memory usage by only loading the required asset
    columns and filtering to the requested date range during the read operation.

    Args:
        prices_file: Path to prices CSV file
        returns_file: Path to returns CSV file
        assets: List of asset tickers to load
        start_date: Optional start date for filtering (inclusive)
        end_date: Optional end date for filtering (inclusive)

    Returns:
        Tuple of (prices DataFrame, returns DataFrame) filtered to requested
        assets and date range

    Raises:
        FileNotFoundError: If prices or returns file doesn't exist
        ValueError: If any requested assets are missing from the data files

    """
    if not prices_file.exists():
        raise FileNotFoundError(f"Prices file not found: {prices_file}")
    if not returns_file.exists():
        raise FileNotFoundError(f"Returns file not found: {returns_file}")

    # First, peek at the header to validate all requested assets exist
    # This provides early error detection before loading the full data
    try:
        prices_header = pd.read_csv(prices_file, nrows=0, index_col=0)
        returns_header = pd.read_csv(returns_file, nrows=0, index_col=0)
    except Exception as e:
        raise ValueError(f"Failed to read CSV headers: {e}") from e

    # Check for missing assets in prices
    missing_prices = [a for a in assets if a not in prices_header.columns]
    if missing_prices:
        raise ValueError(
            f"Missing assets in prices file {prices_file}: {missing_prices}",
        )

    # Check for missing assets in returns
    missing_returns = [a for a in assets if a not in returns_header.columns]
    if missing_returns:
        raise ValueError(
            f"Missing assets in returns file {returns_file}: {missing_returns}",
        )

    # Load only the required columns (index + requested assets)
    # This significantly reduces memory usage for large universes
    usecols = [prices_header.index.name or 0, *assets]

    # Load prices with column filtering
    prices = pd.read_csv(
        prices_file,
        index_col=0,
        parse_dates=True,
        usecols=usecols,
    )

    # Load returns with column filtering
    returns = pd.read_csv(
        returns_file,
        index_col=0,
        parse_dates=True,
        usecols=usecols,
    )

    # Filter by date range if specified
    if start_date is not None:
        prices = prices[prices.index >= pd.Timestamp(start_date)]
        returns = returns[returns.index >= pd.Timestamp(start_date)]

    if end_date is not None:
        prices = prices[prices.index <= pd.Timestamp(end_date)]
        returns = returns[returns.index <= pd.Timestamp(end_date)]

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


def create_membership_policy(args: argparse.Namespace):
    """Create membership policy from CLI arguments.

    Returns:
        MembershipPolicy instance if enabled, None otherwise.

    """
    if not args.membership_enabled:
        return None

    from portfolio_management.portfolio import MembershipPolicy

    return MembershipPolicy(
        buffer_rank=(
            args.membership_buffer_rank if args.membership_buffer_rank else None
        ),
        min_holding_periods=(
            args.membership_min_hold if args.membership_min_hold else None
        ),
        max_turnover=(
            float(args.membership_max_turnover)
            if args.membership_max_turnover
            else None
        ),
        max_new_assets=args.membership_max_new if args.membership_max_new else None,
        max_removed_assets=(
            args.membership_max_removed if args.membership_max_removed else None
        ),
        enabled=True,
    )


def create_preselection_from_universe(
    universe_config: dict,
    args: argparse.Namespace,
    cache=None,
):
    """Create preselection from universe config, with CLI args as override.

    Args:
        universe_config: Universe configuration dictionary.
        args: Parsed command-line arguments.
        cache: Optional FactorCache instance for caching factor scores.

    Returns:
        Preselection instance if configured, None otherwise.

    """
    # CLI args override universe config
    if args.preselect_method and args.preselect_top_k:
        from portfolio_management.portfolio import (
            Preselection,
            PreselectionConfig,
            PreselectionMethod,
        )

        preselection_config = PreselectionConfig(
            method=PreselectionMethod(args.preselect_method),
            top_k=args.preselect_top_k,
            lookback=args.preselect_lookback,
            skip=args.preselect_skip,
            momentum_weight=args.preselect_momentum_weight,
            low_vol_weight=args.preselect_low_vol_weight,
        )
        return Preselection(preselection_config, cache=cache)

    # Check universe config
    if "preselection" in universe_config:
        from portfolio_management.portfolio import (
            Preselection,
            PreselectionConfig,
            PreselectionMethod,
        )

        ps_config = universe_config["preselection"]
        if ps_config.get("method") and ps_config.get("top_k"):
            preselection_config = PreselectionConfig(
                method=PreselectionMethod(ps_config["method"]),
                top_k=ps_config["top_k"],
                lookback=ps_config.get("lookback", 252),
                skip=ps_config.get("skip", 1),
                momentum_weight=ps_config.get("momentum_weight", 0.5),
                low_vol_weight=ps_config.get("low_vol_weight", 0.5),
                min_periods=ps_config.get("min_periods", 60),
            )
            return Preselection(preselection_config, cache=cache)

    return None


def create_membership_policy_from_universe(
    universe_config: dict,
    args: argparse.Namespace,
):
    """Create membership policy from universe config, with CLI args as override.

    Returns:
        MembershipPolicy instance if configured, None otherwise.

    """
    # CLI args override universe config
    if args.membership_enabled:
        return create_membership_policy(args)

    # Check universe config
    if "membership_policy" in universe_config:
        from portfolio_management.portfolio import MembershipPolicy

        mp_config = universe_config["membership_policy"]
        if mp_config.get("enabled", False):
            return MembershipPolicy(
                buffer_rank=mp_config.get("buffer_rank"),
                min_holding_periods=mp_config.get("min_holding_periods"),
                max_turnover=mp_config.get("max_turnover"),
                max_new_assets=mp_config.get("max_new_assets"),
                max_removed_assets=mp_config.get("max_removed_assets"),
                enabled=True,
            )

    return None


def apply_pit_config_from_universe(universe_config: dict, args: argparse.Namespace):
    """Update args with PIT settings from universe config if not already set by CLI.

    CLI args take precedence over universe config.
    """
    if "pit_eligibility" in universe_config:
        pit_config = universe_config["pit_eligibility"]

        # Only apply universe config if CLI didn't explicitly enable
        if not args.use_pit_eligibility and pit_config.get("enabled", False):
            args.use_pit_eligibility = True
            args.min_history_days = pit_config.get("min_history_days", 252)
            args.min_price_rows = pit_config.get("min_price_rows", 252)


def print_validation_warnings(
    warnings: list[ValidationWarning], verbose: bool = False
) -> None:
    """Print validation warnings in a user-friendly format.

    Args:
        warnings: List of validation warnings to print
        verbose: If True, print detailed warnings; if False, print summary

    """
    if not warnings:
        return

    print("\n⚠️  Configuration Warnings:")
    print("=" * 70)

    # Group warnings by severity
    by_severity = {"high": [], "medium": [], "low": []}
    for w in warnings:
        by_severity[w.severity].append(w)

    # Print high severity first
    for severity in ["high", "medium", "low"]:
        severity_warnings = by_severity[severity]
        if not severity_warnings:
            continue

        severity_symbol = {"high": "🔴", "medium": "🟡", "low": "⚪"}[severity]
        print(f"\n{severity_symbol} {severity.upper()} Severity:")

        for w in severity_warnings:
            if verbose:
                print(f"  • {w.category.upper()}: {w.parameter}")
                print(f"    Problem: {w.message}")
                print(f"    Suggestion: {w.suggestion}")
            else:
                print(f"  • {w.parameter}: {w.message}")

    print("\n" + "=" * 70)
    if not verbose:
        print("Run with --verbose for detailed suggestions.")
    print()


def validate_configuration(
    args: argparse.Namespace, universe_config: dict, universe_size: int
) -> None:
    """Validate backtest configuration and print warnings.

    Args:
        args: Parsed command-line arguments
        universe_config: Universe configuration dictionary
        universe_size: Number of assets in universe

    Raises:
        ConfigurationError: If validation fails in strict mode

    """
    all_warnings = []

    universe_preselection = universe_config.get("preselection", {}) if universe_config else {}
    preselection_enabled = bool(args.preselect_method or args.preselect_top_k)
    if not preselection_enabled:
        preselection_enabled = bool(
            universe_preselection.get("method") and universe_preselection.get("top_k")
        )

    preselection_top_k = args.preselect_top_k
    if preselection_top_k is None:
        preselection_top_k = universe_preselection.get("top_k")

    universe_membership = universe_config.get("membership_policy", {}) if universe_config else {}
    membership_enabled = bool(args.membership_enabled)
    membership_config: dict[str, Any] | None = None
    if membership_enabled:
        membership_config = {
            "buffer_rank": args.membership_buffer_rank,
            "min_holding_periods": args.membership_min_hold,
            "max_turnover": float(args.membership_max_turnover)
            if args.membership_max_turnover
            else None,
        }
    elif universe_membership.get("enabled", False):
        membership_enabled = True
        membership_config = {
            "buffer_rank": universe_membership.get("buffer_rank"),
            "min_holding_periods": universe_membership.get("min_holding_periods"),
            "max_turnover": universe_membership.get("max_turnover"),
        }
        if membership_config["max_turnover"] is not None:
            membership_config["max_turnover"] = float(membership_config["max_turnover"])

    # 1. Validate preselection config
    if preselection_enabled:
        result = validate_preselection_config(
            top_k=preselection_top_k,
            lookback=
            args.preselect_lookback
            if args.preselect_lookback is not None
            else universe_preselection.get("lookback"),
            skip=
            args.preselect_skip
            if args.preselect_skip is not None
            else universe_preselection.get("skip"),
            method=
            args.preselect_method
            if args.preselect_method
            else universe_preselection.get("method"),
            strict=args.strict,
        )
        all_warnings.extend(result.warnings)
        if not result.valid:
            raise ConfigurationError(
                f"Preselection validation failed:\n" + "\n".join(result.errors)
            )

    # 2. Validate membership config
    if membership_enabled and membership_config is not None:
        result = validate_membership_config(
            buffer_rank=membership_config.get("buffer_rank"),
            top_k=preselection_top_k,
            min_holding_periods=membership_config.get("min_holding_periods"),
            max_turnover=membership_config.get("max_turnover"),
            strict=args.strict,
        )
        all_warnings.extend(result.warnings)
        if not result.valid:
            raise ConfigurationError(
                f"Membership policy validation failed:\n" + "\n".join(result.errors)
            )

    # 3. Validate PIT config
    if args.use_pit_eligibility:
        result = validate_pit_config(
            min_history_days=args.min_history_days,
            min_price_rows=args.min_price_rows,
            strict=args.strict,
        )
        all_warnings.extend(result.warnings)
        if not result.valid:
            raise ConfigurationError(
                f"PIT eligibility validation failed:\n" + "\n".join(result.errors)
            )

    # 4. Validate cache config
    if args.enable_cache:
        cache_dir = args.cache_dir if args.cache_dir else Path(".cache/backtest")
        result = validate_cache_config(
            cache_dir=cache_dir,
            max_age_days=args.cache_max_age_days,
            enabled=True,
            strict=args.strict,
        )
        all_warnings.extend(result.warnings)
        if not result.valid:
            raise ConfigurationError(
                f"Cache configuration validation failed:\n" + "\n".join(result.errors)
            )

    # 5. Check feature compatibility
    result = validate_feature_compatibility(
        preselection_enabled=preselection_enabled,
        preselection_top_k=preselection_top_k,
        membership_enabled=membership_enabled,
        membership_buffer_rank=
        membership_config.get("buffer_rank") if membership_config else None,
        cache_enabled=args.enable_cache,
        universe_size=universe_size,
        strict=args.strict,
    )
    all_warnings.extend(result.warnings)

    # 6. Check optimality
    config_dict = {
        "preselection": {
            "top_k": preselection_top_k,
            "lookback":
            args.preselect_lookback
            if args.preselect_lookback is not None
            else universe_preselection.get("lookback"),
        },
        "membership": {
            "buffer_rank":
            membership_config.get("buffer_rank") if membership_config else None,
        },
        "universe": {"size": universe_size},
        "cache": {"enabled": args.enable_cache},
    }
    result = check_optimality_warnings(config_dict, strict=args.strict)
    all_warnings.extend(result.warnings)

    # 7. Check dependencies
    result = check_dependencies(
        fast_io_enabled=False,  # Fast IO not exposed in this CLI yet
        universe_size=universe_size,
        strict=args.strict,
    )
    all_warnings.extend(result.warnings)

    # Print warnings (unless suppressed)
    if args.strict and all_warnings:
        warning_summary = "\n".join(
            f"  - {w.parameter}: {w.message} (severity={w.severity})"
            for w in all_warnings
        )
        raise ConfigurationError(
            "Strict mode enabled. Configuration warnings treated as errors:\n"
            + warning_summary
        )

    if all_warnings and not args.ignore_warnings:
        print_validation_warnings(all_warnings, verbose=args.verbose)


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
    if isinstance(equity_curve, pd.DataFrame):
        equity_df = equity_curve.copy()
        if "equity" not in equity_df.columns:
            raise ValueError("Equity curve DataFrame must contain an 'equity' column.")
        equity_df.index = pd.to_datetime(equity_df.index)
        equity_df = equity_df.sort_index()
    else:
        equity_df = pd.DataFrame(equity_curve, columns=["date", "equity"])
        if equity_df.empty:
            raise ValueError("Equity curve is empty; cannot save results.")
        equity_df["date"] = pd.to_datetime(equity_df["date"])
        equity_df = equity_df.set_index("date").sort_index()
    equity_df.index.name = "date"

    # Save configuration
    config_dict = {
        "start_date": config.start_date.isoformat(),
        "end_date": config.end_date.isoformat(),
        "initial_capital": float(config.initial_capital),
        "rebalance_frequency": config.rebalance_frequency.name,
        "rebalance_threshold": float(config.rebalance_threshold),
        "commission_pct": float(config.commission_pct),
        "commission_min": float(config.commission_min),
        "slippage_bps": float(config.slippage_bps),
        "cash_reserve_pct": float(config.cash_reserve_pct),
    }
    with open(output_dir / "config.json", "w") as f:
        json.dump(config_dict, f, indent=2)
    if verbose:
        pass

    # Save metrics
    metrics_dict = asdict(metrics)
    metrics_dict["total_costs"] = float(metrics.total_costs)
    with open(output_dir / "metrics.json", "w") as f:
        json.dump(metrics_dict, f, indent=2)
    if verbose:
        pass

    # Save equity curve
    equity_df.to_csv(output_dir / "equity_curve.csv", index_label="date")
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
        viz_equity = prepare_equity_curve(equity_df).reset_index()
        if "index" in viz_equity.columns:
            viz_equity = viz_equity.rename(columns={"index": "date"})
        viz_equity.to_csv(output_dir / "viz_equity_curve.csv", index=False)

        # Drawdown series
        viz_drawdown = prepare_drawdown_series(equity_df).reset_index()
        if "index" in viz_drawdown.columns:
            viz_drawdown = viz_drawdown.rename(columns={"index": "date"})
        viz_drawdown.to_csv(output_dir / "viz_drawdown.csv", index=False)

        # Rolling metrics
        viz_rolling = prepare_rolling_metrics(equity_df).reset_index()
        if "index" in viz_rolling.columns:
            viz_rolling = viz_rolling.rename(columns={"index": "date"})
        viz_rolling.to_csv(output_dir / "viz_rolling_metrics.csv", index=False)

        # Transaction costs summary
        if rebalance_events:
            viz_costs = prepare_transaction_costs_summary(
                rebalance_events,
            ).reset_index()
            if "index" in viz_costs.columns:
                viz_costs = viz_costs.rename(columns={"index": "date"})
            viz_costs.to_csv(output_dir / "viz_transaction_costs.csv", index=False)

        # Summary report
        summary = create_summary_report(equity_df, metrics, rebalance_events)
        with open(output_dir / "summary_report.json", "w") as f:
            json.dump(summary, f, indent=2)

        if verbose:
            pass


def print_results(metrics, verbose: bool) -> None:
    """Print backtest results to console."""
    if not verbose:
        return

    metrics_dict = asdict(metrics)
    metrics_dict["total_costs"] = float(metrics.total_costs)

    print("Backtest metrics:")
    for key, value in metrics_dict.items():
        print(f"- {key}: {value}")


def main() -> int:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Handle --show-defaults flag
    if args.show_defaults:
        defaults = get_sensible_defaults()
        print("\n📋 Sensible Configuration Defaults")
        print("=" * 70)
        print("\nPreselection:")
        for key, value in defaults["preselection"].items():
            print(f"  --preselect-{key.replace('_', '-')}: {value}")
        print("\nMembership Policy:")
        for key, value in defaults["membership"].items():
            print(f"  --membership-{key.replace('_', '-')}: {value}")
        print("\nPoint-in-Time Eligibility:")
        for key, value in defaults["pit"].items():
            if key == "enabled":
                continue
            print(f"  --{key.replace('_', '-')}: {value}")
        print("\nCaching:")
        for key, value in defaults["cache"].items():
            if key == "enabled":
                continue
            print(f"  --cache-{key.replace('_', '-')}: {value}")
        print("\n" + "=" * 70)
        print("\nUse these values as starting points for your configuration.")
        print("Override with CLI flags or universe YAML configuration.\n")
        return 0

    try:
        # Set up output directory
        if args.output_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            args.output_dir = Path(f"results/backtest_{timestamp}")

        if args.verbose:
            pass

        # Load universe and configuration
        if args.verbose:
            pass
        assets, universe_config = load_universe(args.universe_file, args.universe_name)
        if args.verbose:
            pass

        # Apply PIT eligibility config from universe (if not set via CLI)
        apply_pit_config_from_universe(universe_config, args)

        # Validate configuration early (before expensive data loading)
        if args.verbose:
            print("Validating configuration...")
        validate_configuration(args, universe_config, len(assets))

        # Load data (optimized to only load required columns and date range)
        if args.verbose:
            pass
        prices, returns = load_data(
            args.prices_file,
            args.returns_file,
            assets,
            start_date=args.start_date,
            end_date=args.end_date,
        )
        if args.verbose:
            pass

        # Apply technical indicator filtering if enabled
        if args.enable_indicators:
            if args.verbose:
                print(
                    f"Applying technical indicator filtering (provider: {args.indicator_provider})...",
                )
            indicator_config = IndicatorConfig(
                enabled=True,
                provider=args.indicator_provider,
                params={},
            )
            provider = NoOpIndicatorProvider()
            filter_hook = FilterHook(indicator_config, provider)
            filtered_assets = filter_hook.filter_assets(prices, assets)

            if args.verbose:
                print(
                    f"  Assets after indicator filtering: {len(filtered_assets)} (from {len(assets)})",
                )

            # Reload data with filtered assets
            if filtered_assets != assets:
                prices, returns = load_data(
                    args.prices_file,
                    args.returns_file,
                    filtered_assets,
                    start_date=args.start_date,
                    end_date=args.end_date,
                )
                assets = filtered_assets

        # Create strategy
        if args.verbose:
            pass
        strategy = create_strategy(args.strategy)
        if args.verbose:
            pass

        # Parse rebalance frequency and trigger
        freq_map = {
            "daily": RebalanceFrequency.DAILY,
            "weekly": RebalanceFrequency.WEEKLY,
            "monthly": RebalanceFrequency.MONTHLY,
            "quarterly": RebalanceFrequency.QUARTERLY,
            "annual": RebalanceFrequency.ANNUAL,
        }

        # Create backtest configuration
        config = BacktestConfig(
            start_date=args.start_date,
            end_date=args.end_date,
            initial_capital=args.initial_capital,
            rebalance_frequency=freq_map[args.rebalance_frequency],
            rebalance_threshold=float(args.drift_threshold),
            commission_pct=float(args.commission),
            commission_min=float(args.min_commission),
            slippage_bps=float(args.slippage) * 10000,
            lookback_periods=args.lookback_periods,
            use_pit_eligibility=args.use_pit_eligibility,
            min_history_days=args.min_history_days,
            min_price_rows=args.min_price_rows,
        )

        # Create cache if enabled
        cache = None
        if args.enable_cache:
            from portfolio_management.data.factor_caching import FactorCache

            cache_dir = args.cache_dir if args.cache_dir else Path(".cache/backtest")
            cache = FactorCache(
                cache_dir=cache_dir,
                enabled=True,
                max_cache_age_days=args.cache_max_age_days,
            )
            if args.verbose:
                print(f"Caching enabled: {cache_dir}")
                if args.cache_max_age_days:
                    print(f"  Cache max age: {args.cache_max_age_days} days")

        # Create preselection from universe config or CLI args
        preselection = create_preselection_from_universe(
            universe_config,
            args,
            cache=cache,
        )
        if preselection and args.verbose:
            print(
                f"Preselection enabled: {preselection.config.method.value} "
                f"(top-{preselection.config.top_k})",
            )

        # Create membership policy from universe config or CLI args
        membership_policy = create_membership_policy_from_universe(
            universe_config,
            args,
        )
        if membership_policy and args.verbose:
            print(
                f"Membership policy enabled: buffer_rank={membership_policy.buffer_rank}, "
                f"min_hold={membership_policy.min_holding_periods}",
            )

        def _report_cache_stats(cache_obj: Any) -> None:
            print("\nCache Statistics:")  # noqa: T201
            cache_obj.print_stats()

        backtest_service = BacktestService(
            results_printer=print_results,
            results_saver=save_results,
            cache_reporter=_report_cache_stats,
        )
        backtest_service.run(
            BacktestRequest(
                config=config,
                strategy=strategy,
                prices=prices,
                returns=returns,
                preselection=preselection,
                membership_policy=membership_policy,
                cache=cache,
                output_dir=args.output_dir,
                save_trades=args.save_trades,
                visualize=not args.no_visualize,
                verbose=args.verbose,
            )
        )

        return 0

    except (
        BacktestError,
        InvalidBacktestConfigError,
        InsufficientHistoryError,
    ):
        if args.verbose:
            import traceback

            traceback.print_exc()
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
