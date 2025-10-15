"""Shared utilities for parallel execution and performance monitoring.

This module provides helper functions for:

- Parallel and sequential task execution with result ordering
- Error handling and diagnostics in concurrent operations
- Performance monitoring and timing utilities

Key functions:
    - _run_in_parallel: Execute tasks in parallel with optional ordering
    - log_duration: Context manager for timing operations
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from typing import Any, Callable, Generator, TypeVar

LOGGER = logging.getLogger(__name__)

T = TypeVar("T")


def _run_in_parallel(
    func: Callable[..., T],
    args_list: list[tuple[Any, ...]],
    max_workers: int,
    *,
    preserve_order: bool = True,
    log_tasks: bool = False,
) -> list[T]:
    """Run a function in parallel with a list of arguments.

    Args:
        func: The function to run in parallel.
        args_list: List of argument tuples to pass to func.
        max_workers: Maximum number of worker threads. If <= 1, runs sequentially.
        preserve_order: If True, results match input order. If False, results are
            returned as they complete (faster, but order is unpredictable).
        log_tasks: If True, logs task start/completion events at debug level.

    Returns:
        List of results from func calls. When preserve_order=True, results are
        in the same order as args_list. When preserve_order=False, results may
        be in any order.

    Raises:
        Exception: Re-raises any exception from worker tasks with context about
            which task failed (if available).

    """
    if max_workers <= 1:
        # Sequential execution with error handling
        results_seq: list[T] = []
        for idx, args in enumerate(args_list):
            try:
                if log_tasks:
                    LOGGER.debug("Executing task %d/%d", idx + 1, len(args_list))
                result = func(*args)
                results_seq.append(result)
                if log_tasks:
                    LOGGER.debug("Completed task %d/%d", idx + 1, len(args_list))
            except Exception as exc:
                LOGGER.error("Task %d failed: %s", idx, exc, exc_info=True)
                raise RuntimeError(f"Task {idx} failed: {exc}") from exc
        return results_seq

    results: list[T | Exception] = [None] * len(args_list)  # type: ignore
    completed_count = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks with their original indices
        future_to_index = {
            executor.submit(func, *args): idx for idx, args in enumerate(args_list)
        }

        if preserve_order:
            # Use map-like behavior to preserve order
            for future, idx in sorted(future_to_index.items(), key=lambda x: x[1]):
                try:
                    if log_tasks:
                        LOGGER.debug("Executing task %d/%d", idx + 1, len(args_list))
                    results[idx] = future.result()
                    completed_count += 1
                    if log_tasks:
                        LOGGER.debug(
                            "Completed task %d/%d",
                            completed_count,
                            len(args_list),
                        )
                except Exception as exc:
                    LOGGER.error("Task %d failed: %s", idx, exc, exc_info=True)
                    raise RuntimeError(f"Task {idx} failed: {exc}") from exc
        else:
            # Use as_completed for faster return (order not preserved)
            for future in as_completed(future_to_index.keys()):
                idx = future_to_index[future]
                try:
                    if log_tasks:
                        LOGGER.debug("Executing task %d/%d", idx + 1, len(args_list))
                    results[idx] = future.result()
                    completed_count += 1
                    if log_tasks:
                        LOGGER.debug(
                            "Completed task %d/%d",
                            completed_count,
                            len(args_list),
                        )
                except Exception as exc:
                    LOGGER.error("Task %d failed: %s", idx, exc, exc_info=True)
                    raise RuntimeError(f"Task {idx} failed: {exc}") from exc

    return results  # type: ignore


@contextmanager
def log_duration(step: str) -> Generator[None, None, None]:
    """Context manager to log the duration of an operation.

    Args:
        step: Description of the operation being timed.

    Yields:
        None

    """
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        LOGGER.info("%s completed in %.2fs", step, elapsed)
