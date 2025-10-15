"""Domain models and dataclasses for the portfolio management toolkit.

This module defines the core data structures used throughout the system:

- StooqFile: Metadata about Stooq price files in the index
- TradeableInstrument: A financial instrument from a broker's universe
- TradeableMatch: A successful match between an instrument and a Stooq file
- ExportConfig: Configuration for exporting price data
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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


@dataclass
class ExportConfig:
    """Configuration for exporting tradeable prices."""

    data_dir: Path
    dest_dir: Path
    overwrite: bool = False
    max_workers: int = 1
    diagnostics: dict[str, dict[str, str]] | None = None
    include_empty: bool = False
