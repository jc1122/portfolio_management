# ruff: noqa: E402
"""Portfolio construction command-line interface.

Usage examples:
    python scripts/construct_portfolio.py \
        --returns data/processed/universe_returns.csv \
        --strategy equal_weight \
        --output outputs/portfolio_equal_weight.csv

    python scripts/construct_portfolio.py \
        --returns data/processed/universe_returns.csv \
        --classifications data/processed/asset_classes.csv \
        --strategy mean_variance_max_sharpe \
        --max-equity 0.80 \
        --output outputs/portfolio_mv.csv

    python scripts/construct_portfolio.py \
        --returns data/processed/universe_returns.csv \
        --compare \
        --output outputs/portfolio_comparison.csv
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from collections.abc import Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from portfolio_management.core.exceptions import PortfolioConstructionError
from portfolio_management.portfolio import Portfolio
from portfolio_management.services import (
    PortfolioConstructionConfig,
    PortfolioConstructionService,
)

logger = logging.getLogger(__name__)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Construct and compare portfolio strategies.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Input/output paths
    parser.add_argument(
        "--returns",
        type=Path,
        required=True,
        help="Path to CSV containing asset returns (dates as index, tickers as columns).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to write the resulting weights (or comparison table when --compare is enabled).",
    )
    parser.add_argument(
        "--classifications",
        type=Path,
        help="Optional CSV with columns 'ticker' and 'asset_class' for constraint enforcement.",
    )

    # Strategy configuration
    parser.add_argument(
        "--strategy",
        type=str,
        default="equal_weight",
        help="Strategy name to construct (ignored when --compare is provided).",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare all registered strategies instead of constructing a single one.",
    )

    # Constraint knobs
    parser.add_argument(
        "--max-weight",
        type=float,
        default=0.25,
        help="Maximum allowable weight for any asset (default: 0.25).",
    )
    parser.add_argument(
        "--min-weight",
        type=float,
        default=0.0,
        help="Minimum allowable weight for any asset (default: 0.0).",
    )
    parser.add_argument(
        "--max-equity",
        type=float,
        default=0.90,
        help="Maximum total equity exposure (default: 0.90).",
    )
    parser.add_argument(
        "--min-bond",
        type=float,
        default=0.10,
        help="Minimum total bond/cash exposure (default: 0.10).",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging output.",
    )

    return parser.parse_args(argv)


def _configure_logging(*, verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def _save_portfolio(portfolio: Portfolio, output_path: Path) -> None:
    logger.info("Saving portfolio to %s", output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    weights_df = portfolio.weights.to_frame(name="weight")
    weights_df.to_csv(output_path)
    logger.info(
        "Saved %d holdings (top 3: %s)",
        portfolio.get_position_count(),
        portfolio.get_top_holdings(3).to_dict(),
    )


def _save_comparison(comparison: pd.DataFrame, output_path: Path) -> None:
    logger.info("Saving strategy comparison to %s", output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(output_path)
    logger.info("Saved comparison for %d strategies", len(comparison.columns))


def run_cli(args: argparse.Namespace) -> int:
    """Execute the CLI workflow and return an exit code."""
    _configure_logging(verbose=args.verbose)

    try:
        service = PortfolioConstructionService()
        config = PortfolioConstructionConfig(
            returns_path=args.returns,
            strategy=args.strategy,
            compare=args.compare,
            classifications_path=args.classifications,
            max_weight=args.max_weight,
            min_weight=args.min_weight,
            max_equity=args.max_equity,
            min_bond=args.min_bond,
        )
        result = service.run(config)

        if result.comparison is not None:
            logger.info(
                "Saving comparison for strategies: %s",
                ", ".join(result.strategies_used),
            )
            _save_comparison(result.comparison, args.output)
        elif result.portfolio is not None:
            logger.info("Constructed portfolio using strategy '%s'.", result.strategies_used[0])
            _save_portfolio(result.portfolio, args.output)
        else:  # pragma: no cover - defensive guard
            logger.error("Service returned neither portfolio nor comparison output.")
            return 3
    except PortfolioConstructionError:
        logger.exception("Portfolio construction error.")
        return 1
    except Exception:  # pragma: no cover - defensive guard
        logger.exception("Unexpected error during portfolio construction.")
        return 2

    logger.info("Portfolio construction completed successfully.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    args = parse_args(argv)
    return run_cli(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
