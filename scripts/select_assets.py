# ruff: noqa: E402
"""CLI script for asset selection.

This script provides a command-line interface for filtering and selecting assets
from a tradeable matches report based on specified criteria.

Example:
    python scripts/select_assets.py \
        --match-report data/metadata/tradeable_matches.csv \
        --output /tmp/selected_assets.csv \
        --min-history-days 365 \
        --markets UK,US

"""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

# Add project root to path to allow imports from src
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from portfolio_management.assets.selection import AssetSelector, FilterCriteria
from portfolio_management.core.exceptions import (
    AssetSelectionError,
    PortfolioManagementError,
)


def process_chunked(
    match_report_path: Path,
    criteria: FilterCriteria,
    chunk_size: int,
) -> list:
    """Process match report in chunks to reduce memory usage.

    Args:
        match_report_path: Path to the CSV file.
        criteria: Filtering criteria including allowlist/blocklist.
        chunk_size: Number of rows to process at a time.

    Returns:
        List of selected assets from all chunks.

    Raises:
        AssetSelectionError: If allowlist items are not found.

    """
    selector = AssetSelector()
    all_selected = []
    found_allowlist_items = set()

    logger = logging.getLogger(__name__)
    chunk_num = 0

    # Track which allowlist items we need to find
    required_allowlist = criteria.allowlist.copy() if criteria.allowlist else None

    logger.info(
        "Starting chunked processing with chunk_size=%s from %s",
        chunk_size,
        match_report_path,
    )

    # Read and process CSV in chunks
    for chunk_df in pd.read_csv(match_report_path, chunksize=chunk_size):
        chunk_num += 1
        logger.debug("Processing chunk %s with %s rows", chunk_num, len(chunk_df))

        # Process this chunk through the selector
        # Note: When using allowlist in chunked mode, we need to handle chunks
        # that don't contain any allowlist items (AssetSelectionError)
        try:
            selected_assets = selector.select_assets(chunk_df, criteria)
        except AssetSelectionError as e:
            # If this chunk had no matching allowlist items, that's OK in chunked mode
            # We'll validate the complete allowlist at the end
            if required_allowlist and "No assets matched the provided allowlist" in str(
                e,
            ):
                logger.debug(
                    "Chunk %s contained no allowlist items (expected in streaming mode)",
                    chunk_num,
                )
                selected_assets = []
            else:
                # Re-raise other AssetSelectionError cases
                raise

        # Track found allowlist items
        if required_allowlist:
            for asset in selected_assets:
                if asset.symbol in required_allowlist or asset.isin in required_allowlist:
                    found_allowlist_items.add(asset.symbol)
                    found_allowlist_items.add(asset.isin)

        all_selected.extend(selected_assets)

        logger.debug(
            "Chunk %s yielded %s selected assets (total so far: %s)",
            chunk_num,
            len(selected_assets),
            len(all_selected),
        )

    logger.info(
        "Chunked processing complete. Processed %s chunks, selected %s total assets.",
        chunk_num,
        len(all_selected),
    )

    # Validate allowlist: ensure all required items were found
    if required_allowlist:
        missing_items = required_allowlist - found_allowlist_items
        if missing_items:
            msg = (
                f"Allowlist items not found in any chunk: {missing_items}. "
                f"These symbols/ISINs may not exist in the match report or were "
                f"filtered out by other criteria."
            )
            raise AssetSelectionError(msg)

    return all_selected


