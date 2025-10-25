"""Tests for ``scripts.prepare_tradeable_data`` built on curated fixtures.

The fixture bundle under ``tests/fixtures`` contains 500 tradeable instruments,
matching Stooq price files, and the golden match report generated from the
current script implementation.  The tests below exercise the critical data
preparation pipeline steps to lock in behaviour ahead of the forthcoming
refactor of ``prepare_tradeable_data.py``.
"""

from __future__ import annotations

import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest
pytestmark = pytest.mark.integration

pd = pytest.importorskip("pandas")
ptd = pytest.importorskip("scripts.prepare_tradeable_data")


FIXTURES_ROOT = Path(__file__).resolve().parent.parent / "fixtures"
STOOQ_FIXTURES = FIXTURES_ROOT / "stooq"
TRADEABLE_FIXTURES = FIXTURES_ROOT / "tradeable_instruments"
METADATA_FIXTURES = FIXTURES_ROOT / "metadata"


@pytest.fixture(scope="session")
def stooq_index() -> list[ptd.StooqFile]:
    """Index the curated Stooq fixtures once per test module."""
    return ptd.build_stooq_index(STOOQ_FIXTURES, max_workers=8)


@pytest.fixture(scope="session")
def stooq_lookup(
    stooq_index: list[ptd.StooqFile],
) -> tuple[
    dict[str, ptd.StooqFile],
    dict[str, ptd.StooqFile],
    dict[str, list[ptd.StooqFile]],
]:
    return ptd.build_stooq_lookup(stooq_index)


@pytest.fixture(scope="session")
def tradeable_instruments() -> list[ptd.TradeableInstrument]:
    return ptd.load_tradeable_instruments(TRADEABLE_FIXTURES)


@pytest.fixture(scope="session")
def expected_match_report() -> pd.DataFrame:
    return pd.read_csv(METADATA_FIXTURES / "selected_matches.csv")


def _make_stooq_file(
    ticker: str,
    rel_path: str,
    *,
    region: str = "world",
    category: str = "etfs",
) -> ptd.StooqFile:
    stem = ticker.split(".", 1)[0].upper()
    return ptd.StooqFile(
        ticker=ticker.upper(),
        stem=stem,
        rel_path=rel_path,
        region=region,
        category=category,
    )


def _make_instrument(
    symbol: str,
    *,
    market: str,
    currency: str = "",
    isin: str = "TESTISIN",
    name: str | None = None,
    source_file: str = "fixture.csv",
) -> ptd.TradeableInstrument:
    return ptd.TradeableInstrument(
        symbol=symbol,
        isin=isin,
        market=market,
        name=name or symbol,
        currency=currency,
        source_file=source_file,
    )


@pytest.fixture(scope="session")
def session_tmp_path(tmp_path_factory):
    """Create a session-scoped temporary directory."""
    return tmp_path_factory.mktemp("session_data")


