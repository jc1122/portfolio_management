"""Service for orchestrating the tradeable data preparation pipeline."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from portfolio_management.core.utils import log_duration
from portfolio_management.data import cache
from portfolio_management.data.analysis import (
    collect_available_extensions,
    log_summary_counts,
)
from portfolio_management.data.ingestion import build_stooq_index
from portfolio_management.data.io import (
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
from portfolio_management.data.models import ExportConfig

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class DataPreparationConfig:
    """Configuration for the data preparation workflow."""

    data_dir: Path
    metadata_output: Path
    tradeable_dir: Path
    match_report: Path
    unmatched_report: Path
    prices_output: Path
    force_reindex: bool = False
    overwrite_prices: bool = False
    include_empty_prices: bool = False
    lse_currency_policy: str = "broker"
    max_workers: int | None = None
    index_workers: int | None = None
    incremental: bool = False
    cache_metadata: Path | None = None


@dataclass(frozen=True)
class DataPreparationResult:
    """Represents the outcome of the data preparation workflow."""

    stooq_index_path: Path
    match_report_path: Path
    unmatched_report_path: Path
    diagnostics: dict[str, Any]
    skipped: bool


class DataPreparationService:
    """High-level orchestration service for tradeable data preparation."""

    def __init__(
        self,
        *,
        stooq_index_builder: Callable[[Path, int], Any] | None = None,
        stooq_index_reader: Callable[[Path], Any] | None = None,
        stooq_index_writer: Callable[[Any, Path], None] | None = None,
        tradeable_loader: Callable[[Path], Any] | None = None,
        lookup_builder: Callable[[Any], tuple[Any, Any, Any]] | None = None,
        extension_collector: Callable[[Any], Any] | None = None,
        matcher: Callable[[Any, Any, Any, Any], tuple[Any, Any]] | None = None,
        unmatched_annotator: Callable[[Any, Any, Any], Any] | None = None,
        match_report_writer: Callable[..., tuple[Any, Any, Any, Any, Any, int, int]] | None = None,
        unmatched_writer: Callable[[Any, Path], None] | None = None,
        cache_module=cache,
        logger: logging.Logger | None = None,
    ) -> None:
        self._stooq_index_builder = stooq_index_builder or build_stooq_index
        self._stooq_index_reader = stooq_index_reader or read_stooq_index
        self._stooq_index_writer = stooq_index_writer or write_stooq_index
        self._tradeable_loader = tradeable_loader or load_tradeable_instruments
        self._lookup_builder = lookup_builder or build_stooq_lookup
        self._extension_collector = extension_collector or collect_available_extensions
        self._matcher = matcher or match_tradeables
        self._unmatched_annotator = unmatched_annotator or annotate_unmatched_instruments
        self._match_report_writer = match_report_writer or write_match_report
        self._unmatched_writer = unmatched_writer or write_unmatched_report
        self._cache = cache_module
        self._logger = logger or _LOGGER

    def prepare(self, config: DataPreparationConfig) -> DataPreparationResult:
        """Execute the data preparation workflow."""

        max_workers = self._determine_workers(config.max_workers)
        index_workers = self._determine_workers(
            config.index_workers if config.index_workers is not None else max_workers,
        )
        self._logger.info(
            "Worker configuration: match/export=%s, index=%s (cpu=%s)",
            max_workers,
            index_workers,
            os.cpu_count() or 1,
        )

        if config.incremental and config.cache_metadata is not None:
            metadata = self._cache.load_cache_metadata(config.cache_metadata)
            if self._cache.inputs_unchanged(
                config.tradeable_dir,
                config.metadata_output,
                metadata,
            ) and self._cache.outputs_exist(config.match_report, config.unmatched_report):
                self._logger.info(
                    "Incremental resume: inputs unchanged and outputs exist - skipping",
                )
                return DataPreparationResult(
                    stooq_index_path=config.metadata_output,
                    match_report_path=config.match_report,
                    unmatched_report_path=config.unmatched_report,
                    diagnostics={},
                    skipped=True,
                )
            self._logger.info("Incremental resume requested - running full pipeline")
        else:
            metadata = {}

        stooq_index = self._load_or_build_index(config, index_workers)
        matches, unmatched = self._load_and_match(stooq_index, config, max_workers)
        diagnostics = self._generate_reports(matches, unmatched, config, max_workers)

        if config.incremental and config.cache_metadata is not None:
            new_metadata = self._cache.create_cache_metadata(
                config.tradeable_dir,
                config.metadata_output,
            )
            self._cache.save_cache_metadata(config.cache_metadata, new_metadata)

        return DataPreparationResult(
            stooq_index_path=config.metadata_output,
            match_report_path=config.match_report,
            unmatched_report_path=config.unmatched_report,
            diagnostics=diagnostics,
            skipped=False,
        )

    def _determine_workers(self, requested: int | None) -> int:
        cpu_count = os.cpu_count() or 1
        if requested is None or requested <= 0:
            return max(1, (cpu_count - 1) or 1)
        return max(1, requested)

    def _load_or_build_index(
        self,
        config: DataPreparationConfig,
        index_workers: int,
    ) -> Any:
        if config.metadata_output.exists() and not config.force_reindex:
            with log_duration("stooq_index_load"):
                self._logger.debug("Loading cached Stooq index from %s", config.metadata_output)
                return self._stooq_index_reader(config.metadata_output)
        with log_duration("stooq_index_build"):
            self._logger.debug(
                "Building Stooq index from %s using %s workers",
                config.data_dir,
                index_workers,
            )
            stooq_index = self._stooq_index_builder(config.data_dir, index_workers)
        with log_duration("stooq_index_write"):
            self._stooq_index_writer(stooq_index, config.metadata_output)
        return stooq_index

    def _load_and_match(
        self,
        stooq_index: Any,
        config: DataPreparationConfig,
        max_workers: int,
    ) -> tuple[Any, Any]:
        with log_duration("tradeable_load"):
            tradeables = self._tradeable_loader(config.tradeable_dir)
        stooq_by_ticker, stooq_by_stem, stooq_by_base = self._lookup_builder(stooq_index)
        available_extensions = self._extension_collector(stooq_index)
        with log_duration("tradeable_match"):
            matches, unmatched = self._matcher(
                tradeables,
                stooq_by_ticker,
                stooq_by_stem,
                stooq_by_base,
                max_workers=max_workers,
            )
        unmatched = self._unmatched_annotator(
            unmatched,
            stooq_by_base,
            available_extensions,
        )
        return matches, unmatched

    def _generate_reports(
        self,
        matches: Any,
        unmatched: Any,
        config: DataPreparationConfig,
        max_workers: int,
    ) -> dict[str, Any]:
        export_config = ExportConfig(
            data_dir=config.data_dir,
            dest_dir=config.prices_output,
            overwrite=config.overwrite_prices,
            max_workers=max_workers,
            include_empty=config.include_empty_prices,
        )
        export_config.dest_dir.mkdir(parents=True, exist_ok=True)
        with log_duration("tradeable_match_report"):
            (
                diagnostics_cache,
                currency_counts,
                data_status_counts,
                empty_tickers,
                flagged_samples,
                exported_count,
                skipped_count,
            ) = self._match_report_writer(
                matches,
                config.match_report,
                config.data_dir,
                lse_currency_policy=config.lse_currency_policy,
                max_workers=max_workers,
                export_config=export_config,
            )
        log_summary_counts(currency_counts, data_status_counts)
        if empty_tickers:
            preview = ", ".join(sorted(empty_tickers)[:5])
            self._logger.warning(
                "Detected %s empty Stooq price files (e.g., %s)",
                len(empty_tickers),
                preview,
            )
        if flagged_samples:
            snippet = ", ".join(
                f"{symbol}->{ticker} [{flags}]"
                for symbol, ticker, flags in flagged_samples[:5]
            )
            self._logger.warning(
                "Detected validation flags for %s matched instruments (e.g., %s)",
                len(flagged_samples),
                snippet,
            )
        with log_duration("tradeable_unmatched_report"):
            self._unmatched_writer(unmatched, config.unmatched_report)
        self._logger.info(
            "Exported %s price files to %s", exported_count, export_config.dest_dir
        )
        if skipped_count:
            self._logger.warning("Skipped %s price files without usable data", skipped_count)
        return {
            "cache": diagnostics_cache,
            "exported_count": exported_count,
            "skipped_count": skipped_count,
        }


__all__ = [
    "DataPreparationConfig",
    "DataPreparationResult",
    "DataPreparationService",
]
