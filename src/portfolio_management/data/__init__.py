"""Data management package for portfolio analysis.

This package provides tools for ingesting, processing, and caching financial data,
primarily from Stooq and broker-provided tradeable instrument lists. It forms
the data foundation for portfolio construction and analysis workflows.

Key Modules:
    - ingestion: Tools for scanning and indexing raw Stooq data files.
    - io: High-level I/O operations for reading/writing analysis-ready data.
    - cache: Caching and change detection to accelerate data pipelines.
    - matching: Logic for matching tradeable instruments to Stooq tickers.
    - models: Data models for representing instruments, matches, and files.
    - analysis: Functions for data quality analysis and currency resolution.

Usage Example:
    >>> from portfolio_management.data.io import read_stooq_index
    >>> from pathlib import Path
    >>>
    >>> # Load a pre-built index of Stooq data
    >>> index_path = Path("cache/stooq_index.csv")
    >>> if index_path.exists():
    ...     stooq_files = read_stooq_index(index_path)
    ...     print(f"Loaded {len(stooq_files)} Stooq file entries.")

"""

from portfolio_management.data import analysis, ingestion, io, matching, models

__all__ = [
    "analysis",
    "ingestion",
    "io",
    "matching",
    "models",
]