@pytest.fixture(scope="session")
def pipeline_result(
    session_tmp_path,
    stooq_lookup,
    stooq_index: list[ptd.StooqFile],
    tradeable_instruments: list[ptd.TradeableInstrument],
) -> dict[str, object]:
    report_dir = session_tmp_path / "match_report"
    report_dir.mkdir()
    report_path = report_dir / "tradeable_matches.csv"

    matches, unmatched = ptd.match_tradeables(
        tradeable_instruments,
        *stooq_lookup,
        max_workers=8,
    )
    assert not unmatched, "Fixture subset should have complete matches"

    export_dir = session_tmp_path / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)

    (
        diagnostics,
        currency_counts,
        data_status_counts,
        empty_tickers,
        flagged_records,
        exported_count,
        skipped_count,
    ) = ptd.write_match_report(
        matches,
        report_path,
        STOOQ_FIXTURES,
        lse_currency_policy="broker",
        export_config=ptd.ExportConfig(
            data_dir=STOOQ_FIXTURES,
            dest_dir=export_dir,
            overwrite=True,
            include_empty=True,
            max_workers=8,
        ),
    )
    report_df = pd.read_csv(report_path)

    return {
        "matches": matches,
        "diagnostics": diagnostics,
        "currency_counts": currency_counts,
        "data_status_counts": data_status_counts,
        "empty_tickers": empty_tickers,
        "flagged_records": flagged_records,
        "report_df": report_df,
        "report_path": report_path,
        "exported_count": exported_count,
        "skipped_count": skipped_count,
        "export_dir": export_dir,
    }

    matches, unmatched = ptd.match_tradeables(
        tradeable_instruments,
        *stooq_lookup,
        max_workers=8,
    )
    assert not unmatched, "Fixture subset should have complete matches"

    (
        diagnostics,
        currency_counts,
        data_status_counts,
        empty_tickers,
        flagged_records,
    ) = ptd.write_match_report(
        matches,
        report_path,
        STOOQ_FIXTURES,
        lse_currency_policy="broker",
    )
    report_df = pd.read_csv(report_path)

    return {
        "matches": matches,
        "diagnostics": diagnostics,
        "currency_counts": currency_counts,
        "data_status_counts": data_status_counts,
        "empty_tickers": empty_tickers,
        "flagged_records": flagged_records,
        "report_df": report_df,
        "report_path": report_path,
    }


def test_build_stooq_index_expected_entries(
    stooq_index: list[ptd.StooqFile],
    expected_match_report: pd.DataFrame,
) -> None:
    expected_paths = set(expected_match_report["stooq_path"].unique())
    indexed_paths = {entry.rel_path for entry in stooq_index}

    assert len(stooq_index) == 500
    assert indexed_paths == expected_paths


def test_match_report_matches_fixture(
    pipeline_result: dict[str, object],
    expected_match_report: pd.DataFrame,
) -> None:
    actual = pipeline_result["report_df"].copy()
    expected = expected_match_report[actual.columns].copy()

    actual_sorted = actual.sort_values("matched_ticker").reset_index(drop=True)
    expected_sorted = expected.sort_values("matched_ticker").reset_index(drop=True)

    pd.testing.assert_frame_equal(actual_sorted, expected_sorted, check_dtype=True)
    assert pipeline_result["exported_count"] == len(expected_match_report)
    assert pipeline_result["skipped_count"] == 0


def test_match_report_summaries(
    pipeline_result: dict[str, object],
    expected_match_report: pd.DataFrame,
) -> None:
    currency_counts: Counter = pipeline_result["currency_counts"]
    data_status_counts: Counter = pipeline_result["data_status_counts"]

    expected_currency = Counter(expected_match_report["currency_status"])
    expected_data_status = Counter(expected_match_report["data_status"])

    assert currency_counts == expected_currency
    assert data_status_counts == expected_data_status


@pytest.mark.parametrize(
    "ticker,expected_status,flag_substring",
    [
        ("WPS.UK", "empty", ""),
        ("AGED.UK", "warning", "zero_volume_severity=moderate"),
        ("IEMB.UK", "ok", ""),
    ],
)
def test_summarize_price_file_cases(
    ticker: str,
    expected_status: str,
    flag_substring: str,
    stooq_index: list[ptd.StooqFile],
) -> None:
    lookup = {entry.ticker.upper(): entry for entry in stooq_index}
    stooq_file = lookup[ticker.upper()]

    diagnostics = ptd.summarize_price_file(STOOQ_FIXTURES, stooq_file)

    assert diagnostics["data_status"] == expected_status
    if flag_substring:
        assert flag_substring in diagnostics["data_flags"]
    else:
        assert diagnostics["data_flags"] in {"", None}


def _select_matches(
    matches: list[ptd.TradeableMatch],
    tickers: list[str],
) -> list[ptd.TradeableMatch]:
    lookup = {match.stooq_file.ticker.upper(): match for match in matches}
    return [lookup[ticker.upper()] for ticker in tickers]


