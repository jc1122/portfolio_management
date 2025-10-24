# Best Practices and Guidelines

This guide provides best practices and recommendations for using the portfolio management toolkit effectively, from configuration and data preparation to performance optimization and strategy design.

## Configuration Recommendations

- **Separate Configs from Code**: Avoid hardcoding parameters in your scripts. Use YAML configuration files (`universes.yaml`, or custom config files) to define your strategies. This makes your research more organized, reproducible, and easier to modify. The `examples/` scripts hardcode values for clarity, but the associated `.yaml` files show the best practice.
- **Use a Main Universe File**: Maintain a central `universes.yaml` file for your commonly used universes. For one-off experiments, you can create separate YAML files and specify them with the `--universe-file` argument.
- **Version Your Configurations**: Store your YAML configuration files in Git. This allows you to track changes to your strategies over time and ensures that you can always reproduce past results.

## Performance Optimization Tips

- **Enable Caching**: Always use the `--enable-cache` flag (or `FactorCache(enabled=True)`) for development and production runs. The performance improvement is significant, especially for iterative research.
- **Use Fast I/O**: If you have `polars` and `pyarrow` installed, the toolkit will automatically use them for faster CSV and Parquet file reading. This can provide a 2-5x speedup on data loading.
- **Limit Your Universe**: When possible, work with the specific assets you need. While the toolkit is optimized for large universes, loading data for 1000 assets will always be slower than for 100. Use the filtering capabilities in `manage_universes.py` to create smaller, more focused universes.
- **Choose the Right Rebalancing Frequency**: Rebalancing every day is computationally intensive. For most long-term strategies, monthly or quarterly rebalancing is sufficient and will run much faster.

## Cache Usage Patterns

- **Shared Cache for Batches**: When running a batch of backtests, initialize a single `FactorCache` instance and pass it to each backtest run. This allows the backtests to share cached results (e.g., if they use the same factor calculations on the same data).
- **Dedicated Cache for Experiments**: For unrelated experiments, consider using separate cache directories (`--cache-dir .cache/my_experiment`) to avoid any potential conflicts or unintended cache hits.
- **Set a `max_cache_age_days`**: For production workflows that run daily, it's a good practice to set a maximum cache age (e.g., 7 days). This ensures that the cache is periodically refreshed, which can help to catch subtle data corruption issues.

## Data Preparation Guidelines

- **Garbage In, Garbage Out**: The quality of your backtest results is entirely dependent on the quality of your input data. Take the time to clean and validate your price data.
- **Use the Data Diagnostics**: The `prepare_tradeable_data.py` script generates diagnostic reports. Review these reports to identify issues like missing data, zero-volume days, and price anomalies.
- **Understand Your Survivors**: Be aware of survivorship bias. Your asset universe should include delisted securities to get a realistic picture of historical performance.

## Rebalancing Frequency Guidelines

The choice of rebalancing frequency has a significant impact on both performance and transaction costs.

- **High-Frequency Strategies (Daily/Weekly)**: Suitable for short-term, high-turnover strategies. Be aware that this will lead to higher transaction costs and requires very high-quality data.
- **Medium-Frequency Strategies (Monthly)**: A good default for many factor strategies, including momentum. It provides a good balance between adapting to new information and keeping costs down.
- **Low-Frequency Strategies (Quarterly/Annual)**: Best for long-term, low-turnover strategies like defensive, low-volatility, or strategic asset allocation. This minimizes transaction costs and the impact of short-term market noise.

By following these best practices, you can ensure that your research is robust, reproducible, and efficient.
