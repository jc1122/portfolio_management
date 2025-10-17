"""Tests for portfolio construction exceptions."""

import sys

import numpy as np
import pandas as pd
import pytest

from portfolio_management import exceptions as exc
from portfolio_management import portfolio as portfolio_module

EqualWeightStrategy = portfolio_module.EqualWeightStrategy
Portfolio = portfolio_module.Portfolio
PortfolioConstraints = portfolio_module.PortfolioConstraints
PortfolioStrategy = portfolio_module.PortfolioStrategy
RebalanceConfig = portfolio_module.RebalanceConfig
RiskParityStrategy = getattr(portfolio_module, "RiskParityStrategy", None)
PortfolioConstructionError = exc.PortfolioConstructionError
PortfolioManagementError = exc.PortfolioManagementError
InvalidStrategyError = exc.InvalidStrategyError
ConstraintViolationError = exc.ConstraintViolationError
OptimizationError = exc.OptimizationError
InsufficientDataError = exc.InsufficientDataError
DependencyError = exc.DependencyError


@pytest.mark.skipif(
    RiskParityStrategy is None or sys.version_info < (3, 10),
    reason="Risk parity implementation requires portfolio module support and Python 3.10+ zip(strict=...).",
)
class TestRiskParityStrategy:
    """Tests for risk parity strategy."""

    @pytest.fixture
    def sample_returns(self):
        """Create sample returns DataFrame."""
        dates = pd.date_range("2020-01-01", periods=252, freq="D")
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN"]
        data = np.random.randn(252, 4) * 0.02  # 2% daily vol  # noqa: NPY002
        return pd.DataFrame(data, index=dates, columns=tickers)

    def test_basic_risk_parity(self, sample_returns):
        """Test basic risk parity construction."""
        strategy = RiskParityStrategy()
        constraints = PortfolioConstraints()

        portfolio = strategy.construct(sample_returns, constraints)

        assert len(portfolio.weights) == 4
        assert np.isclose(portfolio.weights.sum(), 1.0)

    def test_insufficient_data(self, sample_returns):
        """Test that insufficient data raises an error."""
        strategy = RiskParityStrategy(min_periods=300)
        constraints = PortfolioConstraints()

        with pytest.raises(InsufficientDataError):
            strategy.construct(sample_returns, constraints)

    def test_singular_covariance(self, sample_returns):
        """Test that a singular covariance matrix raises an error."""
        strategy = RiskParityStrategy()
        constraints = PortfolioConstraints()
        sample_returns["AAPL"] = 0.0  # Make covariance matrix singular

        with pytest.raises(OptimizationError):
            strategy.construct(sample_returns, constraints)

    def test_missing_library(self, monkeypatch):
        """Test that a missing library raises a DependencyError."""
        monkeypatch.setitem(sys.modules, "riskparityportfolio", None)
        strategy = RiskParityStrategy()
        constraints = PortfolioConstraints()
        returns = pd.DataFrame()

        with pytest.raises(DependencyError):
            strategy.construct(returns, constraints)


class TestEqualWeightStrategy:
    """Tests for equal-weight strategy."""

    @pytest.fixture
    def sample_returns(self):
        """Create sample returns DataFrame."""
        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN"]
        data = np.random.randn(100, 4) * 0.02  # 2% daily vol  # noqa: NPY002
        return pd.DataFrame(data, index=dates, columns=tickers)

    def test_basic_equal_weight(self, sample_returns):
        """Test basic equal weighting."""
        strategy = EqualWeightStrategy()
        constraints = PortfolioConstraints()

        portfolio = strategy.construct(sample_returns, constraints)

        assert len(portfolio.weights) == 4
        assert np.allclose(portfolio.weights, 0.25)
        assert np.isclose(portfolio.weights.sum(), 1.0)

    def test_insufficient_data(self):
        """Test that insufficient data raises an error."""
        strategy = EqualWeightStrategy()
        constraints = PortfolioConstraints()
        returns = pd.DataFrame()

        with pytest.raises(InsufficientDataError):
            strategy.construct(returns, constraints)

    def test_max_weight_constraint_violation(self, sample_returns):
        """Test that violating max_weight constraint raises an error."""
        strategy = EqualWeightStrategy()
        constraints = PortfolioConstraints(max_weight=0.2)

        with pytest.raises(ConstraintViolationError):
            strategy.construct(sample_returns, constraints)

    def test_asset_class_constraints(self, sample_returns):
        """Test asset class constraint validation."""
        strategy = EqualWeightStrategy()
        constraints = PortfolioConstraints(
            max_equity_exposure=0.5,
            min_bond_exposure=0.5,
        )
        asset_classes = pd.Series(
            ["equity", "equity", "bond", "bond"],
            index=["AAPL", "MSFT", "GOOGL", "AMZN"],
        )

        portfolio = strategy.construct(
            sample_returns,
            constraints,
            asset_classes=asset_classes,
        )
        assert portfolio is not None

    def test_asset_class_constraint_violation(self, sample_returns):
        """Test that violating asset class constraints raises an error."""
        strategy = EqualWeightStrategy()
        constraints = PortfolioConstraints(
            max_equity_exposure=0.4,
            min_bond_exposure=0.6,
        )
        asset_classes = pd.Series(
            ["equity", "equity", "equity", "bond"],
            index=["AAPL", "MSFT", "GOOGL", "AMZN"],
        )

        with pytest.raises(ConstraintViolationError):
            strategy.construct(sample_returns, constraints, asset_classes=asset_classes)


