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
from portfolio_management.core.exceptions import PortfolioManagementError


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
    return parser.parse_args()


def main() -> None:
    """Run the asset selection CLI."""
    args = get_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    try:
        matches_df = pd.read_csv(args.match_report)

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
