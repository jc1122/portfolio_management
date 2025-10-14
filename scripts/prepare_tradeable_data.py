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
import logging
import os
import re
import time
from collections import Counter
from collections.abc import Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path

try:
    import pandas as pd
except ImportError as exc:  # pragma: no cover - pandas is required for this module
    raise ImportError(
        "pandas is required to run prepare_tradeable_data.py. "
        "Please install pandas before executing this script.",
    ) from exc

LOGGER = logging.getLogger(__name__)


from src.portfolio_management.config import (
    LEGACY_PREFIXES,
    REGION_CURRENCY_MAP,
    STOOQ_COLUMNS,
    SYMBOL_ALIAS_MAP,
)

# Constants for zero volume thresholds
ZERO_VOLUME_CRITICAL_THRESHOLD = 0.5
ZERO_VOLUME_HIGH_THRESHOLD = 0.1
ZERO_VOLUME_MODERATE_THRESHOLD = 0.01

# Constants for path parsing
DAILY_INDEX_OFFSET = 1
DAILY_CATEGORY_OFFSET = 2
MIN_PARTS_FOR_CATEGORY = 2


@contextmanager
def log_duration(step: str):
    """Context manager to log the duration of an operation.

    Args:
        step: Description of the operation being timed.

    Yields:
        None

    """
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        LOGGER.info("%s completed in %.2fs", step, elapsed)


@dataclass
class StooqFile:
    """Represents a Stooq price file with metadata about its location and structure."""

    ticker: str
    stem: str
    rel_path: str
    region: str
    category: str

    def to_path(self) -> Path:
        """Convert the relative path string to a Path object."""
        return Path(self.rel_path)

    @property
    def extension(self) -> str:
        """Extract the market extension from the ticker (e.g., '.UK' from 'ABC.UK')."""
        if "." in self.ticker:
            return f".{self.ticker.split('.', 1)[1]}"
        return ""


@dataclass
class TradeableInstrument:
    """Represents a tradeable financial instrument from a broker's universe."""

    symbol: str
    isin: str
    market: str
    name: str
    currency: str
    source_file: str
    reason: str = ""


@dataclass
class TradeableMatch:
    """Represents a successful match between a tradeable instrument and a Stooq file."""

    instrument: TradeableInstrument
    stooq_file: StooqFile
    matched_ticker: str
    strategy: str


def _read_stooq_csv(file_path: Path, engine: str) -> pd.DataFrame:
    """Read a Stooq CSV file with the specified engine."""
    return pd.read_csv(
        file_path,
        header=None,
        names=STOOQ_COLUMNS,
        comment="<",
        dtype=str,
        engine=engine,
        encoding="utf-8",
        keep_default_na=False,
        na_filter=False,
    )


