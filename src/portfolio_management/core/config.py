"""Global configuration constants for the portfolio management toolkit.

This module centralizes static configuration variables used throughout the
application, from data processing to region-specific settings. Grouping these
constants here ensures consistency and simplifies maintenance.

Constants:
    REGION_CURRENCY_MAP (dict[str, str]): Maps region codes (e.g., "us", "uk")
        to their respective currency codes (e.g., "USD", "GBP").
    LEGACY_PREFIXES (tuple[str, ...]): A tuple of legacy ticker prefixes
        that may need to be handled or stripped during data processing.
    SYMBOL_ALIAS_MAP (dict[tuple[str, str], list[str]]): A mapping to resolve
        ticker symbol changes over time. The key is a tuple of the old
        ticker and its exchange, and the value is a list of new tickers.
    STOOQ_COLUMNS (list[str]): Defines the standard column order and names
        expected in Stooq data files.
    STOOQ_PANDAS_COLUMNS (list[str]): A subset of `STOOQ_COLUMNS` used when
        loading data into pandas DataFrames, focusing on essential fields.

Example:
    >>> from portfolio_management.core.config import (
    ...     REGION_CURRENCY_MAP,
    ...     STOOQ_COLUMNS
    ... )
    >>>
    >>> print(f"Currency for US region: {REGION_CURRENCY_MAP.get('us')}")
    Currency for US region: USD
    >>>
    >>> # Check if 'ticker' is a required column for Stooq data
    >>> 'ticker' in STOOQ_COLUMNS
    True
"""

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
SYMBOL_ALIAS_MAP: dict[tuple[str, str], list[str]] = {
    ("FB", ".US"): ["META.US"],
    ("BRKS", ".US"): ["AZTA.US"],
    ("PKI", ".US"): ["RVTY.US"],
    ("FISV", ".US"): ["FI.US"],
    ("FBHS", ".US"): ["FBIN.US"],
    ("NRZ", ".US"): ["RITM.US"],
    ("DWAV", ".US"): ["QBTS.US"],
}

STOOQ_COLUMNS = [
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

STOOQ_PANDAS_COLUMNS = ["date", "close", "volume"]
