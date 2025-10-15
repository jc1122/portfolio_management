from __future__ import annotations

import logging
import re
from collections.abc import Iterable, Sequence

from .config import LEGACY_PREFIXES, SYMBOL_ALIAS_MAP
from .models import StooqFile, TradeableInstrument, TradeableMatch
from .utils import _run_in_parallel

LOGGER = logging.getLogger(__name__)


def build_stooq_lookup(
    entries: Sequence[StooqFile],
) -> tuple[dict[str, StooqFile], dict[str, StooqFile], dict[str, list[StooqFile]]]:
    """Create lookup dictionaries for Stooq tickers, stems, and base symbols."""
    by_ticker: dict[str, StooqFile] = {}
    by_stem: dict[str, StooqFile] = {}
    by_base: dict[str, list[StooqFile]] = {}
    for entry in entries:
        ticker = entry.ticker.upper()
        by_ticker.setdefault(ticker, entry)
        by_stem.setdefault(entry.stem.upper(), entry)
        base = ticker.split(".", 1)[0]
        by_base.setdefault(base, []).append(entry)
    return by_ticker, by_stem, by_base


def _generate_initial_candidates(
    normalized_symbol: str,
    base: str,
    suffix: str,
    extensions: Sequence[str],
) -> list[str]:
    """Generate initial ticker candidates based on the symbol parts."""
    candidates: list[str] = []
    if suffix:
        candidates.extend([f"{base}{ext}".upper() for ext in extensions if ext])
        candidates.append(normalized_symbol.upper())
    else:
        candidates.append(base.upper())
        candidates.extend([f"{base}{ext}".upper() for ext in extensions if ext])
        if "." in normalized_symbol:
            candidates.append(normalized_symbol.upper())
    return candidates


def _get_desired_extensions(
    extensions: Sequence[str],
    market: str,
) -> list[str]:
    """Get a list of desired extensions, with a fallback to market-based extensions."""
    desired_exts = [ext for ext in extensions if ext]
    if not desired_exts:
        desired_exts = [ext for ext in suffix_to_extensions("", market) if ext]
    return desired_exts


def candidate_tickers(symbol: str, market: str) -> Iterable[str]:
    """Generate possible Stooq tickers for a tradeable symbol."""
    if not symbol:
        return []

    original = symbol.strip()
    normalized = original.replace(" ", "").upper()
    base, suffix = split_symbol(normalized)

    extensions = suffix_to_extensions(suffix, market)
    candidates = _generate_initial_candidates(normalized, base, suffix, extensions)

    desired_exts = _get_desired_extensions(extensions, market)

    base_upper = base.upper()
    for ext in desired_exts:
        key = (base_upper, ext.upper())
        candidates.extend([alias.upper() for alias in SYMBOL_ALIAS_MAP.get(key, [])])
        for prefix in LEGACY_PREFIXES:
            if ext:
                candidates.append(f"{prefix}{base_upper}{ext.upper()}")
            else:
                candidates.append(f"{prefix}{base_upper}")

    seen = set()
    for cand in candidates:
        if cand not in seen:
            seen.add(cand)
            yield cand


def split_symbol(symbol: str) -> tuple[str, str]:
    """Split a broker symbol of the form 'ABC:LN' into base and suffix."""
    if ":" in symbol:
        base, suffix = symbol.split(":", 1)
        return base, suffix
    if "." in symbol:
        base, suffix = symbol.split(".", 1)
        return base, suffix
    return symbol, ""


def suffix_to_extensions(suffix: str, market: str) -> Sequence[str]:
    """Map broker suffixes to likely Stooq ticker extensions."""
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


class TickerMatchingStrategy:
    """A matching strategy that matches by ticker."""

    @staticmethod
    def _extension_is_acceptable(entry_ext: str, desired_exts_set: set[str]) -> bool:
        """Check if an extension is acceptable."""
        if not desired_exts_set:
            return True
        if entry_ext:
            return entry_ext in desired_exts_set
        return "" in desired_exts_set

    def match(
        self,
        candidate: str,
        by_ticker: dict[str, StooqFile],
        desired_exts_set: set[str],
        instrument: TradeableInstrument,
    ) -> TradeableMatch | None:
        """Try to match a tradeable instrument by its ticker."""
        if candidate not in by_ticker:
            return None

        entry = by_ticker[candidate]
        if not self._extension_is_acceptable(entry.extension.upper(), desired_exts_set):
            return None

        return TradeableMatch(
            instrument=instrument,
            stooq_file=entry,
            matched_ticker=candidate,
            strategy="ticker",
        )