def summarize_price_file(base_dir: Path, stooq_file: StooqFile) -> dict[str, str]:
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

    try:
        try:
            raw_price_frame = _read_stooq_csv(file_path, "c")
        except (ValueError, pd.errors.ParserError):
            raw_price_frame = _read_stooq_csv(file_path, "python")
    except (pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
        diagnostics["data_status"] = f"error:{exc.__class__.__name__}"
        return diagnostics
    except OSError as exc:
        diagnostics["data_status"] = f"error:{exc.__class__.__name__}"
        return diagnostics

    if raw_price_frame.empty:
        diagnostics["data_status"] = "empty"
        return diagnostics

    raw_price_frame = raw_price_frame.apply(lambda col: col.str.strip())

    if not raw_price_frame.empty:
        first_row = raw_price_frame.iloc[0]
        if all(
            isinstance(first_row[column], str) and first_row[column].lower() == column
            for column in raw_price_frame.columns
        ):
            raw_price_frame = raw_price_frame.iloc[1:].copy()

    date_series = pd.to_datetime(
        raw_price_frame["date"],
        format="%Y%m%d",
        errors="coerce",
    )
    invalid_rows = int(date_series.isna().sum())
    valid_mask = date_series.notna()
    valid_price_frame = raw_price_frame.loc[valid_mask].copy()
    valid_dates = date_series.loc[valid_mask]

    if valid_price_frame.empty or valid_dates.empty:
        diagnostics["data_status"] = "empty"
        return diagnostics

    row_count = len(valid_price_frame)
    first_date = valid_dates.iloc[0]
    last_date = valid_dates.iloc[-1]

    close_numeric = pd.to_numeric(valid_price_frame["close"], errors="coerce")
    volume_numeric = pd.to_numeric(valid_price_frame["volume"], errors="coerce")

    non_numeric_prices = int(close_numeric.isna().sum())
    non_positive_close = int((close_numeric[close_numeric.notna()] <= 0).sum())
    missing_volume = int(volume_numeric.isna().sum())
    zero_volume = int((volume_numeric == 0).sum())

    duplicate_dates = bool(valid_dates.duplicated().any())
    non_monotonic_dates = not bool(valid_dates.is_monotonic_increasing)

    zero_volume_ratio = (zero_volume / row_count) if row_count else 0.0
    zero_volume_severity: str | None = None
    if zero_volume:
        if zero_volume_ratio >= ZERO_VOLUME_CRITICAL_THRESHOLD:
            zero_volume_severity = "critical"
        elif zero_volume_ratio >= ZERO_VOLUME_HIGH_THRESHOLD:
            zero_volume_severity = "high"
        elif zero_volume_ratio >= ZERO_VOLUME_MODERATE_THRESHOLD:
            zero_volume_severity = "moderate"
        else:
            zero_volume_severity = "low"

    diagnostics["price_start"] = first_date.date().isoformat()
    diagnostics["price_end"] = last_date.date().isoformat()
    diagnostics["price_rows"] = str(row_count)
    diagnostics["data_status"] = "ok" if row_count > 1 else "sparse"

    flags: list[str] = []
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

    if (zero_volume_severity and diagnostics["data_status"] == "ok") or (
        flags and diagnostics["data_status"] == "ok"
    ):
        diagnostics["data_status"] = "warning"

    diagnostics["data_flags"] = ";".join(flags)
    return diagnostics


def infer_currency(stooq_file: StooqFile) -> str | None:
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
    inferred_currency: str | None,
    *,
    lse_policy: str = "broker",
) -> tuple[str, str, str, str]:
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
                LOGGER.warning(
                    "Unknown LSE currency policy '%s'; defaulting to broker.",
                    lse_policy,
                )
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
    return {
        entry.ticker[entry.ticker.find(".") :].upper() if "." in entry.ticker else ""
        for entry in entries
    }


def determine_unmatched_reason(
    instrument: TradeableInstrument,
    stooq_by_base: dict[str, list[StooqFile]],
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


def _run_in_parallel(func, args_list, max_workers):
    """Run a function in parallel with a list of arguments."""
    if max_workers <= 1:
        return [func(*args) for args in args_list]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(func, *args) for args in args_list]
        return [future.result() for future in as_completed(futures)]


def _collect_relative_paths(base_dir: Path, max_workers: int) -> list[str]:
    """Collect relative TXT file paths within the Stooq tree using parallel os.walk scanning."""

    def _scan_directory(start_dir: Path) -> list[str]:
        local_paths: list[str] = []
        try:
            for root, dirs, files in os.walk(start_dir, followlinks=False):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for file_name in files:
                    if file_name.startswith(".") or not file_name.lower().endswith(
                        ".txt",
                    ):
                        continue
                    full_path = Path(root) / file_name
                    try:
                        relative = full_path.relative_to(base_dir)
                    except ValueError:
                        continue
                    if any(part.startswith(".") for part in relative.parts):
                        continue
                    local_paths.append(relative.as_posix())
        except OSError as exc:
            LOGGER.warning("Unable to scan %s: %s", start_dir, exc)
        return local_paths

    try:
        top_level_entries = [
            entry for entry in base_dir.iterdir() if not entry.name.startswith(".")
        ]
    except OSError as exc:
        LOGGER.warning("Unable to iterate %s: %s", base_dir, exc)
        return []

    rel_paths = [
        entry.relative_to(base_dir).as_posix()
        for entry in top_level_entries
        if entry.is_file() and entry.suffix.lower() == ".txt"
    ]
    top_level_dirs = [entry for entry in top_level_entries if entry.is_dir()]

    results = _run_in_parallel(
        _scan_directory,
        [(d,) for d in top_level_dirs],
        max_workers,
    )
    for result in results:
        rel_paths.extend(result)

    rel_paths.sort()
    return rel_paths


