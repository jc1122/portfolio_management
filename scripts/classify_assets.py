# ruff: noqa: E402
"""CLI script for asset classification.

This script provides a command-line interface for classifying assets from a
selected assets CSV file.

Example:
    python scripts/classify_assets.py \
        --input /tmp/selected_assets.csv \
        --output /tmp/classified_assets.csv \
        --summary

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

from portfolio_management.assets.classification import (
    AssetClassifier,
    ClassificationOverrides,
)
from portfolio_management.assets.selection import SelectedAsset
from portfolio_management.core.exceptions import PortfolioManagementError

LOW_CONFIDENCE_THRESHOLD = 0.6


def get_args() -> argparse.Namespace:
    """Parse and return command-line arguments."""
    parser = argparse.ArgumentParser(description="Asset Classification CLI")
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to the selected assets CSV file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path for the classified assets CSV. Prints to stdout if not specified.",
    )
    parser.add_argument(
        "--overrides",
        type=Path,
        default=None,
        help="Path to a CSV file with classification overrides.",
    )
    parser.add_argument(
        "--export-for-review",
        type=Path,
        default=None,
        help="Export a template for manual review.",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print a summary of the classification results.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable detailed logging.",
    )
    return parser.parse_args()


def main() -> None:
    """Run the asset classification CLI."""
    args = get_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    try:
        selected_assets_df = pd.read_csv(args.input)
        assets = [SelectedAsset(**row) for row in selected_assets_df.to_dict("records")]

        overrides = (
            ClassificationOverrides.from_csv(args.overrides) if args.overrides else None
        )

        classifier = AssetClassifier(overrides=overrides)
        classified_df = classifier.classify_universe(assets)

        if args.export_for_review:
            classifier.export_for_review(
                classified_df.to_dict("records"),
                args.export_for_review,
            )
            logging.info(
                "Exported classification review template to %s",
                args.export_for_review,
            )

        if args.summary:
            print("--- Classification Summary ---")  # noqa: T201
            print("\nAsset Class Breakdown:")  # noqa: T201
            print(classified_df["asset_class"].value_counts())  # noqa: T201
            print("\nGeography Breakdown:")  # noqa: T201
            print(classified_df["geography"].value_counts())  # noqa: T201
            low_confidence = classified_df[
                classified_df["confidence"] < LOW_CONFIDENCE_THRESHOLD
            ]
            if not low_confidence.empty:
                print(  # noqa: T201
                    f"\n{len(low_confidence)} Assets with low confidence:",
                )
                print(  # noqa: T201
                    low_confidence[["symbol", "name", "asset_class", "confidence"]],
                )

        if args.output:
            classified_df.to_csv(args.output, index=False)
            logging.info("Classified assets saved to %s", args.output)
        elif not args.summary:
            print(classified_df.to_string())  # noqa: T201

    except PortfolioManagementError:
        logging.exception("Asset classification failed")
        sys.exit(1)
    except Exception:
        logging.exception("An unexpected error occurred")
        sys.exit(1)


if __name__ == "__main__":
    main()
