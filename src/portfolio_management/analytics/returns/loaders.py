"""Price data loaders for return calculation."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from ...assets.selection.selection import SelectedAsset

logger = logging.getLogger(__name__)


class PriceLoader:
    """Utilities for reading price files into pandas objects."""

    def load_price_file(self, path: Path) -> pd.Series:
        """Load a single price file into a ``Series`` indexed by date."""
        if not path.exists():
            raise FileNotFoundError(path)

        if path.suffix.lower() == ".csv":
            df = pd.read_csv(
                path,
                header=0,
                usecols=["date", "close"],
                parse_dates=["date"],
                index_col="date",
            )
        else:
            raw = pd.read_csv(path, header=0)
            if "<DATE>" in raw.columns and "<CLOSE>" in raw.columns:
                df = (
                    raw[["<DATE>", "<CLOSE>"]]
                    .copy()
                    .rename(
                        columns={"<DATE>": "date", "<CLOSE>": "close"},
                    )
                )
            elif "DATE" in raw.columns and "CLOSE" in raw.columns:
                df = (
                    raw[["DATE", "CLOSE"]]
                    .copy()
                    .rename(
                        columns={"DATE": "date", "CLOSE": "close"},
                    )
                )
            elif "date" in raw.columns and "close" in raw.columns:
                df = raw[["date", "close"]].copy()
            else:
                raise ValueError(
                    f"Unsupported price file structure for {path}: columns={list(raw.columns)}",
                )
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df.set_index("date", inplace=True)

        df.sort_index(inplace=True)

        if df.index.duplicated().any():
            duplicate_count = int(df.index.duplicated().sum())
            logger.warning(
                "%s contains %d duplicate dates; keeping latest entries",
                path,
                duplicate_count,
            )
            df = df[~df.index.duplicated(keep="last")]

        non_positive_mask = df["close"] <= 0
        if non_positive_mask.any():
            count = int(non_positive_mask.sum())
            logger.warning("Dropping %d non-positive close values from %s", count, path)
            df = df.loc[~non_positive_mask]

        if df.empty:
            logger.warning("Price file %s is empty after cleaning", path)
            return pd.Series(dtype="float64")

        if len(df.index) > 1:
            gaps = df.index.to_series().diff().dt.days.dropna()
            max_gap = int(gaps.max()) if not gaps.empty else 0
            if max_gap > 10:
                logger.warning("Detected maximum gap of %d days in %s", max_gap, path)

        return df["close"].astype(float)

    def load_multiple_prices(
        self,
        assets: list[SelectedAsset],
        prices_dir: Path,
    ) -> pd.DataFrame:
        """Load price data for many assets and align on the union of dates."""
        logger.info(
            "Loading price series for %d assets from %s", len(assets), prices_dir
        )
        all_prices: dict[str, pd.Series] = {}
        for asset in assets:
            price_path = prices_dir / asset.stooq_path
            if not price_path.exists():
                alt_name = Path(asset.stooq_path).stem.lower()
                alt_path = prices_dir / f"{alt_name}.csv"
                if alt_path.exists():
                    price_path = alt_path
                else:
                    logger.warning(
                        "Price file not found for %s (%s)",
                        asset.symbol,
                        price_path,
                    )
                    continue

            try:
                prices = self.load_price_file(price_path)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.error("Failed to load %s: %s", price_path, exc)
                continue

            if prices.empty:
                logger.warning(
                    "Skipping %s because the price series is empty", asset.symbol
                )
                continue

            all_prices[asset.symbol] = prices

        if not all_prices:
            logger.warning("No price files were successfully loaded")
            return pd.DataFrame()

        df = pd.DataFrame(all_prices).sort_index()
        logger.info("Loaded price matrix with shape %s", df.shape)
        return df