def derive_region_and_category(rel_path: Path) -> tuple[str, str]:
    """Infer region and category from the relative path within the Stooq tree."""
    parts = list(rel_path.parts)
    region = ""
    category = ""
    if "daily" in parts:
        idx = parts.index("daily")
        if idx + DAILY_INDEX_OFFSET < len(parts):
            region = parts[idx + DAILY_INDEX_OFFSET]
        if idx + DAILY_CATEGORY_OFFSET < len(parts):
            category = "/".join(parts[idx + DAILY_CATEGORY_OFFSET : -1])
    else:
        if parts:
            region = parts[0]
        if len(parts) > MIN_PARTS_FOR_CATEGORY:
            category = "/".join(parts[1:-1])
    return region, category


def build_stooq_index(data_dir: Path, *, max_workers: int = 1) -> list[StooqFile]:
    """Create an index describing all unpacked Stooq price files."""
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    relative_paths = _collect_relative_paths(data_dir, max_workers)
    relative_paths.sort()

    entries = [
        StooqFile(
            ticker=(rel_path := Path(rel_path_str)).stem.upper(),
            stem=rel_path.stem.upper(),
            rel_path=rel_path_str,
            region=(region_category := derive_region_and_category(rel_path))[0],
            category=region_category[1],
        )
        for rel_path_str in relative_paths
    ]
    LOGGER.info("Indexed %s Stooq files", len(entries))
    return entries