def test_export_tradeable_prices_skip_empty(
    tmp_path: Path,
    pipeline_result: dict[str, object],
) -> None:
    matches: list[ptd.TradeableMatch] = pipeline_result["matches"]
    diagnostics: dict[str, dict[str, str]] = pipeline_result["diagnostics"]
    subset = _select_matches(matches, ["WPS.UK", "HSON.US", "IEMB.UK"])

    config = ptd.ExportConfig(
        data_dir=STOOQ_FIXTURES,
        dest_dir=tmp_path,
        overwrite=True,
        diagnostics=diagnostics,
        include_empty=False,
    )
    exported, skipped = ptd.export_tradeable_prices(subset, config)

    exported_files = sorted(p.name for p in tmp_path.glob("*.csv"))

    assert skipped == 2
    assert exported == 1
    assert exported_files == ["iemb.uk.csv"]


def test_export_tradeable_prices_include_empty(
    tmp_path: Path,
    pipeline_result: dict[str, object],
) -> None:
    matches: list[ptd.TradeableMatch] = pipeline_result["matches"]
    subset = _select_matches(matches, ["WPS.UK", "HSON.US", "IEMB.UK"])

    config = ptd.ExportConfig(
        data_dir=STOOQ_FIXTURES,
        dest_dir=tmp_path,
        overwrite=True,
        include_empty=True,
    )
    exported, skipped = ptd.export_tradeable_prices(subset, config)

    exported_files = sorted(p.name for p in tmp_path.glob("*.csv"))

    assert skipped == 0
    assert exported == 3
    assert exported_files == ["hson.us.csv", "iemb.uk.csv", "wps.uk.csv"]


def test_cli_end_to_end_matches_golden(tmp_path: Path) -> None:
    """Run the CLI over fixture bundles and compare outputs to golden files."""
    metadata_dir = tmp_path / "metadata"
    prices_dir = tmp_path / "prices"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    prices_dir.mkdir(parents=True, exist_ok=True)
    index_path = metadata_dir / "stooq_index.csv"
    match_path = metadata_dir / "tradeable_matches.csv"
    unmatched_path = metadata_dir / "tradeable_unmatched.csv"

    cmd = [
        sys.executable,
        "-m",
        "scripts.prepare_tradeable_data",
        "--data-dir",
        str(STOOQ_FIXTURES),
        "--metadata-output",
        str(index_path),
        "--tradeable-dir",
        str(TRADEABLE_FIXTURES),
        "--match-report",
        str(match_path),
        "--unmatched-report",
        str(unmatched_path),
        "--prices-output",
        str(prices_dir),
        "--max-workers",
        "4",
        "--index-workers",
        "2",
        "--overwrite-prices",
        "--log-level",
        "WARNING",
    ]

    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    assert result.returncode == 0

    expected_df = pd.read_csv(METADATA_FIXTURES / "selected_matches.csv")
    actual_df = pd.read_csv(match_path)
    expected_subset = expected_df[actual_df.columns].copy()

    pd.testing.assert_frame_equal(
        actual_df.sort_values("matched_ticker").reset_index(drop=True),
        expected_subset.sort_values("matched_ticker").reset_index(drop=True),
        check_dtype=True,
    )

    index_df = pd.read_csv(index_path)
    assert len(index_df) == 500

    unmatched_df = pd.read_csv(unmatched_path)
    assert unmatched_df.empty

    expected_exports = {
        f"{ticker.lower()}.csv"
        for ticker, status in expected_df[["matched_ticker", "data_status"]].itertuples(
            index=False,
        )
        if status not in {"empty", "missing", "missing_file"}
        and not str(status).startswith("error:")
    }
    actual_exports = {path.name for path in prices_dir.glob("*.csv")}
    assert actual_exports == expected_exports


