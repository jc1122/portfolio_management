"""Transaction cost modeling for realistic backtesting.

This module provides the `TransactionCostModel`, a class for calculating
commissions, slippage, and other costs associated with trading. Applying
realistic transaction costs is essential for accurate backtesting, as they
can significantly impact performance.

Key Classes:
    - TransactionCostModel: Calculates costs for individual or batch trades.

Cost Components:
    - **Commission**: The fee paid to a broker for executing a trade. It can be
      a percentage of the trade value or a minimum flat fee.
    - **Slippage**: The difference between the expected price of a trade and the
      price at which the trade is actually executed. It is often modeled as a
      small percentage (basis points) of the trade value and always acts as a
      cost to the trader.

Usage Example:
    >>> from decimal import Decimal
    >>> from portfolio_management.backtesting.transactions.costs import TransactionCostModel
    >>>
    >>> # Model with 0.1% commission and 5 bps slippage
    >>> cost_model = TransactionCostModel(
    ...     commission_pct=0.001,
    ...     commission_min=1.0,
    ...     slippage_bps=5.0
    ... )
    >>>
    >>> # Calculate cost for buying 100 shares of AAPL at $150
    >>> cost = cost_model.calculate_cost(
    ...     ticker="AAPL",
    ...     shares=100,
    ...     price=150.0,
    ...     is_buy=True
    ... )
    >>>
    >>> # Expected commission: max(100 * 150 * 0.001, 1.0) = $15.00
    >>> # Expected slippage: 100 * 150 * (5 / 10000) = $7.50
    >>> # Total cost: 15.00 + 7.50 = $22.50
    >>> print(f"Total cost for the trade: ${cost}")
    Total cost for the trade: $22.50
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from portfolio_management.core.exceptions import TransactionCostError


@dataclass
class TransactionCostModel:
    """Model for calculating realistic transaction costs.

    This class combines multiple cost components (commission, slippage) to
    provide a total cost for a given trade.

    Attributes:
        commission_pct (float): The commission charged as a percentage of the
            total trade value. E.g., 0.001 for 0.1%.
        commission_min (float): The minimum flat fee for a commission. The actual
            commission will be `max(trade_value * commission_pct, commission_min)`.
        slippage_bps (float): The estimated slippage cost in basis points (1/100th
            of a percent). E.g., 5.0 bps means a cost of 0.05% of the trade value.

    Example:
        >>> model = TransactionCostModel(commission_pct=0.001, slippage_bps=10)
        >>> cost = model.calculate_cost("MSFT", shares=50, price=300.0, is_buy=True)
        >>> # Commission = 50 * 300 * 0.001 = 15.0
        >>> # Slippage = 50 * 300 * (10 / 10000) = 15.0
        >>> # Total = 15.0 + 15.0 = 30.0
        >>> print(cost)
        30.00
    """

    commission_pct: float = 0.001  # 0.1%
    commission_min: float = 0.0
    slippage_bps: float = 5.0  # 5 bps

    def calculate_cost(
        self,
        ticker: str,
        shares: int,
        price: float,
        is_buy: bool,
    ) -> Decimal:
        """Calculate the total transaction cost for a single trade.

        The total cost is the sum of the commission and slippage.

        Args:
            ticker (str): The symbol of the asset being traded.
            shares (int): The absolute number of shares being traded.
            price (float): The execution price per share.
            is_buy (bool): True if the trade is a buy, False for a sell.

        Returns:
            Decimal: The total calculated cost for the trade, always positive.

        Raises:
            TransactionCostError: If input `shares` is negative or `price` is
                non-positive.
        """
        if shares < 0:
            raise TransactionCostError(
                transaction_type=f"{'buy' if is_buy else 'sell'} {ticker}",
                amount=float(shares),
                reason=f"Shares must be non-negative, got {shares}",
            )
        if price <= 0:
            raise TransactionCostError(
                transaction_type=f"{'buy' if is_buy else 'sell'} {ticker}",
                amount=price,
                reason=f"Price must be positive, got {price}",
            )

        # Calculate base trade value
        trade_value = abs(shares) * price

        # Commission (max of percentage or minimum)
        commission = max(
            trade_value * self.commission_pct,
            self.commission_min if shares > 0 else 0.0,
        )

        # Slippage (always a cost, regardless of direction)
        slippage = trade_value * (self.slippage_bps / 10000.0)

        total_cost = commission + slippage
        return Decimal(str(round(total_cost, 2)))

    def calculate_batch_cost(
        self,
        trades: dict[str, tuple[int, float]],
    ) -> dict[str, Decimal]:
        """Calculate costs for a batch of multiple trades.

        Args:
            trades (dict[str, tuple[int, float]]): A dictionary mapping a ticker
                to a tuple of (shares, price). A positive number of shares
                indicates a buy, and a negative number indicates a sell.

        Returns:
            dict[str, Decimal]: A dictionary mapping each ticker to its
            calculated transaction cost.
        """
        costs = {}
        for ticker, (shares, price) in trades.items():
            if shares == 0:
                costs[ticker] = Decimal("0.00")
                continue
            is_buy = shares > 0
            costs[ticker] = self.calculate_cost(ticker, abs(shares), price, is_buy)
        return costs