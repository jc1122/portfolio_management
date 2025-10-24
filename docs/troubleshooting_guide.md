# Troubleshooting Guide

This guide provides solutions and diagnostic steps for common issues you might encounter while using the portfolio management toolkit.

## Performance Issues / Slow Backtests

If your backtests are running slower than expected, here are the most common causes and solutions.

#### 1. Caching is Disabled

**Symptom**: Running the same backtest twice takes the same amount of time. Subsequent runs are not faster.

**Solution**: Ensure that caching is enabled.

- **CLI**: Add the `--enable-cache` flag to your `run_backtest.py` command.
- **Programmatic**: Make sure you are creating a `FactorCache` object with `enabled=True` and passing it to the `BacktestEngine`.

#### 2. Large Universe Without Filtering

**Symptom**: The backtest is slow, especially during the initial data loading and factor calculation phases.

**Solution**: Pre-filter your universe if possible.

- If your strategy only applies to a subset of assets (e.g., equities only, US stocks only), create a smaller universe using `manage_universes.py`.
- Even if the preselection step will reduce the number of assets, the initial factor calculation is still performed on the entire universe. A smaller starting universe will always be faster.

#### 3. High Rebalancing Frequency

**Symptom**: The backtest is very slow, and the console output shows it processing day by day.

**Solution**: Use a lower rebalancing frequency if appropriate for your strategy.

- Changing from `--rebalance-frequency daily` to `monthly` or `quarterly` will dramatically reduce the number of calculations and speed up the backtest.

## Cache Issues

#### 1. Cache Not Invalidating (Stale Results)

**Symptom**: You've updated your data or configuration, but the backtest results don't change. The cache statistics show all hits.

**Solution**: This is rare, as the hashing mechanism is robust. However, if you suspect the cache is stale, you can force a refresh.

- **Clear the Cache**: The simplest solution is to delete the cache directory (e.g., `rm -rf .cache/`). The cache will be rebuilt on the next run.
- **Use a New Cache Directory**: Use the `--cache-dir .cache/new_experiment` argument to force the backtest to use a new, empty cache.

#### 2. Cache Corruption

**Symptom**: The backtest fails with a `pickle.UnpicklingError` or a similar error related to reading a file from the cache directory.

**Solution**: This can happen if a backtest is terminated abruptly while writing to the cache.

- **Clear the Cache**: Delete the cache directory. This will remove the corrupted file and allow the cache to be rebuilt cleanly on the next run.

## Data Quality Problems

#### 1. `InsufficientHistoryError`

**Symptom**: The backtest fails with an `InsufficientHistoryError`.

**Solution**: This error means that at a given rebalancing date, no assets in the universe met the minimum history requirements to be included in the portfolio.

- **Check `min_history_days`**: Your `use_pit_eligibility` setting might be too strict for your data. Try reducing `min_history_days`.
- **Check Your Data**: Your price/return data might have large gaps or start later than you think. Inspect the CSV files.
- **Broaden Your Universe**: The assets in your chosen universe might all be relatively new. Try using a universe with assets that have a longer history.

#### 2. Missing Assets in Data Files

**Symptom**: The backtest fails with `ValueError: Missing assets in prices file...`

**Solution**: The asset list in your universe configuration does not match the columns in your `prices.csv` or `returns.csv` files.

- **Check Universe vs. Data**: Make sure that every asset listed in your universe's `assets` list exists as a column header in your data files.
- **Regenerate Data**: If you've recently changed your universe, you may need to regenerate your processed data files using `prepare_tradeable_data.py` to ensure they are consistent.

## Configuration Errors

#### 1. Universe Not Found

**Symptom**: The CLI fails with `ValueError: Universe 'my_universe' not found.`

**Solution**: The `--universe-name` you provided doesn't exist in the specified `--universe-file`.

- **Check Spelling**: Double-check the spelling of the universe name.
- **Check File**: Make sure you are pointing to the correct YAML file and that the universe is defined within it.

#### 2. Invalid Strategy Name

**Symptom**: The CLI fails with an error related to an unknown strategy.

**Solution**: You have provided a strategy name that is not recognized.

- **Check `strategy` argument**: The first argument to `run_backtest.py` must be one of the implemented strategies: `equal_weight`, `risk_parity`, or `mean_variance`.
