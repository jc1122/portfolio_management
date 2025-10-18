"""Tests for concurrency utilities in utils module."""

from __future__ import annotations

import logging
from typing import Any

import pytest

from src.portfolio_management.utils import _run_in_parallel


def simple_task(x: int) -> int:
    """Simple task that returns input doubled."""
    return x * 2


def failing_task(x: int) -> int:
    """Task that fails on specific input."""
    if x < 0:
        raise ValueError(f"Cannot process negative value: {x}")
    return x * 2


def slow_task(x: int) -> int:
    """Slower task for testing timing."""
    import time

    time.sleep(0.01)
    return x * 2


class TestRunInParallel:
    """Tests for _run_in_parallel function."""

    def test_sequential_execution_single_worker(self) -> None:
        """Test that max_workers=1 executes sequentially."""
        args = [(1,), (2,), (3,), (4,), (5,)]
        results = _run_in_parallel(simple_task, args, max_workers=1)
        assert results == [2, 4, 6, 8, 10]

    def test_sequential_execution_zero_workers(self) -> None:
        """Test that max_workers=0 executes sequentially."""
        args = [(1,), (2,), (3,)]
        results = _run_in_parallel(simple_task, args, max_workers=0)
        assert results == [2, 4, 6]

    def test_sequential_execution_negative_workers(self) -> None:
        """Test that negative max_workers executes sequentially."""
        args = [(1,), (2,), (3,)]
        results = _run_in_parallel(simple_task, args, max_workers=-1)
        assert results == [2, 4, 6]

    def test_parallel_execution_multiple_workers(self) -> None:
        """Test parallel execution with multiple workers."""
        args = [(1,), (2,), (3,), (4,), (5,)]
        results = _run_in_parallel(simple_task, args, max_workers=2)
        assert sorted(results) == [2, 4, 6, 8, 10]

    def test_result_ordering_preserved(self) -> None:
        """Test that preserve_order=True maintains input order."""
        args = [(5,), (1,), (3,), (2,), (4,)]
        results = _run_in_parallel(
            simple_task,
            args,
            max_workers=2,
            preserve_order=True,
        )
        assert results == [10, 2, 6, 4, 8]

    def test_result_ordering_not_preserved(self) -> None:
        """Test that preserve_order=False may return unordered results."""
        args = [(1,), (2,), (3,), (4,), (5,)]
        # Can't guarantee specific order, but should have all results
        results = _run_in_parallel(
            simple_task,
            args,
            max_workers=2,
            preserve_order=False,
        )
        assert len(results) == 5
        assert sorted(results) == [2, 4, 6, 8, 10]

    def test_empty_task_list(self) -> None:
        """Test with empty task list."""
        args: list[tuple[Any, ...]] = []
        results = _run_in_parallel(simple_task, args, max_workers=2)
        assert results == []

    def test_single_task(self) -> None:
        """Test with single task."""
        args = [(42,)]
        results = _run_in_parallel(simple_task, args, max_workers=4)
        assert results == [84]

    def test_error_handling_single_worker(self) -> None:
        """Test error handling with sequential execution."""
        args = [(1,), (-5,), (3,)]
        with pytest.raises(RuntimeError, match="Task 1 failed"):
            _run_in_parallel(failing_task, args, max_workers=1)

    def test_error_handling_parallel(self) -> None:
        """Test error handling with parallel execution."""
        args = [(1,), (-5,), (3,)]
        with pytest.raises(RuntimeError, match="Task.*failed"):
            _run_in_parallel(failing_task, args, max_workers=2)

    def test_error_context_includes_task_index(self) -> None:
        """Test that error message includes task index."""
        args = [(1,), (2,), (-3,), (4,)]
        with pytest.raises(RuntimeError, match="Task 2"):
            _run_in_parallel(failing_task, args, max_workers=1)

    def test_task_logging_enabled(self, caplog: Any) -> None:
        """Test that log_tasks=True produces debug logs."""
        args = [(1,), (2,), (3,)]
        with caplog.at_level(
            logging.DEBUG, logger="src.portfolio_management.core.utils"
        ):
            _run_in_parallel(simple_task, args, max_workers=1, log_tasks=True)

        # Should have logs for each task
        assert (
            "executing task" in caplog.text.lower()
            or "completed task" in caplog.text.lower()
        )

    def test_task_logging_disabled(self, caplog: Any) -> None:
        """Test that log_tasks=False doesn't produce debug logs."""
        args = [(1,), (2,), (3,)]
        with caplog.at_level(
            logging.DEBUG, logger="src.portfolio_management.core.utils"
        ):
            _run_in_parallel(simple_task, args, max_workers=2, log_tasks=False)

        # Should not have debug logs about task execution
        assert "executing task" not in caplog.text.lower()

    def test_many_tasks_parallel_execution(self) -> None:
        """Test with larger number of tasks."""
        args = [(i,) for i in range(100)]
        results = _run_in_parallel(
            simple_task,
            args,
            max_workers=4,
            preserve_order=True,
        )
        assert results == [i * 2 for i in range(100)]

    def test_worker_count_scaling(self) -> None:
        """Test that different worker counts produce same results."""
        args = [(i,) for i in range(20)]

        result_1_worker = _run_in_parallel(simple_task, args, max_workers=1)
        result_2_workers = _run_in_parallel(
            simple_task,
            args,
            max_workers=2,
            preserve_order=True,
        )
        result_4_workers = _run_in_parallel(
            simple_task,
            args,
            max_workers=4,
            preserve_order=True,
        )

        assert result_1_worker == result_2_workers == result_4_workers

    def test_preserve_order_correctness_with_timing_variance(self) -> None:
        """Test that preserve_order works correctly despite timing variance."""
        # slow_task takes longer, so completion order would be different from submission order
        args = [(5,), (1,), (3,), (2,), (4,)]
        results = _run_in_parallel(slow_task, args, max_workers=2, preserve_order=True)
        assert results == [10, 2, 6, 4, 8]

    def test_multiple_argument_task(self) -> None:
        """Test with tasks that take multiple arguments."""

        def add(a: int, b: int) -> int:
            return a + b

        args = [(1, 2), (3, 4), (5, 6)]
        results = _run_in_parallel(add, args, max_workers=2, preserve_order=True)
        assert results == [3, 7, 11]

    def test_default_parameters(self) -> None:
        """Test that default parameters work as expected."""
        args = [(1,), (2,), (3,)]
        # Should work with just required parameters
        results = _run_in_parallel(simple_task, args, max_workers=2)
        assert sorted(results) == [2, 4, 6]

    def test_concurrent_error_handling_first_task(self) -> None:
        """Test error handling when first task fails in parallel."""

        def failing_first(x: int) -> int:
            if x == 1:
                raise ValueError("First task failed")
            return x * 2

        args = [(1,), (2,), (3,)]
        with pytest.raises(RuntimeError, match="Task 0 failed"):
            _run_in_parallel(failing_first, args, max_workers=2)

    def test_concurrent_error_handling_last_task(self) -> None:
        """Test error handling when last task fails in parallel."""

        def failing_last(x: int) -> int:
            if x == 3:
                raise ValueError("Last task failed")
            return x * 2

        args = [(1,), (2,), (3,)]
        with pytest.raises(RuntimeError, match="Task 2 failed"):
            _run_in_parallel(failing_last, args, max_workers=2)

    def test_concurrent_error_handling_middle_task(self) -> None:
        """Test error handling when middle task fails in parallel."""

        def failing_middle(x: int) -> int:
            if x == 2:
                raise ValueError("Middle task failed")
            return x * 2

        args = [(1,), (2,), (3,), (4,), (5,)]
        with pytest.raises(RuntimeError, match="Task.*failed"):
            _run_in_parallel(failing_middle, args, max_workers=2)

    def test_error_with_exception_type_preserved(self) -> None:
        """Test that error information is preserved."""

        def task_with_type_error(x: int) -> int:
            if x < 0:
                raise TypeError(f"Type error: {x}")
            return x * 2

        args = [(1,), (-1,), (3,)]
        with pytest.raises(RuntimeError) as exc_info:
            _run_in_parallel(task_with_type_error, args, max_workers=1)
        # Error should be wrapped but information preserved
        assert "Task 1 failed" in str(exc_info.value)

    def test_sequential_multiple_errors_stops_at_first(self) -> None:
        """Test that sequential execution stops at first error."""
        call_count = 0

        def counting_failing_task(x: int) -> int:
            nonlocal call_count
            call_count += 1
            if x < 0:
                raise ValueError(f"Cannot process negative: {x}")
            return x * 2

        args = [(1,), (-2,), (3,)]
        with pytest.raises(RuntimeError):
            _run_in_parallel(counting_failing_task, args, max_workers=1)
        # Should have called function twice (1, then -2)
        assert call_count == 2

    def test_parallel_error_with_preserve_order_false(self) -> None:
        """Test error handling with preserve_order=False."""
        args = [(1,), (-5,), (3,), (4,)]
        with pytest.raises(RuntimeError, match="Task.*failed"):
            _run_in_parallel(failing_task, args, max_workers=2, preserve_order=False)

    def test_logging_with_error_sequential(self, caplog: Any) -> None:
        """Test logging when error occurs in sequential mode."""
        args = [(1,), (-1,), (3,)]
        with caplog.at_level(logging.DEBUG, logger="src.portfolio_management.utils"):
            with pytest.raises(RuntimeError):
                _run_in_parallel(failing_task, args, max_workers=1, log_tasks=True)
        # Should log error
        assert "failed" in caplog.text.lower() or "error" in caplog.text.lower()

    def test_logging_with_error_parallel(self, caplog: Any) -> None:
        """Test logging when error occurs in parallel mode."""
        args = [(1,), (-1,), (3,)]
        with caplog.at_level(logging.DEBUG, logger="src.portfolio_management.utils"):
            with pytest.raises(RuntimeError):
                _run_in_parallel(failing_task, args, max_workers=2, log_tasks=True)
        # Should have logged error
        assert "failed" in caplog.text.lower() or "error" in caplog.text.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
