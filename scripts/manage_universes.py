# ruff: noqa: E402
"""CLI script for universe management.

This script provides a command-line interface for managing investment universes.

Example:
    python scripts/manage_universes.py list
    python scripts/manage_universes.py show core_global

"""

import argparse
import logging
import sys
import tempfile
from pathlib import Path

import pandas as pd

# Add project root to path to allow imports from src
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from portfolio_management.assets.universes import UniverseConfigLoader, UniverseManager
from portfolio_management.core.exceptions import PortfolioManagementError


def get_args() -> argparse.Namespace:
    """Parse and return command-line arguments."""
    parser = argparse.ArgumentParser(description="Universe Management CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # List command
    subparsers.add_parser("list", help="List available universes.")

    # Show command
    parser_show = subparsers.add_parser("show", help="Show details for a universe.")
    parser_show.add_argument("name", type=str, help="Name of the universe.")

    # Load command
    parser_load = subparsers.add_parser("load", help="Load and export a universe.")
    parser_load.add_argument("name", type=str, help="Name of the universe.")
    parser_load.add_argument(
        "--output-dir",
        type=Path,
        default=Path(tempfile.gettempdir()),
        help="Output directory.",
    )

    # Compare command
    parser_compare = subparsers.add_parser("compare", help="Compare universes.")
    parser_compare.add_argument(
        "names",
        type=str,
        nargs="+",
        help="Names of the universes to compare.",
    )

    # Validate command
    parser_validate = subparsers.add_parser("validate", help="Validate a universe.")
    parser_validate.add_argument("name", type=str, help="Name of the universe.")

    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/universes.yaml"),
        help="Path to the universe config file.",
    )
    parser.add_argument(
        "--matches",
        type=Path,
        default=Path("data/metadata/tradeable_matches.csv"),
        help="Path to the tradeable matches CSV file.",
    )
    parser.add_argument(
        "--prices-dir",
        type=Path,
        default=Path("data/processed/tradeable_prices"),
        help="Directory with price files.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable detailed logging.",
    )
    return parser.parse_args()


def main() -> None:
    """Run the universe management CLI."""
    args = get_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    try:
        # For lightweight commands, only load the config
        if args.command in ("list", "show"):
            universes = UniverseConfigLoader.load_config(args.config)

            if args.command == "list":
                print("Available universes:")  # noqa: T201
                for name in universes:
                    print(f"- {name}")  # noqa: T201

            elif args.command == "show":
                if args.name not in universes:
                    logging.error(
                        "Universe '%s' not found in configuration.",
                        args.name,
                    )
                    sys.exit(1)
                definition = universes[args.name]
                print(f"--- Universe: {args.name} ---")  # noqa: T201
                print(definition)  # noqa: T201

        # For heavy commands, load the full manager with data
        else:
            matches_df = pd.read_csv(args.matches)
            manager = UniverseManager(args.config, matches_df, args.prices_dir)

            if args.command == "load":
                universe = manager.load_universe(args.name)
                if universe:
                    for key, df in universe.items():
                        if isinstance(df, pd.DataFrame):
                            df.to_csv(
                                args.output_dir / f"{args.name}_{key}.csv",
                                index=False,
                            )
                    print(  # noqa: T201
                        f"Universe '{args.name}' loaded and exported to {args.output_dir}",
                    )

            elif args.command == "compare":
                comparison_df = manager.compare_universes(args.names)
                print(comparison_df.to_string())  # noqa: T201

            elif args.command == "validate":
                result = manager.validate_universe(args.name)
                print(result)  # noqa: T201

    except PortfolioManagementError:
        logging.exception("Universe management failed")
        sys.exit(1)
    except Exception:
        logging.exception("An unexpected error occurred")
        sys.exit(1)


if __name__ == "__main__":
    main()
