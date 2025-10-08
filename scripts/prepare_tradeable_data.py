"""Prepare tradeable instrument datasets from unpacked Stooq price files.

The script expects the unpacked Stooq directory tree (e.g., `data/stooq/d_pl_txt/...`)
and three CSV files describing the tradeable universes. It performs the following steps:

1. Scan the unpacked data tree to build an index of available price files.
2. Load and normalize the broker tradeable lists.
3. Match tradeable instruments to Stooq tickers using heuristic symbol mapping.
4. Export matched price histories and emit reports for matched/unmatched assets.

Example usage:
    python scripts/prepare_tradeable_data.py \\
        --data-dir data/stooq \\
        --metadata-output data/metadata/stooq_index.csv \\
        --tradeable-dir tradeable_instruments \\
        --match-report data/metadata/tradeable_matches.csv \\
        --unmatched-report data/metadata/tradeable_unmatched.csv \\
        --prices-output data/processed/tradeable_prices \\
        --max-workers 8 \\
        --overwrite-prices
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


LOGGER = logging.getLogger(__name__)


@dataclass
class StooqFile:
    ticker: str
    stem: str
    rel_path: Path
    region: str
    category: str


@dataclass
class TradeableInstrument:
    symbol: str
    isin: str
    market: str
    name: str
    currency: str
    source_file: str


@dataclass
class TradeableMatch:
    instrument: TradeableInstrument
    stooq_file: StooqFile
    matched_ticker: str
    strategy: str


def _scan_subtree(base_dir: Path, rel_prefix: Path) -> List[Path]:
    """Return a list of relative TXT file paths within a subtree using os.scandir."""
    pending: List[Tuple[Path, Path]] = [(base_dir, rel_prefix)]
    rel_paths: List[Path] = []

    while pending:
        dir_path, rel_dir = pending.pop()
        try:
            with os.scandir(dir_path) as it:
                for entry in it:
                    name = entry.name
                    if not name or name.startswith("."):
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        pending.append((Path(entry.path), rel_dir / name))
                    elif entry.is_file(follow_symlinks=False) and name.lower().endswith(".txt"):
                        rel_paths.append(rel_dir / name)
        except OSError as exc:
            LOGGER.warning("Unable to scan %s: %s", dir_path, exc)
            continue

    return rel_paths


def derive_region_and_category(rel_path: Path) -> Tuple[str, str]:
    """Infer region and category from the relative path within the Stooq tree."""
    parts = list(rel_path.parts)
    region = ""
    category = ""
    if "daily" in parts:
        idx = parts.index("daily")
        if idx + 1 < len(parts):
            region = parts[idx + 1]
        if idx + 2 < len(parts):
            category = "/".join(parts[idx + 2 : -1])
    else:
        if parts:
            region = parts[0]
        if len(parts) > 2:
            category = "/".join(parts[1:-1])
    return region, category


def build_stooq_index(data_dir: Path, *, max_workers: int = 1) -> List[StooqFile]:
    """Create an index describing all unpacked Stooq price files."""
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    relative_paths: List[Path] = []
    subdirs: List[Path] = []

    try:
        with os.scandir(data_dir) as it:
            for entry in it:
                name = entry.name
                if not name or name.startswith("."):
                    continue
                if entry.is_dir(follow_symlinks=False):
                    subdirs.append(Path(entry.path))
                elif entry.is_file(follow_symlinks=False) and name.lower().endswith(".txt"):
                    relative_paths.append(Path(name))
    except OSError as exc:
        raise RuntimeError(f"Unable to scan data directory {data_dir}: {exc}") from exc

    if max_workers > 1 and len(subdirs) > 1:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_scan_subtree, subdir, Path(subdir.name)): subdir
                for subdir in subdirs
            }
            for future in as_completed(futures):
                relative_paths.extend(future.result())
    else:
        for subdir in subdirs:
            relative_paths.extend(_scan_subtree(subdir, Path(subdir.name)))

    relative_paths.sort(key=lambda p: p.as_posix())

    entries: List[StooqFile] = []
    for rel_path in relative_paths:
        region, category = derive_region_and_category(rel_path)
        ticker = rel_path.stem.upper()
        entries.append(
            StooqFile(
                ticker=ticker,
                stem=rel_path.stem.upper(),
                rel_path=rel_path,
                region=region,
                category=category,
            )
        )
    LOGGER.info("Indexed %s Stooq files", len(entries))
    return entries


def write_stooq_index(entries: Sequence[StooqFile], output_path: Path) -> None:
    """Persist the Stooq index to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["ticker", "stem", "relative_path", "region", "category"])
        for entry in entries:
            writer.writerow(
                [
                    entry.ticker,
                    entry.stem,
                    entry.rel_path.as_posix(),
                    entry.region,
                    entry.category,
                ]
            )
    LOGGER.info("Stooq index written to %s", output_path)


