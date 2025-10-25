"""Unit tests for :mod:`portfolio_management.services.data_preparation`."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from portfolio_management.data.models import StooqFile, TradeableInstrument, TradeableMatch
from portfolio_management.services import DataPreparationService


@pytest.fixture()
def sample_match() -> TradeableMatch:
    instrument = TradeableInstrument(
        symbol="AAPL",
        isin="US0378331005",
        market="NASDAQ",
        name="Apple Inc",
        currency="USD",
        source_file="tradeable.csv",
    )
    stooq_file = StooqFile(
        ticker="AAPL.US",
        stem="AAPL",
        rel_path="us/nasdaq/aapl.txt",
        region="us",
        category="stocks",
    )
    return TradeableMatch(
        instrument=instrument,
        stooq_file=stooq_file,
        matched_ticker="AAPL.US",
        strategy="ticker",
    )


def _cache_namespace() -> SimpleNamespace:
    return SimpleNamespace(
        load_cache_metadata=lambda _: {},
        save_cache_metadata=lambda *_, **__: None,
        inputs_unchanged=lambda *_, **__: False,
        create_cache_metadata=lambda *_, **__: {},
    )


def test_prepare_tradeable_data_builds_index(tmp_path: Path, sample_match: TradeableMatch) -> None:
    build_index = MagicMock(return_value=[sample_match.stooq_file])
    read_index = MagicMock()
    write_index = MagicMock()
    load_tradeables = MagicMock(return_value=[sample_match.instrument])
    build_lookup = MagicMock(
        return_value=(
            {sample_match.stooq_file.ticker: sample_match.stooq_file},
            {sample_match.stooq_file.stem: sample_match.stooq_file},
            {sample_match.stooq_file.stem: [sample_match.stooq_file]},
        )
    )
    collect_extensions = MagicMock(return_value={})
    matcher = MagicMock(return_value=([sample_match], []))
    unmatched_annotator = MagicMock(return_value=[])
    report_writer = MagicMock(
        return_value=(
            {sample_match.stooq_file.ticker: {"rows": "100"}},
            Counter({"USD": 1}),
            Counter({"ok": 1}),
            [],
            [],
            1,
            0,
        )
    )
    unmatched_writer = MagicMock()

    service = DataPreparationService(
        build_index=build_index,
        read_index=read_index,
        write_index=write_index,
        load_tradeables=load_tradeables,
        build_lookup=build_lookup,
        collect_extensions=collect_extensions,
        matcher=matcher,
        unmatched_annotator=unmatched_annotator,
        report_writer=report_writer,
        unmatched_writer=unmatched_writer,
        cache_module=_cache_namespace(),
    )

    result = service.prepare_tradeable_data(
        data_dir=tmp_path,
        tradeable_dir=tmp_path,
        metadata_output=tmp_path / "stooq_index.csv",
        match_report_path=tmp_path / "matches.csv",
        unmatched_report_path=tmp_path / "unmatched.csv",
        prices_output_dir=tmp_path / "prices",
    )

    build_index.assert_called_once()
    write_index.assert_called_once()
    assert not result.skipped
    assert result.exported_count == 1
    assert list(result.matched_data["symbol"]) == [sample_match.instrument.symbol]


def test_prepare_tradeable_data_reads_existing_index(tmp_path: Path, sample_match: TradeableMatch) -> None:
    metadata_path = tmp_path / "stooq_index.csv"
    metadata_path.write_text("ticker,stem,relative_path,region,category\n")

    build_index = MagicMock()
    read_index = MagicMock(return_value=[sample_match.stooq_file])
    write_index = MagicMock()
    load_tradeables = MagicMock(return_value=[sample_match.instrument])
    build_lookup = MagicMock(
        return_value=(
            {sample_match.stooq_file.ticker: sample_match.stooq_file},
            {sample_match.stooq_file.stem: sample_match.stooq_file},
            {sample_match.stooq_file.stem: [sample_match.stooq_file]},
        )
    )
    collect_extensions = MagicMock(return_value={})
    matcher = MagicMock(return_value=([sample_match], []))
    unmatched_annotator = MagicMock(return_value=[])
    report_writer = MagicMock(
        return_value=(
            {},
            Counter(),
            Counter(),
            [],
            [],
            0,
            0,
        )
    )
    unmatched_writer = MagicMock()

    service = DataPreparationService(
        build_index=build_index,
        read_index=read_index,
        write_index=write_index,
        load_tradeables=load_tradeables,
        build_lookup=build_lookup,
        collect_extensions=collect_extensions,
        matcher=matcher,
        unmatched_annotator=unmatched_annotator,
        report_writer=report_writer,
        unmatched_writer=unmatched_writer,
        cache_module=_cache_namespace(),
    )

    service.prepare_tradeable_data(
        data_dir=tmp_path,
        tradeable_dir=tmp_path,
        metadata_output=metadata_path,
        match_report_path=tmp_path / "matches.csv",
        unmatched_report_path=tmp_path / "unmatched.csv",
        prices_output_dir=tmp_path / "prices",
    )

    read_index.assert_called_once()
    build_index.assert_not_called()


def test_prepare_tradeable_data_incremental_skip(tmp_path: Path) -> None:
    match_report = tmp_path / "matches.csv"
    match_report.write_text("symbol\nAAPL\n")
    unmatched_report = tmp_path / "unmatched.csv"
    unmatched_report.write_text("symbol\nMSFT\n")

    cache_module = SimpleNamespace(
        load_cache_metadata=MagicMock(return_value={"hash": "abc"}),
        save_cache_metadata=MagicMock(),
        inputs_unchanged=MagicMock(return_value=True),
        create_cache_metadata=MagicMock(),
    )

    service = DataPreparationService(
        build_index=MagicMock(side_effect=AssertionError("should not rebuild")),
        read_index=MagicMock(side_effect=AssertionError("should not read")),
        write_index=MagicMock(side_effect=AssertionError("should not write")),
        load_tradeables=MagicMock(side_effect=AssertionError("should not load")),
        build_lookup=MagicMock(side_effect=AssertionError("should not build lookup")),
        collect_extensions=MagicMock(side_effect=AssertionError("should not collect")),
        matcher=MagicMock(side_effect=AssertionError("should not match")),
        unmatched_annotator=MagicMock(side_effect=AssertionError("should not annotate")),
        report_writer=MagicMock(side_effect=AssertionError("should not write report")),
        unmatched_writer=MagicMock(side_effect=AssertionError("should not write unmatched")),
        cache_module=cache_module,
    )

    result = service.prepare_tradeable_data(
        data_dir=tmp_path,
        tradeable_dir=tmp_path,
        metadata_output=tmp_path / "stooq_index.csv",
        match_report_path=match_report,
        unmatched_report_path=unmatched_report,
        prices_output_dir=tmp_path / "prices",
        incremental=True,
    )

    assert result.skipped
    cache_module.save_cache_metadata.assert_not_called()
