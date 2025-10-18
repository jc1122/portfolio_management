"""Transaction cost modeling for realistic backtesting.

This module provides models for calculating commissions, slippage, and other
transaction costs that occur during portfolio rebalancing.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from portfolio_management.exceptions import TransactionCostError


@dataclass
class TransactionCostModel:
    """Model for calculating realistic transaction costs.

    Attributes:
        commission_pct: Commission as percentage of trade value.
        commission_min: Minimum commission per trade.
        slippage_bps: Slippage in basis points.

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
        """Calculate total transaction cost for a trade.

        Args:
            ticker: Asset ticker symbol.
            shares: Number of shares traded (absolute value).
            price: Execution price per share.
            is_buy: True for buy orders, False for sell orders.

        Returns:
            Total cost as Decimal (always positive).

        Raises:
            TransactionCostError: If calculation fails.

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
        """Calculate costs for multiple trades.

        Args:
            trades: Dict mapping ticker to (shares, price) tuples.
                   shares > 0 for buys, < 0 for sells.

        Returns:
            Dict mapping ticker to transaction cost.

        """
        costs = {}
        for ticker, (shares, price) in trades.items():
            if shares == 0:
                costs[ticker] = Decimal("0.00")
                continue
            is_buy = shares > 0
            costs[ticker] = self.calculate_cost(ticker, abs(shares), price, is_buy)
        return costs
