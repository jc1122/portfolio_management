"""Tests for portfolio construction exceptions."""

from __future__ import annotations

from portfolio_management.exceptions import (
    ConstraintViolationError,
    DependencyError,
    InsufficientDataError,
    InvalidStrategyError,
    OptimizationError,
    PortfolioConstructionError,
    PortfolioManagementError,
)


def test_portfolio_construction_error_inheritance():
    """Test that PortfolioConstructionError inherits from PortfolioManagementError."""
    assert issubclass(PortfolioConstructionError, PortfolioManagementError)


def test_invalid_strategy_error_inheritance():
    """Test that InvalidStrategyError inherits from PortfolioConstructionError."""
    assert issubclass(InvalidStrategyError, PortfolioConstructionError)


def test_constraint_violation_error():
    """Test ConstraintViolationError creation and attributes."""
    error = ConstraintViolationError(constraint_name="turnover", violated_value=0.5)
    assert issubclass(ConstraintViolationError, PortfolioConstructionError)
    assert error.constraint_name == "turnover"
    assert error.violated_value == 0.5
    assert "Constraint 'turnover' was violated with value: 0.5." in str(error)


def test_optimization_error():
    """Test OptimizationError creation and attributes."""
    error = OptimizationError(strategy_name="mean_variance")
    assert issubclass(OptimizationError, PortfolioConstructionError)
    assert error.strategy_name == "mean_variance"
    assert "Optimization failed for strategy: 'mean_variance'." in str(error)


def test_insufficient_data_error():
    """Test InsufficientDataError creation and attributes."""
    error = InsufficientDataError(required_periods=100, available_periods=50)
    assert issubclass(InsufficientDataError, PortfolioConstructionError)
    assert error.required_periods == 100
    assert error.available_periods == 50
    assert (
        "Insufficient data for portfolio construction. Required: 100, Available: 50."
        in str(error)
    )


def test_dependency_error():
    """Test DependencyError creation and attributes."""
    error = DependencyError(dependency_name="riskparityportfolio")
    assert issubclass(DependencyError, PortfolioConstructionError)
    assert error.dependency_name == "riskparityportfolio"
    assert "Optional dependency 'riskparityportfolio' is not installed." in str(error)
