r"""Prepare tradeable instrument datasets from unpacked Stooq price files.

The script expects the unpacked Stooq directory tree (e.g., `data/stooq/d_pl_txt/...`)
and three CSV files describing the tradeable universes. It performs the following steps:

1. Scan the unpacked data tree to build an index of available price files.
2. Load and normalize the broker tradeable lists.
3. Match tradeable instruments to Stooq tickers using heuristic symbol mapping.
4. Export matched price histories and emit reports for matched/unmatched assets.

Example usage:
    python scripts/prepare_tradeable_data.py \
        --data-dir data/stooq \
        --metadata-output data/metadata/stooq_index.csv \
        --tradeable-dir tradeable_instruments \
        --match-report data/metadata/tradeable_matches.csv \
        --unmatched-report data/metadata/tradeable_unmatched.csv \
        --prices-output data/processed/tradeable_prices \
        --max-workers 8 \
        --overwrite-prices
"""

from __future__ import annotations

import argparse
import importlib.util
import logging
import os
import sys
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

from src.portfolio_management.analysis import (
    collect_available_extensions,
    infer_currency,
    log_summary_counts,
    resolve_currency,
    summarize_price_file,
)
from src.portfolio_management.io import (
    export_tradeable_prices,
    load_tradeable_instruments,
    read_stooq_index,
    write_match_report,
    write_stooq_index,
    write_unmatched_report,
)
from src.portfolio_management.matching import (
    annotate_unmatched_instruments,
    build_stooq_lookup,
    determine_unmatched_reason,
    match_tradeables,
)
from src.portfolio_management.models import (
    ExportConfig,
    StooqFile,
    TradeableInstrument,
    TradeableMatch,
)
from src.portfolio_management.stooq import build_stooq_index
from src.portfolio_management.utils import log_duration

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


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
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
    return parser.parse_args()


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


def _generate_reports(matches, unmatched, args, data_dir):
    with log_duration("tradeable_match_report"):
        (
            diagnostics_cache,
            currency_counts,
            data_status_counts,
            empty_tickers,
            flagged_samples,
        ) = write_match_report(
            matches,
            args.match_report,
            data_dir,
            lse_currency_policy=args.lse_currency_policy,
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
    return diagnostics_cache


def _export_prices(matches, args, diagnostics_cache, max_workers):
    with log_duration("tradeable_export"):
        config = ExportConfig(
            data_dir=args.data_dir,
            dest_dir=args.prices_output,
            overwrite=args.overwrite_prices,
            max_workers=max_workers,
            diagnostics=diagnostics_cache,
            include_empty=args.include_empty_prices,
        )
        export_tradeable_prices(matches, config)


def main() -> None:
    """Run the end-to-end tradeable data preparation workflow."""
    args = parse_args()
    configure_logging(args.log_level)

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

    stooq_index = _handle_stooq_index(args, index_workers)
    matches, unmatched = _load_and_match_tradeables(stooq_index, args, max_workers)
    diagnostics_cache = _generate_reports(matches, unmatched, args, data_dir)
    _export_prices(matches, args, diagnostics_cache, max_workers)


if __name__ == "__main__":
    main()
