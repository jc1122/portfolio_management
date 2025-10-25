"""High-level data preparation orchestration service."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence

from portfolio_management.data import cache
from portfolio_management.data.analysis import (
    collect_available_extensions,
    log_summary_counts,
)
from portfolio_management.data.ingestion import build_stooq_index
from portfolio_management.data.io import (
    load_tradeable_instruments,
    read_stooq_index,
    write_stooq_index,
    write_match_report,
    write_unmatched_report,
)
from portfolio_management.data.matching import (
    annotate_unmatched_instruments,
    build_stooq_lookup,
    match_tradeables,
)
from portfolio_management.data.models import (
    ExportConfig,
    TradeableInstrument,
    TradeableMatch,
)

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class DataPreparationConfig:
    """Configuration for the data preparation workflow."""

    data_dir: Path
    metadata_output: Path
    tradeable_dir: Path
    match_report: Path
    unmatched_report: Path
    prices_output: Path
    overwrite_prices: bool = False
    include_empty_prices: bool = False
    lse_currency_policy: str = "broker"
    max_workers: int | None = None
    index_workers: int | None = None
    incremental: bool = False
    cache_metadata: Path | None = None
    force_reindex: bool = False


@dataclass(frozen=True)
class DataPreparationDiagnostics:
    """Diagnostics produced by the data preparation workflow."""

    diagnostics_cache: Mapping[str, Mapping[str, str]] = field(default_factory=dict)
    currency_counts: Mapping[str, int] = field(default_factory=dict)
    data_status_counts: Mapping[str, int] = field(default_factory=dict)
    empty_tickers: Sequence[str] = field(default_factory=list)
    flagged_samples: Sequence[tuple[str, str, str]] = field(default_factory=list)
    exported_count: int = 0
    skipped_count: int = 0


@dataclass(frozen=True)
class DataPreparationResult:
    """Result of running the data preparation workflow."""

    matches: Sequence[TradeableMatch]
    unmatched: Sequence[TradeableInstrument]
    match_report_path: Path
    unmatched_report_path: Path
    export_directory: Path
    diagnostics: DataPreparationDiagnostics
    skipped: bool = False
    cache_metadata_path: Path | None = None


class DataPreparationService:
    """Service coordinating the tradeable data preparation workflow."""

    def __init__(self, *, logger: logging.Logger | None = None) -> None:
        self._logger = logger or LOGGER

    def run(self, config: DataPreparationConfig) -> DataPreparationResult:
        """Execute the full workflow and return a structured result."""

        max_workers = self._resolve_worker_count(config.max_workers)
        index_workers = self._resolve_worker_count(
            config.index_workers if config.index_workers is not None else max_workers,
        )

        cache_path = config.cache_metadata or config.match_report.parent / ".prepare_cache.json"
        skip_processing = False
        cache_metadata: dict[str, object] = {}

        if config.incremental:
            cache_metadata = cache.load_cache_metadata(cache_path)
            inputs_unchanged = cache.inputs_unchanged(
                config.tradeable_dir,
                config.metadata_output,
                cache_metadata,
            )
            outputs_exist = cache.outputs_exist(
                config.match_report,
                config.unmatched_report,
            )
            if inputs_unchanged and outputs_exist:
                self._logger.info(
                    "Incremental resume: inputs unchanged and outputs present - skipping run.",
                )
                skip_processing = True

        if skip_processing:
            return DataPreparationResult(
                matches=(),
                unmatched=(),
                match_report_path=config.match_report,
                unmatched_report_path=config.unmatched_report,
                export_directory=config.prices_output,
                diagnostics=DataPreparationDiagnostics(),
                skipped=True,
                cache_metadata_path=cache_path,
            )

        stooq_index = self._load_or_build_index(
            metadata_output=config.metadata_output,
            data_dir=config.data_dir,
            force_reindex=config.force_reindex,
            index_workers=index_workers,
        )

        matches, unmatched = self._match_tradeables(
            stooq_index=stooq_index,
            tradeable_dir=config.tradeable_dir,
            max_workers=max_workers,
        )

        diagnostics = self._generate_reports(
            matches=matches,
            unmatched=unmatched,
            config=config,
            max_workers=max_workers,
        )

        if config.incremental:
            new_cache_metadata = cache.create_cache_metadata(
                config.tradeable_dir,
                config.metadata_output,
            )
            cache.save_cache_metadata(cache_path, new_cache_metadata)

        return DataPreparationResult(
            matches=tuple(matches),
            unmatched=tuple(unmatched),
            match_report_path=config.match_report,
            unmatched_report_path=config.unmatched_report,
            export_directory=config.prices_output,
            diagnostics=diagnostics,
            skipped=False,
            cache_metadata_path=cache_path if config.incremental else None,
        )

    def _resolve_worker_count(self, configured: int | None) -> int:
        cpu_count = os.cpu_count() or 1
        auto_workers = max(1, (cpu_count - 1) or 1)
        if configured is None or configured <= 0:
            return auto_workers
        return max(1, configured)

    def _load_or_build_index(
        self,
        *,
        metadata_output: Path,
        data_dir: Path,
        force_reindex: bool,
        index_workers: int,
    ):
        if metadata_output.exists() and not force_reindex:
            self._logger.debug("Loading existing Stooq index from %s", metadata_output)
            return read_stooq_index(metadata_output)

        self._logger.info("Building Stooq index from %s", data_dir)
        index = build_stooq_index(data_dir, max_workers=index_workers)
        self._logger.debug("Writing Stooq index to %s", metadata_output)
        metadata_output.parent.mkdir(parents=True, exist_ok=True)
        write_stooq_index(index, metadata_output)
        return index

    def _match_tradeables(
        self,
        *,
        stooq_index,
        tradeable_dir: Path,
        max_workers: int,
    ) -> tuple[Sequence[TradeableMatch], Sequence[TradeableInstrument]]:
        tradeables = load_tradeable_instruments(tradeable_dir)
        stooq_by_ticker, stooq_by_stem, stooq_by_base = build_stooq_lookup(stooq_index)
        available_extensions = collect_available_extensions(stooq_index)
        matches, unmatched = match_tradeables(
            tradeables,
            stooq_by_ticker,
            stooq_by_stem,
            stooq_by_base,
            max_workers=max_workers,
        )
        annotated_unmatched = annotate_unmatched_instruments(
            list(unmatched),
            stooq_by_base,
            available_extensions,
        )
        return matches, annotated_unmatched

    def _generate_reports(
        self,
        *,
        matches: Sequence[TradeableMatch],
        unmatched: Sequence[TradeableInstrument],
        config: DataPreparationConfig,
        max_workers: int,
    ) -> DataPreparationDiagnostics:
        export_config = ExportConfig(
            data_dir=config.data_dir,
            dest_dir=config.prices_output,
            overwrite=config.overwrite_prices,
            max_workers=max_workers,
            include_empty=config.include_empty_prices,
        )
        export_config.dest_dir.mkdir(parents=True, exist_ok=True)
        (
            diagnostics_cache,
            currency_counts,
            data_status_counts,
            empty_tickers,
            flagged_samples,
            exported_count,
            skipped_count,
        ) = write_match_report(
            matches,
            config.match_report,
            config.data_dir,
            lse_currency_policy=config.lse_currency_policy,
            max_workers=max_workers,
            export_config=export_config,
        )
        log_summary_counts(currency_counts, data_status_counts)
        write_unmatched_report(unmatched, config.unmatched_report)

        return DataPreparationDiagnostics(
            diagnostics_cache=diagnostics_cache,
            currency_counts=dict(currency_counts),
            data_status_counts=dict(data_status_counts),
            empty_tickers=tuple(empty_tickers),
            flagged_samples=tuple(flagged_samples),
            exported_count=exported_count,
            skipped_count=skipped_count,
        )
