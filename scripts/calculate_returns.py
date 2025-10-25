# ruff: noqa: E402
"""Command-line interface for the return preparation pipeline."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

import pandas as pd

# Add project root to path to allow imports from src
REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from portfolio_management.analytics.returns import ReturnCalculator, ReturnConfig
from portfolio_management.analytics.returns.loaders import PriceLoader
from portfolio_management.assets.selection import SelectedAsset
from portfolio_management.core.exceptions import PortfolioManagementError


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Prepare aligned return series for selected assets",
    )
    parser.add_argument(
        "--assets",
        type=Path,
        required=True,
        help="Path to selected assets CSV file",
    )
    parser.add_argument(
        "--prices-dir",
        type=Path,
        required=True,
        help="Directory containing price files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Destination CSV for prepared returns",
    )
    parser.add_argument(
        "--method",
        choices=["simple", "log", "excess"],
        default="simple",
        help="Return calculation method",
    )
    parser.add_argument(
        "--frequency",
        choices=["daily", "weekly", "monthly"],
        default="daily",
        help="Frequency for the prepared returns",
    )
    parser.add_argument(
        "--risk-free-rate",
        type=float,
        default=0.0,
        help="Annual risk-free rate used for excess returns",
    )
    parser.add_argument(
        "--handle-missing",
        choices=["forward_fill", "drop", "interpolate"],
        default="forward_fill",
        help="Missing data strategy",
    )
    parser.add_argument(
        "--max-forward-fill",
        type=int,
        default=5,
        help="Maximum consecutive days to forward-fill or interpolate",
    )
    parser.add_argument(
        "--min-periods",
        type=int,
        default=2,
        help="Minimum number of price observations required per asset",
    )
    parser.add_argument(
        "--loader-workers",
        type=int,
        default=None,
        help="Maximum worker threads for price loading (default: auto)",
    )
    parser.add_argument(
        "--cache-size",
        type=int,
        default=1000,
        help="Maximum number of price series to cache (default: 1000, 0 to disable)",
    )
    parser.add_argument(
        "--io-backend",
        choices=["pandas", "polars", "pyarrow", "auto"],
        default="pandas",
        help="IO backend for CSV reading (default: pandas). "
        "Options: pandas (default), polars (fast), pyarrow (fast), auto (select best available)",
    )
    parser.add_argument(
        "--align-method",
        choices=["outer", "inner"],
        default="outer",
        help="How to align return date indexes before resampling",
    )
    parser.add_argument(
        "--business-days",
        action="store_true",
        help="Reindex returns to the business-day calendar before coverage filtering",
    )
    parser.add_argument(
        "--min-coverage",
        type=float,
        default=0.8,
        help="Minimum proportion of non-NaN returns required per asset",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print a textual summary instead of raw returns",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        help="Number of top/bottom assets to display in the summary",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser


def parse_args(
    argv: Sequence[str] | None = None,
) -> argparse.Namespace:
    """Parse command-line arguments."""
    return build_parser().parse_args(argv)


def _load_assets(csv_path: Path) -> list[SelectedAsset]:
    if not csv_path.exists():
        raise FileNotFoundError(f"Assets file not found: {csv_path}")

    assets_df = pd.read_csv(csv_path, keep_default_na=False)
    if "price_rows" in assets_df.columns:
        assets_df["price_rows"] = (
            pd.to_numeric(
                assets_df["price_rows"],
                errors="coerce",
            )
            .fillna(0)
            .astype(int)
        )

    records = assets_df.to_dict("records")
    return [SelectedAsset(**record) for record in records]


def _build_config(args: argparse.Namespace) -> ReturnConfig:
    return ReturnConfig(
        method=args.method,
        frequency=args.frequency,
        risk_free_rate=args.risk_free_rate,
        handle_missing=args.handle_missing,
        max_forward_fill_days=args.max_forward_fill,
        min_periods=args.min_periods,
        align_method=args.align_method,
        reindex_to_business_days=args.business_days,
        min_coverage=args.min_coverage,
    )


def _print_summary(
    returns_df: pd.DataFrame,
    calculator: ReturnCalculator,
    top: int,
) -> None:
    print("--- Return Statistics Summary ---")  # noqa: T201
    print(f"Assets with returns: {returns_df.shape[1]}")  # noqa: T201

    if returns_df.empty:
        print("No return series available; check filtering criteria.")  # noqa: T201
        return

    print(  # noqa: T201
        f"Date range: {returns_df.index.min().date()} to {returns_df.index.max().date()}",
    )

    detailed = calculator.latest_summary
    if not detailed:
        print("Summary statistics unavailable.")  # noqa: T201
        return

    mean_sorted = detailed.mean_returns.sort_values(ascending=False)
    print("\nTop mean returns (annualised):")  # noqa: T201
    print(  # noqa: T201
        mean_sorted.head(top).to_string(float_format=lambda v: f"{v:.2%}"),
    )

    bottom = mean_sorted.tail(top)
    if len(bottom) > 0:
        print("\nBottom mean returns (annualised):")  # noqa: T201
        print(bottom.to_string(float_format=lambda v: f"{v:.2%}"))  # noqa: T201

    print("\nVolatility (annualised):")  # noqa: T201
    print(  # noqa: T201
        detailed.volatility.to_string(float_format=lambda v: f"{v:.2%}"),
    )

    print("\nData coverage (% of periods with data):")  # noqa: T201
    print((detailed.coverage * 100).round(2).to_string())  # noqa: T201

    if detailed.correlation.shape[1] <= top:
        print("\nCorrelation matrix:")  # noqa: T201
        print(detailed.correlation.round(3).to_string())  # noqa: T201


def run_cli(args: argparse.Namespace) -> int:
    """Execute the CLI command. Returns 0 for success, non-zero for failure."""
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    try:
        assets = _load_assets(args.assets)
    except Exception:  # pragma: no cover - defensive
        logging.exception("Failed to load assets")
        return 1

    if not assets:
        logging.error("Assets file %s is empty", args.assets)
        return 1

    if not args.prices_dir.exists():
        logging.error("Prices directory not found: %s", args.prices_dir)
        return 1

    config = _build_config(args)

    price_loader = PriceLoader(
        max_workers=args.loader_workers,
        io_backend=args.io_backend,
        cache_size=args.cache_size,
    )
    calculator = ReturnCalculator(price_loader=price_loader)
    try:
        returns_df = calculator.load_and_prepare(assets, args.prices_dir, config)
    except PortfolioManagementError:
        logging.exception("Return calculation failed")
        return 1

    if returns_df.empty:
        logging.error("Return preparation produced no data.")
        return 1

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        calculator.export_returns(returns_df, args.output)
        logging.info("Returns saved to %s", args.output)

    if args.summary:
        _print_summary(returns_df, calculator, args.top)
    else:
        print(returns_df.to_string())  # noqa: T201

    return 0


def main(argv: Sequence[str] | None = None) -> None:
    """Parse arguments and execute the returns CLI."""
    args = parse_args(argv)
    sys.exit(run_cli(args))


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
