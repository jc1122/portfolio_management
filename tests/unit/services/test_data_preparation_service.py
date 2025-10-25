from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from portfolio_management.data.models import StooqFile, TradeableInstrument, TradeableMatch
from portfolio_management.services import (
    DataPreparationConfig,
    DataPreparationService,
)
from portfolio_management.services import data_preparation as module


def test_service_skips_when_incremental(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def _fail(*_: Any, **__: Any) -> None:  # pragma: no cover - defensive
        pytest.fail("Expensive operations should not run when skipping")

    monkeypatch.setattr(module.cache, "load_cache_metadata", lambda path: {"cached": True})
    monkeypatch.setattr(module.cache, "inputs_unchanged", lambda *args, **kwargs: True)
    monkeypatch.setattr(module.cache, "outputs_exist", lambda *args, **kwargs: True)
    monkeypatch.setattr(module, "build_stooq_index", _fail)
    monkeypatch.setattr(module, "read_stooq_index", _fail)

    config = DataPreparationConfig(
        data_dir=tmp_path / "data",
        metadata_output=tmp_path / "meta.csv",
        tradeable_dir=tmp_path / "tradeable",
        match_report=tmp_path / "match.csv",
        unmatched_report=tmp_path / "unmatched.csv",
        prices_output=tmp_path / "prices",
        incremental=True,
        cache_metadata=tmp_path / "cache.json",
    )

    result = DataPreparationService().run(config)

    assert result.skipped is True
    assert result.matches == ()
    assert result.unmatched == ()
    assert result.cache_metadata_path == tmp_path / "cache.json"


def test_service_runs_pipeline(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    instrument = TradeableInstrument(
        symbol="AAA",
        isin="ISINAAA",
        market="NYSE",
        name="Example",
        currency="USD",
        source_file="tradeable.csv",
    )
    stooq_file = StooqFile(
        ticker="AAA.US",
        stem="AAA",
        rel_path="us/nasdaq/aaa.csv",
    )
    match = TradeableMatch(
        instrument=instrument,
        stooq_file=stooq_file,
        matched_ticker="AAA.US",
        strategy="ticker",
    )

    monkeypatch.setattr(module, "build_stooq_index", lambda data_dir, max_workers: pd.DataFrame())
    monkeypatch.setattr(module, "load_tradeable_instruments", lambda path: [instrument])
    monkeypatch.setattr(module, "build_stooq_lookup", lambda index: ({}, {}, {}))
    monkeypatch.setattr(module, "collect_available_extensions", lambda index: {"US"})
    monkeypatch.setattr(module, "match_tradeables", lambda *args, **kwargs: ([match], []))
    monkeypatch.setattr(module, "annotate_unmatched_instruments", lambda unmatched, *_: unmatched)
    monkeypatch.setattr(module, "log_summary_counts", lambda *args, **kwargs: None)

    diagnostics_cache: dict[str, dict[str, str]] = {"AAA": {"price_rows": "10"}}

    def fake_write_match_report(*args, **kwargs):
        return (
            diagnostics_cache,
            {"USD": 1},
            {"ok": 1},
            ["EMPTY"],
            [("AAA", "AAA.US", "flag")],
            2,
            1,
        )

    captured_unmatched: dict[str, Path] = {}

    def fake_write_unmatched(unmatched, output_path):
        captured_unmatched["path"] = output_path

    monkeypatch.setattr(module, "write_match_report", fake_write_match_report)
    monkeypatch.setattr(module, "write_unmatched_report", fake_write_unmatched)

    config = DataPreparationConfig(
        data_dir=tmp_path / "data",
        metadata_output=tmp_path / "meta" / "index.csv",
        tradeable_dir=tmp_path / "tradeable",
        match_report=tmp_path / "output" / "match.csv",
        unmatched_report=tmp_path / "output" / "unmatched.csv",
        prices_output=tmp_path / "prices",
        overwrite_prices=True,
        include_empty_prices=True,
        lse_currency_policy="broker",
        max_workers=2,
        index_workers=1,
    )

    result = DataPreparationService().run(config)

    assert result.skipped is False
    assert result.matches[0].matched_ticker == "AAA.US"
    assert result.diagnostics.exported_count == 2
    assert result.diagnostics.skipped_count == 1
    assert result.diagnostics.diagnostics_cache == diagnostics_cache
    assert captured_unmatched["path"] == config.unmatched_report
