"""Prepare tradeable instrument datasets from unpacked Stooq price files."""

from __future__ import annotations

import argparse
import importlib.util
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

if (
    importlib.util.find_spec("pandas") is None
):  # pragma: no cover - runtime dependency check
    raise ImportError(
        "pandas is required to run prepare_tradeable_data.py. "
        "Please install pandas before executing this script.",
    )

LOGGER = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from portfolio_management.services import DataPreparationConfig, DataPreparationService

__all__ = [
    "build_parser",
    "parse_args",
    "configure_logging",
    "prepare_tradeable_data",
    "run_cli",
    "main",
]


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(description="Prepare tradeable Stooq datasets.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/stooq"),
        help="Root directory containing unpacked Stooq data.",
    )
    parser.add_argument(
        "--metadata-output",
        type=Path,
        default=Path("data/metadata/stooq_index.csv"),
        help="Path to write the Stooq metadata index CSV.",
    )
    parser.add_argument(
        "--force-reindex",
        action="store_true",
        help="Rebuild the Stooq metadata index even if the CSV already exists.",
    )
    parser.add_argument(
        "--tradeable-dir",
        type=Path,
        default=Path("tradeable_instruments"),
        help="Directory containing tradeable instrument CSV files.",
    )
    parser.add_argument(
        "--match-report",
        type=Path,
        default=Path("data/metadata/tradeable_matches.csv"),
        help="Output CSV for matched tradeable instruments.",
    )
    parser.add_argument(
        "--unmatched-report",
        type=Path,
        default=Path("data/metadata/tradeable_unmatched.csv"),
        help="Output CSV listing unmatched instruments.",
    )
    parser.add_argument(
        "--prices-output",
        type=Path,
        default=Path("data/processed/tradeable_prices"),
        help="Directory for exported tradeable price histories.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity.",
    )
    parser.add_argument(
        "--overwrite-prices",
        action="store_true",
        help="Rewrite price CSVs even if they already exist.",
    )
    parser.add_argument(
        "--include-empty-prices",
        action="store_true",
        help="Export price CSVs even when the source file lacks usable data.",
    )
    parser.add_argument(
        "--lse-currency-policy",
        choices=["broker", "stooq", "strict"],
        default="broker",
        help="How to resolve LSE currency mismatches: keep broker currency (default), "
        "force Stooq inferred currency, or treat overrides as errors.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Maximum number of threads to use for matching and exporting (auto if unset).",
    )
    parser.add_argument(
        "--index-workers",
        type=int,
        default=0,
        help="Number of threads for directory indexing (0 falls back to --max-workers).",
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Enable incremental resume: skip processing if inputs unchanged and outputs exist.",
    )
    parser.add_argument(
        "--cache-metadata",
        type=Path,
        default=Path("data/metadata/.prepare_cache.json"),
        help="Path to cache metadata file for incremental resume.",
    )
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    return build_parser().parse_args(argv)


def configure_logging(level: str) -> None:
    """Configure module-wide logging based on a string log level value."""
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )


def _build_config(args: argparse.Namespace) -> DataPreparationConfig:
    return DataPreparationConfig(
        data_dir=args.data_dir,
        metadata_output=args.metadata_output,
        tradeable_dir=args.tradeable_dir,
        match_report=args.match_report,
        unmatched_report=args.unmatched_report,
        prices_output=args.prices_output,
        force_reindex=args.force_reindex,
        overwrite_prices=args.overwrite_prices,
        include_empty_prices=args.include_empty_prices,
        lse_currency_policy=args.lse_currency_policy,
        max_workers=args.max_workers,
        index_workers=args.index_workers if args.index_workers else None,
        incremental=args.incremental,
        cache_metadata=args.cache_metadata if args.incremental else None,
    )


def prepare_tradeable_data(args: argparse.Namespace) -> None:
    """Run the end-to-end tradeable data preparation workflow."""
    config = _build_config(args)
    service = DataPreparationService(logger=LOGGER)
    result = service.prepare(config)
    if result.skipped:
        LOGGER.info(
            "Incremental resume: inputs unchanged and outputs exist - skipping processing",
        )
    else:
        LOGGER.info(
            "Tradeable data preparation complete. Reports: match=%s unmatched=%s",
            result.match_report_path,
            result.unmatched_report_path,
        )


def run_cli(args: argparse.Namespace) -> int:
    """Execute the CLI workflow with logging and error handling."""
    configure_logging(args.log_level)
    try:
        prepare_tradeable_data(args)
    except Exception:  # pragma: no cover - defensive
        LOGGER.exception("Tradeable data preparation failed")
        return 1
    return 0


def main(argv: Sequence[str] | None = None) -> None:
    """CLI entry point."""
    args = parse_args(argv)
    sys.exit(run_cli(args))


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
