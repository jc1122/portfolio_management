# Example: Production and Research Workflows

Running a single backtest is useful, but in a real-world research or production environment, you need to manage more complex workflows. This guide covers common patterns for daily operations, batch execution, cache management, and error handling.

## Daily Data Update Process

A typical daily workflow might involve:

1. **Fetch New Data**: Update your raw price data from your data source (e.g., Stooq).
1. **Prepare Data**: Run the `prepare_tradeable_data.py` script to process the new raw data into the `prices.csv` and `returns.csv` files used by the backtesting engine. Thanks to the incremental resume feature, this will be very fast if no new data is found.
1. **Run Scheduled Backtests**: Execute your suite of regular backtests (e.g., using a batch script) to monitor strategy performance with the latest data.
1. **Archive and Report**: Archive the results and generate reports for review.

This process ensures that your research is always based on the most up-to-date information.

## Batch Backtest Execution

It's often necessary to run many backtests at once, for example, to compare different strategies or to test the sensitivity of a strategy to its parameters. The `examples/batch_backtest.py` script provides a template for this.

### How It Works

1. **Load Data Once**: The script starts by loading the price and return data into memory. This data is then reused for all subsequent backtests, which is much more efficient than reloading it for each run.
1. **Define a Batch**: A list of configurations is defined. Each configuration specifies the parameters for a single backtest (e.g., the preselection method, `top_k`, membership policy).
1. **Loop and Execute**: The script loops through the configurations, creating and running a `BacktestEngine` for each one.
1. **Organize Output**: The results for each run are saved to a dedicated subdirectory (e.g., `outputs/examples/batch_backtest/Momentum_Top30_Buffer50/`), keeping the results clean and organized.
1. **Final Summary**: After all backtests are complete, the script generates a final summary CSV file that compares the key performance metrics of all the strategies, making it easy to see which one performed best.

This pattern is highly extensible and can be adapted for parameter sweeps, strategy comparisons, or daily production runs.

## Cache Management and Maintenance

The on-disk caching system is a powerful feature for improving performance, especially when running the same backtest multiple times or when running backtests with overlapping data (like in a daily process).

### How It Works

- When you run a backtest with caching enabled (`--enable-cache` flag or `FactorCache(enabled=True)`), the results of expensive calculations (momentum scores, volatility scores, PIT eligibility masks) are saved to disk.
- The cache key is a hash of the dataset, the configuration, and the date, so it's very specific.
- The next time a backtest is run with the same configuration, the engine will find the results in the cache and load them directly, skipping the expensive recalculation.

### The `examples/cache_management.py` Script

This script provides a clear demonstration of the cache's impact:

1. It first clears the cache to ensure a clean state.
1. It runs a backtest and times it. On this first run, all calculations are done from scratch, and the results are written to the cache. You'll see that the cache statistics show all "misses."
1. It then runs the *exact same backtest again*. This time, it's significantly faster because all the results are read from the cache. The cache statistics will now show all "hits."

### Cache Maintenance

- **Cache Directory**: By default, the cache is stored in `.cache/`. You can specify a different directory with the `--cache-dir` argument. It's good practice to use different cache directories for different projects or experiments.
- **Cache Invalidation**: The cache is automatically invalidated if the underlying data or configuration changes. You don't need to clear it manually unless you want to force a full recalculation.
- **Clearing the Cache**: You can clear the cache at any time by simply deleting the cache directory. The `FactorCache` object also has a `.clear()` method for programmatic clearing.

## Error Handling and Monitoring

In a production workflow, robust error handling is crucial.

- **Custom Exceptions**: The backtesting engine uses a hierarchy of custom exceptions (e.g., `InsufficientHistoryError`, `InvalidBacktestConfigError`). This allows you to catch specific errors and handle them appropriately in your scripts.
- **Verbose Logging**: Using the `--verbose` flag in `run_backtest.py` will print detailed progress information and error tracebacks, which is essential for debugging.
- **Exit Codes**: The CLI scripts return non-zero exit codes on failure, which can be used by schedulers (like `cron`) or workflow tools (like Airflow) to detect and handle failed runs.

By combining these patterns, you can build a robust, efficient, and automated workflow for your investment research and strategy execution.
