"""Diagnostics and currency helpers for Stooq price data.

This module centralizes the data-quality analysis utilities that power the
tradeable preparation pipeline. It exposes helpers for summarizing price files,
inferring listing currencies, and maintaining aggregated diagnostics that the
CLI scripts re-export for downstream workflows.

Key Functions:
    summarize_price_file: Stream through Stooq file to compute diagnostics (NEW: streaming)
    summarize_clean_price_frame: Compute diagnostics from existing DataFrame
    infer_currency: Guess trading currency from Stooq metadata
    resolve_currency: Reconcile broker vs. Stooq currency with LSE policy

Performance:
    The streaming implementation (_stream_stooq_file_for_diagnostics) reduces memory
    usage by 43.7% compared to loading full DataFrames, with only an 8.8% time overhead.
    This is critical when processing 70,000+ files in production.

    For details, see docs/streaming_performance.md
"""

from __future__ import annotations

import logging
import pathlib
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

from portfolio_management.core.config import REGION_CURRENCY_MAP, STOOQ_COLUMNS
from portfolio_management.core.exceptions import DependencyNotInstalledError

if TYPE_CHECKING:
    from portfolio_management.data.models import StooqFile, TradeableInstrument

try:
    import pandas as pd
except ImportError as exc:  # pragma: no cover - pandas is required for this module
    raise DependencyNotInstalledError(
        "pandas",
        context="to run analysis routines",
    ) from exc

LOGGER = logging.getLogger(__name__)

# Columns required for diagnostics. Using a minimal subset avoids parsing
# unused values from every Stooq file during summarisation.
SUMMARY_COLUMNS: Sequence[str] = ("date", "close", "volume")

# Constants for zero volume thresholds
ZERO_VOLUME_CRITICAL_THRESHOLD = 0.5
ZERO_VOLUME_HIGH_THRESHOLD = 0.1
ZERO_VOLUME_MODERATE_THRESHOLD = 0.01


