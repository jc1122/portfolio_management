"""Data models for defining portfolio investment constraints.

This module provides data classes for specifying constraints to be used during
portfolio optimization. These constraints help ensure that the resulting portfolio
adheres to specific investment rules, risk limits, and diversification requirements.

Key Classes:
    - PortfolioConstraints: Defines basic constraints like min/max weights and
      group exposure limits.
    - CardinalityConstraints: Defines rules for the number of assets in a portfolio.
    - CardinalityMethod: Enumerates the different methods for enforcing cardinality.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class PortfolioConstraints:
    """Defines basic investment constraints and guardrails for a portfolio.

    This data class holds common constraints that can be applied during the
    optimization process to ensure the portfolio meets diversification and
    exposure mandates.

    Attributes:
        max_weight (float): Maximum weight for any single asset.
        min_weight (float): Minimum weight for any single asset.
        max_equity_exposure (float): Maximum total allocation to equity assets.
        min_bond_exposure (float): Minimum total allocation to bond/cash assets.
        sector_limits (dict[str, float] | None): A dictionary mapping sector names
            to their maximum allowed weight in the portfolio.
        require_full_investment (bool): If True, forces the sum of all asset
            weights to equal 1.0.

    Configuration Example (YAML):
        ```yaml
        constraints:
          max_weight: 0.15
          min_weight: 0.01
          max_equity_exposure: 0.80
          sector_limits:
            Technology: 0.30
            Healthcare: 0.25
          require_full_investment: true
        ```
    """

    max_weight: float = 0.25
    min_weight: float = 0.0
    max_equity_exposure: float = 0.90
    min_bond_exposure: float = 0.10
    sector_limits: dict[str, float] | None = None
    require_full_investment: bool = True

    def __post_init__(self) -> None:
        """Validate constraint parameters."""
        if not 0.0 <= self.min_weight <= self.max_weight <= 1.0:
            msg = (
                f"Invalid weight bounds: min_weight={self.min_weight}, "
                f"max_weight={self.max_weight}"
            )
            raise ValueError(msg)

        if not 0.0 <= self.min_bond_exposure <= 1.0:
            msg = f"Invalid min_bond_exposure: {self.min_bond_exposure}"
            raise ValueError(msg)

        if not 0.0 <= self.max_equity_exposure <= 1.0:
            msg = f"Invalid max_equity_exposure: {self.max_equity_exposure}"
            raise ValueError(msg)


class CardinalityMethod(str, Enum):
    """Methods for handling cardinality constraints in optimization.

    Attributes:
        PRESELECTION: Use factor-based preselection before optimization (current default)
        MIQP: Mixed-Integer Quadratic Programming (future: requires commercial solver)
        HEURISTIC: Iterative heuristic approach (future: custom implementation)
        RELAXATION: Continuous relaxation with post-processing (future)

    """

    PRESELECTION = "preselection"
    MIQP = "miqp"
    HEURISTIC = "heuristic"
    RELAXATION = "relaxation"


@dataclass(frozen=True)
class CardinalityConstraints:
    """Defines constraints on the number of assets in a portfolio.

    Cardinality constraints limit the number of non-zero positions, which is
    critical for managing transaction costs, improving liquidity, and adhering
    to fund mandates that limit the number of holdings.

    Mathematical Formulation:
        Let w ∈ ℝⁿ be the portfolio weights and z ∈ {0,1}ⁿ be binary indicators
        where zᵢ = 1 if asset i is included in the portfolio, and 0 otherwise.

        1. Position Limit:
           min_assets ≤ Σᵢ zᵢ ≤ max_assets

        2. Linking weights and indicators:
           min_position_size * zᵢ ≤ wᵢ ≤ max_weight * zᵢ

        This formulation requires a Mixed-Integer Programming (MIP) solver.

    Attributes:
        enabled (bool): Whether cardinality constraints are active.
        method (CardinalityMethod): The method for enforcing cardinality.
            'preselection' is the default and filters assets before optimization.
            Other methods like 'miqp' integrate constraints into the optimizer.
        max_assets (int | None): Maximum number of non-zero positions.
        min_position_size (float): The minimum weight for any non-zero position.
        group_limits (dict[str, int] | None): A dictionary mapping asset groups
            to the maximum number of positions allowed in that group.
        enforce_in_optimizer (bool): If True, integrates the constraints directly
            into the optimization problem, which requires a MIP-capable solver.
            Defaults to False, relying on pre-selection.

    Configuration Example (YAML):
        ```yaml
        cardinality:
          enabled: true
          method: preselection
          max_assets: 50
          min_position_size: 0.015
          group_limits:
            equity: 40
            alternatives: 5
        ```

    Performance Notes:
        - `preselection`: Very fast, suitable for all optimizers. Sub-optimal
          as it doesn't consider correlations during selection.
        - `miqp`: Provides the optimal solution but is computationally expensive
          (NP-hard) and requires a specialized solver (e.g., Gurobi, CBC).
          Complexity scales exponentially with the number of assets.

    """

    enabled: bool = False
    method: CardinalityMethod = CardinalityMethod.PRESELECTION
    max_assets: int | None = None
    min_position_size: float = 0.01
    group_limits: dict[str, int] | None = None
    enforce_in_optimizer: bool = False

    def __post_init__(self) -> None:
        """Validate cardinality constraint parameters."""
        if not self.enabled:
            # No validation needed if disabled
            return

        # Validate max_assets
        if self.max_assets is not None and self.max_assets < 1:
            msg = f"max_assets must be >= 1, got {self.max_assets}"
            raise ValueError(msg)

        # Validate min_position_size
        if not 0.0 < self.min_position_size <= 1.0:
            msg = f"min_position_size must be in (0, 1], got {self.min_position_size}"
            raise ValueError(msg)

        # Validate group_limits
        if self.group_limits is not None:
            for group, limit in self.group_limits.items():
                if limit < 1:
                    msg = f"group_limits['{group}'] must be >= 1, got {limit}"
                    raise ValueError(msg)

        # Validate enforce_in_optimizer consistency
        if self.enforce_in_optimizer and self.method == CardinalityMethod.PRESELECTION:
            msg = (
                "enforce_in_optimizer=True requires method != PRESELECTION. "
                "Use method=MIQP, HEURISTIC, or RELAXATION for optimizer integration."
            )
            raise ValueError(msg)

        # Warn about future methods
        if self.method != CardinalityMethod.PRESELECTION:
            # This will be raised when actually attempting to use these methods
            # For now, just ensure the config is valid
            pass
