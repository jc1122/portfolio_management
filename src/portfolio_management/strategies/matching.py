"""Matching strategies for resolving broker tradeable instruments."""

from __future__ import annotations

from typing import TYPE_CHECKING

from portfolio_management.models import TradeableMatch

if TYPE_CHECKING:
    from portfolio_management.models import StooqFile, TradeableInstrument


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

        from portfolio_management.matching import suffix_to_extensions

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
            instrument_suffix,
            instrument.market,
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
