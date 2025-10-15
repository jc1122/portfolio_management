from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path

try:
    import pandas as pd
except ImportError as exc:  # pragma: no cover - pandas is required for this module
    raise ImportError(
        "pandas is required to run io.py. "
        "Please install pandas before using this module.",
    ) from exc

from collections import Counter
from dataclasses import asdict

from .analysis import infer_currency, resolve_currency, summarize_price_file
from .config import STOOQ_COLUMNS
from .models import ExportConfig, StooqFile, TradeableInstrument, TradeableMatch
from .utils import _run_in_parallel

LOGGER = logging.getLogger(__name__)


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


def _prepare_match_report_data(
    matches: Sequence[TradeableMatch],
    data_dir: Path,
    lse_currency_policy: str,
) -> tuple[
    list[dict[str, str]],
    dict[str, dict[str, str]],
    Counter[str],
    Counter[str],
    list[str],
    list[tuple[str, str, str]],
]:
    """Prepare data for the match report."""
    diagnostics_cache: dict[str, dict[str, str]] = {}
    currency_counts: Counter[str] = Counter()
    data_status_counts: Counter[str] = Counter()
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
    Counter[str],
    Counter[str],
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


def export_tradeable_prices(
    matches: Sequence[TradeableMatch],
    config: ExportConfig,
) -> tuple[int, int]:
    """Convert matched Stooq price files into CSVs stored in the destination directory.

    Returns a tuple of (exported_count, skipped_count).
    """
    config.dest_dir.mkdir(parents=True, exist_ok=True)

    unique_matches: dict[str, TradeableMatch] = {}
    for match in matches:
        ticker_upper = match.stooq_file.ticker.upper()
        unique_matches.setdefault(ticker_upper, match)

    skipped = 0

    def _export_single(match: TradeableMatch) -> bool:
        nonlocal skipped
        source_path = config.data_dir / match.stooq_file.rel_path
        target_path = config.dest_dir / f"{match.stooq_file.ticker.lower()}.csv"
        diag = (
            config.diagnostics.get(match.stooq_file.ticker.upper())
            if config.diagnostics
            else None
        )
        if diag is None:
            diag = summarize_price_file(config.data_dir, match.stooq_file)
        status = diag.get("data_status", "")
        if not config.include_empty and (
            status in {"empty", "missing", "missing_file"}
            or (status.startswith("error:") if status else False)
        ):
            LOGGER.debug(
                "Skipping export for %s due to data_status=%s",
                match.stooq_file.ticker,
                status,
            )
            skipped += 1
            if target_path.exists() and config.overwrite:
                try:
                    target_path.unlink()
                except OSError as exc:
                    LOGGER.warning(
                        "Unable to remove stale export for %s: %s",
                        match.stooq_file.ticker,
                        exc,
                    )
            return False
        if target_path.exists() and not config.overwrite:
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
            if price_frame.empty and not config.include_empty:
                if target_path.exists() and config.overwrite:
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
        config.max_workers,
    )
    exported = sum(1 for r in results if r)

    LOGGER.info("Exported %s price files to %s", exported, config.dest_dir)
    if skipped:
        LOGGER.warning("Skipped %s price files without usable data", skipped)
    return exported, skipped
