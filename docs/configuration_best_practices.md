# Configuration Best Practices

This guide provides best practices, tips for performance optimization, and common mistakes to avoid when configuring your universes.

## General Best Practices

1.  **Start Simple**: Begin with a simple configuration and gradually add complexity. Don't try to enable everything at once.
2.  **Use a `description`**: Always add a `description` to your universes. It makes it much easier to remember what each configuration is for.
3.  **Separate Universes**: Create separate universe definitions for different strategies. Don't try to make one universe that does everything.
4.  **Version Control**: Keep your `universes.yaml` file in version control (e.g., Git). This allows you to track changes to your strategies over time.

## Performance Optimization Tips

If your backtests are running slowly, consider the following:

1.  **Use Preselection**: This is the most important optimization. Use the `preselection` section to reduce the number of assets before they are passed to the optimizer. Reducing a universe of 1000 assets to 100 can result in a 1000x speedup for some optimizers.
2.  **Use a Shorter `lookback`**: A shorter `lookback` period in the `preselection` section means less data to process at each rebalance. A 6-month lookback (`126` days) can be significantly faster than a 12-month one (`252` days).
3.  **Enable Caching**: Use the `--use-cache` command-line flag when running your backtests. This will store intermediate results and speed up subsequent runs.
4.  **Use Chunked I/O**: If your initial master list of assets is very large, use the `--chunk-size` command-line flag to process it in chunks. This dramatically reduces memory usage.
5.  **Rebalance Less Frequently**: Changing the `frequency` in `return_config` from `monthly` to `quarterly` will reduce the number of rebalancing events and thus the total backtest time.

## Common Mistakes and How to Avoid Them

1.  **Mistake**: Setting `max_assets` in `constraints` to be smaller than `top_k` in `preselection`.
    - **Problem**: This will cause an error, as the preselection will select `top_k` assets, but the constraint will then try to reduce the universe to a smaller number.
    - **Solution**: Ensure that `max_assets` is always greater than or equal to `top_k`.

2.  **Mistake**: Forgetting that `membership_policy` requires preselection.
    - **Problem**: The membership policy needs ranked assets to work, and this ranking is provided by the preselection step.
    - **Solution**: If you enable `membership_policy`, you must also have a `preselection` section in your configuration.

3.  **Mistake**: Setting a `buffer_rank` that is smaller than `top_k`.
    - **Problem**: The `buffer_rank` is the total rank an asset must be within, not an addition to `top_k`. If `top_k` is 50 and `buffer_rank` is 40, the buffer will have no effect.
    - **Solution**: Ensure that `buffer_rank` is always greater than `top_k`. A good rule of thumb is `buffer_rank = top_k + 10`.

4.  **Mistake**: Using a very aggressive membership policy.
    - **Problem**: Setting `max_turnover` or `max_new_assets` to very low values can starve your portfolio of new opportunities and force it to hold onto losing assets.
    - **Solution**: Use membership policy to gently guide the portfolio. Start with `min_holding_periods` and `buffer_rank`, and only use the `max_` constraints if necessary.

## Debugging Configuration Issues

If your universe isn't behaving as you expect:

1.  **Check the Logs**: Run the backtest script with the `--verbose` flag to get detailed logging output. This will often show you which assets are being filtered out at each stage.
2.  **Use `manage_universes.py`**: The `manage_universes.py` script has a `validate` command that can check your YAML file for syntax errors.
3.  **Isolate the Problem**: Create a copy of your universe and disable sections one by one. For example, disable the `membership_policy` to see if that is the source of the problem. Then disable `preselection`. This can help you pinpoint the issue.

## When to Enable Caching

- **Always** enable caching (`--use-cache`) if you are running the same backtest multiple times.
- The cache is smart enough to invalidate itself if you change the configuration of the universe.
- Caching is most effective for the return calculation step, which can be slow for large universes.

## When to Enable Fast IO

- Enable Fast I/O (`--chunk-size`) when your master list of all possible assets is very large (e.g., > 100,000 rows).
- This is a feature of the asset selection script, not the backtester, so you need to use it when you are running the `manage_universes.py load` command.
- A good starting value is `--chunk-size 5000`.