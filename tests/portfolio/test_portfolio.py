"""Tests for portfolio construction exceptions and strategies."""

import importlib
import sys
import types

import numpy as np
import pandas as pd
import pytest

from portfolio_management import portfolio as portfolio_module
from portfolio_management.core import exceptions as exc

EqualWeightStrategy = portfolio_module.EqualWeightStrategy
MeanVarianceStrategy = portfolio_module.MeanVarianceStrategy
Portfolio = portfolio_module.Portfolio
PortfolioConstraints = portfolio_module.PortfolioConstraints
PortfolioConstructor = portfolio_module.PortfolioConstructor
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


# Skip risk-parity specific tests if the strategy implementation is unavailable.
@pytest.mark.skipif(
    RiskParityStrategy is None,
    reason="Risk parity strategy not available in portfolio module.",
)
class TestRiskParityStrategy:
    """Tests for risk parity strategy."""

    pytest.importorskip("riskparityportfolio")

    @pytest.fixture
    def sample_returns(self):
        """Create sample returns DataFrame."""
        dates = pd.date_range("2020-01-01", periods=252, freq="D")
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN"]
        data = np.random.randn(252, 4) * 0.02  # 2% daily vol
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
        """Singular covariance matrices are regularised instead of failing."""
        strategy = RiskParityStrategy()
        constraints = PortfolioConstraints()
        sample_returns["AAPL"] = 0.0  # Make covariance matrix singular

        portfolio = strategy.construct(sample_returns, constraints)

        assert len(portfolio.weights) == 4
        assert np.isclose(portfolio.weights.sum(), 1.0)
        assert portfolio.metadata.get("n_assets") == 4

    def test_missing_library(self, monkeypatch):
        """Test that a missing library raises a DependencyError."""
        monkeypatch.setitem(sys.modules, "riskparityportfolio", None)
        strategy = RiskParityStrategy()
        constraints = PortfolioConstraints()
        returns = pd.DataFrame()

        with pytest.raises(DependencyError):
            strategy.construct(returns, constraints)


