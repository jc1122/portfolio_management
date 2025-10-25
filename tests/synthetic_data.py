"""Synthetic data generator for end-to-end workflow tests.

This module builds a deterministic Stooq-style price tree, tradeable instrument
lists, and universe configuration files tailored for integration tests. The
synthetic market covers ~50 years of business-day prices across multiple asset
classes while injecting a variety of data-quality edge cases (missing files,
zero volume, sparse histories, negative prices, and gapped segments).
"""

from __future__ import annotations
import pytest

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

_START_DATE = "1975-01-02"
_END_DATE = "2024-12-31"
_BUSINESS_DATES = pd.date_range(_START_DATE, _END_DATE, freq="B")


@dataclass(frozen=True)
class SyntheticAssetSpec:
    """Configuration for a single synthetic asset."""

    ticker: str  # Stooq ticker including market extension (e.g., SYN_STOCK_01.US)
    symbol: str  # Broker symbol with suffix (e.g., SYN_STOCK_01:US)
    isin: str
    name: str
    market: str
    currency: str
    category: str  # Stooq category (stocks, bonds, reits, commodities, etc.)
    region: str  # Stooq region (world, us, etc.)
    scenario: str  # CLEAN, GAPPED, ZEROVOL, NEGPRICE, SPARSE, MISSING, LATESTART
    drift: float  # Annualised drift
    volatility: float  # Annualised volatility


@dataclass
class SyntheticDataset:
    """Output paths from the synthetic data generator."""

    root: Path
    stooq_dir: Path
    tradeable_dir: Path
    metadata_dir: Path
    prices_output_dir: Path
    universe_config: Path
    specs: list[SyntheticAssetSpec]


def _scenario_rotation() -> dict[str, list[str]]:
    """Return scenario rotations per asset sleeve."""
    rotation = [
        "CLEAN",
        "GAPPED",
        "ZEROVOL",
        "NEGPRICE",
        "SPARSE",
        "MISSING",
        "LATESTART",
        "CLEAN",
        "CLEAN",
        "CLEAN",
    ]
    return {
        "stocks": rotation,
        "bonds": rotation,
        "reits": rotation,
        "commodities": rotation,
    }


def _build_specs() -> list[SyntheticAssetSpec]:
    """Create asset specifications for the synthetic market."""
    specs: list[SyntheticAssetSpec] = []
    scenario_map = _scenario_rotation()

    sleeve_profiles = {
        "stocks": {
            "drift": 0.07,
            "volatility": 0.25,
            "region": "world",
            "category": "stocks",
            "name_suffix": "High Vol Equity",
        },
        "bonds": {
            "drift": 0.03,
            "volatility": 0.07,
            "region": "us",
            "category": "bonds",
            "name_suffix": "Investment Grade Bond",
        },
        "reits": {
            "drift": 0.05,
            "volatility": 0.18,
            "region": "world",
            "category": "reits",
            "name_suffix": "Global REIT",
        },
        "commodities": {
            "drift": 0.04,
            "volatility": 0.30,
            "region": "world",
            "category": "commodities",
            "name_suffix": "Alternative Strategy",
        },
    }

    for sleeve, profile in sleeve_profiles.items():
        for idx, scenario in enumerate(scenario_map[sleeve], start=1):
            ticker_base = f"SYN_{sleeve.upper()}_{idx:02d}"
            ticker = f"{ticker_base}.US"
            symbol = f"{ticker_base}:US"
            isin = f"US{hash(ticker) & 0xFFFFFFFF:08X}{idx:02d}"
            name = f"{ticker_base.replace('_', ' ')} {profile['name_suffix']}"
            specs.append(
                SyntheticAssetSpec(
                    ticker=ticker,
                    symbol=symbol,
                    isin=isin,
                    name=name,
                    market="NYSE",
                    currency="USD",
                    category=profile["category"],
                    region=profile["region"],
                    scenario=scenario,
                    drift=profile["drift"],
                    volatility=profile["volatility"],
                ),
            )
    return specs


def _render_line(
    ticker: str,
    date: pd.Timestamp,
    open_px: float | None,
    high_px: float | None,
    low_px: float | None,
    close_px: float | None,
    volume: float | None,
) -> str:
    """Format a single Stooq line."""

    def _fmt(value: float | None, precision: int = 2) -> str:
        if value is None or np.isnan(value):
            return ""
        return f"{value:.{precision}f}"

    open_str = _fmt(open_px)
    high_str = _fmt(high_px)
    low_str = _fmt(low_px)
    close_str = _fmt(close_px)
    volume_str = "" if volume is None or np.isnan(volume) else f"{int(volume)}"

    return ",".join(
        [
            ticker.upper(),
            "D",
            date.strftime("%Y%m%d"),
            "000000",
            open_str,
            high_str,
            low_str,
            close_str,
            volume_str,
            "0",
        ],
    )


def _price_path_for_scenario(
    spec: SyntheticAssetSpec,
    rng: np.random.Generator,
) -> tuple[pd.DatetimeIndex, np.ndarray, np.ndarray]:
    """Generate synthetic price/volume paths according to the scenario."""
    dates = _BUSINESS_DATES
    if spec.scenario == "LATESTART":
        dates = pd.date_range("2015-01-02", _END_DATE, freq="B")
    elif spec.scenario == "SPARSE":
        dates = pd.date_range(_END_DATE, periods=1, freq="B")

    steps = len(dates)
    if steps == 0:
        return dates, np.array([]), np.array([])

    daily_drift = spec.drift / 252
    daily_vol = spec.volatility / np.sqrt(252)
    base_returns = rng.normal(daily_drift, daily_vol, size=steps)
    prices = 100.0 * np.exp(np.cumsum(base_returns))

    volumes = rng.lognormal(mean=10, sigma=0.5, size=steps)

    if spec.scenario == "ZEROVOL":
        mask = rng.random(size=steps) < 0.65
        volumes[mask] = 0.0
    if spec.scenario == "NEGPRICE" and steps > 10:
        idx = int(steps * 0.4)
        prices[idx] = -abs(prices[idx])
    if spec.scenario == "GAPPED" and steps > 200:
        start = int(steps * 0.5)
        end = min(steps, start + 20)
        prices[start:end] = np.nan
        volumes[start:end] = 0.0

    return dates, prices, volumes