def test_determine_unmatched_reason_variants() -> None:
    available_exts = {".US", ".UK"}
    stooq_us = _make_stooq_file(
        "ABC.US",
        "daily/world/stocks/abc.us.txt",
        region="world",
        category="stocks",
    )
    stooq_dupe_us = _make_stooq_file(
        "XYZ.US",
        "daily/world/stocks/xyz.us.txt",
        region="world",
        category="stocks",
    )
    stooq_dupe_uk = _make_stooq_file(
        "XYZ.UK",
        "daily/uk/stocks/xyz.uk.txt",
        region="uk",
        category="stocks",
    )
    stooq_single = _make_stooq_file(
        "LMN.US",
        "daily/world/stocks/lmn.us.txt",
        region="world",
        category="stocks",
    )

    # Desired extension missing from available set.
    reason_missing_ext = ptd.determine_unmatched_reason(
        _make_instrument("ABC:TO", market="TSX"),
        {"ABC": [stooq_us]},
        available_exts,
    )
    assert reason_missing_ext == "no_source_data(.TO)"

    # Base ticker exists but extension mismatch requires alias.
    reason_alias = ptd.determine_unmatched_reason(
        _make_instrument("ABC:TO", market="TSX"),
        {"ABC": [stooq_us]},
        available_exts | {".TO"},
    )
    assert reason_alias == "alias_required"

    # Multiple variants present in Stooq index.
    reason_ambiguous = ptd.determine_unmatched_reason(
        _make_instrument("XYZ", market="NYSE"),
        {"XYZ": [stooq_dupe_us, stooq_dupe_uk]},
        available_exts,
    )
    assert reason_ambiguous == "ambiguous_variants"

    # Single variant falls back to manual review.
    reason_manual = ptd.determine_unmatched_reason(
        _make_instrument("LMN", market="NYSE"),
        {"LMN": [stooq_single]},
        available_exts,
    )
    assert reason_manual == "manual_review"


@pytest.mark.parametrize(
    "policy,expected_resolved,expected_status",
    [
        ("broker", "USD", "override"),
        ("stooq", "GBP", "mismatch"),
        ("strict", "", "error:lse_currency_override"),
    ],
)
def test_resolve_currency_lse_policies(
    policy: str,
    expected_resolved: str,
    expected_status: str,
) -> None:
    instrument = _make_instrument(
        "IEMB:LN",
        market="LSE",
        currency="USD",
        name="iShares JP Morgan EM Bond",
    )
    stooq_file = _make_stooq_file(
        "IEMB.UK",
        "daily/uk/etfs/iemb.uk.txt",
        region="uk",
        category="etfs",
    )

    _, _, resolved, status = ptd.resolve_currency(
        instrument,
        stooq_file,
        inferred_currency="GBP",
        lse_policy=policy,
    )

    assert resolved == expected_resolved
    assert status == expected_status


def test_resolve_currency_non_lse_mismatch() -> None:
    instrument = _make_instrument(
        "SPY:US",
        market="NYSE",
        currency="EUR",
        name="SPDR S&P 500 ETF",
    )
    stooq_file = _make_stooq_file(
        "SPY.US",
        "daily/us/etfs/spy.us.txt",
        region="us",
        category="etfs",
    )

    expected, inferred, resolved, status = ptd.resolve_currency(
        instrument,
        stooq_file,
        inferred_currency="USD",
        lse_policy="broker",
    )

    assert expected == "EUR"
    assert inferred == "USD"
    assert resolved == "USD"
    assert status == "mismatch"


