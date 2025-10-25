"""Fast unit tests for portfolio strategies using in-memory data."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from portfolio_management.core.exceptions import (
    ConstraintViolationError,
    InsufficientDataError,
)
from portfolio_management.portfolio.constraints.models import PortfolioConstraints
from portfolio_management.portfolio.strategies.equal_weight import EqualWeightStrategy
from portfolio_management.portfolio.strategies.risk_parity import RiskParityStrategy


@pytest.mark.unit
def test_equal_weight_constructs_uniform_portfolio(mock_returns: pd.DataFrame) -> None:
    """Equal weight strategy should distribute weights evenly across assets."""

    strategy = EqualWeightStrategy()
    constraints = PortfolioConstraints()
    portfolio = strategy.construct(mock_returns, constraints)

    expected_weight = pytest.approx(1.0 / len(mock_returns.columns))
    assert all(weight == expected_weight for weight in portfolio.weights)
    assert portfolio.weights.sum() == pytest.approx(1.0)


@pytest.mark.unit
def test_equal_weight_respects_max_weight(mock_returns: pd.DataFrame) -> None:
    """Equal weight strategy raises when equal weights violate the max constraint."""

    strategy = EqualWeightStrategy()
    constraints = PortfolioConstraints(max_weight=0.05)

    with pytest.raises(ConstraintViolationError):
        strategy.construct(mock_returns, constraints)


@pytest.mark.unit
def test_equal_weight_requires_non_empty_returns() -> None:
    """Equal weight strategy rejects empty input data."""

    strategy = EqualWeightStrategy()
    constraints = PortfolioConstraints()

    with pytest.raises(InsufficientDataError):
        strategy.construct(pd.DataFrame(), constraints)


@pytest.mark.unit
def test_equal_weight_with_asset_classes(mock_returns: pd.DataFrame) -> None:
    """Asset class constraints are enforced for equal-weight allocations."""

    strategy = EqualWeightStrategy()
    constraints = PortfolioConstraints(max_equity_exposure=0.6, min_bond_exposure=0.2)
    asset_classes = pd.Series(
        ["equity", "equity", "bond", "bond", "cash"],
        index=mock_returns.columns,
    )

    portfolio = strategy.construct(mock_returns, constraints, asset_classes=asset_classes)

    assert portfolio.weights.sum() == pytest.approx(1.0)
    assert portfolio.metadata["n_assets"] == len(mock_returns.columns)


class _DummyRiskParityModule:
    """Lightweight stub replicating the riskparityportfolio API."""

    class RiskParityPortfolio:
        def __init__(self, covariance: np.ndarray) -> None:
            self.weights = np.full(covariance.shape[0], 1.0 / covariance.shape[0])

        def design(self, *args, **kwargs) -> None:  # noqa: D401, ANN001
            """Preserve pre-computed uniform weights."""
            return None


@pytest.mark.unit
def test_risk_parity_uses_mock_backend(
    mock_returns: pd.DataFrame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Risk parity strategy can construct a portfolio using a stub backend."""

    strategy = RiskParityStrategy(min_periods=10)
    constraints = PortfolioConstraints()

    monkeypatch.setattr(
        RiskParityStrategy,
        "_load_backend",
        lambda self: _DummyRiskParityModule(),
    )

    portfolio = strategy.construct(mock_returns, constraints)

    assert portfolio.strategy == "risk_parity"
    assert portfolio.weights.sum() == pytest.approx(1.0)
    assert all(weight >= 0 for weight in portfolio.weights)