def get_args() -> argparse.Namespace:
    """Parse and return command-line arguments."""
    parser = argparse.ArgumentParser(description="Asset Selection CLI")
    parser.add_argument(
        "--match-report",
        type=Path,
        required=True,
        help="Path to the tradeable matches CSV file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path for the selected assets CSV. Prints to stdout if not specified.",
    )
    parser.add_argument(
        "--data-status",
        type=str,
        default="ok",
        help='Comma-separated list of acceptable data statuses (e.g., "ok,warning").',
    )
    parser.add_argument(
        "--min-history-days",
        type=int,
        default=252,
        help="Minimum required days of price history.",
    )
    parser.add_argument(
        "--min-price-rows",
        type=int,
        default=252,
        help="Minimum required number of price rows.",
    )
    parser.add_argument(
        "--max-gap-days",
        type=int,
        default=10,
        help="Maximum allowed gap in days between consecutive prices.",
    )
    parser.add_argument(
        "--severity",
        type=str,
        default=None,
        help="Comma-separated list of zero-volume severity levels to include.",
    )
    parser.add_argument(
        "--markets",
        type=str,
        default=None,
        help="Comma-separated list of markets to include.",
    )
    parser.add_argument(
        "--regions",
        type=str,
        default=None,
        help="Comma-separated list of regions to include.",
    )
    parser.add_argument(
        "--currencies",
        type=str,
        default=None,
        help="Comma-separated list of currencies to include.",
    )
    parser.add_argument(
        "--allowlist",
        type=Path,
        default=None,
        help="Path to a file with symbols/ISINs to allow (one per line).",
    )
    parser.add_argument(
        "--blocklist",
        type=Path,
        default=None,
        help="Path to a file with symbols/ISINs to block (one per line).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable detailed logging.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be selected without performing the action.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=None,
        help="Enable streaming mode with specified chunk size (e.g., 5000). "
        "If not specified, loads entire file into memory (default behavior).",
    )
    return parser.parse_args()


def main() -> None:
    """Run the asset selection CLI."""
    args = get_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    try:
        # Load allowlist and blocklist if provided
        allowlist = (
            set(args.allowlist.read_text().splitlines()) if args.allowlist else None
        )
        blocklist = (
            set(args.blocklist.read_text().splitlines()) if args.blocklist else None
        )

        criteria = FilterCriteria(
            data_status=args.data_status.split(","),
            min_history_days=args.min_history_days,
            min_price_rows=args.min_price_rows,
            max_gap_days=args.max_gap_days,
            zero_volume_severity=args.severity.split(",") if args.severity else None,
            markets=args.markets.split(",") if args.markets else None,
            regions=args.regions.split(",") if args.regions else None,
            currencies=args.currencies.split(",") if args.currencies else None,
            allowlist=allowlist,
            blocklist=blocklist,
        )

        # Choose between chunked and eager loading based on --chunk-size
        if args.chunk_size is not None:
            if args.chunk_size <= 0:
                logging.error("--chunk-size must be a positive integer")
                sys.exit(1)

            logging.info("Using streaming mode with chunk_size=%s", args.chunk_size)
            selected_assets = process_chunked(
                args.match_report,
                criteria,
                args.chunk_size,
            )
        else:
            # Eager loading: original behavior
            logging.info("Using eager loading (entire file in memory)")
            matches_df = pd.read_csv(args.match_report)

            selector = AssetSelector()
            selected_assets = selector.select_assets(matches_df, criteria)

        selected_df = pd.DataFrame([asset.__dict__ for asset in selected_assets])

        if args.dry_run:
            print("--- DRY RUN ---")  # noqa: T201
            print(f"Would select {len(selected_df)} assets.")  # noqa: T201
            if not selected_df.empty:
                print("\n--- Summary ---")  # noqa: T201
                print(f"Total selected: {len(selected_df)}")  # noqa: T201
                print("\nBreakdown by market:")  # noqa: T201
                print(selected_df["market"].value_counts())  # noqa: T201
                print("\nBreakdown by region:")  # noqa: T201
                print(selected_df["region"].value_counts())  # noqa: T201
            return

        if args.output:
            selected_df.to_csv(args.output, index=False)
            logging.info("Selected assets saved to %s", args.output)
        else:
            print(selected_df.to_string())  # noqa: T201

    except PortfolioManagementError:
        logging.exception("Asset selection failed")
        sys.exit(1)
    except Exception:
        logging.exception("An unexpected error occurred")
        sys.exit(1)


if __name__ == "__main__":
    main()
