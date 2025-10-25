"""Data models for Stooq files, tradeable instruments, and pipeline configurations.

This module defines the core data structures used throughout the data processing
pipeline. These models ensure that data is handled in a consistent and
type-safe manner.

Key Classes:
    - StooqFile: Represents a Stooq price file with its metadata.
    - TradeableInstrument: Represents a tradeable instrument from a broker.
    - TradeableMatch: Links a `TradeableInstrument` to a `StooqFile`.
    - ExportConfig: Configuration for exporting price data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class StooqFile:
    """Represents a Stooq price file with its associated metadata.

    Attributes:
        ticker: The full ticker symbol (e.g., 'AAPL.US').
        stem: The base part of the ticker, without the extension.
        rel_path: The relative path to the data file.
        region: The geographical or market region (e.g., 'us', 'uk').
        category: The market category (e.g., 'nasdaq stocks').
    """

    ticker: str
    stem: str
    rel_path: str
    region: str = ""
    category: str = ""


@dataclass
class TradeableInstrument:
    """Represents a tradeable instrument from a broker's data.

    Attributes:
        symbol: The broker's symbol for the instrument.
        isin: The International Securities Identification Number.
        market: The market or exchange where the instrument is traded.
        name: The name of the instrument.
        currency: The currency in which the instrument is traded.
        source_file: The original file from which this instrument was loaded.
        reason: If unmatched, the reason for the failure.
    """

    symbol: str
    isin: str
    market: str
    name: str
    currency: str
    source_file: str
    reason: str = ""  # Unmatched reason, if any


@dataclass
class TradeableMatch:
    """Represents a successful match between a tradeable instrument and a Stooq file.

    Attributes:
        instrument: The `TradeableInstrument` that was matched.
        stooq_file: The `StooqFile` that it was matched to.
        matched_ticker: The specific Stooq ticker that was matched.
        strategy: The matching strategy that succeeded (e.g., 'ticker', 'base_market').
    """

    instrument: TradeableInstrument
    stooq_file: StooqFile
    matched_ticker: str
    strategy: str


@dataclass
class ExportConfig:
    """Configuration settings for exporting tradeable price files.

    Attributes:
        data_dir: The root directory of the Stooq data.
        dest_dir: The destination directory for the exported CSV files.
        overwrite: If True, existing files will be overwritten.
        include_empty: If True, files with no data will still be exported.
        max_workers: The maximum number of parallel workers for the export.
        diagnostics: A cache of pre-computed diagnostics to speed up processing.
    """

    data_dir: Path
    dest_dir: Path
    overwrite: bool = False
    include_empty: bool = False
    max_workers: int | None = None
    diagnostics: dict[str, dict[str, str]] = field(default_factory=dict)