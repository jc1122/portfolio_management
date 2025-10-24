"""Regime gating for asset selection (currently NoOp stubs).

This module provides regime-based gating that can modify asset selection
based on macroeconomic conditions. Currently implemented as NoOp stubs that
always return neutral signals and leave selection unchanged.

Future implementations will add actual regime detection logic based on
macro series data.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:

    from portfolio_management.assets.selection import SelectedAsset
    from portfolio_management.macro.models import RegimeConfig

LOGGER = logging.getLogger(__name__)


class RegimeGate:
    """Apply regime-based gating to asset selection (currently NoOp).

    This class applies regime rules to modify asset selection based on
    macroeconomic conditions. The current implementation is a NoOp stub
    that always returns neutral signals and leaves selection unchanged.

    This documented behavior ensures the system is ready for future regime
    logic without affecting current selection workflows.

    Attributes:
        config: RegimeConfig defining detection rules and gating behavior.

    Example:
        >>> from portfolio_management.macro import RegimeConfig
        >>> from portfolio_management.macro.regime import RegimeGate
        >>> config = RegimeConfig(enable_gating=False)  # NoOp
        >>> gate = RegimeGate(config)
        >>> # Apply gating (currently does nothing)
        >>> filtered_assets = gate.apply_gating(selected_assets)
        >>> # Assets unchanged (pass-through behavior)
        >>> assert filtered_assets == selected_assets

    """

    def __init__(self, config: RegimeConfig) -> None:
        """Initialize the RegimeGate.

        Args:
            config: RegimeConfig defining gating rules.

        Example:
            >>> from portfolio_management.macro import RegimeConfig
            >>> from portfolio_management.macro.regime import RegimeGate
            >>> config = RegimeConfig()
            >>> gate = RegimeGate(config)

        """
        self.config = config
        LOGGER.info(
            "Initialized RegimeGate (gating_enabled=%s, mode=NoOp)",
            config.is_enabled(),
        )

    def apply_gating(
        self,
        assets: list[SelectedAsset],
        date: str | None = None,
    ) -> list[SelectedAsset]:
        """Apply regime gating to selected assets (currently NoOp).

        This method applies regime-based filtering to the asset list. The
        current implementation is a NoOp that returns all assets unchanged,
        regardless of the regime configuration.

        Args:
            assets: List of selected assets to potentially filter.
            date: Optional date for regime evaluation (ISO format YYYY-MM-DD).
                Currently ignored in NoOp implementation.

        Returns:
            List of assets after gating. Currently returns input unchanged.

        Example:
            >>> from portfolio_management.macro import RegimeConfig
            >>> from portfolio_management.macro.regime import RegimeGate
            >>> config = RegimeConfig(enable_gating=False)
            >>> gate = RegimeGate(config)
            >>> filtered = gate.apply_gating(assets, date="2025-10-23")
            >>> assert filtered == assets  # NoOp behavior

        """
        if not self.config.is_enabled():
            LOGGER.debug(
                "Regime gating disabled, passing through %d assets unchanged",
                len(assets),
            )
            return assets

        # Even if enabled, current implementation is NoOp
        # Future: implement actual regime detection and filtering
        LOGGER.debug(
            "Regime gating enabled but NoOp implementation active, "
            "passing through %d assets unchanged",
            len(assets),
        )
        return assets

    def get_current_regime(self, date: str | None = None) -> dict[str, str]:
        """Get the current regime classification (currently NoOp).

        Returns a dictionary describing the current market regime. The
        current implementation always returns neutral signals.

        Args:
            date: Optional date for regime evaluation (ISO format YYYY-MM-DD).
                Currently ignored in NoOp implementation.

        Returns:
            Dictionary with regime classifications. Always returns neutral
            in the current NoOp implementation.

        Example:
            >>> from portfolio_management.macro import RegimeConfig
            >>> from portfolio_management.macro.regime import RegimeGate
            >>> config = RegimeConfig()
            >>> gate = RegimeGate(config)
            >>> regime = gate.get_current_regime(date="2025-10-23")
            >>> print(regime)
            {'recession': 'neutral', 'risk_sentiment': 'neutral', 'mode': 'noop'}

        """
        # NoOp: always return neutral regime
        regime = {
            "recession": "neutral",
            "risk_sentiment": "neutral",
            "mode": "noop",
        }

        LOGGER.debug(
            "Current regime (NoOp): %s (date=%s)",
            regime,
            date if date else "current",
        )
        return regime

    def filter_by_asset_class(
        self,
        assets: list[SelectedAsset],
        allowed_classes: list[str] | None = None,
    ) -> list[SelectedAsset]:
        """Filter assets by asset class based on regime (currently NoOp).

        This method could filter assets by asset class in risk-off regimes
        (e.g., exclude equities, favor bonds). Current implementation is NoOp.

        Args:
            assets: List of selected assets to filter.
            allowed_classes: Optional list of allowed asset classes.
                Currently ignored in NoOp implementation.

        Returns:
            List of assets after filtering. Currently returns input unchanged.

        Example:
            >>> from portfolio_management.macro import RegimeConfig
            >>> from portfolio_management.macro.regime import RegimeGate
            >>> config = RegimeConfig()
            >>> gate = RegimeGate(config)
            >>> filtered = gate.filter_by_asset_class(assets, ["equity"])
            >>> assert filtered == assets  # NoOp behavior

        """
        # NoOp: always pass through unchanged
        LOGGER.debug(
            "Asset class filtering (NoOp): passing through %d assets unchanged",
            len(assets),
        )
        return assets

    def adjust_selection_scores(
        self,
        assets: list[SelectedAsset],
        date: str | None = None,
    ) -> list[tuple[SelectedAsset, float]]:
        """Adjust selection scores based on regime (currently NoOp).

        This method could adjust asset scores based on regime conditions.
        Current implementation returns all assets with neutral score of 1.0.

        Args:
            assets: List of selected assets.
            date: Optional date for regime evaluation (ISO format YYYY-MM-DD).
                Currently ignored in NoOp implementation.

        Returns:
            List of (asset, score) tuples. Currently all scores are 1.0.

        Example:
            >>> from portfolio_management.macro import RegimeConfig
            >>> from portfolio_management.macro.regime import RegimeGate
            >>> config = RegimeConfig()
            >>> gate = RegimeGate(config)
            >>> scored = gate.adjust_selection_scores(assets, date="2025-10-23")
            >>> assert all(score == 1.0 for _, score in scored)

        """
        # NoOp: return all assets with neutral score
        scored_assets = [(asset, 1.0) for asset in assets]
        LOGGER.debug(
            "Score adjustment (NoOp): returning %d assets with neutral score 1.0",
            len(scored_assets),
        )
        return scored_assets
