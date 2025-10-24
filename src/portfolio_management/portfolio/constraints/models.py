"""Portfolio constraints and guardrails."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class PortfolioConstraints:
    """Portfolio investment constraints and guardrails.

    Attributes:
        max_weight: Maximum weight for any single asset (default: 0.25)
        min_weight: Minimum weight for any single asset (default: 0.0)
        max_equity_exposure: Maximum total equity allocation (default: 0.90)
        min_bond_exposure: Minimum total bond/cash allocation (default: 0.10)
        sector_limits: Optional dict mapping sector names to max weights
        require_full_investment: Whether weights must sum to 1.0 (default: True)

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
    """Cardinality constraints for portfolio optimization.

    Cardinality constraints limit the number of non-zero positions in the portfolio,
    which is useful for controlling transaction costs, simplifying portfolio management,
    and enforcing minimum investment sizes.

    Two approaches are supported:
    1. **Preselection** (current): Filter assets before optimization using factors
    2. **Integrated** (future): Enforce cardinality within the optimizer itself

    Attributes:
        enabled: Whether cardinality constraints are active (default: False)
        method: Method for enforcing cardinality (default: PRESELECTION)
        max_assets: Maximum number of non-zero positions (None = unlimited)
        min_position_size: Minimum weight for non-zero positions (default: 0.01)
        group_limits: Optional dict mapping group names to max positions per group
        enforce_in_optimizer: Whether to enforce within optimizer vs preselection
            (default: False, requires method != PRESELECTION)

    Example:
        >>> # Simple cardinality: max 30 assets
        >>> constraints = CardinalityConstraints(
        ...     enabled=True,
        ...     max_assets=30,
        ...     min_position_size=0.02
        ... )

        >>> # Group-based cardinality: max 20 equity, max 10 bonds
        >>> constraints = CardinalityConstraints(
        ...     enabled=True,
        ...     max_assets=30,
        ...     group_limits={"equity": 20, "fixed_income": 10}
        ... )

    Design Notes:
        - Preselection (current): Fast, deterministic, factor-driven filtering
        - MIQP (future): Optimal but requires commercial solver (Gurobi/CPLEX)
        - Heuristic (future): Good approximate solutions, no special solver needed
        - Relaxation (future): Continuous optimization + rounding heuristics

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
