"""Unit tests for equal-weight portfolio strategy."""

from __future__ import annotations

import pandas as pd
import pytest

from portfolio_management.core.exceptions import ConstraintViolationError, InsufficientDataError
from portfolio_management.portfolio.constraints.models import PortfolioConstraints
from portfolio_management.portfolio.strategies.equal_weight import EqualWeightStrategy

pytestmark = pytest.mark.unit


@pytest.fixture
def strategy() -> EqualWeightStrategy:
    """Provide a strategy instance for testing."""
    return EqualWeightStrategy()


def test_construct_produces_equal_weights(
    strategy: EqualWeightStrategy, mock_returns: pd.DataFrame, mock_portfolio_constraints: PortfolioConstraints
) -> None:
    """Constructing on valid returns yields equal weights that sum to one."""
    portfolio = strategy.construct(mock_returns, mock_portfolio_constraints)

    assert pytest.approx(portfolio.weights.sum()) == 1.0
    assert all(weight == pytest.approx(1 / len(portfolio.weights)) for weight in portfolio.weights)
    assert portfolio.metadata["n_assets"] == len(mock_returns.columns)


def test_construct_empty_returns_raises(strategy: EqualWeightStrategy, mock_portfolio_constraints: PortfolioConstraints) -> None:
    """Empty returns should raise an insufficiency error."""
    empty_returns = pd.DataFrame()

    with pytest.raises(InsufficientDataError):
        strategy.construct(empty_returns, mock_portfolio_constraints)


def test_construct_respects_max_weight(strategy: EqualWeightStrategy, mock_returns: pd.DataFrame) -> None:
    """If max_weight is below 1/N the strategy should raise an error."""
    tight_constraints = PortfolioConstraints(max_weight=0.2, min_bond_exposure=0.0)

    with pytest.raises(ConstraintViolationError):
        strategy.construct(mock_returns, tight_constraints)


def test_construct_metadata_contains_equal_weight(
    strategy: EqualWeightStrategy, mock_returns: pd.DataFrame, mock_portfolio_constraints: PortfolioConstraints
) -> None:
    """Metadata should expose the equal weight and asset count."""
    portfolio = strategy.construct(mock_returns, mock_portfolio_constraints)

    assert "equal_weight" in portfolio.metadata
    assert portfolio.metadata["equal_weight"] == pytest.approx(1 / len(mock_returns.columns))


def test_asset_class_constraints_enforced(
    strategy: EqualWeightStrategy, mock_returns: pd.DataFrame, mock_portfolio_constraints: PortfolioConstraints
) -> None:
    """Equity exposure above the constraint should raise an error."""
    asset_classes = pd.Series({ticker: "Equity" for ticker in mock_returns.columns})
    constrained = PortfolioConstraints(max_weight=0.6, max_equity_exposure=0.5, min_bond_exposure=0.0)

    with pytest.raises(ConstraintViolationError):
        strategy.construct(mock_returns, constrained, asset_classes=asset_classes)


def test_min_history_property(strategy: EqualWeightStrategy) -> None:
    """The minimum history requirement should be one period."""
    assert strategy.min_history_periods == 1
