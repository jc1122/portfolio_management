"""Skeleton module for future data preparation service extraction."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class DataPreparationBackend(Protocol):
    """Protocol describing the dependencies required by the preparation service."""

    def prepare(self, config: dict[str, object]) -> dict[str, object]:
        """Execute the preparation workflow and return diagnostic information."""


@dataclass(slots=True)
class DataPreparationArtifacts:
    """Placeholder return object for the eventual data preparation service."""

    match_report: Path | None = None
    unmatched_report: Path | None = None
    diagnostics: dict[str, object] | None = None


class DataPreparationService:
    """Placeholder implementation documenting the forthcoming service API."""

    def __init__(self, backend: DataPreparationBackend | None = None) -> None:
        self._backend = backend

    def run(self, config: dict[str, object]) -> DataPreparationArtifacts:  # pragma: no cover - stub
        """Execute the workflow using the configured backend."""

        if self._backend is None:
            msg = (
                "DataPreparationService backend not provided. "
                "Full implementation will be introduced in a future change."
            )
            raise NotImplementedError(msg)
        result = self._backend.prepare(config)
        return DataPreparationArtifacts(
            match_report=result.get("match_report"),
            unmatched_report=result.get("unmatched_report"),
            diagnostics=result.get("diagnostics"),
        )