def _write_price_file(
    base_dir: Path,
    spec: SyntheticAssetSpec,
    rng: np.random.Generator,
) -> None:
    """Write a Stooq-style TXT file for the given asset spec."""
    if spec.scenario == "MISSING":
        return

    dates, prices, volumes = _price_path_for_scenario(spec, rng)
    if dates.empty:
        return

    if spec.category == "bonds":
        rel_dir = base_dir / "daily" / spec.region / "bonds"
    elif spec.category == "reits":
        rel_dir = base_dir / "daily" / spec.region / "reits"
    elif spec.category == "commodities":
        rel_dir = base_dir / "daily" / spec.region / "commodities"
    else:
        rel_dir = base_dir / "daily" / spec.region / "stocks"

    rel_dir.mkdir(parents=True, exist_ok=True)
    file_path = rel_dir / f"{spec.ticker.lower()}.txt"

    lines: list[str] = []
    for date, close_px, volume in zip(dates, prices, volumes):
        if spec.scenario == "SPARSE":
            open_px = close_px
            high_px = close_px
            low_px = close_px
        else:
            noise = rng.normal(0, 0.003)
            open_px = close_px * (1 + noise)
            high_px = max(open_px, close_px) * (1 + abs(rng.normal(0, 0.01)))
            low_px = min(open_px, close_px) * (1 - abs(rng.normal(0, 0.01)))

        if np.isnan(close_px):
            open_px = high_px = low_px = np.nan
        lines.append(
            _render_line(
                spec.ticker,
                date,
                open_px,
                high_px,
                low_px,
                close_px,
                volume,
            ),
        )

    file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_tradeable_instruments(
    tradeable_dir: Path,
    specs: Iterable[SyntheticAssetSpec],
    rng: np.random.Generator,
) -> None:
    """Create broker tradeable CSVs from specs."""
    tradeable_dir.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "symbol": spec.symbol,
            "isin": spec.isin,
            "market": spec.market,
            "name": spec.name,
            "currency": spec.currency,
        }
        for spec in specs
    ]

    # Append unmatched decoy instrument
    rows.append(
        {
            "symbol": "SYN_UNKNOWN_01:US",
            "isin": "USFFFF000001",
            "market": "NASDAQ",
            "name": "Synthetic Unknown Asset",
            "currency": "USD",
        },
    )

    frame = pd.DataFrame(rows)
    frame = frame.sample(frac=1.0, random_state=rng.integers(0, 2**32 - 1)).reset_index(
        drop=True,
    )
    midpoint = len(frame) // 2
    frame.iloc[:midpoint].to_csv(tradeable_dir / "broker_a.csv", index=False)
    frame.iloc[midpoint:].to_csv(tradeable_dir / "broker_b.csv", index=False)


def _write_universe_config(
    config_path: Path,
    specs: Iterable[SyntheticAssetSpec],
) -> None:
    """Persist a YAML universe configuration referencing generated assets."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    universe_config = {
        "universes": {
            "synthetic_strict": {
                "description": "Strict synthetic universe excluding warnings.",
                "filter_criteria": {
                    "data_status": ["ok"],
                    "min_history_days": 4000,
                    "min_price_rows": 4000,
                },
                "return_config": {
                    "method": "log",
                    "frequency": "monthly",
                    "handle_missing": "forward_fill",
                },
                "constraints": {"max_assets": 20},
            },
            "synthetic_balanced": {
                "description": "Balanced synthetic universe allowing warnings.",
                "filter_criteria": {
                    "data_status": ["ok", "warning"],
                    "min_history_days": 2000,
                    "min_price_rows": 2000,
                },
                "return_config": {
                    "method": "simple",
                    "frequency": "weekly",
                    "handle_missing": "interpolate",
                },
                "constraints": {"max_assets": 24},
            },
        },
    }
    with config_path.open("w", encoding="utf-8") as stream:
        yaml.safe_dump(universe_config, stream, sort_keys=False)


def generate_synthetic_market(
    root: Path,
    *,
    seed: int = 7,
) -> SyntheticDataset:
    """Generate synthetic Stooq-style fixtures under *root*."""
    rng = np.random.default_rng(seed)
    specs = _build_specs()

    stooq_dir = root / "stooq"
    tradeable_dir = root / "tradeable_instruments"
    metadata_dir = root / "metadata"
    prices_output_dir = root / "processed_prices"
    universe_config = root / "config" / "universes.yaml"

    stooq_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)
    prices_output_dir.mkdir(parents=True, exist_ok=True)

    for spec in specs:
        _write_price_file(stooq_dir, spec, rng)

    _write_tradeable_instruments(tradeable_dir, specs, rng)
    _write_universe_config(universe_config, specs)

    return SyntheticDataset(
        root=root,
        stooq_dir=stooq_dir,
        tradeable_dir=tradeable_dir,
        metadata_dir=metadata_dir,
        prices_output_dir=prices_output_dir,
        universe_config=universe_config,
        specs=specs,
    )
