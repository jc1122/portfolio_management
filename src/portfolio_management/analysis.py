"""Diagnostics and currency helpers for Stooq price data.

This module centralizes the data-quality analysis utilities that power the
tradeable preparation pipeline. It exposes helpers for summarizing price files,
inferring listing currencies, and maintaining aggregated diagnostics that the
CLI scripts re-export for downstream workflows.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .exceptions import DependencyNotInstalledError

try:
    import pandas as pd
except ImportError as exc:  # pragma: no cover - pandas is required for this module
    raise DependencyNotInstalledError(
        "pandas",
        context="to run analysis routines",
    ) from exc

from .config import REGION_CURRENCY_MAP, STOOQ_COLUMNS

if TYPE_CHECKING:
    from collections import Counter
    from collections.abc import Sequence
    from pathlib import Path

    from .models import StooqFile, TradeableInstrument

LOGGER = logging.getLogger(__name__)

# Constants for zero volume thresholds
ZERO_VOLUME_CRITICAL_THRESHOLD = 0.5
ZERO_VOLUME_HIGH_THRESHOLD = 0.1
ZERO_VOLUME_MODERATE_THRESHOLD = 0.01


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


def _read_and_clean_stooq_csv(
    file_path: Path,
) -> tuple[pd.DataFrame | None, str]:
    """Read and clean a Stooq CSV file, handling errors and initial validation."""
    if not file_path.exists():
        return None, "missing_file"

    try:
        try:
            raw_price_frame = _read_stooq_csv(file_path, "c")
        except (ValueError, pd.errors.ParserError):
            raw_price_frame = _read_stooq_csv(file_path, "python")
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


def summarize_price_file(base_dir: Path, stooq_file: StooqFile) -> dict[str, str]:
    """Extract diagnostics and validation flags from a Stooq price file.

    Pipeline:
    1. Read and clean the CSV file
    2. Validate dates and extract valid rows
    3. Calculate data quality metrics
    4. Generate diagnostic flags
    5. Determine overall data status
    """
    file_path = base_dir / stooq_file.rel_path
    diagnostics = _initialize_diagnostics()

    # Step 1: Read and clean
    raw_price_frame, status = _read_and_clean_stooq_csv(file_path)
    if raw_price_frame is None:
        diagnostics["data_status"] = status
        return diagnostics

    # Step 2: Validate dates
    valid_price_frame, valid_dates, invalid_rows = _validate_dates(raw_price_frame)
    if valid_price_frame.empty or valid_dates.empty:
        diagnostics["data_status"] = "empty"
        return diagnostics

    # Step 3: Calculate metrics
    row_count = len(valid_price_frame)
    first_date = valid_dates.iloc[0]
    last_date = valid_dates.iloc[-1]
    metrics = _calculate_data_quality_metrics(valid_price_frame, valid_dates)

    # Step 4: Determine zero volume severity and generate flags
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

    # Step 5: Build results
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
    currency_counts: Counter[str],
    data_status_counts: Counter[str],
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
