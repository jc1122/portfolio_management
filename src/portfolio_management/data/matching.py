"""Tradeable instrument matching logic."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from portfolio_management.data.models import StooqFile, TradeableInstrument, TradeableMatch

LOGGER = logging.getLogger(__name__)


def build_stooq_lookup(
    stooq_index: Sequence[StooqFile],
) -> tuple[
    dict[str, StooqFile],
    dict[str, StooqFile],
    dict[str, list[StooqFile]],
]:
    """Build lookup dictionaries for efficient matching.
    
    Returns:
        Tuple of (by_ticker, by_stem, by_base) lookup dictionaries
    """
    raise NotImplementedError(
        "build_stooq_lookup needs to be implemented - missing from grafted repository"
    )


def match_tradeables(
    tradeables: Sequence[TradeableInstrument],
    stooq_by_ticker: dict[str, StooqFile],
    stooq_by_stem: dict[str, StooqFile],
    stooq_by_base: dict[str, list[StooqFile]],
    max_workers: int | None = None,
) -> tuple[list[TradeableMatch], list[TradeableInstrument]]:
    """Match tradeable instruments to Stooq files.
    
    Returns:
        Tuple of (matched, unmatched) instruments
    """
    raise NotImplementedError(
        "match_tradeables needs to be implemented - missing from grafted repository"
    )


def annotate_unmatched_instruments(
    unmatched: list[TradeableInstrument],
    stooq_by_base: dict[str, list[StooqFile]],
    available_extensions: set[str],
) -> list[TradeableInstrument]:
    """Annotate unmatched instruments with reason for failure.
    
    Returns:
        List of unmatched instruments with reason field populated
    """
    raise NotImplementedError(
        "annotate_unmatched_instruments needs to be implemented - missing from grafted repository"
    )


def determine_unmatched_reason(
    instrument: TradeableInstrument,
    stooq_by_base: dict[str, list[StooqFile]],
    available_extensions: set[str],
) -> str:
    """Determine why an instrument could not be matched.
    
    Returns:
        Reason string (e.g., 'no_source_data', 'alias_required', 'manual_review')
    """
    raise NotImplementedError(
        "determine_unmatched_reason needs to be implemented - missing from grafted repository"
    )
