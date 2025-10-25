"""CLI script for universe management."""

import argparse
import logging
import sys
import tempfile
from pathlib import Path

# Add project root to path to allow imports from src
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from portfolio_management.core.exceptions import PortfolioManagementError
from portfolio_management.services import UniverseManagementService


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

    service = UniverseManagementService()

    try:
        if args.command in ("list", "show"):
            universes = service.list_universes(args.config)

            if args.command == "list":
                print("Available universes:")  # noqa: T201
                for name in universes.names:
                    print(f"- {name}")  # noqa: T201

            elif args.command == "show":
                definition = service.show_universe(args.config, args.name)
                print(f"--- Universe: {args.name} ---")  # noqa: T201
                print(definition)  # noqa: T201

        else:
            if args.command == "load":
                service.load_universe(
                    args.config,
                    args.matches,
                    args.prices_dir,
                    args.name,
                    output_dir=args.output_dir,
                )
                print(  # noqa: T201
                    f"Universe '{args.name}' loaded and exported to {args.output_dir}",
                )

            elif args.command == "compare":
                comparison = service.compare_universes(
                    args.config,
                    args.matches,
                    args.prices_dir,
                    args.names,
                )
                print(comparison.table.to_string())  # noqa: T201

            elif args.command == "validate":
                result = service.validate_universe(
                    args.config,
                    args.matches,
                    args.prices_dir,
                    args.name,
                )
                print(result)  # noqa: T201

    except PortfolioManagementError:
        logging.exception("Universe management failed")
        sys.exit(1)
    except Exception:
        logging.exception("An unexpected error occurred")
        sys.exit(1)


if __name__ == "__main__":
    main()
