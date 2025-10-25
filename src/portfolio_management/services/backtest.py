"""Placeholder for the backtest orchestration service."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class BacktestResult:
    """Placeholder result for the forthcoming backtest service."""

    equity_curve_path: str | None = None
    diagnostics: dict[str, object] | None = None


class BacktestService:
    """Backtest orchestration service stub."""

    def run(self, config: dict[str, object]) -> BacktestResult:  # pragma: no cover - stub
        raise NotImplementedError(
            "BacktestService is a stub and will be implemented in a follow-up iteration."
        )