class StemMatchingStrategy:
    """A matching strategy that matches by stem."""

    @staticmethod
    def _extension_is_acceptable(entry_ext: str, desired_exts_set: set[str]) -> bool:
        """Check if an extension is acceptable."""
        if not desired_exts_set:
            return True
        if entry_ext:
            return entry_ext in desired_exts_set
        return "" in desired_exts_set

    def match(
        self,
        candidate: str,
        by_stem: dict[str, StooqFile],
        desired_exts_set: set[str],
        instrument: TradeableInstrument,
    ) -> TradeableMatch | None:
        """Try to match a tradeable instrument by its stem."""
        stem_candidate = candidate.split(".", 1)[0]
        if stem_candidate not in by_stem:
            return None

        entry = by_stem[stem_candidate]
        if not self._extension_is_acceptable(entry.extension.upper(), desired_exts_set):
            return None

        return TradeableMatch(
            instrument=instrument,
            stooq_file=entry,
            matched_ticker=entry.ticker,
            strategy="stem",
        )


class BaseMarketMatchingStrategy:
    """A matching strategy that matches by base and market."""

    @staticmethod
    def _build_desired_extensions(
        instrument_suffix: str,
        market: str,
    ) -> list[str]:
        """Build a list of desired extensions, removing duplicates while preserving order."""
        desired_exts: list[str] = []
        desired_exts_set: set[str] = set()

        for ext in suffix_to_extensions(instrument_suffix, market):
            if ext:
                ext_up = ext.upper()
                if ext_up not in desired_exts_set:
                    desired_exts.append(ext_up)
                    desired_exts_set.add(ext_up)

        for ext in suffix_to_extensions("", market):
            if ext:
                ext_up = ext.upper()
                if ext_up not in desired_exts_set:
                    desired_exts.append(ext_up)
                    desired_exts_set.add(ext_up)

        return desired_exts

    @staticmethod
    def _get_candidate_extension(candidate: str) -> str:
        """Extract the extension from a candidate ticker."""
        if "." in candidate:
            return candidate[candidate.find(".") :].upper()
        return ""

    @staticmethod
    def _find_matching_entry(
        base_entries: list[StooqFile],
        preferred_exts: list[str],
    ) -> StooqFile | None:
        """Find an entry matching the preferred extensions."""
        if not preferred_exts:
            return base_entries[0] if len(base_entries) == 1 else None

        for ext in preferred_exts:
            for entry in base_entries:
                if entry.ticker.upper().endswith(ext):
                    return entry

        return None

    def match(
        self,
        candidate: str,
        by_base: dict[str, list[StooqFile]],
        instrument: TradeableInstrument,
        instrument_suffix: str,
    ) -> TradeableMatch | None:
        """Try to match a tradeable instrument by its base and market."""
        stem_candidate = candidate.split(".", 1)[0]
        base_entries = by_base.get(stem_candidate)
        if not base_entries:
            return None

        # Build extensions and get available extensions in base_entries
        desired_exts = self._build_desired_extensions(
            instrument_suffix, instrument.market
        )
        desired_exts_set = set(desired_exts)

        available_exts = {
            entry.ticker[entry.ticker.find(".") :].upper()
            for entry in base_entries
            if "." in entry.ticker
        }

        # If desired extensions are specified but none are available, no match
        if desired_exts_set and not any(
            ext in available_exts for ext in desired_exts_set
        ):
            return None

        # Build preferred extensions list with candidate extension first if present
        candidate_ext = self._get_candidate_extension(candidate)
        preferred_exts = [ext for ext in desired_exts if ext]
        if candidate_ext and candidate_ext not in desired_exts_set:
            preferred_exts.insert(0, candidate_ext)

        chosen = self._find_matching_entry(base_entries, preferred_exts)
        if not chosen:
            return None

        return TradeableMatch(
            instrument=instrument,
            stooq_file=chosen,
            matched_ticker=chosen.ticker,
            strategy="base_market",
        )


def _build_candidate_extensions(
    norm_symbol: str,
    instrument_suffix: str,
    market: str,
) -> tuple[set[str], set[str]]:
    """Build desired and fallback extensions for a candidate."""
    desired = {
        ext.upper() for ext in suffix_to_extensions(instrument_suffix, market) if ext
    }
    fallback = {ext.upper() for ext in suffix_to_extensions("", market) if ext}
    return desired, fallback


def _extract_candidate_extension(candidate: str) -> str:
    """Extract the extension (with dot) from a candidate ticker."""
    if "." in candidate:
        return candidate[candidate.find(".") :].upper()
    return ""