def write_stooq_index(entries: Sequence[StooqFile], output_path: Path) -> None:
    """Persist the Stooq index to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    records = [
        {
            "ticker": entry.ticker,
            "stem": entry.stem,
            "relative_path": entry.rel_path,
            "region": entry.region,
            "category": entry.category,
        }
        for entry in entries
    ]
    columns = ["ticker", "stem", "relative_path", "region", "category"]
    pd.DataFrame.from_records(records, columns=columns).to_csv(output_path, index=False)
    LOGGER.info("Stooq index written to %s", output_path)


def read_stooq_index(csv_path: Path) -> list[StooqFile]:
    """Load the Stooq index from an existing CSV."""
    index_frame = pd.read_csv(csv_path, dtype=str).fillna("")
    entries = [
        StooqFile(
            ticker=row["ticker"].upper(),
            stem=row["stem"].upper(),
            rel_path=row["relative_path"],
            region=row.get("region", ""),
            category=row.get("category", ""),
        )
        for row in index_frame.to_dict(orient="records")
    ]
    LOGGER.info("Loaded %s Stooq index entries from %s", len(entries), csv_path)
    return entries


def _load_tradeable_frame(
    csv_path: Path,
    expected_columns: Sequence[str],
) -> pd.DataFrame | None:
    """Load and normalize a single tradeable instrument CSV."""
    instrument_frame = pd.read_csv(
        csv_path,
        dtype=str,
        keep_default_na=False,
        na_filter=False,
        encoding="utf-8",
    )
    instrument_frame.columns = [col.lower() for col in instrument_frame.columns]
    for column in expected_columns:
        if column not in instrument_frame.columns:
            instrument_frame[column] = ""
    for column in expected_columns:
        instrument_frame[column] = instrument_frame[column].astype(str).str.strip()
    instrument_frame = instrument_frame[instrument_frame["symbol"] != ""].copy()
    if instrument_frame.empty:
        return None
    instrument_frame["source_file"] = csv_path.name
    return instrument_frame[[*expected_columns, "source_file"]]


def load_tradeable_instruments(tradeable_dir: Path) -> list[TradeableInstrument]:
    """Load and normalize tradeable instrument CSV files."""
    instruments: list[TradeableInstrument] = []
    csv_paths = sorted(tradeable_dir.glob("*.csv"))
    expected_cols = ["symbol", "isin", "market", "name", "currency"]
    instrument_frames = [
        frame
        for csv_path in csv_paths
        if (frame := _load_tradeable_frame(csv_path, expected_cols)) is not None
    ]
    if instrument_frames:
        combined_frame = pd.concat(instrument_frames, ignore_index=True)
        instruments = [
            TradeableInstrument(
                symbol=row["symbol"],
                isin=row.get("isin", ""),
                market=row.get("market", ""),
                name=row.get("name", ""),
                currency=row.get("currency", ""),
                source_file=row.get("source_file", ""),
            )
            for row in combined_frame.to_dict(orient="records")
        ]
    LOGGER.info("Loaded %s tradeable instruments", len(instruments))
    return instruments


def build_stooq_lookup(
    entries: Sequence[StooqFile],
) -> tuple[dict[str, StooqFile], dict[str, StooqFile], dict[str, list[StooqFile]]]:
    """Create lookup dictionaries for Stooq tickers, stems, and base symbols."""
    by_ticker: dict[str, StooqFile] = {}
    by_stem: dict[str, StooqFile] = {}
    by_base: dict[str, list[StooqFile]] = {}
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
    candidates: list[str] = []

    normalized = original.replace(" ", "").upper()
    base, suffix = split_symbol(normalized)

    extensions = suffix_to_extensions(suffix, market)
    if suffix:
        candidates.extend([f"{base}{ext}".upper() for ext in extensions if ext])
        candidates.append(normalized.upper())
    else:
        candidates.append(base.upper())
        candidates.extend([f"{base}{ext}".upper() for ext in extensions if ext])
        if "." in normalized:
            candidates.append(normalized.upper())

    candidates.append(base.upper())

    desired_exts = [ext for ext in extensions if ext]
    if not desired_exts:
        desired_exts = [ext for ext in suffix_to_extensions("", market) if ext]

    base_upper = base.upper()
    for ext in desired_exts:
        key = (base_upper, ext.upper())
        candidates.extend([alias.upper() for alias in SYMBOL_ALIAS_MAP.get(key, [])])
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


def split_symbol(symbol: str) -> tuple[str, str]:
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
    by_ticker: dict[str, StooqFile],
    by_stem: dict[str, StooqFile],
    by_base: dict[str, list[StooqFile]],
) -> tuple[TradeableMatch | None, TradeableInstrument | None]:
    tried: list[str] = []
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
        candidate_ext = (
            candidate[candidate.find(".") :].upper() if "." in candidate else ""
        )
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
            desired_exts: list[str] = []
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

            if desired_exts_set and not any(
                ext in available_exts for ext in desired_exts_set
            ):
                continue

            preferred_exts = [ext for ext in desired_exts if ext]
            chosen: StooqFile | None = None
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
    by_ticker: dict[str, StooqFile],
    by_stem: dict[str, StooqFile],
    by_base: dict[str, list[StooqFile]],
    *,
    max_workers: int = 1,
) -> tuple[list[TradeableMatch], list[TradeableInstrument]]:
    """Match tradeable instruments to Stooq files."""
    matches: list[TradeableMatch] = []
    unmatched: list[TradeableInstrument] = []

    results = _run_in_parallel(
        _match_instrument,
        [(instrument, by_ticker, by_stem, by_base) for instrument in instruments],
        max_workers,
    )

    for match, missing in results:
        if match:
            matches.append(match)
        elif missing:
            unmatched.append(missing)

    LOGGER.info("Matched %s instruments, %s unmatched", len(matches), len(unmatched))
    return matches, unmatched


def _prepare_match_report_data(
    matches: Sequence[TradeableMatch],
    data_dir: Path,
    lse_currency_policy: str,
) -> tuple[
    list[dict[str, str]],
    dict[str, dict[str, str]],
    Counter,
    Counter,
    list[str],
    list[tuple[str, str, str]],
]:
    """Prepare data for the match report."""
    diagnostics_cache: dict[str, dict[str, str]] = {}
    currency_counts: Counter = Counter()
    data_status_counts: Counter = Counter()
    empty_tickers: list[str] = []
    flagged_samples: list[tuple[str, str, str]] = []
    rows: list[dict[str, str]] = []

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
                (match.instrument.symbol, match.stooq_file.ticker, data_flags),
            )
        rows.append(
            {
                "symbol": match.instrument.symbol,
                "isin": match.instrument.isin,
                "market": match.instrument.market,
                "name": match.instrument.name,
                "currency": match.instrument.currency,
                "matched_ticker": match.matched_ticker,
                "stooq_path": match.stooq_file.rel_path,
                "region": match.stooq_file.region,
                "category": match.stooq_file.category,
                "strategy": match.strategy,
                "source_file": match.instrument.source_file,
                "price_start": diagnostics["price_start"],
                "price_end": diagnostics["price_end"],
                "price_rows": diagnostics["price_rows"],
                "inferred_currency": inferred,
                "resolved_currency": resolved,
                "currency_status": currency_status,
                "data_status": data_status,
                "data_flags": data_flags,
            },
        )
    return (
        rows,
        diagnostics_cache,
        currency_counts,
        data_status_counts,
        empty_tickers,
        flagged_samples,
    )


def write_match_report(
    matches: Sequence[TradeableMatch],
    output_path: Path,
    data_dir: Path,
    *,
    lse_currency_policy: str,
) -> tuple[
    dict[str, dict[str, str]],
    Counter,
    Counter,
    list[str],
    list[tuple[str, str, str]],
]:
    """Persist the match report showing which tradeables map to which Stooq files."""
    (
        rows,
        diagnostics_cache,
        currency_counts,
        data_status_counts,
        empty_tickers,
        flagged_samples,
    ) = _prepare_match_report_data(matches, data_dir, lse_currency_policy)
    columns = [
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
    _write_report(rows, output_path, columns)
    LOGGER.info("Match report written to %s", output_path)
    return (
        diagnostics_cache,
        currency_counts,
        data_status_counts,
        empty_tickers,
        flagged_samples,
    )


def _write_report(
    data: Sequence[object],
    output_path: Path,
    columns: list[str],
) -> None:
    """Write a list of dataclasses to a CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if data and not isinstance(data[0], dict):
        records = [asdict(item) for item in data]
    else:
        records = data
    report_frame = pd.DataFrame.from_records(records, columns=columns)
    report_frame.to_csv(output_path, index=False)