def read_stooq_index(csv_path: Path) -> List[StooqFile]:
    """Load the Stooq index from an existing CSV."""
    entries: List[StooqFile] = []
    with open(csv_path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rel_path = Path(row["relative_path"])
            entries.append(
                StooqFile(
                    ticker=row["ticker"].upper(),
                    stem=row["stem"].upper(),
                    rel_path=rel_path,
                    region=row.get("region", ""),
                    category=row.get("category", ""),
                )
            )
    LOGGER.info("Loaded %s Stooq index entries from %s", len(entries), csv_path)
    return entries


def load_tradeable_instruments(tradeable_dir: Path) -> List[TradeableInstrument]:
    """Load and normalize tradeable instrument CSV files."""
    instruments: List[TradeableInstrument] = []
    for csv_path in sorted(tradeable_dir.glob("*.csv")):
        with open(csv_path, newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            lower_map = {field.lower(): field for field in reader.fieldnames or []}
            get_field = lower_map.get
            for row in reader:
                symbol = row.get(get_field("symbol") or "", "").strip()
                isin = row.get(get_field("isin") or "", "").strip()
                market = row.get(get_field("market") or "", "").strip()
                name = row.get(get_field("name") or "", "").strip()
                currency = row.get(get_field("currency") or "", "").strip()
                if not symbol:
                    continue
                instruments.append(
                    TradeableInstrument(
                        symbol=symbol,
                        isin=isin,
                        market=market,
                        name=name,
                        currency=currency,
                        source_file=csv_path.name,
                    )
                )
    LOGGER.info("Loaded %s tradeable instruments", len(instruments))
    return instruments


def build_stooq_lookup(entries: Sequence[StooqFile]) -> Tuple[Dict[str, StooqFile], Dict[str, StooqFile]]:
    """Create lookup dictionaries for Stooq tickers and stems."""
    by_ticker: Dict[str, StooqFile] = {}
    by_stem: Dict[str, StooqFile] = {}
    for entry in entries:
        by_ticker.setdefault(entry.ticker.upper(), entry)
        by_stem.setdefault(entry.stem.upper(), entry)
    return by_ticker, by_stem


def candidate_tickers(symbol: str, market: str) -> Iterable[str]:
    """Generate possible Stooq tickers for a tradeable symbol."""
    if not symbol:
        return []

    original = symbol.strip()
    candidates: List[str] = []

    normalized = original.replace(" ", "").upper()
    base, suffix = split_symbol(normalized)

    if suffix:
        for ext in suffix_to_extensions(suffix, market):
            candidates.append(f"{base}{ext}".upper())
    else:
        candidates.append(base.upper())
        if "." in normalized:
            candidates.append(normalized.upper())

    candidates.append(base.upper())

    seen = set()
    for cand in candidates:
        if cand not in seen:
            seen.add(cand)
            yield cand


def split_symbol(symbol: str) -> Tuple[str, str]:
    """Split a broker symbol of the form 'ABC:LN' into base and suffix."""
    if ":" in symbol:
        base, suffix = symbol.split(":", 1)
        return base, suffix
    if "." in symbol:
        base, suffix = symbol.split(".", 1)
        return base, suffix
    return symbol, ""


def suffix_to_extensions(suffix: str, market: str) -> Sequence[str]:
    """Map broker suffixes to likely Stooq ticker extensions."""
    suffix = suffix.upper()
    market = (market or "").upper()

    mapping = {
        "PW": [".PL"],
        "PL": [".PL"],
        "GPW": [".PL"],
        "LN": [".UK"],
        "L": [".UK"],
        "GB": [".UK"],
        "US": [".US"],
        "UN": [".US"],
        "U": [".US"],
        "NYSE": [".US"],
        "NASDAQ": [".US"],
        "HK": [".HK"],
        "H": [".HK"],
        "JP": [".JP"],
        "T": [".JP"],
        "HU": [".HU"],
        "BSE": [".HU"],
    }

    if suffix in mapping:
        return mapping[suffix]

    market_matchers = [
        (r"XETRA|FRANKFURT|GER", [".DE"]),
        (r"NASDAQ|NYSE|USA|UNITED STATES", [".US"]),
        (r"GPW|WARSAW|POL", [".PL"]),
        (r"LSE|LONDON", [".UK"]),
        (r"HK", [".HK"]),
        (r"JPX|TOKYO", [".JP"]),
        (r"HUNGARY|BUDAPEST", [".HU"]),
    ]

    for pattern, exts in market_matchers:
        if re.search(pattern, market):
            return exts

    return [""]


def _match_instrument(
    instrument: TradeableInstrument,
    by_ticker: Dict[str, StooqFile],
    by_stem: Dict[str, StooqFile],
) -> Tuple[Optional[TradeableMatch], Optional[TradeableInstrument]]:
    tried: List[str] = []
    for candidate in candidate_tickers(instrument.symbol, instrument.market):
        tried.append(candidate)
        if candidate in by_ticker:
            return (
                TradeableMatch(
                    instrument=instrument,
                    stooq_file=by_ticker[candidate],
                    matched_ticker=candidate,
                    strategy="ticker",
                ),
                None,
            )
        stem_candidate = candidate.split(".", 1)[0]
        if stem_candidate in by_stem:
            entry = by_stem[stem_candidate]
            return (
                TradeableMatch(
                    instrument=instrument,
                    stooq_file=entry,
                    matched_ticker=entry.ticker,
                    strategy="stem",
                ),
                None,
            )
    LOGGER.debug(
        "Unmatched instrument %s (market=%s) candidates=%s",
        instrument.symbol,
        instrument.market,
        tried,
    )
    return None, instrument


def match_tradeables(
    instruments: Sequence[TradeableInstrument],
    by_ticker: Dict[str, StooqFile],
    by_stem: Dict[str, StooqFile],
    *,
    max_workers: int = 1,
) -> Tuple[List[TradeableMatch], List[TradeableInstrument]]:
    """Match tradeable instruments to Stooq files."""
    matches: List[TradeableMatch] = []
    unmatched: List[TradeableInstrument] = []

    if max_workers <= 1:
        for instrument in instruments:
            match, missing = _match_instrument(instrument, by_ticker, by_stem)
            if match:
                matches.append(match)
            elif missing:
                unmatched.append(missing)
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(_match_instrument, instrument, by_ticker, by_stem)
                for instrument in instruments
            ]
            for future in as_completed(futures):
                match, missing = future.result()
                if match:
                    matches.append(match)
                elif missing:
                    unmatched.append(missing)

    LOGGER.info("Matched %s instruments, %s unmatched", len(matches), len(unmatched))
    return matches, unmatched


def write_match_report(matches: Sequence[TradeableMatch], output_path: Path) -> None:
    """Persist the match report showing which tradeables map to which Stooq files."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "symbol",
                "isin",
                "market",
                "name",
                "currency",
                "matched_ticker",
                "stooq_path",
                "region",
                "category",
                "strategy",
            ]
        )
        for match in matches:
            writer.writerow(
                [
                    match.instrument.symbol,
                    match.instrument.isin,
                    match.instrument.market,
                    match.instrument.name,
                    match.instrument.currency,
                    match.matched_ticker,
                    match.stooq_file.rel_path.as_posix(),
                    match.stooq_file.region,
                    match.stooq_file.category,
                    match.strategy,
                ]
            )
    LOGGER.info("Match report written to %s", output_path)


def write_unmatched_report(unmatched: Sequence[TradeableInstrument], output_path: Path) -> None:
    """Persist the unmatched instrument list for manual follow-up."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["symbol", "isin", "market", "name", "currency", "source_file"])
        for instrument in unmatched:
            writer.writerow(
                [
                    instrument.symbol,
                    instrument.isin,
                    instrument.market,
                    instrument.name,
                    instrument.currency,
                    instrument.source_file,
                ]
            )
    LOGGER.info("Unmatched report written to %s", output_path)


def export_tradeable_prices(
    matches: Sequence[TradeableMatch],
    data_dir: Path,
    dest_dir: Path,
    *,
    overwrite: bool = False,
    max_workers: int = 1,
) -> None:
    """Convert matched Stooq price files into CSVs stored in the destination directory."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    header = [
        "ticker",
        "per",
        "date",
        "time",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "openint",
    ]

    unique_matches: Dict[str, TradeableMatch] = {}
    for match in matches:
        ticker_upper = match.stooq_file.ticker.upper()
        unique_matches.setdefault(ticker_upper, match)

    def _export_single(match: TradeableMatch) -> bool:
        source_path = data_dir / match.stooq_file.rel_path
        target_path = dest_dir / f"{match.stooq_file.ticker.lower()}.csv"
        if target_path.exists() and not overwrite:
            return False
        try:
            with open(source_path, "r", encoding="utf-8") as src, open(
                target_path, "w", newline="", encoding="utf-8"
            ) as dst:
                reader = csv.reader(src)
                writer = csv.writer(dst)
                writer.writerow(header)
                for row in reader:
                    if not row:
                        continue
                    if row[0].startswith("<"):
                        continue
                    writer.writerow(row)
            return True
        except OSError as exc:
            LOGGER.warning("Failed to export %s -> %s: %s", source_path, target_path, exc)
            return False

    exported = 0
    tasks = list(unique_matches.values())
    if max_workers <= 1:
        for match in tasks:
            if _export_single(match):
                exported += 1
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(_export_single, match) for match in tasks]
            for future in as_completed(futures):
                if future.result():
                    exported += 1

    LOGGER.info("Exported %s price files to %s", exported, dest_dir)


def parse_args() -> argparse.Namespace:
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
        "--max-workers",
        type=int,
        default=1,
        help="Maximum number of threads to use for matching and exporting.",
    )
    parser.add_argument(
        "--index-workers",
        type=int,
        default=0,
        help="Number of threads for directory indexing (0 falls back to --max-workers).",
    )
    return parser.parse_args()


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )


def main() -> None:
    args = parse_args()
    configure_logging(args.log_level)

    data_dir = args.data_dir
    metadata_path = args.metadata_output
    index_workers = args.index_workers if args.index_workers > 0 else args.max_workers
    index_workers = max(1, index_workers)
    if metadata_path.exists() and not args.force_reindex:
        stooq_index = read_stooq_index(metadata_path)
    else:
        stooq_index = build_stooq_index(data_dir, max_workers=index_workers)
        write_stooq_index(stooq_index, metadata_path)

    tradeables = load_tradeable_instruments(args.tradeable_dir)

    stooq_by_ticker, stooq_by_stem = build_stooq_lookup(stooq_index)
    matches, unmatched = match_tradeables(
        tradeables,
        stooq_by_ticker,
        stooq_by_stem,
        max_workers=max(1, args.max_workers),
    )
    write_match_report(matches, args.match_report)
    write_unmatched_report(unmatched, args.unmatched_report)

    export_tradeable_prices(
        matches,
        data_dir,
        args.prices_output,
        overwrite=args.overwrite_prices,
        max_workers=max(1, args.max_workers),
    )


if __name__ == "__main__":
    main()
