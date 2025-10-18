"""Data models for return calculation."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class ReturnSummary:
    """Summary statistics produced alongside prepared returns."""

    mean_returns: pd.Series
    volatility: pd.Series
    correlation: pd.DataFrame
    coverage: pd.Series