def _build_desired_extensions_for_candidate(
    instrument_desired_exts: set[str],
    fallback_desired_exts: set[str],
    candidate_ext: str,
) -> set[str]:
    """Build the set of desired extensions for a specific candidate."""
    desired_exts_set = set(instrument_desired_exts)
    if not desired_exts_set:
        desired_exts_set.update(fallback_desired_exts)
    if candidate_ext:
        desired_exts_set.add(candidate_ext)
    return desired_exts_set


def _match_instrument(
    instrument: TradeableInstrument,
    by_ticker: dict[str, StooqFile],
    by_stem: dict[str, StooqFile],
    by_base: dict[str, list[StooqFile]],
) -> tuple[TradeableMatch | None, TradeableInstrument | None]:
    """Try to match a tradeable instrument to a Stooq file using multiple strategies."""
    tried: list[str] = []
    norm_symbol = (instrument.symbol or "").replace(" ", "").upper()
    _, instrument_suffix = split_symbol(norm_symbol)

    instrument_desired_exts, fallback_desired_exts = _build_candidate_extensions(
        norm_symbol, instrument_suffix, instrument.market
    )

    ticker_strategy = TickerMatchingStrategy()
    stem_strategy = StemMatchingStrategy()
    base_market_strategy = BaseMarketMatchingStrategy()

    for candidate in candidate_tickers(instrument.symbol, instrument.market):
        tried.append(candidate)
        candidate_ext = _extract_candidate_extension(candidate)
        desired_exts_set = _build_desired_extensions_for_candidate(
            instrument_desired_exts, fallback_desired_exts, candidate_ext
        )

        # Try each strategy in order
        if match := ticker_strategy.match(
            candidate, by_ticker, desired_exts_set, instrument
        ):
            return match, None

        if match := stem_strategy.match(
            candidate, by_stem, desired_exts_set, instrument
        ):
            return match, None

        if match := base_market_strategy.match(
            candidate, by_base, instrument, instrument_suffix
        ):
            return match, None

    LOGGER.debug(
        "Unmatched instrument %s (market=%s) candidates=%s",
        instrument.symbol,
        instrument.market,
        tried,
    )
    return None, instrument


def match_tradeables(
    instruments: Sequence[TradeableInstrument],
    by_ticker: dict[str, StooqFile],
    by_stem: dict[str, StooqFile],
    by_base: dict[str, list[StooqFile]],
    *,
    max_workers: int = 1,
) -> tuple[list[TradeableMatch], list[TradeableInstrument]]:
    """Match tradeable instruments to Stooq files."""
    matches: list[TradeableMatch] = []
    unmatched: list[TradeableInstrument] = []

    results = _run_in_parallel(
        _match_instrument,
        [(instrument, by_ticker, by_stem, by_base) for instrument in instruments],
        max_workers,
    )

    for match, missing in results:
        if match:
            matches.append(match)
        elif missing:
            unmatched.append(missing)

    LOGGER.info("Matched %s instruments, %s unmatched", len(matches), len(unmatched))
    return matches, unmatched


def determine_unmatched_reason(
    instrument: TradeableInstrument,
    stooq_by_base: dict[str, list[StooqFile]],
    available_extensions: set[str],
) -> str:
    """Explain why a tradeable instrument could not be matched."""
    symbol = (instrument.symbol or "").upper().strip()
    market = (instrument.market or "").upper()
    base, suffix = split_symbol(symbol)
    desired_exts = {ext.upper() for ext in suffix_to_extensions(suffix, market) if ext}
    if not desired_exts:
        desired_exts.update(
            ext.upper() for ext in suffix_to_extensions("", market) if ext
        )

    if desired_exts and not any(ext in available_extensions for ext in desired_exts):
        return f"no_source_data({','.join(sorted(desired_exts))})"

    base_entries = stooq_by_base.get(base.upper())
    if not base_entries:
        return "no_stooq_ticker"

    if desired_exts:
        matching = [
            entry
            for entry in base_entries
            if any(entry.ticker.upper().endswith(ext) for ext in desired_exts)
        ]
        if not matching:
            return "alias_required"

    if len(base_entries) > 1:
        return "ambiguous_variants"

    return "manual_review"


def annotate_unmatched_instruments(
    unmatched: Sequence[TradeableInstrument],
    stooq_by_base: dict[str, list[StooqFile]],
    available_extensions: set[str],
) -> list[TradeableInstrument]:
    """Attach diagnostic reasons to unmatched instruments."""
    return [
        TradeableInstrument(
            symbol=instrument.symbol,
            isin=instrument.isin,
            market=instrument.market,
            name=instrument.name,
            currency=instrument.currency,
            source_file=instrument.source_file,
            reason=determine_unmatched_reason(
                instrument,
                stooq_by_base,
                available_extensions,
            ),
        )
        for instrument in unmatched
    ]
