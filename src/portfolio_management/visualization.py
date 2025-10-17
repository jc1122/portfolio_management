"""Visualization data preparation utilities.

Provides functions to prepare backtest results for charting libraries
like Matplotlib, Plotly, or web dashboards.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from portfolio_management.backtest import PerformanceMetrics, RebalanceEvent


def prepare_equity_curve(equity_df: pd.DataFrame) -> pd.DataFrame:
    """Prepare equity curve data for plotting.

    Args:
        equity_df: DataFrame with equity values (from BacktestEngine.run).

    Returns:
        DataFrame with date index and normalized equity column.
    """
    result = equity_df.copy()
    initial_value = result["equity"].iloc[0]
    result["equity_normalized"] = result["equity"] / initial_value * 100
    result["equity_change_pct"] = (result["equity"] / initial_value - 1) * 100
    return result


def prepare_drawdown_series(equity_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate drawdown series for plotting.

    Args:
        equity_df: DataFrame with equity values.

    Returns:
        DataFrame with drawdown percentages and underwater periods.
    """
    equity = equity_df["equity"]
    
    # Calculate running maximum
    running_max = equity.expanding().max()
    
    # Calculate drawdown as percentage
    drawdown = (equity - running_max) / running_max * 100
    
    # Identify underwater periods (when in drawdown)
    underwater = drawdown < 0
    
    return pd.DataFrame({
        "drawdown_pct": drawdown,
        "running_max": running_max,
        "underwater": underwater,
    })


def prepare_allocation_history(
    rebalance_events: list[RebalanceEvent],
) -> pd.DataFrame:
    """Prepare allocation history for stacked area chart.

    Args:
        rebalance_events: List of rebalance events from backtest.

    Returns:
        DataFrame with dates and allocation percentages per asset.
    """
    if not rebalance_events:
        return pd.DataFrame()

    records = []
    for event in rebalance_events:
        total_value = float(event.post_rebalance_value)
        if total_value == 0:
            continue

        record = {"date": event.date}
        
        # Calculate cash percentage
        record["cash_pct"] = float(event.cash_after) / total_value * 100
        
        # Calculate holdings percentages
        holdings_value = float(event.post_rebalance_value - event.cash_after)
        record["holdings_pct"] = holdings_value / total_value * 100 if total_value > 0 else 0.0
        
        # Add trigger type
        record["trigger"] = event.trigger.value
        
        records.append(record)

    return pd.DataFrame(records).set_index("date")


def prepare_rolling_metrics(
    equity_df: pd.DataFrame, window: int = 60
) -> pd.DataFrame:
    """Calculate rolling performance metrics.

    Args:
        equity_df: DataFrame with equity values.
        window: Rolling window size in days (default: 60).

    Returns:
        DataFrame with rolling Sharpe, volatility, and return.
    """
    # Calculate daily returns
    returns = equity_df["equity"].pct_change()

    # Rolling statistics
    rolling_return = returns.rolling(window).mean() * 252  # Annualized
    rolling_vol = returns.rolling(window).std() * (252**0.5)  # Annualized
    rolling_sharpe = rolling_return / rolling_vol

    # Rolling max drawdown
    equity = equity_df["equity"]
    rolling_max = equity.rolling(window).max()
    rolling_dd = (equity - rolling_max) / rolling_max * 100

    return pd.DataFrame(
        {
            "rolling_return_annual": rolling_return,
            "rolling_volatility_annual": rolling_vol,
            "rolling_sharpe": rolling_sharpe,
            "rolling_max_drawdown": rolling_dd.rolling(window).min(),
        }
    )


def prepare_transaction_costs_summary(
    rebalance_events: list[RebalanceEvent],
) -> pd.DataFrame:
    """Summarize transaction costs over time.

    Args:
        rebalance_events: List of rebalance events from backtest.

    Returns:
        DataFrame with cumulative costs and cost breakdown.
    """
    if not rebalance_events:
        return pd.DataFrame()

    records = []
    cumulative = 0.0
    
    for event in rebalance_events:
        costs = float(event.costs)
        cumulative += costs
        
        records.append({
            "date": event.date,
            "costs": costs,
            "cumulative_costs": cumulative,
            "trigger": event.trigger.value,
            "num_trades": len([t for t in event.trades.values() if t != 0]),
            "portfolio_value": float(event.pre_rebalance_value),
            "costs_bps": (costs / float(event.pre_rebalance_value) * 10000) 
                if event.pre_rebalance_value > 0 else 0.0,
        })

    df = pd.DataFrame(records)
    df = df.set_index("date")
    return df


def prepare_returns_distribution(equity_df: pd.DataFrame) -> pd.DataFrame:
    """Prepare returns distribution data for histogram plotting.

    Args:
        equity_df: DataFrame with equity values.

    Returns:
        DataFrame with returns and distribution statistics.
    """
    returns = equity_df["equity"].pct_change().dropna()
    
    # Calculate statistics
    mean_return = returns.mean()
    std_return = returns.std()
    
    # Create bins for histogram
    return pd.DataFrame({
        "returns": returns,
        "returns_pct": returns * 100,
        "positive": returns > 0,
        "mean": mean_return,
        "std": std_return,
    })


