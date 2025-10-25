"""Tradeable instrument matching utilities.

This module provides a robust matching engine to link broker-provided tradeable
instrument lists with the Stooq price data index. It uses a series of strategies,
from direct ticker matching to suffix mapping and alias lookups, to find the
correct Stooq file for each instrument.

Key Functions:
    - match_tradeables: The main entry point to run the matching process.
    - candidate_tickers: Generates potential Stooq ticker variations for a symbol.
    - suffix_to_extensions: Maps broker-specific suffixes (e.g., ':LN') to Stooq
      extensions (e.g., '.UK').
    - build_stooq_lookup: Creates efficient lookup tables from the Stooq index.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from portfolio_management.core.config import LEGACY_PREFIXES, SYMBOL_ALIAS_MAP
from portfolio_management.core.utils import _run_in_parallel
from portfolio_management.data.models import (
    StooqFile,
    TradeableInstrument,
    TradeableMatch,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence


@dataclass(frozen=True)
class _MatchContext:
    instrument: TradeableInstrument
    normalized_symbol: str
    desired_exts: list[str]
    stooq_by_ticker: dict[str, StooqFile]
    original_symbol: str
    has_suffix: bool


LOGGER = logging.getLogger(__name__)


def _stooq_extension(ticker: str) -> str:
    if "." in ticker:
        return ticker[ticker.find(".") :].upper()
    return ""


def _extension_is_acceptable(entry_ext: str, desired_exts_set: set[str]) -> bool:
    if not desired_exts_set:
        return True
    if entry_ext:
        return entry_ext in desired_exts_set
    return "" in desired_exts_set


def split_symbol(symbol: str) -> tuple[str, str]:
    """Split a broker symbol into its base and suffix components.

    Args:
        symbol: The symbol to split (e.g., 'AAPL:US' or 'VOD.L').

    Returns:
        A tuple containing the base and suffix.
    """
    if ":" in symbol:
        base, suffix = symbol.split(":", 1)
        return base, suffix
    if "." in symbol:
        base, suffix = symbol.split(".", 1)
        return base, suffix
    return symbol, ""


def suffix_to_extensions(suffix: str, market: str) -> Sequence[str]:
    """Map broker suffixes and market names to likely Stooq ticker extensions.

    Args:
        suffix: The symbol suffix (e.g., 'LN', 'US').
        market: The market name (e.g., 'LSE', 'NASDAQ').

    Returns:
        A sequence of possible Stooq extensions (e.g., ['.UK'], ['.US']).
    """
    suffix = suffix.upper()
    market = (market or "").upper()

    mapping = {
        "PW": [".PL"],
        "PL": [".PL"],
        "GPW": [".PL"],
        "LN": [".UK"],
        "L": [".UK"],
        "GB": [".UK"],
        "US": [".US"],
        "UN": [".US"],
        "U": [".US"],
        "NYSE": [".US"],
        "NASDAQ": [".US"],
        "NSQ": [".US"],
        "NAS": [".US"],
        "NASDAQ (USD)": [".US"],
        "NYSE-MKT": [".US"],
        "AMEX": [".US"],
        "HK": [".HK"],
        "H": [".HK"],
        "JP": [".JP"],
        "T": [".JP"],
        "HU": [".HU"],
        "BSE": [".HU"],
        "TSX": [".TO"],
        "TSXV": [".V"],
        "TO": [".TO"],
        "V": [".V"],
        "CN": [".CN"],
        "C": [".TO"],
        "GR": [".DE"],
        "DE": [".DE"],
        "PA": [".PA", ".FR"],
        "PAR": [".PA", ".FR"],
        "AMS": [".NL", ".AS"],
        "AS": [".AS", ".NL"],
        "SWX": [".CH"],
        "SW": [".CH"],
        "CH": [".CH"],
        "BRU": [".BE"],
        "BR": [".BE"],
        "BRX": [".BE"],
    }

    if suffix in mapping:
        return mapping[suffix]

    market_matchers = [
        (r"XETRA|FRANKFURT|GER|DEU", [".DE"]),
        (r"EURONEXT\s*PARIS|\bPAR\b|PARIS|FRANCE", [".PA", ".FR"]),
        (r"EURONEXT\s*AMSTERDAM|AMSTERDAM|NED|NETHERLANDS", [".NL", ".AS"]),
        (r"NSQ|NASDAQ|NYSE|USA|UNITED STATES|AMERICAN", [".US"]),
        (r"TSX|TORONTO|CANADA", [".TO"]),
        (r"GPW|WARSAW|POL", [".PL"]),
        (r"LSE|LONDON|UNITED KINGDOM|UK", [".UK"]),
        (r"HK", [".HK"]),
        (r"JPX|TOKYO|JAPAN", [".JP"]),
        (r"HUNGARY|BUDAPEST", [".HU"]),
        (r"SWISS|ZURICH|SWX|SIX|SWITZERLAND", [".CH"]),
        (r"BRUSSELS|BELGIUM", [".BE"]),
    ]

    for pattern, exts in market_matchers:
        if re.search(pattern, market):
            return exts

    return [""]


def _get_desired_extensions(
    extensions: Sequence[str],
    market: str,
) -> list[str]:
    desired_exts = [ext.upper() for ext in extensions if ext]
    if desired_exts:
        return desired_exts
    return [ext.upper() for ext in suffix_to_extensions("", market) if ext]


def candidate_tickers(symbol: str, market: str) -> Iterable[str]:
    """Generate possible Stooq tickers for a tradeable symbol.

    This function produces a sequence of potential ticker variations to try
    when matching against the Stooq index.

    Args:
        symbol: The broker symbol (e.g., 'AAPL:US').
        market: The market name (e.g., 'NASDAQ').

    Returns:
        An iterable of candidate ticker strings.
    """
    if not symbol:
        return []

    original = symbol.strip()
    normalized = original.replace(" ", "").upper()
    base, suffix = split_symbol(normalized)

    extensions = suffix_to_extensions(suffix, market)
    candidates: list[str] = []

    if suffix:
        candidates.extend([f"{base}{ext}".upper() for ext in extensions if ext])
        candidates.append(normalized.upper())
    else:
        candidates.append(base.upper())
        candidates.extend([f"{base}{ext}".upper() for ext in extensions if ext])
        if "." in normalized:
            candidates.append(normalized.upper())

    desired_exts = set(_get_desired_extensions(extensions, market))
    base_upper = base.upper()
    for ext in desired_exts:
        key = (base_upper, ext.upper())
        candidates.extend([alias.upper() for alias in SYMBOL_ALIAS_MAP.get(key, [])])
        for prefix in LEGACY_PREFIXES:
            if ext:
                candidates.append(f"{prefix}{base_upper}{ext.upper()}")
            else:
                candidates.append(f"{prefix}{base_upper}")

    # Yield unique while preserving order
    seen: set[str] = set()
    for cand in candidates:
        if cand not in seen:
            seen.add(cand)
            yield cand


def build_stooq_lookup(
    stooq_index: Sequence[StooqFile],
) -> tuple[
    dict[str, StooqFile],
    dict[str, StooqFile],
    dict[str, list[StooqFile]],
]:
    """Create lookup dictionaries for efficient matching.

    Args:
        stooq_index: A sequence of `StooqFile` objects.

    Returns:
        A tuple of three dictionaries: by ticker, by stem, and by base symbol.
    """
    by_ticker: dict[str, StooqFile] = {}
    by_stem: dict[str, StooqFile] = {}
    by_base: dict[str, list[StooqFile]] = {}

    for entry in stooq_index:
        ticker = entry.ticker.upper()
        stem = entry.stem.upper()
        base = ticker.split(".", 1)[0]

        by_ticker.setdefault(ticker, entry)
        by_stem.setdefault(stem, entry)
        by_base.setdefault(base, []).append(entry)

    return by_ticker, by_stem, by_base


def _match_instrument(
    instrument: TradeableInstrument,
    stooq_by_ticker: dict[str, StooqFile],
    stooq_by_stem: dict[str, StooqFile],
    stooq_by_base: dict[str, list[StooqFile]],
    available_extensions: set[str],
) -> tuple[TradeableMatch | None, TradeableInstrument | None]:
    symbol = (instrument.symbol or "").strip()
    if not symbol:
        return None, replace(instrument, reason="missing_symbol")

    normalized = symbol.replace(" ", "").upper()
    base, suffix = split_symbol(normalized)
    desired_exts = [
        ext.upper() for ext in suffix_to_extensions(suffix, instrument.market or "")
    ]
    context = _MatchContext(
        instrument=instrument,
        normalized_symbol=normalized,
        desired_exts=desired_exts,
        stooq_by_ticker=stooq_by_ticker,
        original_symbol=symbol,
        has_suffix=bool(suffix),
    )

    direct = _match_candidates(context)
    if direct is not None:
        return direct, None

    stem = _match_by_stem(instrument, base, desired_exts, stooq_by_stem)
    if stem is not None:
        return stem, None

    base_match = _match_by_base(instrument, base, desired_exts, stooq_by_base)
    if base_match is not None:
        return base_match, None

    reason = determine_unmatched_reason(
        instrument,
        stooq_by_base,
        available_extensions,
    )
    return None, replace(instrument, reason=reason)


def _match_candidates(context: _MatchContext) -> TradeableMatch | None:
    for candidate in candidate_tickers(
        context.original_symbol,
        context.instrument.market or "",
    ):
        entry = context.stooq_by_ticker.get(candidate.upper())
        if entry is None:
            continue
        entry_ext = _stooq_extension(entry.ticker)
        if not _extension_is_acceptable(entry_ext, set(context.desired_exts)):
            continue
        strategy_name = (
            "ticker"
            if context.has_suffix or candidate.upper() == context.normalized_symbol
            else "base_market"
        )
        return TradeableMatch(
            instrument=context.instrument,
            stooq_file=entry,
            matched_ticker=entry.ticker.upper(),
            strategy=strategy_name,
        )
    return None


def _match_by_stem(
    instrument: TradeableInstrument,
    base: str,
    desired_exts: list[str],
    stooq_by_stem: dict[str, StooqFile],
) -> TradeableMatch | None:
    stem_entry = stooq_by_stem.get(base.upper())
    if stem_entry is None:
        return None
    entry_ext = _stooq_extension(stem_entry.ticker)
    if not _extension_is_acceptable(entry_ext, set(desired_exts)):
        return None
    return TradeableMatch(
        instrument=instrument,
        stooq_file=stem_entry,
        matched_ticker=stem_entry.ticker.upper(),
        strategy="base_market",
    )


def _match_by_base(
    instrument: TradeableInstrument,
    base: str,
    desired_exts: list[str],
    stooq_by_base: dict[str, list[StooqFile]],
) -> TradeableMatch | None:
    candidates = stooq_by_base.get(base.upper(), [])
    filtered = [
        entry
        for entry in candidates
        if _extension_is_acceptable(_stooq_extension(entry.ticker), set(desired_exts))
    ]
    if len(filtered) == 1:
        entry = filtered[0]
        return TradeableMatch(
            instrument=instrument,
            stooq_file=entry,
            matched_ticker=entry.ticker.upper(),
            strategy="base_market",
        )
    if not filtered and len(candidates) == 1:
        entry = candidates[0]
        return TradeableMatch(
            instrument=instrument,
            stooq_file=entry,
            matched_ticker=entry.ticker.upper(),
            strategy="base_market",
        )
    return None


def match_tradeables(
    tradeables: Sequence[TradeableInstrument],
    stooq_by_ticker: dict[str, StooqFile],
    stooq_by_stem: dict[str, StooqFile],
    stooq_by_base: dict[str, list[StooqFile]],
    max_workers: int | None = None,
) -> tuple[list[TradeableMatch], list[TradeableInstrument]]:
    """Match a sequence of tradeable instruments to Stooq files in parallel.

    Args:
        tradeables: A sequence of `TradeableInstrument` objects.
        stooq_by_ticker: A lookup from Stooq ticker to `StooqFile`.
        stooq_by_stem: A lookup from Stooq stem to `StooqFile`.
        stooq_by_base: A lookup from base symbol to a list of `StooqFile`s.
        max_workers: The maximum number of parallel workers to use.

    Returns:
        A tuple containing a list of successful matches and a list of
        unmatched instruments.
    """
    if not tradeables:
        return [], []

    available_extensions = {_stooq_extension(ticker) for ticker in stooq_by_ticker}

    workers = max(1, max_workers or os.cpu_count() or 1)
    results = _run_in_parallel(
        _match_instrument,
        [
            (
                instrument,
                stooq_by_ticker,
                stooq_by_stem,
                stooq_by_base,
                available_extensions,
            )
            for instrument in tradeables
        ],
        workers,
        preserve_order=True,
    )

    matches: list[TradeableMatch] = []
    unmatched: list[TradeableInstrument] = []
    for match, missing in results:
        if match is not None:
            matches.append(match)
        elif missing is not None:
            unmatched.append(missing)

    return matches, unmatched


def annotate_unmatched_instruments(
    unmatched: list[TradeableInstrument],
    stooq_by_base: dict[str, list[StooqFile]],
    available_extensions: set[str],
) -> list[TradeableInstrument]:
    """Annotate unmatched instruments with reason codes for diagnostics.

    Args:
        unmatched: A list of `TradeableInstrument` objects that were not matched.
        stooq_by_base: A lookup from base symbol to a list of `StooqFile`s.
        available_extensions: A set of available Stooq extensions.

    Returns:
        A list of unmatched instruments with an added `reason` attribute.
    """
    annotated: list[TradeableInstrument] = []
    for instrument in unmatched:
        reason = determine_unmatched_reason(
            instrument,
            stooq_by_base,
            available_extensions,
        )
        annotated.append(replace(instrument, reason=reason))
    return annotated


def determine_unmatched_reason(
    instrument: TradeableInstrument,
    stooq_by_base: dict[str, list[StooqFile]],
    available_extensions: set[str],
) -> str:
    """Determine the most likely reason why an instrument could not be matched.

    Args:
        instrument: The unmatched `TradeableInstrument`.
        stooq_by_base: A lookup from base symbol to a list of `StooqFile`s.
        available_extensions: A set of available Stooq extensions.

    Returns:
        A string code representing the reason for the match failure.
    """
    symbol = (instrument.symbol or "").strip()
    if not symbol:
        return "missing_symbol"

    normalized = symbol.replace(" ", "").upper()
    base, suffix = split_symbol(normalized)
    desired_exts = [
        ext.upper() for ext in suffix_to_extensions(suffix, instrument.market or "")
    ]

    if desired_exts:
        missing = [ext for ext in desired_exts if ext not in available_extensions]
        if missing:
            return f"no_source_data({missing[0]})"

    entries = stooq_by_base.get(base.upper(), [])
    if not entries:
        return "manual_review"

    if len(entries) > 1:
        return "ambiguous_variants"

    entry_ext = _stooq_extension(entries[0].ticker)
    if desired_exts and entry_ext not in desired_exts:
        return "alias_required"

    return "manual_review"