class TestMeanVarianceStrategy:
    """Tests for mean-variance optimisation strategy."""

    def _install_pypfopt_stub(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Install a lightweight PyPortfolioOpt stub for testing."""
        module = types.ModuleType("pypfopt")

        expected_returns_module = types.ModuleType("pypfopt.expected_returns")

        def mean_historical_return(
            returns: pd.DataFrame,
            frequency: int = 252,
        ) -> pd.Series:
            del frequency  # not used in stub
            return returns.mean()

        expected_returns_module.mean_historical_return = mean_historical_return

        risk_models_module = types.ModuleType("pypfopt.risk_models")

        def sample_cov(returns: pd.DataFrame, frequency: int = 252) -> pd.DataFrame:
            del frequency  # not used in stub
            return returns.cov()

        risk_models_module.sample_cov = sample_cov

        class DummyEfficientFrontier:
            def __init__(self, mu, cov, weight_bounds):
                self.mu = mu
                self.cov = cov
                self.weight_bounds = weight_bounds
                self._constraints = []
                self._weights = {ticker: 1.0 / len(mu) for ticker in mu.index}

            def add_constraint(self, constraint):
                self._constraints.append(constraint)

            def max_sharpe(self, risk_free_rate: float = 0.0) -> None:
                del risk_free_rate

            def min_volatility(self) -> None:
                return

            def efficient_risk(self, target_volatility: float) -> None:
                del target_volatility

            def clean_weights(self):
                return self._weights

            def portfolio_performance(
                self,
                *,
                verbose: bool = False,
                risk_free_rate: float = 0.0,
            ):
                del verbose, risk_free_rate
                return 0.08, 0.12, 0.5

        module.EfficientFrontier = DummyEfficientFrontier
        module.expected_returns = expected_returns_module
        module.risk_models = risk_models_module

        monkeypatch.setitem(sys.modules, "pypfopt", module)
        monkeypatch.setitem(
            sys.modules,
            "pypfopt.expected_returns",
            expected_returns_module,
        )
        monkeypatch.setitem(sys.modules, "pypfopt.risk_models", risk_models_module)

    def test_invalid_objective(self):
        """Invalid optimisation objective raises ValueError."""
        with pytest.raises(ValueError, match="Invalid objective"):
            MeanVarianceStrategy(objective="not_real")

    def test_dependency_missing(self, monkeypatch):
        """Missing PyPortfolioOpt raises DependencyError."""
        for module_name in [
            "pypfopt",
            "pypfopt.expected_returns",
            "pypfopt.risk_models",
        ]:
            monkeypatch.delitem(sys.modules, module_name, raising=False)

        original_import_module = importlib.import_module

        def fake_import(name, *args, **kwargs):
            if name.startswith("pypfopt"):
                raise ModuleNotFoundError("No module named 'pypfopt'")
            return original_import_module(name, *args, **kwargs)

        monkeypatch.setattr(importlib, "import_module", fake_import)

        strategy = MeanVarianceStrategy(min_periods=5)
        constraints = PortfolioConstraints()
        sample_returns = pd.DataFrame()

        with pytest.raises(DependencyError):
            strategy.construct(sample_returns, constraints)

    def test_construct_with_stub(self, monkeypatch):
        """Strategy constructs portfolio when PyPortfolioOpt stub is available."""
        self._install_pypfopt_stub(monkeypatch)

        rng = np.random.default_rng(42)
        dates = pd.date_range("2020-01-01", periods=30, freq="D")
        tickers = ["AAPL", "MSFT", "TLT"]
        data = rng.normal(loc=0.001, scale=0.01, size=(30, 3))
        returns = pd.DataFrame(data, index=dates, columns=tickers)

        asset_classes = pd.Series(
            ["equity", "equity", "bond"],
            index=tickers,
        )

        constraints = PortfolioConstraints(
            max_weight=0.6,
            min_weight=0.0,
            max_equity_exposure=0.8,
            min_bond_exposure=0.2,
        )

        strategy = MeanVarianceStrategy(min_periods=10)
        portfolio = strategy.construct(
            returns,
            constraints,
            asset_classes=asset_classes,
        )

        assert isinstance(portfolio, Portfolio)
        assert np.isclose(portfolio.weights.sum(), 1.0)
        assert {"expected_return", "volatility", "sharpe_ratio"}.issubset(
            portfolio.metadata or {},
        )


class TestEqualWeightStrategy:
    """Tests for equal-weight strategy."""

    @pytest.fixture
    def sample_returns(self):
        """Create sample returns DataFrame."""
        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN"]
        data = np.random.randn(100, 4) * 0.02  # 2% daily vol
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


class TestPortfolioConstructor:
    """Tests for the PortfolioConstructor orchestrator."""

    def test_list_strategies_contains_defaults(self):
        """Default constructor registers baseline strategies."""
        constructor = PortfolioConstructor()
        strategies = constructor.list_strategies()
        assert "equal_weight" in strategies
        assert "risk_parity" in strategies

    def test_construct_equal_weight(self):
        """Constructor delegates to equal-weight strategy."""
        constructor = PortfolioConstructor()
        dates = pd.date_range("2020-01-01", periods=5, freq="D")
        tickers = ["AAPL", "MSFT"]
        returns = pd.DataFrame(
            np.random.default_rng(0).normal(size=(5, 2)),
            index=dates,
            columns=tickers,
        )
        constraints = PortfolioConstraints(max_weight=0.6, min_weight=0.0)
        result = constructor.construct("equal_weight", returns, constraints=constraints)
        assert isinstance(result, Portfolio)
        assert np.isclose(result.weights.sum(), 1.0)

    def test_invalid_strategy_name(self):
        """Invalid strategy name raises InvalidStrategyError."""
        constructor = PortfolioConstructor()
        returns = pd.DataFrame({"AAPL": [0.01, 0.02]})
        with pytest.raises(InvalidStrategyError):
            constructor.construct("does_not_exist", returns)

    def test_compare_strategies(self):
        """Compare multiple strategies returns aligned DataFrame."""
        constructor = PortfolioConstructor()

        class DummyStrategy(PortfolioStrategy):
            @property
            def name(self) -> str:
                return "dummy"

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
                    strategy="dummy",
                )

        constructor.register_strategy("dummy", DummyStrategy())
        returns = pd.DataFrame(
            {
                "A": [0.01, 0.02],
                "B": [0.015, 0.005],
            },
        )
        constraints = PortfolioConstraints(max_weight=1.0, min_weight=0.0)
        comparison = constructor.compare_strategies(
            ["equal_weight", "dummy"],
            returns,
            constraints=constraints,
        )
        assert isinstance(comparison, pd.DataFrame)
        assert {"equal_weight", "dummy"}.issubset(comparison.columns)


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

    def test_constraints_allow_flexible_allocations(self):
        """Constraints should allow room for non-equity/bond allocations."""
        constraints = PortfolioConstraints(
            min_bond_exposure=0.6,
            max_equity_exposure=0.3,
        )
        assert constraints.min_bond_exposure == 0.6
        assert constraints.max_equity_exposure == 0.3


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
