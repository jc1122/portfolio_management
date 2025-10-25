"""High-level service for the tradeable data preparation workflow."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Sequence

import pandas as pd

from portfolio_management.data import cache
from portfolio_management.data.analysis import collect_available_extensions
from portfolio_management.data.ingestion import build_stooq_index
from portfolio_management.data.io.io import (
    load_tradeable_instruments,
    read_stooq_index,
    write_match_report,
    write_stooq_index,
    write_unmatched_report,
)
from portfolio_management.data.matching import (
    annotate_unmatched_instruments,
    build_stooq_lookup,
    match_tradeables,
)
from portfolio_management.data.models import ExportConfig, StooqFile, TradeableInstrument, TradeableMatch


@dataclass(slots=True)
class DataPreparationResult:
    """Container for the outcome of :class:`DataPreparationService`."""

    matched_data: pd.DataFrame
    unmatched_symbols: list[str]
    match_report_path: Path
    unmatched_report_path: Path
    diagnostics: dict[str, dict[str, str]]
    currency_counts: Counter[str]
    data_status_counts: Counter[str]
    exported_count: int
    skipped_count: int
    empty_tickers: list[str] = field(default_factory=list)
    flagged_samples: list[tuple[str, str, str]] = field(default_factory=list)
    skipped: bool = False


class DataPreparationService:
    """Coordinate the tradeable data preparation pipeline."""

    def __init__(
        self,
        *,
        build_index: Callable[[Path, int | None], Sequence[StooqFile]] | None = None,
        read_index: Callable[[Path], Sequence[StooqFile]] | None = None,
        write_index: Callable[[Sequence[StooqFile], Path], None] | None = None,
        load_tradeables: Callable[[Path], Sequence[TradeableInstrument]] | None = None,
        build_lookup: Callable[[Sequence[StooqFile]], tuple[dict[str, StooqFile], dict[str, StooqFile], dict[str, list[StooqFile]]]]
        | None = None,
        collect_extensions: Callable[[Sequence[StooqFile]], Any] | None = None,
        matcher: Callable[[Sequence[TradeableInstrument], dict[str, StooqFile], dict[str, StooqFile], dict[str, list[StooqFile]], int | None], tuple[list[TradeableMatch], list[TradeableInstrument]]]
        | None = None,
        unmatched_annotator: Callable[[Sequence[TradeableInstrument], dict[str, list[StooqFile]], Any], Sequence[TradeableInstrument]]
        | None = None,
        report_writer: Callable[[Sequence[TradeableMatch], Path, Path, str, int | None, ExportConfig | None], tuple[
            dict[str, dict[str, str]],
            Counter[str],
            Counter[str],
            list[str],
            list[tuple[str, str, str]],
            int,
            int,
        ]]
        | None = None,
        unmatched_writer: Callable[[Sequence[TradeableInstrument], Path], None] | None = None,
        cache_module: Any = None,
        cached_result_loader: Callable[[Path, Path], tuple[pd.DataFrame, list[str]]] | None = None,
    ) -> None:
        self._build_index = build_index or build_stooq_index
        self._read_index = read_index or read_stooq_index
        self._write_index = write_index or write_stooq_index
        self._load_tradeables = load_tradeables or load_tradeable_instruments
        self._build_lookup = build_lookup or build_stooq_lookup
        self._collect_extensions = collect_extensions or collect_available_extensions
        self._matcher = matcher or match_tradeables
        self._annotate_unmatched = unmatched_annotator or annotate_unmatched_instruments
        self._report_writer = report_writer or write_match_report
        self._unmatched_writer = unmatched_writer or write_unmatched_report
        self._cache = cache_module or SimpleNamespace(
            load_cache_metadata=cache.load_cache_metadata,
            save_cache_metadata=cache.save_cache_metadata,
            inputs_unchanged=cache.inputs_unchanged,
            create_cache_metadata=cache.create_cache_metadata,
        )
        self._cached_result_loader = cached_result_loader or self._default_cached_loader

    def prepare_tradeable_data(
        self,
        *,
        data_dir: Path,
        tradeable_dir: Path,
        metadata_output: Path,
        match_report_path: Path,
        unmatched_report_path: Path,
        prices_output_dir: Path,
        overwrite_prices: bool = False,
        include_empty_prices: bool = False,
        lse_currency_policy: str = "broker",
        incremental: bool = False,
        cache_metadata_path: Path | None = None,
        force_reindex: bool = False,
        max_workers: int | None = None,
        index_workers: int | None = None,
    ) -> DataPreparationResult:
        """Run the tradeable data pipeline and return detailed results."""

        data_dir = Path(data_dir)
        tradeable_dir = Path(tradeable_dir)
        metadata_output = Path(metadata_output)
        match_report_path = Path(match_report_path)
        unmatched_report_path = Path(unmatched_report_path)
        prices_output_dir = Path(prices_output_dir)
        cache_metadata_path = (
            Path(cache_metadata_path)
            if cache_metadata_path is not None
            else metadata_output.with_name(".prepare_cache.json")
        )

        max_workers = self._normalise_workers(max_workers)
        index_workers = self._normalise_workers(index_workers or max_workers)

        if incremental:
            cached_result = self._maybe_skip_pipeline(
                tradeable_dir=tradeable_dir,
                metadata_output=metadata_output,
                cache_metadata_path=cache_metadata_path,
                match_report_path=match_report_path,
                unmatched_report_path=unmatched_report_path,
            )
            if cached_result is not None:
                return cached_result

        stooq_index = self._load_or_build_index(
            data_dir=data_dir,
            metadata_output=metadata_output,
            force_reindex=force_reindex,
            index_workers=index_workers,
        )

        tradeables = list(self._load_tradeables(tradeable_dir))
        lookup_by_ticker, lookup_by_stem, lookup_by_base = self._build_lookup(stooq_index)
        available_extensions = self._collect_extensions(stooq_index)
        matches, unmatched = self._matcher(
            tradeables,
            lookup_by_ticker,
            lookup_by_stem,
            lookup_by_base,
            max_workers,
        )
        annotated_unmatched = list(
            self._annotate_unmatched(unmatched, lookup_by_base, available_extensions)
        )

        export_config = ExportConfig(
            data_dir=data_dir,
            dest_dir=prices_output_dir,
            overwrite=overwrite_prices,
            include_empty=include_empty_prices,
            max_workers=max_workers,
        )
        export_config.dest_dir.mkdir(parents=True, exist_ok=True)

        (
            diagnostics,
            currency_counts,
            data_status_counts,
            empty_tickers,
            flagged_samples,
            exported_count,
            skipped_count,
        ) = self._report_writer(
            matches,
            match_report_path,
            data_dir,
            lse_currency_policy=lse_currency_policy,
            max_workers=max_workers,
            export_config=export_config,
        )
        self._unmatched_writer(annotated_unmatched, unmatched_report_path)

        matched_frame = self._build_matched_frame(matches)
        unmatched_symbols = [item.symbol for item in annotated_unmatched]

        if incremental:
            metadata = self._cache.create_cache_metadata(tradeable_dir, metadata_output)
            self._cache.save_cache_metadata(cache_metadata_path, metadata)

        return DataPreparationResult(
            matched_data=matched_frame,
            unmatched_symbols=unmatched_symbols,
            match_report_path=match_report_path,
            unmatched_report_path=unmatched_report_path,
            diagnostics=diagnostics,
            currency_counts=currency_counts,
            data_status_counts=data_status_counts,
            exported_count=exported_count,
            skipped_count=skipped_count,
            empty_tickers=empty_tickers,
            flagged_samples=flagged_samples,
        )

    def _load_or_build_index(
        self,
        *,
        data_dir: Path,
        metadata_output: Path,
        force_reindex: bool,
        index_workers: int,
    ) -> Sequence[StooqFile]:
        if metadata_output.exists() and not force_reindex:
            return self._read_index(metadata_output)

        index = self._build_index(data_dir, index_workers)
        self._write_index(index, metadata_output)
        return index

    def _normalise_workers(self, workers: int | None) -> int:
        if workers is None or workers <= 0:
            return 1
        return workers

    def _maybe_skip_pipeline(
        self,
        *,
        tradeable_dir: Path,
        metadata_output: Path,
        cache_metadata_path: Path,
        match_report_path: Path,
        unmatched_report_path: Path,
    ) -> DataPreparationResult | None:
        cached_metadata = self._cache.load_cache_metadata(cache_metadata_path)
        inputs_unchanged = self._cache.inputs_unchanged(
            tradeable_dir,
            metadata_output,
            cached_metadata,
        )
        outputs_exist = match_report_path.exists() and unmatched_report_path.exists()

        if inputs_unchanged and outputs_exist:
            matched_frame, unmatched_symbols = self._cached_result_loader(
                match_report_path,
                unmatched_report_path,
            )
            return DataPreparationResult(
                matched_data=matched_frame,
                unmatched_symbols=unmatched_symbols,
                match_report_path=match_report_path,
                unmatched_report_path=unmatched_report_path,
                diagnostics={},
                currency_counts=Counter(),
                data_status_counts=Counter(),
                exported_count=0,
                skipped_count=0,
                empty_tickers=[],
                flagged_samples=[],
                skipped=True,
            )
        return None

    def _build_matched_frame(self, matches: Sequence[TradeableMatch]) -> pd.DataFrame:
        if not matches:
            return pd.DataFrame(
                columns=[
                    "symbol",
                    "isin",
                    "market",
                    "name",
                    "currency",
                    "source_file",
                    "matched_ticker",
                    "stooq_ticker",
                    "stooq_region",
                    "stooq_category",
                    "stooq_path",
                    "strategy",
                ]
            )

        records: list[dict[str, Any]] = []
        for match in matches:
            instrument_data = asdict(match.instrument)
            stooq_data = asdict(match.stooq_file)
            records.append(
                {
                    **instrument_data,
                    "matched_ticker": match.matched_ticker,
                    "stooq_ticker": stooq_data.get("ticker", ""),
                    "stooq_region": stooq_data.get("region", ""),
                    "stooq_category": stooq_data.get("category", ""),
                    "stooq_path": stooq_data.get("rel_path", ""),
                    "strategy": match.strategy,
                }
            )
        return pd.DataFrame.from_records(records)

    def _default_cached_loader(
        self,
        match_report_path: Path,
        unmatched_report_path: Path,
    ) -> tuple[pd.DataFrame, list[str]]:
        matched_frame = (
            pd.read_csv(match_report_path)
            if match_report_path.exists()
            else pd.DataFrame()
        )
        unmatched_frame = (
            pd.read_csv(unmatched_report_path)
            if unmatched_report_path.exists()
            else pd.DataFrame()
        )
        unmatched_symbols = (
            unmatched_frame.get("symbol", pd.Series(dtype=str)).dropna().astype(str).tolist()
        )
        return matched_frame, unmatched_symbols
