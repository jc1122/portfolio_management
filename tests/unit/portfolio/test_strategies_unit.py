"""Unit tests for portfolio strategy helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from portfolio_management.core.exceptions import ConstraintViolationError, InsufficientDataError
from portfolio_management.portfolio.constraints.models import PortfolioConstraints
from portfolio_management.portfolio.strategies.equal_weight import EqualWeightStrategy
from portfolio_management.portfolio.strategies.mean_variance import MeanVarianceStrategy
from portfolio_management.portfolio.strategies.risk_parity import RiskParityStrategy

pytestmark = pytest.mark.unit


def test_equal_weight_constructs_uniform_weights(mock_returns: pd.DataFrame) -> None:
    """Equal weight strategy should assign 1/N to each asset."""

    strategy = EqualWeightStrategy()
    constraints = PortfolioConstraints(max_weight=1.0)

    portfolio = strategy.construct(mock_returns, constraints)

    expected_weight = pytest.approx(1 / mock_returns.shape[1])
    assert all(weight == expected_weight for weight in portfolio.weights)
    assert pytest.approx(portfolio.weights.sum(), rel=1e-6) == 1.0


def test_equal_weight_raises_for_insufficient_data() -> None:
    """Empty input should raise an InsufficientDataError."""

    strategy = EqualWeightStrategy()
    constraints = PortfolioConstraints()

    with pytest.raises(InsufficientDataError):
        strategy.construct(pd.DataFrame(), constraints)


def test_equal_weight_enforces_max_weight(mock_returns: pd.DataFrame) -> None:
    """The max_weight constraint must be honoured."""

    strategy = EqualWeightStrategy()
    constraints = PortfolioConstraints(max_weight=0.2)

    with pytest.raises(ConstraintViolationError):
        strategy.construct(mock_returns, constraints)


def test_equal_weight_asset_class_constraint_violation(mock_returns: pd.DataFrame) -> None:
    """Asset class exposures above bounds should trigger an error."""

    strategy = EqualWeightStrategy()
    constraints = PortfolioConstraints(min_bond_exposure=0.2, max_equity_exposure=0.5)
    asset_classes = pd.Series({"AAA": "Equity", "BBB": "Equity", "CCC": "Bond"})

    with pytest.raises(ConstraintViolationError):
        strategy.construct(mock_returns, constraints, asset_classes=asset_classes)


def test_mean_variance_prepare_returns_filters_invalid_rows(mock_returns: pd.DataFrame) -> None:
    """Rows containing NaN or infinite values should be removed."""

    enriched = mock_returns.copy()
    enriched.iloc[0, 0] = np.nan
    enriched.iloc[1, 1] = np.inf

    strategy = MeanVarianceStrategy(min_periods=1)
    cleaned = strategy._prepare_returns(enriched)

    assert cleaned.notna().all().all()
    assert list(cleaned.columns) == ["CCC"]


def test_mean_variance_validate_returns_respects_min_periods(mock_returns: pd.DataFrame) -> None:
    """Validation should fail when history is shorter than required."""

    strategy = MeanVarianceStrategy(min_periods=len(mock_returns) + 1)

    with pytest.raises(InsufficientDataError):
        strategy._validate_returns(mock_returns)


def test_risk_parity_regularize_covariance_adds_diagonal(mock_covariance_matrix: pd.DataFrame) -> None:
    """Regularisation should ensure covariance is positive definite."""

    strategy = RiskParityStrategy(min_periods=1)
    adjusted = strategy._regularize_covariance(mock_covariance_matrix, n_assets=3)

    # Jitter should increase diagonal values to stabilise the matrix
    diagonal_increase = np.diag(adjusted) - np.diag(mock_covariance_matrix)
    assert (diagonal_increase > 0).all()
    eigenvalues = np.linalg.eigvalsh(adjusted)
    assert (eigenvalues > 0).all()
