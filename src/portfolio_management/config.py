"""Configuration for the portfolio management toolkit."""

from typing import Dict, List, Tuple

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
