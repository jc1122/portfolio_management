"""Portfolio constraints and guardrails."""

from __future__ import annotations

from dataclasses import dataclass


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
