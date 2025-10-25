from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from portfolio_management.services import DataPreparationConfig, DataPreparationService


@dataclass
class StubCache:
    inputs_called: bool = False
    outputs_called: bool = False
    saved: bool = False

    def load_cache_metadata(self, path: Path) -> dict[str, Any]:
        return {"meta": 1}

    def inputs_unchanged(self, tradeable_dir: Path, metadata_output: Path, metadata: dict[str, Any]) -> bool:
        self.inputs_called = True
        return True

    def outputs_exist(self, match_report: Path, unmatched_report: Path) -> bool:
        self.outputs_called = True
        return True

    def create_cache_metadata(self, tradeable_dir: Path, metadata_output: Path) -> dict[str, Any]:
        return {"new": 2}

    def save_cache_metadata(self, cache_path: Path, metadata: dict[str, Any]) -> None:
        self.saved = True


def test_prepare_skips_when_cache_valid(tmp_path: Path) -> None:
    cache = StubCache()

    config = DataPreparationConfig(
        data_dir=tmp_path,
        metadata_output=tmp_path / "index.csv",
        tradeable_dir=tmp_path,
        match_report=tmp_path / "match.csv",
        unmatched_report=tmp_path / "unmatched.csv",
        prices_output=tmp_path / "prices",
        incremental=True,
        cache_metadata=tmp_path / "cache.json",
    )

    service = DataPreparationService(
        stooq_index_builder=lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("builder should not run")),
        tradeable_loader=lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("loader should not run")),
        cache_module=cache,
    )

    result = service.prepare(config)

    assert result.skipped is True
    assert cache.inputs_called
    assert cache.outputs_called


def test_prepare_runs_pipeline_and_updates_cache(tmp_path: Path) -> None:
    diagnostics_return = {"diag": 1}
    saved_metadata: dict[str, Any] | None = None

    class CacheModule:
        def load_cache_metadata(self, path: Path) -> dict[str, Any]:
            return {}

        def inputs_unchanged(self, *args: Any, **kwargs: Any) -> bool:
            return False

        def outputs_exist(self, *args: Any, **kwargs: Any) -> bool:
            return False

        def create_cache_metadata(self, tradeable_dir: Path, metadata_output: Path) -> dict[str, Any]:
            return {"tradeable": str(tradeable_dir), "index": str(metadata_output)}

        def save_cache_metadata(self, cache_path: Path, metadata: dict[str, Any]) -> None:
            nonlocal saved_metadata
            saved_metadata = metadata

    stooq_written: list[Path] = []
    unmatched_written: list[Path] = []

    def stooq_builder(data_dir: Path, workers: int) -> pd.DataFrame:
        return pd.DataFrame({"ticker": ["AAA"]})

    def stooq_writer(index: pd.DataFrame, path: Path) -> None:
        stooq_written.append(path)

    def tradeable_loader(path: Path):
        return ["AAA"]

    def lookup_builder(_index: Any):
        return ({"AAA": "AAA.txt"}, {}, {})

    def extension_collector(_index: Any):
        return {".txt"}

    def matcher(*_args, **_kwargs):
        return (["match"], ["unmatched"])

    def annotator(unmatched, *_args, **_kwargs):
        return [f"annotated-{item}" for item in unmatched]

    def match_writer(*_args, **_kwargs):
        return diagnostics_return, {"USD": 1}, {"ok": 1}, [], [], 2, 0

    def unmatched_writer(data, path: Path) -> None:
        unmatched_written.append(path)

    config = DataPreparationConfig(
        data_dir=tmp_path,
        metadata_output=tmp_path / "index.csv",
        tradeable_dir=tmp_path,
        match_report=tmp_path / "match.csv",
        unmatched_report=tmp_path / "unmatched.csv",
        prices_output=tmp_path / "prices",
        incremental=True,
        cache_metadata=tmp_path / "cache.json",
    )

    service = DataPreparationService(
        stooq_index_builder=stooq_builder,
        stooq_index_writer=stooq_writer,
        tradeable_loader=tradeable_loader,
        lookup_builder=lookup_builder,
        extension_collector=extension_collector,
        matcher=matcher,
        unmatched_annotator=annotator,
        match_report_writer=match_writer,
        unmatched_writer=unmatched_writer,
        cache_module=CacheModule(),
    )

    result = service.prepare(config)

    assert result.skipped is False
    assert result.diagnostics["exported_count"] == 2
    assert stooq_written == [config.metadata_output]
    assert unmatched_written == [config.unmatched_report]
    assert saved_metadata == {
        "tradeable": str(config.tradeable_dir),
        "index": str(config.metadata_output),
    }
