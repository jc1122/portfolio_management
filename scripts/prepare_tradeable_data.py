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
import threading
import time
from datetime import datetime
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from queue import Queue
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


LOGGER = logging.getLogger(__name__)


REGION_CURRENCY_MAP = {
    "us": "USD",
    "world": "USD",
    "uk": "GBP",
    "pl": "PLN",
    "hk": "HKD",
    "jp": "JPY",
    "hu": "HUF",
}

LEGACY_PREFIXES = ("L", "Q")
SYMBOL_ALIAS_MAP: Dict[Tuple[str, str], List[str]] = {
    ("FB", ".US"): ["META.US"],
    ("BRKS", ".US"): ["AZTA.US"],
    ("PKI", ".US"): ["RVTY.US"],
    ("FISV", ".US"): ["FI.US"],
    ("FBHS", ".US"): ["FBIN.US"],
    ("NRZ", ".US"): ["RITM.US"],
    ("DWAV", ".US"): ["QBTS.US"],
}


@contextmanager
def log_duration(step: str):
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        LOGGER.info("%s completed in %.2fs", step, elapsed)


@dataclass
class StooqFile:
    ticker: str
    stem: str
    rel_path: str
    region: str
    category: str

    def to_path(self) -> Path:
        return Path(self.rel_path)

    @property
    def extension(self) -> str:
        if "." in self.ticker:
            return f".{self.ticker.split('.', 1)[1]}"
        return ""


@dataclass
class TradeableInstrument:
    symbol: str
    isin: str
    market: str
    name: str
    currency: str
    source_file: str
    reason: str = ""


@dataclass
class TradeableMatch:
    instrument: TradeableInstrument
    stooq_file: StooqFile
    matched_ticker: str
    strategy: str


