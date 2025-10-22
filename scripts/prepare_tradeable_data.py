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

from portfolio_management.core.utils import log_duration
from portfolio_management.data import cache
from portfolio_management.data.analysis import (
    collect_available_extensions,
    infer_currency,
    log_summary_counts,
    resolve_currency,
    summarize_price_file,
)
from portfolio_management.data.ingestion import build_stooq_index
from portfolio_management.data.io import (
    export_tradeable_prices,
    load_tradeable_instruments,
    read_stooq_index,
    write_match_report,
    write_stooq_index,
    write_unmatched_report,
)
from portfolio_management.data.matching import (
    annotate_unmatched_instruments,
    build_stooq_lookup,
    determine_unmatched_reason,
    match_tradeables,
)
from portfolio_management.data.models import (
    ExportConfig,
    StooqFile,
    TradeableInstrument,
    TradeableMatch,
)

__all__ = [
    "ExportConfig",
    "StooqFile",
    "TradeableInstrument",
    "TradeableMatch",
    "annotate_unmatched_instruments",
    "build_stooq_lookup",
    "collect_available_extensions",
    "determine_unmatched_reason",
    "export_tradeable_prices",
    "infer_currency",
    "load_tradeable_instruments",
    "log_summary_counts",
    "match_tradeables",
    "read_stooq_index",
    "resolve_currency",
    "summarize_price_file",
    "write_match_report",
    "write_stooq_index",
    "write_unmatched_report",
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


def _handle_stooq_index(args, index_workers):
    if args.metadata_output.exists() and not args.force_reindex:
        with log_duration("stooq_index_load"):
            stooq_index = read_stooq_index(args.metadata_output)
    else:
        with log_duration("stooq_index_build"):
            stooq_index = build_stooq_index(args.data_dir, max_workers=index_workers)
        with log_duration("stooq_index_write"):
            write_stooq_index(stooq_index, args.metadata_output)
    return stooq_index


def _load_and_match_tradeables(stooq_index, args, max_workers):
    with log_duration("tradeable_load"):
        tradeables = load_tradeable_instruments(args.tradeable_dir)

    stooq_by_ticker, stooq_by_stem, stooq_by_base = build_stooq_lookup(stooq_index)
    available_extensions = collect_available_extensions(stooq_index)
    with log_duration("tradeable_match"):
        matches, unmatched = match_tradeables(
            tradeables,
            stooq_by_ticker,
            stooq_by_stem,
            stooq_by_base,
            max_workers=max_workers,
        )
    unmatched = annotate_unmatched_instruments(
        unmatched,
        stooq_by_base,
        available_extensions,
    )
    return matches, unmatched


def _generate_reports(matches, unmatched, args, data_dir, max_workers):
    export_config = ExportConfig(
        data_dir=args.data_dir,
        dest_dir=args.prices_output,
        overwrite=args.overwrite_prices,
        max_workers=max_workers,
        include_empty=args.include_empty_prices,
    )
    export_config.dest_dir.mkdir(parents=True, exist_ok=True)
    with log_duration("tradeable_match_report"):
        (
            diagnostics_cache,
            currency_counts,
            data_status_counts,
            empty_tickers,
            flagged_samples,
            exported_count,
            skipped_count,
        ) = write_match_report(
            matches,
            args.match_report,
            data_dir,
            lse_currency_policy=args.lse_currency_policy,
            max_workers=max_workers,
            export_config=export_config,
        )
    log_summary_counts(currency_counts, data_status_counts)
    if empty_tickers:
        sample = ", ".join(sorted(empty_tickers)[:5])
        LOGGER.warning(
            "Detected %s empty Stooq price files (e.g., %s)",
            len(empty_tickers),
            sample,
        )
    if flagged_samples:
        preview = ", ".join(
            f"{symbol}->{ticker} [{flags}]"
            for symbol, ticker, flags in flagged_samples[:5]
        )
        LOGGER.warning(
            "Detected validation flags for %s matched instruments (e.g., %s)",
            len(flagged_samples),
            preview,
        )
    with log_duration("tradeable_unmatched_report"):
        write_unmatched_report(unmatched, args.unmatched_report)
    LOGGER.info("Exported %s price files to %s", exported_count, export_config.dest_dir)
    if skipped_count:
        LOGGER.warning("Skipped %s price files without usable data", skipped_count)
    return diagnostics_cache


def prepare_tradeable_data(args: argparse.Namespace) -> None:
    """Run the end-to-end tradeable data preparation workflow."""
    data_dir = args.data_dir
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

    # Check for incremental resume opportunity
    if args.incremental:
        cache_metadata = cache.load_cache_metadata(args.cache_metadata)
        
        # Check if we can skip processing
        if (
            cache.inputs_unchanged(
                args.tradeable_dir,
                args.metadata_output,
                cache_metadata,
            )
            and cache.outputs_exist(args.match_report, args.unmatched_report)
        ):
            LOGGER.info(
                "Incremental resume: inputs unchanged and outputs exist - skipping processing"
            )
            LOGGER.info("Match report: %s", args.match_report)
            LOGGER.info("Unmatched report: %s", args.unmatched_report)
            LOGGER.info(
                "To force full rebuild, use --force-reindex or omit --incremental"
            )
            return
        
        LOGGER.info("Incremental resume: inputs changed or outputs missing - running full pipeline")

    stooq_index = _handle_stooq_index(args, index_workers)
    matches, unmatched = _load_and_match_tradeables(stooq_index, args, max_workers)
    _generate_reports(matches, unmatched, args, data_dir, max_workers)
    
    # Save cache metadata for next run if incremental mode enabled
    if args.incremental:
        new_cache_metadata = cache.create_cache_metadata(
            args.tradeable_dir,
            args.metadata_output,
        )
        cache.save_cache_metadata(args.cache_metadata, new_cache_metadata)
        LOGGER.debug("Saved cache metadata for future incremental resumes")


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
