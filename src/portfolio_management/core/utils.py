"""Shared utilities for parallel execution and performance monitoring.

This module provides high-level helper functions for common tasks such as
concurrent execution and performance timing. These utilities are designed to be
robust, with clear error handling and configurable behavior.

The `run_in_parallel` function is a powerful tool for speeding up I/O-bound
or CPU-bound tasks that can be broken into independent chunks of work. The
`log_duration` context manager provides a simple way to measure and log the
time taken by critical sections of code.

Key Functions:
    run_in_parallel: Executes a function over a list of arguments in parallel.
    log_duration: A context manager for timing a code block.

Example:
    Using `run_in_parallel` to execute tasks and handle errors.

    >>> from portfolio_management.core.utils import run_in_parallel
    >>>
    >>> def slow_square(x: int) -> int:
    ...     if x == 2:
    ...         raise ValueError("Task failed for x=2")
    ...     return x * x
    >>>
    >>> try:
    ...     run_in_parallel(
    ...         slow_square,
    ...         [(0,), (1,), (2,), (3,)],
    ...         max_workers=2
    ...     )
    ... except RuntimeError as e:
    ...     print(f"Caught expected runtime error: {e}")
    Caught expected runtime error: Task 2 failed: Task failed for x=2
"""
from __future__ import annotations

import logging
import time
from collections.abc import Callable, Generator
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from typing import Any, TypeVar

LOGGER = logging.getLogger(__name__)

T = TypeVar("T")


def run_in_parallel(
    func: Callable[..., T],
    args_list: list[tuple[Any, ...]],
    max_workers: int,
    *,
    preserve_order: bool = True,
    log_tasks: bool = False,
) -> list[T]:
    """Runs a function in parallel over a list of argument sets.

    This function uses a `ThreadPoolExecutor` to distribute work across
    multiple threads. It includes robust error handling that wraps and
    re-raises exceptions from worker threads.

    If `max_workers` is 1 or less, the function executes sequentially, which is
    useful for debugging.

    Args:
        func: The function to execute in parallel.
        args_list: A list of tuples, where each tuple contains the arguments
            for one call to `func`.
        max_workers: The maximum number of worker threads to use.
        preserve_order: If `True` (default), results are returned in the
            same order as `args_list`. If `False`, results are returned in the
            order of completion.
        log_tasks: If `True`, logs task start/completion at DEBUG level.

    Returns:
        A list containing the results from each call to `func`.

    Raises:
        RuntimeError: If any worker task raises an exception. The original
            exception is chained.

    Example:
        Running a simple task and preserving order.

        >>> def add(x: int, y: int) -> int:
        ...     return x + y
        >>> args = [(1, 2), (3, 4), (5, 6)]
        >>> results = run_in_parallel(add, args, max_workers=2)
        >>> print(results)
        [3, 7, 11]

    Example:
        Handling a failed task.

        >>> def fail_on_two(x: int) -> int:
        ...     if x == 2:
        ...         raise ValueError("Failure")
        ...     return x
        >>> args = [(1,), (2,), (3,)]
        >>> try:
        ...     run_in_parallel(fail_on_two, args, max_workers=2)
        ... except RuntimeError as e:
        ...     print(f"Caught expected error: {e}")
        Caught expected error: Task 1 failed: Failure
    """
    if max_workers <= 1:
        # Sequential execution for easy debugging
        results_seq: list[T] = []
        for idx, args in enumerate(args_list):
            try:
                if log_tasks:
                    LOGGER.debug("Executing task %d/%d", idx + 1, len(args_list))
                result = func(*args)
                results_seq.append(result)
            except Exception as exc:
                LOGGER.error("Task %d failed: %s", idx, exc, exc_info=log_tasks)
                raise RuntimeError(f"Task {idx} failed: {exc}") from exc
        return results_seq

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {
            executor.submit(func, *args): idx for idx, args in enumerate(args_list)
        }

        if preserve_order:
            results: list[T | None] = [None] * len(args_list)
            index_to_future = {v: k for k, v in future_to_index.items()}
            for idx in sorted(index_to_future.keys()):
                future = index_to_future[idx]
                try:
                    results[idx] = future.result()
                except Exception as exc:
                    LOGGER.error("Task %d failed: %s", idx, exc, exc_info=log_tasks)
                    for f in future_to_index:
                        f.cancel()
                    raise RuntimeError(f"Task {idx} failed: {exc}") from exc
            return [res for res in results if res is not None]
        else:
            # When order is not preserved, append results as they complete.
            results_unordered: list[T] = []
            try:
                for future in as_completed(future_to_index):
                    idx = future_to_index[future]
                    try:
                        results_unordered.append(future.result())
                    except Exception as exc:
                        LOGGER.error("Task %d failed: %s", idx, exc, exc_info=log_tasks)
                        # Raise the first exception encountered.
                        raise RuntimeError(f"Task {idx} failed: {exc}") from exc
            finally:
                # Ensure all other futures are cancelled on exit.
                for f in future_to_index:
                    f.cancel()
            return results_unordered


@contextmanager
def log_duration(step: str) -> Generator[None, None, None]:
    """Context manager to log the duration of an operation.

    This is useful for performance monitoring and identifying bottlenecks.
    It logs the completion time upon exiting the context.

    Args:
        step: A description of the operation being timed.

    Yields:
        None.

    Example:
        >>> import time
        >>> import logging
        >>> import sys
        >>>
        >>> # Configure a logger to capture output for the doctest
        >>> logger = logging.getLogger("portfolio_management.core.utils")
        >>> handler = logging.StreamHandler(sys.stdout)
        >>> logger.addHandler(handler)
        >>> logger.setLevel(logging.INFO)
        >>>
        >>> with log_duration("data processing"): # doctest: +ELLIPSIS
        ...     time.sleep(0.01)
        data processing completed in ...s
        >>>
        >>> # Clean up the handler to avoid affecting other tests
        >>> logger.removeHandler(handler)
    """
    start_time = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start_time
        LOGGER.info("%s completed in %.2fs", step, elapsed)