class TestPortfolioStrategy:
    """Tests for the PortfolioStrategy abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that PortfolioStrategy cannot be instantiated directly."""
        with pytest.raises(TypeError):
            PortfolioStrategy()

    def test_can_instantiate_concrete_class(self):
        """Test that a concrete implementation can be instantiated."""

        class ConcreteStrategy(PortfolioStrategy):
            @property
            def name(self) -> str:
                return "concrete"

            @property
            def min_history_periods(self) -> int:
                return 1

            def construct(
                self,
                returns,  # noqa: ARG002
                constraints,  # noqa: ARG002
                asset_classes=None,  # noqa: ARG002
            ):
                return Portfolio(
                    weights=pd.Series([1.0], index=["A"]),
                    strategy="concrete",
                )

        strategy = ConcreteStrategy()
        assert strategy.name == "concrete"
        assert strategy.min_history_periods == 1


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


class TestPortfolioConstraints:
    """Tests for PortfolioConstraints dataclass."""

    def test_valid_constraints(self):
        """Test valid constraint initialization."""
        constraints = PortfolioConstraints(
            max_weight=0.25,
            min_weight=0.0,
            max_equity_exposure=0.90,
            min_bond_exposure=0.10,
        )
        assert constraints.max_weight == 0.25
        assert constraints.min_weight == 0.0

    def test_invalid_weight_bounds(self):
        """Test invalid weight bounds raise ValueError."""
        with pytest.raises(ValueError, match="Invalid weight bounds"):
            PortfolioConstraints(max_weight=0.1, min_weight=0.2)

    def test_invalid_exposure_bounds(self):
        """Test invalid exposure bounds raise ValueError."""
        with pytest.raises(ValueError, match="Invalid min_bond_exposure"):
            PortfolioConstraints(min_bond_exposure=1.1)

        with pytest.raises(ValueError, match="Invalid max_equity_exposure"):
            PortfolioConstraints(max_equity_exposure=-0.1)

    def test_infeasible_constraints(self):
        """Test infeasible constraints raise ValueError."""
        with pytest.raises(ValueError, match="Infeasible constraints"):
            PortfolioConstraints(min_bond_exposure=0.6, max_equity_exposure=0.3)


class TestRebalanceConfig:
    """Tests for RebalanceConfig dataclass."""

    def test_valid_config(self):
        """Test valid rebalance config initialization."""
        config = RebalanceConfig(
            frequency=30,
            tolerance_bands=0.2,
            min_trade_size=0.01,
            cost_per_trade=0.001,
        )
        assert config.frequency == 30

    def test_invalid_frequency(self):
        """Test invalid frequency raises ValueError."""
        with pytest.raises(ValueError, match="Invalid frequency"):
            RebalanceConfig(frequency=0)

    def test_invalid_tolerance_bands(self):
        """Test invalid tolerance bands raise ValueError."""
        with pytest.raises(ValueError, match="Invalid tolerance_bands"):
            RebalanceConfig(tolerance_bands=1.1)


class TestPortfolio:
    """Tests for Portfolio dataclass."""

    def test_valid_portfolio(self):
        """Test valid portfolio initialization."""
        weights = pd.Series([0.5, 0.5], index=["A", "B"])
        portfolio = Portfolio(weights=weights, strategy="test")
        assert portfolio.get_position_count() == 2

    def test_negative_weights(self):
        """Test negative weights raise ValueError."""
        weights = pd.Series([1.1, -0.1], index=["A", "B"])
        with pytest.raises(ValueError, match="Portfolio weights cannot be negative"):
            Portfolio(weights=weights, strategy="test")

    def test_non_normalized_weights(self):
        """Test non-normalized weights raise ValueError."""
        weights = pd.Series([0.5, 0.6], index=["A", "B"])
        with pytest.raises(ValueError, match=r"Portfolio weights must sum to 1\.0"):
            Portfolio(weights=weights, strategy="test")

    def test_empty_portfolio(self):
        """Test empty portfolio raises ValueError."""
        weights = pd.Series([], dtype=float)
        with pytest.raises(
            ValueError,
            match="Portfolio must contain at least one asset",
        ):
            Portfolio(weights=weights, strategy="test")

    def test_get_top_holdings(self):
        """Test get_top_holdings method."""
        weights = pd.Series([0.1, 0.4, 0.3, 0.2], index=["D", "A", "B", "C"])
        portfolio = Portfolio(weights=weights, strategy="test")
        top_2 = portfolio.get_top_holdings(2)
        assert top_2.equals(pd.Series([0.4, 0.3], index=["A", "B"]))