def test_export_tradeable_prices_deduplicates_and_overwrites(tmp_path: Path) -> None:
    data_dir = tmp_path / "stooq"
    rel_path = Path("daily/world/etfs/sample.us.txt")
    source_path = data_dir / rel_path
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(
        "\n".join(
            [
                "SAMPLE.US,0,20200102,000000,10,11,9,10,100,0",
                "SAMPLE.US,0,20200103,000000,11,12,10,11,150,0",
            ],
        ),
    )

    stooq_file = _make_stooq_file(
        "SAMPLE.US",
        rel_path.as_posix(),
        region="world",
        category="etfs",
    )
    instrument_a = _make_instrument("SAMPLE:US", market="NYSE", currency="USD")
    instrument_b = _make_instrument(
        "SAMPLE",
        market="NYSE",
        currency="USD",
        name="Sample Dup",
    )
    matches = [
        ptd.TradeableMatch(
            instrument=instrument_a,
            stooq_file=stooq_file,
            matched_ticker=stooq_file.ticker,
            strategy="ticker",
        ),
        ptd.TradeableMatch(
            instrument=instrument_b,
            stooq_file=stooq_file,
            matched_ticker=stooq_file.ticker,
            strategy="stem",
        ),
    ]

    diagnostics = {
        stooq_file.ticker.upper(): ptd.summarize_price_file(data_dir, stooq_file),
    }

    export_dir = tmp_path / "exports"
    config = ptd.ExportConfig(
        data_dir=data_dir,
        dest_dir=export_dir,
        overwrite=False,
        max_workers=4,
        diagnostics=diagnostics,
    )
    exported, skipped = ptd.export_tradeable_prices(matches, config)
    assert exported == 1
    assert skipped == 0

    target_path = export_dir / "sample.us.csv"
    assert target_path.exists()

    # Preserve existing file when overwrite is disabled.
    target_path.write_text("sentinel")
    config_again = ptd.ExportConfig(
        data_dir=data_dir,
        dest_dir=export_dir,
        overwrite=False,
        diagnostics=diagnostics,
    )
    exported_again, skipped_again = ptd.export_tradeable_prices(matches, config_again)
    assert exported_again == 0
    assert skipped_again == 0
    assert target_path.read_text() == "sentinel"

    # Allow replacement when overwrite=True.
    config_final = ptd.ExportConfig(
        data_dir=data_dir,
        dest_dir=export_dir,
        overwrite=True,
        diagnostics=diagnostics,
    )
    exported_final, skipped_final = ptd.export_tradeable_prices(matches, config_final)
    assert exported_final == 1
    assert skipped_final == 0
    content = target_path.read_text()
    assert "SAMPLE.US" in content
    assert "20200102" in content


def test_match_tradeables_parallel_consistency(
    stooq_lookup,
    tradeable_instruments: list[ptd.TradeableInstrument],
) -> None:
    matches_single, unmatched_single = ptd.match_tradeables(
        tradeable_instruments,
        *stooq_lookup,
        max_workers=1,
    )
    matches_parallel, unmatched_parallel = ptd.match_tradeables(
        tradeable_instruments,
        *stooq_lookup,
        max_workers=8,
    )

    def _signature(match: ptd.TradeableMatch) -> tuple[str, str, str]:
        return (
            match.instrument.symbol,
            match.matched_ticker,
            match.strategy,
        )

    assert sorted(_signature(match) for match in matches_single) == sorted(
        _signature(match) for match in matches_parallel
    )
    assert sorted(inst.symbol for inst in unmatched_single) == sorted(
        inst.symbol for inst in unmatched_parallel
    )


def test_write_unmatched_report_schema(tmp_path: Path) -> None:
    unmatched = [
        _make_instrument(
            "AAA:US",
            market="NYSE",
            currency="USD",
            name="Alpha",
            source_file="alpha.csv",
        ),
        _make_instrument(
            "BBB:LN",
            market="LSE",
            currency="GBP",
            name="Bravo",
            source_file="bravo.csv",
        ),
    ]
    unmatched[0].reason = "alias_required"
    unmatched[1].reason = "manual_review"

    output_path = tmp_path / "unmatched.csv"
    ptd.write_unmatched_report(unmatched, output_path)

    df = pd.read_csv(output_path)
    assert list(df.columns) == [
        "symbol",
        "isin",
        "market",
        "name",
        "currency",
        "source_file",
        "reason",
    ]
    assert df["reason"].tolist() == ["alias_required", "manual_review"]