def prepare_monthly_returns_heatmap(equity_df: pd.DataFrame) -> pd.DataFrame:
    """Prepare monthly returns data for heatmap visualization.

    Args:
        equity_df: DataFrame with equity values.

    Returns:
        DataFrame with years as index and months as columns.
    """
    # Calculate daily returns
    returns = equity_df["equity"].pct_change()
    
    # Resample to monthly
    monthly_returns = (1 + returns).resample("M").prod() - 1
    
    # Create pivot table with years and months
    monthly_returns_df = pd.DataFrame({
        "return": monthly_returns.values,
        "year": monthly_returns.index.year,
        "month": monthly_returns.index.month,
    })
    
    # Pivot to create heatmap structure
    heatmap = monthly_returns_df.pivot(
        index="year", columns="month", values="return"
    ) * 100  # Convert to percentage
    
    # Rename columns to month names
    month_names = {
        1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
        5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
        9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
    }
    heatmap.columns = [month_names.get(m, str(m)) for m in heatmap.columns]
    
    return heatmap


def prepare_metrics_comparison(
    metrics_list: list[tuple[str, PerformanceMetrics]]
) -> pd.DataFrame:
    """Prepare performance metrics comparison table.

    Args:
        metrics_list: List of tuples (strategy_name, metrics).

    Returns:
        DataFrame with strategies as rows and metrics as columns.
    """
    records = []
    
    for strategy_name, metrics in metrics_list:
        records.append({
            "Strategy": strategy_name,
            "Total Return %": metrics.total_return * 100,
            "Annual Return %": metrics.annualized_return * 100,
            "Volatility %": metrics.annualized_volatility * 100,
            "Sharpe Ratio": metrics.sharpe_ratio,
            "Sortino Ratio": metrics.sortino_ratio,
            "Max Drawdown %": metrics.max_drawdown * 100,
            "Calmar Ratio": metrics.calmar_ratio,
            "Win Rate %": metrics.win_rate * 100,
            "Total Costs $": float(metrics.total_costs),
            "Num Rebalances": metrics.num_rebalances,
        })
    
    return pd.DataFrame(records).set_index("Strategy")


def prepare_trade_analysis(
    rebalance_events: list[RebalanceEvent],
) -> pd.DataFrame:
    """Analyze individual trades from rebalance events.

    Args:
        rebalance_events: List of rebalance events from backtest.

    Returns:
        DataFrame with trade-level details.
    """
    if not rebalance_events:
        return pd.DataFrame()

    records = []
    
    for event in rebalance_events:
        for ticker, shares in event.trades.items():
            if shares == 0:
                continue
                
            records.append({
                "date": event.date,
                "ticker": ticker,
                "shares": shares,
                "direction": "BUY" if shares > 0 else "SELL",
                "abs_shares": abs(shares),
                "trigger": event.trigger.value,
                "portfolio_value": float(event.pre_rebalance_value),
            })
    
    if not records:
        return pd.DataFrame()
    
    df = pd.DataFrame(records)
    
    # Add aggregations
    df["trade_count"] = 1
    
    return df


def create_summary_report(
    equity_df: pd.DataFrame,
    metrics: PerformanceMetrics,
    rebalance_events: list[RebalanceEvent],
) -> dict[str, object]:
    """Create a comprehensive summary report dictionary.

    Args:
        equity_df: DataFrame with equity values.
        metrics: Performance metrics from backtest.
        rebalance_events: List of rebalance events.

    Returns:
        Dictionary with all key statistics and data for reporting.
    """
    returns = equity_df["equity"].pct_change().dropna()
    
    summary = {
        # Performance
        "performance": {
            "total_return_pct": round(metrics.total_return * 100, 2),
            "annualized_return_pct": round(metrics.annualized_return * 100, 2),
            "volatility_pct": round(metrics.annualized_volatility * 100, 2),
            "sharpe_ratio": round(metrics.sharpe_ratio, 2),
            "sortino_ratio": round(metrics.sortino_ratio, 2),
            "max_drawdown_pct": round(metrics.max_drawdown * 100, 2),
            "calmar_ratio": round(metrics.calmar_ratio, 2),
        },
        
        # Risk metrics
        "risk": {
            "expected_shortfall_95_pct": round(metrics.expected_shortfall_95 * 100, 2),
            "win_rate_pct": round(metrics.win_rate * 100, 1),
            "avg_win_pct": round(metrics.avg_win * 100, 2),
            "avg_loss_pct": round(metrics.avg_loss * 100, 2),
            "best_day_pct": round(returns.max() * 100, 2) if len(returns) > 0 else 0.0,
            "worst_day_pct": round(returns.min() * 100, 2) if len(returns) > 0 else 0.0,
        },
        
        # Trading activity
        "trading": {
            "num_rebalances": metrics.num_rebalances,
            "total_costs_usd": float(metrics.total_costs),
            "avg_turnover": round(metrics.turnover, 2),
            "total_trades": sum(
                len([t for t in event.trades.values() if t != 0])
                for event in rebalance_events
            ),
        },
        
        # Portfolio evolution
        "portfolio": {
            "initial_value": float(equity_df["equity"].iloc[0]),
            "final_value": float(equity_df["equity"].iloc[-1]),
            "peak_value": float(equity_df["equity"].max()),
            "num_days": len(equity_df),
        },
    }
    
    return summary
