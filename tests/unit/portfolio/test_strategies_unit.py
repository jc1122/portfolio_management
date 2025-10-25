"""Fast unit tests for portfolio strategies using mocks."""

import pytest
import pandas as pd
from portfolio_management.portfolio.strategies.equal_weight import EqualWeightStrategy
from portfolio_management.portfolio.strategies.risk_parity import RiskParityStrategy
from portfolio_management.portfolio.constraints import PortfolioConstraints


@pytest.mark.unit
def test_equal_weight_simple_case(mock_returns):
    """Equal weight should allocate 1/N to each asset."""
    strategy = EqualWeightStrategy()
    constraints = PortfolioConstraints()
    portfolio = strategy.construct(mock_returns, constraints)
    weights = portfolio.weights

    expected_weight = 1.0 / len(mock_returns.columns)
    assert len(weights) == len(mock_returns.columns)
    for weight in weights.values:
        assert abs(weight - expected_weight) < 1e-6


@pytest.mark.unit
def test_equal_weight_weights_sum_to_one(mock_returns):
    """Equal weight should always sum to 1.0."""
    strategy = EqualWeightStrategy()
    constraints = PortfolioConstraints()
    portfolio = strategy.construct(mock_returns, constraints)
    weights = portfolio.weights
    assert abs(sum(weights.values) - 1.0) < 1e-6


@pytest.mark.unit
def test_risk_parity_with_mock_data(mock_returns, mock_covariance_matrix):
    """Risk parity should work with simple mock data."""
    strategy = RiskParityStrategy()
    constraints = PortfolioConstraints()

    # If strategy accepts covariance matrix directly (dependency injection)
    # portfolio = strategy.construct(mock_covariance_matrix, constraints)
    # Otherwise use returns
    portfolio = strategy.construct(mock_returns, constraints)
    weights = portfolio.weights

    assert len(weights) > 0
    assert abs(sum(weights.values) - 1.0) < 1e-6
    assert all(w >= 0 for w in weights.values)