def summarize_price_file(base_dir: Path, stooq_file: StooqFile) -> Dict[str, str]:
    """Extract diagnostics and validation flags from a Stooq price file."""
    file_path = base_dir / stooq_file.rel_path
    diagnostics = {
        "price_start": "",
        "price_end": "",
        "price_rows": "0",
        "data_status": "missing",
        "data_flags": "",
    }

    if not file_path.exists():
        diagnostics["data_status"] = "missing_file"
        return diagnostics

    expected_cols = 10
    invalid_rows = 0
    non_numeric_prices = 0
    non_positive_close = 0
    zero_volume = 0
    missing_volume = 0
    zero_volume_ratio = 0.0
    zero_volume_severity: Optional[str] = None
    duplicate_dates = False
    non_monotonic_dates = False
    seen_dates: set[str] = set()
    previous_date: Optional[str] = None
    flags: List[str] = []

    try:
        with open(file_path, "r", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            header = next(reader, None)
            if not header:
                diagnostics["data_status"] = "empty"
                return diagnostics

            first_row: Optional[List[str]] = None
            for initial_row in reader:
                if len(initial_row) < expected_cols:
                    invalid_rows += 1
                    continue
                first_row = initial_row
                break

            if not first_row:
                diagnostics["data_status"] = "empty"
                return diagnostics

            first_date = first_row[2]
            last_date = first_date
            row_count = 1
            previous_date = first_date
            seen_dates.add(first_date)

            def _parse_float(value: str) -> Optional[float]:
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return None

            close_value = _parse_float(first_row[7])
            volume_value = _parse_float(first_row[8]) if len(first_row) > 8 else None
            if close_value is None:
                non_numeric_prices += 1
            elif close_value <= 0:
                non_positive_close += 1
            if volume_value is None:
                missing_volume += 1
            elif volume_value == 0:
                zero_volume += 1

            for row in reader:
                if len(row) < expected_cols:
                    invalid_rows += 1
                    continue
                date_value = row[2]
                if date_value in seen_dates:
                    duplicate_dates = True
                else:
                    seen_dates.add(date_value)
                if previous_date and date_value < previous_date:
                    non_monotonic_dates = True
                previous_date = date_value
                last_date = date_value
                close_value = _parse_float(row[7])
                if close_value is None:
                    non_numeric_prices += 1
                elif close_value <= 0:
                    non_positive_close += 1
                volume_value = _parse_float(row[8]) if len(row) > 8 else None
                if volume_value is None:
                    missing_volume += 1
                elif volume_value == 0:
                    zero_volume += 1
                row_count += 1

            diagnostics["price_start"] = format_stooq_date(first_date)
            diagnostics["price_end"] = format_stooq_date(last_date)
            diagnostics["price_rows"] = str(row_count)
            diagnostics["data_status"] = "ok" if row_count > 1 else "sparse"

            if row_count:
                zero_volume_ratio = zero_volume / row_count
                if zero_volume:
                    if zero_volume_ratio >= 0.5:
                        zero_volume_severity = "critical"
                    elif zero_volume_ratio >= 0.1:
                        zero_volume_severity = "high"
                    elif zero_volume_ratio >= 0.01:
                        zero_volume_severity = "moderate"
                    else:
                        zero_volume_severity = "low"

            if invalid_rows:
                flags.append(f"invalid_rows={invalid_rows}")
            if non_numeric_prices:
                flags.append(f"non_numeric_prices={non_numeric_prices}")
            if non_positive_close:
                flags.append(f"non_positive_close={non_positive_close}")
            if missing_volume:
                flags.append(f"missing_volume={missing_volume}")
            if zero_volume:
                flags.append(f"zero_volume={zero_volume}")
                flags.append(f"zero_volume_ratio={zero_volume_ratio:.4f}")
                if zero_volume_severity:
                    flags.append(f"zero_volume_severity={zero_volume_severity}")
            if duplicate_dates:
                flags.append("duplicate_dates")
            if non_monotonic_dates:
                flags.append("non_monotonic_dates")

            if zero_volume_severity:
                if diagnostics["data_status"] == "ok":
                    diagnostics["data_status"] = "warning"
            elif flags and diagnostics["data_status"] == "ok":
                diagnostics["data_status"] = "warning"

            diagnostics["data_flags"] = ";".join(flags)
    except OSError as exc:
        diagnostics["data_status"] = f"error:{exc.__class__.__name__}"

    return diagnostics


def format_stooq_date(value: str) -> str:
    """Convert Stooq YYYYMMDD date strings into ISO format when possible."""
    if not value:
        return ""
    try:
        parsed = datetime.strptime(value, "%Y%m%d")
        return parsed.date().isoformat()
    except ValueError:
        return value


def infer_currency(stooq_file: StooqFile) -> Optional[str]:
    """Guess the trading currency from the Stooq region/category."""
    region_key = (stooq_file.region or "").lower()
    return REGION_CURRENCY_MAP.get(region_key)


def _is_lse_listing(symbol: str, market: str) -> bool:
    symbol_upper = (symbol or "").upper()
    market_upper = (market or "").upper()
    if "LSE" in market_upper or "LONDON" in market_upper or "GBR-LSE" in market_upper:
        return True
    return symbol_upper.endswith((":LN", ":L", ".LN", ".L"))


def resolve_currency(
    instrument: TradeableInstrument,
    stooq_file: StooqFile,
    inferred_currency: Optional[str],
    *,
    lse_policy: str = "broker",
) -> Tuple[str, str, str, str]:
    """Determine effective currency and status for reporting."""

    expected = (instrument.currency or "").upper()
    inferred = (inferred_currency or "").upper()
    market = (instrument.market or "").upper()
    symbol = (instrument.symbol or "").upper()

    # Default outputs
    resolved = inferred
    status = ""

    lse_listing = stooq_file.region.lower() == "uk" and _is_lse_listing(symbol, market)

    if expected and inferred:
        if expected == inferred:
            resolved = inferred
            status = "match"
        elif lse_listing:
            policy = lse_policy.lower()
            if policy == "broker":
                # LSE multi-currency lines are often denominated per share class; keep broker currency.
                resolved = expected
                status = "override"
            elif policy == "stooq":
                resolved = inferred
                status = "mismatch"
            elif policy == "strict":
                resolved = ""
                status = "error:lse_currency_override"
            else:
                LOGGER.warning("Unknown LSE currency policy '%s'; defaulting to broker.", lse_policy)
                resolved = expected
                status = "override"
        else:
            resolved = inferred
            status = "mismatch"
    elif expected:
        resolved = expected
        status = "expected_only"
    elif inferred:
        resolved = inferred
        status = "inferred_only"
    else:
        resolved = ""
        status = "unknown"

    return expected, inferred, resolved, status


def log_summary_counts(currency_counts: Counter, data_status_counts: Counter) -> None:
    """Log aggregate summaries for currency and data validation statuses."""
    if currency_counts:
        summary = ", ".join(
            f"{key}={count}" for key, count in sorted(currency_counts.items())
        )
        LOGGER.info("Currency status summary: %s", summary)
    if data_status_counts:
        summary = ", ".join(
            f"{key}={count}" for key, count in sorted(data_status_counts.items())
        )
        LOGGER.info("Data status summary: %s", summary)


def collect_available_extensions(entries: Sequence[StooqFile]) -> set[str]:
    """Return the set of ticker extensions present in the Stooq index."""
    extensions: set[str] = set()
    for entry in entries:
        if "." in entry.ticker:
            extensions.add(entry.ticker[entry.ticker.find(".") :].upper())
        else:
            extensions.add("")
    return extensions


def determine_unmatched_reason(
    instrument: TradeableInstrument,
    stooq_by_base: Dict[str, List[StooqFile]],
    available_extensions: set[str],
) -> str:
    """Explain why a tradeable instrument could not be matched."""
    symbol = (instrument.symbol or "").upper().strip()
    market = (instrument.market or "").upper()
    base, suffix = split_symbol(symbol)
    desired_exts = {ext.upper() for ext in suffix_to_extensions(suffix, market) if ext}
    if not desired_exts:
        desired_exts.update(
            ext.upper() for ext in suffix_to_extensions("", market) if ext
        )

    if desired_exts and not any(ext in available_extensions for ext in desired_exts):
        return f"no_source_data({','.join(sorted(desired_exts))})"

    base_entries = stooq_by_base.get(base.upper())
    if not base_entries:
        return "no_stooq_ticker"

    if desired_exts:
        matching = [
            entry
            for entry in base_entries
            if any(entry.ticker.upper().endswith(ext) for ext in desired_exts)
        ]
        if not matching:
            return "alias_required"

    if len(base_entries) > 1:
        return "ambiguous_variants"

    return "manual_review"


def _collect_relative_paths(base_dir: Path, max_workers: int) -> List[str]:
    """Collect relative TXT file paths within the Stooq tree using a worker queue."""
    queue: Queue[Tuple[Path, Path]] = Queue()
    queue.put((base_dir, Path()))
    rel_paths: List[str] = []
    lock = threading.Lock()

    max_workers = max(1, max_workers)

    def worker() -> None:
        while True:
            item = queue.get()
            if item is None:
                queue.task_done()
                break
            dir_path, rel_dir = item
            try:
                with os.scandir(dir_path) as it:
                    for entry in it:
                        name = entry.name
                        if not name or name.startswith("."):
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            queue.put((Path(entry.path), rel_dir / name))
                        elif entry.is_file(follow_symlinks=False) and name.lower().endswith(".txt"):
                            rel_file = rel_dir / name
                            rel_str = rel_file.as_posix()
                            with lock:
                                rel_paths.append(rel_str)
            except OSError as exc:
                LOGGER.warning("Unable to scan %s: %s", dir_path, exc)
            finally:
                queue.task_done()

    threads = [
        threading.Thread(target=worker, name=f"stooq-scan-{idx}", daemon=True)
        for idx in range(max_workers)
    ]
    for thread in threads:
        thread.start()

    queue.join()

    for _ in threads:
        queue.put(None)

    for thread in threads:
        thread.join()

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

    relative_paths = _collect_relative_paths(data_dir, max_workers)
    relative_paths.sort()

    entries: List[StooqFile] = []
    for rel_path_str in relative_paths:
        rel_path = Path(rel_path_str)
        region, category = derive_region_and_category(rel_path)
        ticker = rel_path.stem.upper()
        entries.append(
            StooqFile(
                ticker=ticker,
                stem=rel_path.stem.upper(),
                rel_path=rel_path_str,
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
                    entry.rel_path,
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
            rel_path_str = row["relative_path"]
            entries.append(
                StooqFile(
                    ticker=row["ticker"].upper(),
                    stem=row["stem"].upper(),
                    rel_path=rel_path_str,
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


def build_stooq_lookup(
    entries: Sequence[StooqFile],
) -> Tuple[Dict[str, StooqFile], Dict[str, StooqFile], Dict[str, List[StooqFile]]]:
    """Create lookup dictionaries for Stooq tickers, stems, and base symbols."""
    by_ticker: Dict[str, StooqFile] = {}
    by_stem: Dict[str, StooqFile] = {}
    by_base: Dict[str, List[StooqFile]] = {}
    for entry in entries:
        ticker = entry.ticker.upper()
        by_ticker.setdefault(ticker, entry)
        by_stem.setdefault(entry.stem.upper(), entry)
        base = ticker.split(".", 1)[0]
        by_base.setdefault(base, []).append(entry)
    return by_ticker, by_stem, by_base


def candidate_tickers(symbol: str, market: str) -> Iterable[str]:
    """Generate possible Stooq tickers for a tradeable symbol."""
    if not symbol:
        return []

    original = symbol.strip()
    candidates: List[str] = []

    normalized = original.replace(" ", "").upper()
    base, suffix = split_symbol(normalized)

    extensions = suffix_to_extensions(suffix, market)
    if suffix:
        for ext in extensions:
            if ext:
                candidates.append(f"{base}{ext}".upper())
        candidates.append(normalized.upper())
    else:
        candidates.append(base.upper())
        for ext in extensions:
            if ext:
                candidates.append(f"{base}{ext}".upper())
        if "." in normalized:
            candidates.append(normalized.upper())

    candidates.append(base.upper())

    desired_exts = [ext for ext in extensions if ext]
    if not desired_exts:
        desired_exts = [ext for ext in suffix_to_extensions("", market) if ext]

    base_upper = base.upper()
    for ext in desired_exts:
        key = (base_upper, ext.upper())
        for alias in SYMBOL_ALIAS_MAP.get(key, []):
            candidates.append(alias.upper())
        for prefix in LEGACY_PREFIXES:
            if ext:
                candidates.append(f"{prefix}{base_upper}{ext.upper()}")
            else:
                candidates.append(f"{prefix}{base_upper}")

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
        "NSQ": [".US"],
        "NAS": [".US"],
        "NASDAQ (USD)": [".US"],
        "NYSE-MKT": [".US"],
        "AMEX": [".US"],
        "HK": [".HK"],
        "H": [".HK"],
        "JP": [".JP"],
        "T": [".JP"],
        "HU": [".HU"],
        "BSE": [".HU"],
        "TSX": [".TO"],
        "TSXV": [".V"],
        "TO": [".TO"],
        "V": [".V"],
        "CN": [".CN"],
        "C": [".TO"],
        "GR": [".DE"],
        "DE": [".DE"],
        "PA": [".PA", ".FR"],
        "PAR": [".PA", ".FR"],
        "AMS": [".NL", ".AS"],
        "AS": [".AS", ".NL"],
        "SWX": [".CH"],
        "SW": [".CH"],
        "CH": [".CH"],
        "BRU": [".BE"],
        "BR": [".BE"],
        "BRX": [".BE"],
    }

    if suffix in mapping:
        return mapping[suffix]

    market_matchers = [
        (r"XETRA|FRANKFURT|GER|DEU", [".DE"]),
        (r"EURONEXT\s*PARIS|\bPAR\b|PARIS|FRANCE", [".PA", ".FR"]),
        (r"EURONEXT\s*AMSTERDAM|AMSTERDAM|NED|NETHERLANDS", [".NL", ".AS"]),
        (r"NSQ|NASDAQ|NYSE|USA|UNITED STATES|AMERICAN", [".US"]),
        (r"TSX|TORONTO|CANADA", [".TO"]),
        (r"GPW|WARSAW|POL", [".PL"]),
        (r"LSE|LONDON|UNITED KINGDOM|UK", [".UK"]),
        (r"HK", [".HK"]),
        (r"JPX|TOKYO|JAPAN", [".JP"]),
        (r"HUNGARY|BUDAPEST", [".HU"]),
        (r"SWISS|ZURICH|SWX|SIX|SWITZERLAND", [".CH"]),
        (r"BRUSSELS|BELGIUM", [".BE"]),
    ]

    for pattern, exts in market_matchers:
        if re.search(pattern, market):
            return exts

    return [""]


def _match_instrument(
    instrument: TradeableInstrument,
    by_ticker: Dict[str, StooqFile],
    by_stem: Dict[str, StooqFile],
    by_base: Dict[str, List[StooqFile]],
) -> Tuple[Optional[TradeableMatch], Optional[TradeableInstrument]]:
    tried: List[str] = []
    norm_symbol = (instrument.symbol or "").replace(" ", "").upper()
    _, instrument_suffix = split_symbol(norm_symbol)
    instrument_desired_exts = {
        ext.upper()
        for ext in suffix_to_extensions(instrument_suffix, instrument.market)
        if ext
    }
    fallback_desired_exts = {
        ext.upper() for ext in suffix_to_extensions("", instrument.market) if ext
    }
    for candidate in candidate_tickers(instrument.symbol, instrument.market):
        tried.append(candidate)
        candidate_ext = candidate[candidate.find(".") :].upper() if "." in candidate else ""
        desired_exts_set = set(instrument_desired_exts)
        if not desired_exts_set:
            desired_exts_set.update(fallback_desired_exts)
        if candidate_ext:
            desired_exts_set.add(candidate_ext)
        if candidate in by_ticker:
            entry = by_ticker[candidate]
            entry_ext = entry.extension.upper()
            if desired_exts_set:
                if entry_ext and entry_ext not in desired_exts_set:
                    continue
                if not entry_ext and "" not in desired_exts_set:
                    continue
            return (
                TradeableMatch(
                    instrument=instrument,
                    stooq_file=entry,
                    matched_ticker=candidate,
                    strategy="ticker",
                ),
                None,
            )
        stem_candidate = candidate.split(".", 1)[0]
        if stem_candidate in by_stem:
            entry = by_stem[stem_candidate]
            entry_ext = entry.extension.upper()
            allow_stem_match = False
            if desired_exts_set:
                if entry_ext:
                    allow_stem_match = entry_ext in desired_exts_set
                else:
                    allow_stem_match = "" in desired_exts_set
            else:
                allow_stem_match = True

            if allow_stem_match:
                return (
                    TradeableMatch(
                        instrument=instrument,
                        stooq_file=entry,
                        matched_ticker=entry.ticker,
                        strategy="stem",
                    ),
                    None,
                )
        base_entries = by_base.get(stem_candidate)
        if base_entries:
            desired_exts: List[str] = []
            desired_exts_set: set[str] = set()

            for ext in suffix_to_extensions(instrument_suffix, instrument.market):
                if ext:
                    ext_up = ext.upper()
                    if ext_up not in desired_exts_set:
                        desired_exts.append(ext_up)
                        desired_exts_set.add(ext_up)

            for ext in suffix_to_extensions("", instrument.market):
                if ext:
                    ext_up = ext.upper()
                    if ext_up not in desired_exts_set:
                        desired_exts.append(ext_up)
                        desired_exts_set.add(ext_up)

            candidate_ext = (
                candidate[candidate.find(".") :].upper() if "." in candidate else ""
            )
            if candidate_ext and candidate_ext not in desired_exts_set:
                desired_exts.insert(0, candidate_ext)
                desired_exts_set.add(candidate_ext)

            available_exts = {
                entry.ticker[entry.ticker.find(".") :].upper()
                for entry in base_entries
                if "." in entry.ticker
            }

            if desired_exts_set and not any(ext in available_exts for ext in desired_exts_set):
                continue

            preferred_exts = [ext for ext in desired_exts if ext]
            chosen: Optional[StooqFile] = None
            if preferred_exts:
                for ext in preferred_exts:
                    for entry in base_entries:
                        if entry.ticker.upper().endswith(ext):
                            chosen = entry
                            break
                    if chosen:
                        break
            if not chosen and not desired_exts_set and len(base_entries) == 1:
                chosen = base_entries[0]
            if chosen:
                return (
                    TradeableMatch(
                        instrument=instrument,
                        stooq_file=chosen,
                        matched_ticker=chosen.ticker,
                        strategy="base_market",
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
    by_base: Dict[str, List[StooqFile]],
    *,
    max_workers: int = 1,
) -> Tuple[List[TradeableMatch], List[TradeableInstrument]]:
    """Match tradeable instruments to Stooq files."""
    matches: List[TradeableMatch] = []
    unmatched: List[TradeableInstrument] = []

    if max_workers <= 1:
        for instrument in instruments:
            match, missing = _match_instrument(instrument, by_ticker, by_stem, by_base)
            if match:
                matches.append(match)
            elif missing:
                unmatched.append(missing)
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(_match_instrument, instrument, by_ticker, by_stem, by_base)
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


def write_match_report(
    matches: Sequence[TradeableMatch],
    output_path: Path,
    data_dir: Path,
    *,
    lse_currency_policy: str,
) -> Tuple[Dict[str, Dict[str, str]], Counter, Counter, List[str], List[Tuple[str, str, str]]]:
    """Persist the match report showing which tradeables map to which Stooq files.

    Returns a tuple containing a diagnostics cache, currency status counts, data status
    counts, a list of tickers with empty datasets, and a sample of records with data flags.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    diagnostics_cache: Dict[str, Dict[str, str]] = {}
    currency_counts: Counter = Counter()
    data_status_counts: Counter = Counter()
    empty_tickers: List[str] = []
    flagged_samples: List[Tuple[str, str, str]] = []

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
                "source_file",
                "price_start",
                "price_end",
                "price_rows",
                "inferred_currency",
                "resolved_currency",
                "currency_status",
                "data_status",
                "data_flags",
            ]
        )
        for match in matches:
            diagnostics = summarize_price_file(data_dir, match.stooq_file)
            diagnostics_cache[match.stooq_file.ticker.upper()] = diagnostics
            _expected, inferred, resolved, currency_status = resolve_currency(
                match.instrument,
                match.stooq_file,
                infer_currency(match.stooq_file),
                lse_policy=lse_currency_policy,
            )
            currency_counts[currency_status] += 1
            data_status = diagnostics["data_status"]
            data_status_counts[data_status] += 1
            if data_status == "empty":
                empty_tickers.append(match.stooq_file.ticker)
            data_flags = diagnostics.get("data_flags", "")
            if data_flags:
                flagged_samples.append(
                    (match.instrument.symbol, match.stooq_file.ticker, data_flags)
                )
            writer.writerow(
                [
                    match.instrument.symbol,
                    match.instrument.isin,
                    match.instrument.market,
                    match.instrument.name,
                    match.instrument.currency,
                    match.matched_ticker,
                    match.stooq_file.rel_path,
                    match.stooq_file.region,
                    match.stooq_file.category,
                    match.strategy,
                    match.instrument.source_file,
                    diagnostics["price_start"],
                    diagnostics["price_end"],
                    diagnostics["price_rows"],
                    inferred,
                    resolved,
                    currency_status,
                    data_status,
                    data_flags,
                ]
            )
    LOGGER.info("Match report written to %s", output_path)
    return diagnostics_cache, currency_counts, data_status_counts, empty_tickers, flagged_samples


def write_unmatched_report(unmatched: Sequence[TradeableInstrument], output_path: Path) -> None:
    """Persist the unmatched instrument list for manual follow-up."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["symbol", "isin", "market", "name", "currency", "source_file", "reason"]
        )
        for instrument in unmatched:
            writer.writerow(
                [
                    instrument.symbol,
                    instrument.isin,
                    instrument.market,
                    instrument.name,
                    instrument.currency,
                    instrument.source_file,
                    instrument.reason,
                ]
            )
    LOGGER.info("Unmatched report written to %s", output_path)


def annotate_unmatched_instruments(
    unmatched: Sequence[TradeableInstrument],
    stooq_by_base: Dict[str, List[StooqFile]],
    available_extensions: set[str],
) -> List[TradeableInstrument]:
    """Attach diagnostic reasons to unmatched instruments."""
    annotated: List[TradeableInstrument] = []
    for instrument in unmatched:
        instrument.reason = determine_unmatched_reason(
            instrument, stooq_by_base, available_extensions
        )
        annotated.append(instrument)
    return annotated


def export_tradeable_prices(
    matches: Sequence[TradeableMatch],
    data_dir: Path,
    dest_dir: Path,
    *,
    overwrite: bool = False,
    max_workers: int = 1,
    diagnostics: Optional[Dict[str, Dict[str, str]]] = None,
    include_empty: bool = False,
) -> Tuple[int, int]:
    """Convert matched Stooq price files into CSVs stored in the destination directory.

    Returns a tuple of (exported_count, skipped_count).
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    header_line = "ticker,per,date,time,open,high,low,close,volume,openint\n"

    unique_matches: Dict[str, TradeableMatch] = {}
    for match in matches:
        ticker_upper = match.stooq_file.ticker.upper()
        unique_matches.setdefault(ticker_upper, match)

    skipped = 0

    def _export_single(match: TradeableMatch) -> bool:
        nonlocal skipped
        source_path = data_dir / match.stooq_file.rel_path
        target_path = dest_dir / f"{match.stooq_file.ticker.lower()}.csv"
        diag = diagnostics.get(match.stooq_file.ticker.upper()) if diagnostics else None
        if diag is None:
            diag = summarize_price_file(data_dir, match.stooq_file)
        status = diag.get("data_status", "")
        if (
            not include_empty
            and (
                status in {"empty", "missing", "missing_file"}
                or (status.startswith("error:") if status else False)
            )
        ):
            LOGGER.debug(
                "Skipping export for %s due to data_status=%s",
                match.stooq_file.ticker,
                status,
            )
            skipped += 1
            if target_path.exists() and overwrite:
                try:
                    target_path.unlink()
                except OSError as exc:
                    LOGGER.warning(
                        "Unable to remove stale export for %s: %s",
                        match.stooq_file.ticker,
                        exc,
                    )
            return False
        if target_path.exists() and not overwrite:
            return False
        try:
            with open(source_path, "r", encoding="utf-8") as src, open(
                target_path, "w", encoding="utf-8"
            ) as dst:
                dst.write(header_line)
                for line in src:
                    if not line or line.startswith("<"):
                        continue
                    dst.write(line)
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
    if skipped:
        LOGGER.warning("Skipped %s price files without usable data", skipped)
    return exported, skipped


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
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )


def main() -> None:
    args = parse_args()
    configure_logging(args.log_level)

    data_dir = args.data_dir
    metadata_path = args.metadata_output
    cpu_count = os.cpu_count() or 1
    auto_workers = min(8, cpu_count)
    max_workers = args.max_workers if args.max_workers and args.max_workers > 0 else auto_workers
    max_workers = max(1, max_workers)
    index_workers = args.index_workers if args.index_workers and args.index_workers > 0 else max_workers
    index_workers = max(1, index_workers)
    LOGGER.info(
        "Worker configuration: match/export=%s, index=%s (cpu=%s)",
        max_workers,
        index_workers,
        cpu_count,
    )

    if metadata_path.exists() and not args.force_reindex:
        with log_duration("stooq_index_load"):
            stooq_index = read_stooq_index(metadata_path)
    else:
        with log_duration("stooq_index_build"):
            stooq_index = build_stooq_index(data_dir, max_workers=index_workers)
        with log_duration("stooq_index_write"):
            write_stooq_index(stooq_index, metadata_path)

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
    unmatched = annotate_unmatched_instruments(unmatched, stooq_by_base, available_extensions)
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

    with log_duration("tradeable_export"):
        export_tradeable_prices(
            matches,
            data_dir,
            args.prices_output,
            overwrite=args.overwrite_prices,
            max_workers=max_workers,
            diagnostics=diagnostics_cache,
            include_empty=args.include_empty_prices,
        )


if __name__ == "__main__":
    main()
