r"""Prepare tradeable instrument datasets from unpacked Stooq price files.

The script expects the unpacked Stooq directory tree (e.g., `data/stooq/d_pl_txt/...`)
and three CSV files describing the tradeable universes. It performs the following steps:

1. Scan the unpacked data tree to build an index of available price files.
2. Load and normalize the broker tradeable lists.
3. Match tradeable instruments to Stooq tickers using heuristic symbol mapping.
4. Export matched price histories and emit reports for matched/unmatched assets.

Incremental Resume Feature:
    The --incremental flag enables smart caching to skip redundant processing when
    inputs haven't changed. The script tracks:
    - Stooq index file hash
    - Tradeable CSV directory hash (file names and modification times)

    When both inputs are unchanged and output files exist, processing is skipped
    entirely, completing in seconds instead of minutes. Use --force-reindex to
    override the cache.

Example usage:
    # First run - builds everything
    python scripts/prepare_tradeable_data.py \
        --data-dir data/stooq \
        --metadata-output data/metadata/stooq_index.csv \
        --tradeable-dir tradeable_instruments \
        --match-report data/metadata/tradeable_matches.csv \
        --unmatched-report data/metadata/tradeable_unmatched.csv \
        --prices-output data/processed/tradeable_prices \
        --max-workers 8 \
        --incremental

    # Second run - skips if unchanged (completes in seconds)
    python scripts/prepare_tradeable_data.py \
        --incremental

    # Force full rebuild
    python scripts/prepare_tradeable_data.py \
        --force-reindex
"""

from __future__ import annotations

import argparse
import importlib.util
import logging
import os
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

from portfolio_management.data.analysis import log_summary_counts
from portfolio_management.services import DataPreparationService


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
def prepare_tradeable_data(args: argparse.Namespace) -> None:
    """Run the end-to-end tradeable data preparation workflow."""
    cpu_count = os.cpu_count() or 1
    auto_workers = max(1, (cpu_count - 1) or 1)
    max_workers = (
        args.max_workers if args.max_workers and args.max_workers > 0 else auto_workers
    )
    max_workers = max(1, max_workers)
    index_workers = (
        args.index_workers
        if args.index_workers and args.index_workers > 0
        else max_workers
    )
    index_workers = max(1, index_workers)
    LOGGER.info(
        "Worker configuration: match/export=%s, index=%s (cpu=%s)",
        max_workers,
        index_workers,
        cpu_count,
    )

    service = DataPreparationService()

    result = service.prepare_tradeable_data(
        data_dir=args.data_dir,
        tradeable_dir=args.tradeable_dir,
        metadata_output=args.metadata_output,
        match_report_path=args.match_report,
        unmatched_report_path=args.unmatched_report,
        prices_output_dir=args.prices_output,
        overwrite_prices=args.overwrite_prices,
        include_empty_prices=args.include_empty_prices,
        lse_currency_policy=args.lse_currency_policy,
        incremental=args.incremental,
        cache_metadata_path=args.cache_metadata,
        force_reindex=args.force_reindex,
        max_workers=max_workers,
        index_workers=index_workers,
    )

    if result.skipped:
        LOGGER.info(
            "Incremental resume: inputs unchanged and outputs exist - skipping processing",
        )
        LOGGER.info("Match report: %s", result.match_report_path)
        LOGGER.info("Unmatched report: %s", result.unmatched_report_path)
        LOGGER.info(
            "To force full rebuild, use --force-reindex or omit --incremental",
        )
        return

    log_summary_counts(result.currency_counts, result.data_status_counts)
    if result.empty_tickers:
        sample = ", ".join(sorted(result.empty_tickers)[:5])
        LOGGER.warning(
            "Detected %s empty Stooq price files (e.g., %s)",
            len(result.empty_tickers),
            sample,
        )
    if result.flagged_samples:
        preview = ", ".join(
            f"{symbol}->{ticker} [{flags}]"
            for symbol, ticker, flags in result.flagged_samples[:5]
        )
        LOGGER.warning(
            "Detected validation flags for %s matched instruments (e.g., %s)",
            len(result.flagged_samples),
            preview,
        )
    LOGGER.info(
        "Exported %s price files to %s",
        result.exported_count,
        args.prices_output,
    )
    if result.skipped_count:
        LOGGER.warning("Skipped %s price files without usable data", result.skipped_count)


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