def write_unmatched_report(
    unmatched: Sequence[TradeableInstrument],
    output_path: Path,
) -> None:
    """Persist the unmatched instrument list for manual follow-up."""
    columns = ["symbol", "isin", "market", "name", "currency", "source_file", "reason"]
    _write_report(unmatched, output_path, columns)
    LOGGER.info("Unmatched report written to %s", output_path)


def annotate_unmatched_instruments(
    unmatched: Sequence[TradeableInstrument],
    stooq_by_base: dict[str, list[StooqFile]],
    available_extensions: set[str],
) -> list[TradeableInstrument]:
    """Attach diagnostic reasons to unmatched instruments."""
    return [
        TradeableInstrument(
            symbol=instrument.symbol,
            isin=instrument.isin,
            market=instrument.market,
            name=instrument.name,
            currency=instrument.currency,
            source_file=instrument.source_file,
            reason=determine_unmatched_reason(
                instrument,
                stooq_by_base,
                available_extensions,
            ),
        )
        for instrument in unmatched
    ]


def export_tradeable_prices(
    matches: Sequence[TradeableMatch],
    data_dir: Path,
    dest_dir: Path,
    *,
    overwrite: bool = False,
    max_workers: int = 1,
    diagnostics: dict[str, dict[str, str]] | None = None,
    include_empty: bool = False,
) -> tuple[int, int]:
    """Convert matched Stooq price files into CSVs stored in the destination directory.

    Returns a tuple of (exported_count, skipped_count).
    """
    dest_dir.mkdir(parents=True, exist_ok=True)

    unique_matches: dict[str, TradeableMatch] = {}
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
        if not include_empty and (
            status in {"empty", "missing", "missing_file"}
            or (status.startswith("error:") if status else False)
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
            price_frame = pd.read_csv(
                source_path,
                header=None,
                names=STOOQ_COLUMNS,
                comment="<",
                dtype=str,
                encoding="utf-8",
                keep_default_na=False,
                na_filter=False,
            )
            if price_frame.empty and not include_empty:
                if target_path.exists() and overwrite:
                    try:
                        target_path.unlink()
                    except OSError as exc:
                        LOGGER.warning(
                            "Unable to remove empty export for %s: %s",
                            match.stooq_file.ticker,
                            exc,
                        )
                return False
            price_frame.to_csv(target_path, index=False)
            return True
        except OSError as exc:
            LOGGER.warning(
                "Failed to export %s -> %s: %s",
                source_path,
                target_path,
                exc,
            )
            return False

    results = _run_in_parallel(
        _export_single,
        [(m,) for m in unique_matches.values()],
        max_workers,
    )
    exported = sum(1 for r in results if r)

    LOGGER.info("Exported %s price files to %s", exported, dest_dir)
    if skipped:
        LOGGER.warning("Skipped %s price files without usable data", skipped)
    return exported, skipped


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
        export_tradeable_prices(
            matches,
            args.data_dir,
            args.prices_output,
            overwrite=args.overwrite_prices,
            max_workers=max_workers,
            diagnostics=diagnostics_cache,
            include_empty=args.include_empty_prices,
        )


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