def _read_stooq_csv(
    file_path: pathlib.Path,
    engine: str,
    *,
    columns: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Read a Stooq CSV file with the specified engine."""
    read_kwargs = {
        "header": None,
        "names": STOOQ_COLUMNS,
        "comment": "<",
        "dtype": str,
        "engine": engine,
        "encoding": "utf-8",
        "keep_default_na": False,
        "na_filter": False,
    }
    if columns is not None:
        read_kwargs["usecols"] = list(columns)
    return pd.read_csv(file_path, **read_kwargs)


def _stream_stooq_file_for_diagnostics(
    file_path: pathlib.Path,
) -> tuple[dict[str, str], str]:
    """Stream through a Stooq file to compute diagnostics without loading entire file.

    This function reads the file in chunks and accumulates statistics incrementally,
    significantly reducing memory usage compared to loading the full DataFrame.

    Returns:
        Tuple of (diagnostics dict, status string)

    """
    if not file_path.exists():
        return _initialize_diagnostics(), "missing_file"

    # Statistics to accumulate
    valid_row_count = 0
    invalid_row_count = 0
    non_numeric_prices = 0
    non_positive_close = 0
    missing_volume = 0
    zero_volume = 0
    first_valid_date = None
    last_valid_date = None
    previous_date = None
    has_duplicate_dates = False
    has_non_monotonic_dates = False
    seen_date_ints: set[int] | None = set()

    # Read file in chunks
    chunk_size = 10000
    try:
        # Try fast C engine first
        try:
            chunks = pd.read_csv(
                file_path,
                header=None,
                names=STOOQ_COLUMNS,
                comment="<",
                dtype=str,
                engine="c",
                encoding="utf-8",
                keep_default_na=False,
                na_filter=False,
                usecols=list(SUMMARY_COLUMNS),
                chunksize=chunk_size,
            )
        except (ValueError, pd.errors.ParserError):
            # Fall back to Python engine
            chunks = pd.read_csv(
                file_path,
                header=None,
                names=STOOQ_COLUMNS,
                comment="<",
                dtype=str,
                engine="python",
                encoding="utf-8",
                keep_default_na=False,
                na_filter=False,
                usecols=list(SUMMARY_COLUMNS),
                chunksize=chunk_size,
            )

        first_chunk = True
        for raw_chunk in chunks:
            # Strip whitespace from all columns
            chunk = raw_chunk.apply(lambda col: col.str.strip())

            # Skip header row if present (only in first chunk)
            if first_chunk:
                first_row = chunk.iloc[0] if not chunk.empty else None
                if first_row is not None and all(
                    isinstance(first_row[column], str)
                    and first_row[column].lower() == column
                    for column in chunk.columns
                ):
                    chunk = chunk.iloc[1:]
                first_chunk = False

            if chunk.empty:
                continue

            # Parse dates
            date_series = pd.to_datetime(
                chunk["date"],
                format="%Y%m%d",
                errors="coerce",
            )
            invalid_in_chunk = int(date_series.isna().sum())
            invalid_row_count += invalid_in_chunk

            # Filter to valid dates
            valid_mask = date_series.notna()
            valid_dates_in_chunk = date_series[valid_mask]
            chunk_valid = chunk[valid_mask]

            if valid_dates_in_chunk.empty:
                continue

            valid_row_count += len(chunk_valid)

            # Track date range
            chunk_first_date = valid_dates_in_chunk.iloc[0]
            chunk_last_date = valid_dates_in_chunk.iloc[-1]

            if first_valid_date is None:
                first_valid_date = chunk_first_date
            last_valid_date = chunk_last_date

            # Check for duplicate dates within and across chunks
            if not has_duplicate_dates:
                if bool(valid_dates_in_chunk.duplicated().any()):
                    has_duplicate_dates = True
                    seen_date_ints = None
                elif seen_date_ints is not None:
                    date_int_values = valid_dates_in_chunk.astype("int64", copy=False)
                    for date_value in date_int_values:
                        if date_value in seen_date_ints:
                            has_duplicate_dates = True
                            seen_date_ints = None
                            break
                    else:
                        seen_date_ints.update(int(value) for value in date_int_values)

            # Check for non-monotonic dates (between chunks and within chunk)
            if previous_date is not None and chunk_first_date < previous_date:
                has_non_monotonic_dates = True
            if (
                not has_non_monotonic_dates
                and not valid_dates_in_chunk.is_monotonic_increasing
            ):
                has_non_monotonic_dates = True

            previous_date = chunk_last_date

            # Parse close prices
            close_numeric = pd.to_numeric(chunk_valid["close"], errors="coerce")
            non_numeric_prices += int(close_numeric.isna().sum())
            non_positive_close += int((close_numeric[close_numeric.notna()] <= 0).sum())

            # Parse volume
            volume_numeric = pd.to_numeric(chunk_valid["volume"], errors="coerce")
            missing_volume += int(volume_numeric.isna().sum())
            zero_volume += int((volume_numeric == 0).sum())

    except (pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
        return _initialize_diagnostics(), f"error:{exc.__class__.__name__}"
    except OSError as exc:
        return _initialize_diagnostics(), f"error:{exc.__class__.__name__}"

    # Build diagnostics
    diagnostics = _initialize_diagnostics()

    if valid_row_count == 0:
        diagnostics["data_status"] = "empty"
        return diagnostics, "empty"

    # Calculate zero volume ratio
    zero_volume_ratio = (zero_volume / valid_row_count) if valid_row_count else 0.0

    # Determine severity
    zero_volume_severity = (
        _determine_zero_volume_severity(zero_volume_ratio) if zero_volume else None
    )

    # Generate flags
    flags = _generate_flags(
        invalid_rows=invalid_row_count,
        non_numeric_prices=non_numeric_prices,
        non_positive_close=non_positive_close,
        missing_volume=missing_volume,
        zero_volume=zero_volume,
        zero_volume_ratio=zero_volume_ratio,
        zero_volume_severity=zero_volume_severity,
        duplicate_dates=has_duplicate_dates,
        non_monotonic_dates=has_non_monotonic_dates,
    )

    # Populate diagnostics
    diagnostics["price_start"] = first_valid_date.date().isoformat()
    diagnostics["price_end"] = last_valid_date.date().isoformat()
    diagnostics["price_rows"] = str(valid_row_count)
    diagnostics["data_status"] = _determine_data_status(
        valid_row_count,
        zero_volume_severity,
        has_flags=bool(flags),
    )
    diagnostics["data_flags"] = ";".join(flags)

    return diagnostics, "ok"


def _read_and_clean_stooq_csv(
    file_path: pathlib.Path,
    *,
    columns: Sequence[str] | None = SUMMARY_COLUMNS,
) -> tuple[pd.DataFrame | None, str]:
    """Read and clean a Stooq CSV file, handling errors and initial validation."""
    if not file_path.exists():
        return None, "missing_file"

    try:
        try:
            raw_price_frame = _read_stooq_csv(
                file_path,
                "c",
                columns=columns,
            )
        except (ValueError, pd.errors.ParserError):
            raw_price_frame = _read_stooq_csv(
                file_path,
                "python",
                columns=columns,
            )
    except (pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
        return None, f"error:{exc.__class__.__name__}"
    except OSError as exc:
        return None, f"error:{exc.__class__.__name__}"

    if raw_price_frame.empty:
        return None, "empty"

    raw_price_frame = raw_price_frame.apply(lambda col: col.str.strip())

    if not raw_price_frame.empty:
        first_row = raw_price_frame.iloc[0]
        if all(
            isinstance(first_row[column], str) and first_row[column].lower() == column
            for column in raw_price_frame.columns
        ):
            raw_price_frame = raw_price_frame.iloc[1:].copy()

    if raw_price_frame.empty:
        return None, "empty"

    return raw_price_frame, "ok"


def _validate_dates(
    price_frame: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series, int]:
    """Validate dates and filter out invalid rows."""
    date_series = pd.to_datetime(
        price_frame["date"],
        format="%Y%m%d",
        errors="coerce",
    )
    invalid_rows = int(date_series.isna().sum())
    valid_mask = date_series.notna()
    valid_price_frame = price_frame.loc[valid_mask].copy()
    valid_dates = date_series.loc[valid_mask]
    return valid_price_frame, valid_dates, invalid_rows


def _calculate_data_quality_metrics(
    valid_price_frame: pd.DataFrame,
    valid_dates: pd.Series,
) -> dict[str, int | float | bool]:
    """Calculate data quality metrics from a validated price frame."""
    row_count = len(valid_price_frame)
    close_numeric = pd.to_numeric(valid_price_frame["close"], errors="coerce")
    volume_numeric = pd.to_numeric(valid_price_frame["volume"], errors="coerce")

    non_numeric_prices = int(close_numeric.isna().sum())
    non_positive_close = int((close_numeric[close_numeric.notna()] <= 0).sum())
    missing_volume = int(volume_numeric.isna().sum())
    zero_volume = int((volume_numeric == 0).sum())

    duplicate_dates = bool(valid_dates.duplicated().any())
    non_monotonic_dates = not bool(valid_dates.is_monotonic_increasing)

    zero_volume_ratio = (zero_volume / row_count) if row_count else 0.0

    return {
        "non_numeric_prices": non_numeric_prices,
        "non_positive_close": non_positive_close,
        "missing_volume": missing_volume,
        "zero_volume": zero_volume,
        "duplicate_dates": duplicate_dates,
        "non_monotonic_dates": non_monotonic_dates,
        "zero_volume_ratio": zero_volume_ratio,
    }


def _determine_zero_volume_severity(zero_volume_ratio: float) -> str | None:
    """Determine the severity of zero volume data."""
    if zero_volume_ratio >= ZERO_VOLUME_CRITICAL_THRESHOLD:
        return "critical"
    if zero_volume_ratio >= ZERO_VOLUME_HIGH_THRESHOLD:
        return "high"
    if zero_volume_ratio >= ZERO_VOLUME_MODERATE_THRESHOLD:
        return "moderate"
    return "low"


def _generate_flags(  # noqa: PLR0913
    *,
    invalid_rows: int,
    non_numeric_prices: int,
    non_positive_close: int,
    missing_volume: int,
    zero_volume: int,
    zero_volume_ratio: float,
    zero_volume_severity: str | None,
    duplicate_dates: bool,
    non_monotonic_dates: bool,
) -> list[str]:
    """Generate a list of data quality flags from metrics."""
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
    return flags


def _initialize_diagnostics() -> dict[str, str]:
    """Create a diagnostics dictionary with default values."""
    return {
        "price_start": "",
        "price_end": "",
        "price_rows": "0",
        "data_status": "missing",
        "data_flags": "",
    }


def _determine_data_status(
    row_count: int,
    zero_volume_severity: str | None,
    *,
    has_flags: bool,
) -> str:
    """Determine the data status based on row count, volume severity, and flags."""
    if row_count <= 1:
        return "sparse"
    if zero_volume_severity or has_flags:
        return "warning"
    return "ok"


def _summarize_valid_frame(
    valid_price_frame: pd.DataFrame,
    valid_dates: pd.Series,
    invalid_rows: int,
) -> dict[str, str]:
    """Build diagnostics from a validated price frame."""
    diagnostics = _initialize_diagnostics()
    if valid_price_frame.empty or valid_dates.empty:
        diagnostics["data_status"] = "empty"
        return diagnostics

    row_count = len(valid_price_frame)
    first_date = valid_dates.iloc[0]
    last_date = valid_dates.iloc[-1]
    metrics = _calculate_data_quality_metrics(valid_price_frame, valid_dates)

    zero_volume_severity = (
        _determine_zero_volume_severity(metrics["zero_volume_ratio"])
        if metrics["zero_volume"]
        else None
    )
    flags = _generate_flags(
        invalid_rows=invalid_rows,
        zero_volume_severity=zero_volume_severity,
        **metrics,
    )

    diagnostics["price_start"] = first_date.date().isoformat()
    diagnostics["price_end"] = last_date.date().isoformat()
    diagnostics["price_rows"] = str(row_count)
    diagnostics["data_status"] = _determine_data_status(
        row_count,
        zero_volume_severity,
        has_flags=bool(flags),
    )
    diagnostics["data_flags"] = ";".join(flags)

    return diagnostics


def summarize_price_file(
    base_dir: pathlib.Path,
    stooq_file: StooqFile,
) -> dict[str, str]:
    """Extract diagnostics and validation flags from a Stooq price file.

    This function uses a streaming approach to minimize memory usage by reading
    the file in chunks and accumulating statistics incrementally, rather than
    loading the entire file into a DataFrame.

    Pipeline:
    1. Stream through the CSV file in chunks
    2. Validate dates and extract valid rows incrementally
    3. Accumulate data quality metrics
    4. Generate diagnostic flags
    5. Determine overall data status

    Returns:
        Dictionary with keys: price_start, price_end, price_rows, data_status, data_flags

    """
    file_path = base_dir / stooq_file.rel_path
    diagnostics, status = _stream_stooq_file_for_diagnostics(file_path)

    # If status is not "ok", update data_status accordingly
    if status != "ok":
        diagnostics["data_status"] = status

    return diagnostics


def summarize_clean_price_frame(price_frame: pd.DataFrame) -> dict[str, str]:
    """Generate diagnostics from an already cleaned Stooq price frame."""
    valid_price_frame, valid_dates, invalid_rows = _validate_dates(price_frame)
    return _summarize_valid_frame(valid_price_frame, valid_dates, invalid_rows)


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


def log_summary_counts(
    currency_counts: Mapping[str, int],
    data_status_counts: Mapping[str, int],
) -> None:
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
