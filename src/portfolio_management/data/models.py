"""Data models for Stooq files and tradeable instruments."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class StooqFile:
    """Represents a Stooq price file with metadata."""

    ticker: str
    stem: str
    rel_path: str
    region: str = ""
    category: str = ""


@dataclass
class TradeableInstrument:
    """Represents a tradeable instrument from broker data."""

    symbol: str
    isin: str
    market: str
    name: str
    currency: str
    source_file: str
    reason: str = ""  # Unmatched reason, if any


@dataclass
class TradeableMatch:
    """Represents a successful match between tradeable instrument and Stooq file."""

    instrument: TradeableInstrument
    stooq_file: StooqFile
    matched_ticker: str
    strategy: str


@dataclass
class ExportConfig:
    """Configuration for exporting tradeable price files."""

    data_dir: Path
    dest_dir: Path
    overwrite: bool = False
    include_empty: bool = False
    max_workers: int | None = None
    diagnostics: dict[str, dict[str, str]] = field(default_factory=dict)
