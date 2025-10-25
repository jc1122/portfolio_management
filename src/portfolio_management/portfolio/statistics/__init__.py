"""Portfolio statistics package.

This package provides efficient rolling statistics computation for portfolio strategies,
including caching mechanisms to avoid redundant calculations during rebalancing.
"""

from .rolling_statistics import StatisticsCache, RollingStatistics

__all__ = ["StatisticsCache", "RollingStatistics"]
