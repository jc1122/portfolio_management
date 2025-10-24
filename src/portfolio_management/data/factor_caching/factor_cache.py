"""Factor Score and Eligibility Caching Module.

Provides on-disk caching for factor scores (momentum, low-vol) and PIT eligibility
masks to avoid recomputation across backtest runs when inputs haven't changed.

Cache keys are computed from:
- Dataset hash (returns matrix content)
- Configuration hash (lookback, skip, min_history_days, etc.)
- Date range

Invalidation occurs automatically when any of these components change.
"""

import hashlib
import json
import logging
import pickle
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class CacheMetadata:
    """Metadata for a cache entry."""

    cache_key: str
    dataset_hash: str
    config_hash: str
    start_date: str
    end_date: str
    created_at: str
    entry_type: str  # 'factor_scores' or 'pit_eligibility'
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "cache_key": self.cache_key,
            "dataset_hash": self.dataset_hash,
            "config_hash": self.config_hash,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "created_at": self.created_at,
            "entry_type": self.entry_type,
            "params": self.params,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CacheMetadata":
        """Create from dictionary."""
        return cls(
            cache_key=data["cache_key"],
            dataset_hash=data["dataset_hash"],
            config_hash=data["config_hash"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            created_at=data["created_at"],
            entry_type=data["entry_type"],
            params=data.get("params", {}),
        )


class FactorCache:
    """On-disk cache for factor scores and PIT eligibility masks.

    Cache structure:
        cache_dir/
            metadata/
                {cache_key}.json
            data/
                {cache_key}.pkl

    Examples:
        >>> cache = FactorCache(Path(".cache/factors"))
        >>> # Cache factor scores
        >>> scores = compute_momentum_scores(returns, lookback=252)
        >>> cache.put_factor_scores(
        ...     scores,
        ...     returns,
        ...     {"method": "momentum", "lookback": 252},
        ...     "2020-01-01",
        ...     "2025-10-24"
        ... )
        >>> # Retrieve cached scores
        >>> cached = cache.get_factor_scores(
        ...     returns,
        ...     {"method": "momentum", "lookback": 252},
        ...     "2020-01-01",
        ...     "2025-10-24"
        ... )

    """

    def __init__(
        self,
        cache_dir: Path,
        enabled: bool = True,
        max_cache_age_days: int | None = None,
    ):
        """Initialize factor cache.

        Args:
            cache_dir: Directory to store cache files
            enabled: Whether caching is enabled (default: True)
            max_cache_age_days: Maximum cache age in days before invalidation
                               (None = no age limit)

        """
        self.cache_dir = cache_dir
        self.enabled = enabled
        self.max_cache_age_days = max_cache_age_days

        if enabled:
            self.metadata_dir = cache_dir / "metadata"
            self.data_dir = cache_dir / "data"
            self.metadata_dir.mkdir(parents=True, exist_ok=True)
            self.data_dir.mkdir(parents=True, exist_ok=True)

        self._stats = {"hits": 0, "misses": 0, "puts": 0}

    def _compute_dataset_hash(self, data: pd.DataFrame) -> str:
        """Compute a stable hash for the entire dataset."""

        hasher = hashlib.sha256()
        hasher.update(str(data.shape).encode())

        if data.empty:
            hasher.update("|".join(map(str, data.columns)).encode())
            hasher.update("|".join(map(str, data.index)).encode())
            return hasher.hexdigest()[:16]

        column_hash = pd.util.hash_pandas_object(pd.Index(data.columns), index=False)
        data_hash = pd.util.hash_pandas_object(data, index=True)

        hasher.update(column_hash.values.tobytes())
        hasher.update(data_hash.values.tobytes())

        return hasher.hexdigest()[:16]

    def _compute_config_hash(self, config: dict[str, Any]) -> str:
        """Compute hash of configuration parameters."""
        # Sort keys for consistent hashing
        sorted_config = json.dumps(config, sort_keys=True)
        return hashlib.sha256(sorted_config.encode()).hexdigest()[:16]

    def _compute_cache_key(
        self,
        dataset_hash: str,
        config_hash: str,
        start_date: str,
        end_date: str,
        entry_type: str,
    ) -> str:
        """Compute unique cache key."""
        components = [dataset_hash, config_hash, start_date, end_date, entry_type]
        combined = "|".join(components)
        return hashlib.sha256(combined.encode()).hexdigest()[:32]

    def _is_cache_valid(self, metadata: CacheMetadata) -> bool:
        """Check if cache entry is still valid based on age."""
        if self.max_cache_age_days is None:
            return True

        created_dt = datetime.fromisoformat(metadata.created_at)
        age_days = (datetime.now() - created_dt).days
        return age_days <= self.max_cache_age_days

    def get_factor_scores(
        self,
        returns: pd.DataFrame,
        config: dict[str, Any],
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame | None:
        """Retrieve cached factor scores.

        Args:
            returns: Returns matrix
            config: Configuration dict (method, lookback, skip, etc.)
            start_date: Start date for cache key
            end_date: End date for cache key

        Returns:
            Cached DataFrame if found and valid, None otherwise

        """
        if not self.enabled:
            return None

        dataset_hash = self._compute_dataset_hash(returns)
        config_hash = self._compute_config_hash(config)
        cache_key = self._compute_cache_key(
            dataset_hash,
            config_hash,
            start_date,
            end_date,
            "factor_scores",
        )

        metadata_path = self.metadata_dir / f"{cache_key}.json"
        data_path = self.data_dir / f"{cache_key}.pkl"

        if not metadata_path.exists() or not data_path.exists():
            self._stats["misses"] += 1
            logger.debug(f"Cache miss for factor scores (key: {cache_key[:8]}...)")
            return None

        # Load and validate metadata
        with open(metadata_path) as f:
            metadata = CacheMetadata.from_dict(json.load(f))

        if not self._is_cache_valid(metadata):
            logger.debug(f"Cache expired for factor scores (key: {cache_key[:8]}...)")
            self._stats["misses"] += 1
            return None

        # Load cached data
        try:
            with open(data_path, "rb") as f:
                cached_data = pickle.load(f)
            self._stats["hits"] += 1
            logger.info(
                f"Cache hit for factor scores (key: {cache_key[:8]}..., "
                f"config: {config.get('method', 'unknown')})",
            )
            return cached_data
        except Exception as e:
            logger.warning(f"Failed to load cached data: {e}")
            self._stats["misses"] += 1
            return None

    def put_factor_scores(
        self,
        scores: pd.DataFrame,
        returns: pd.DataFrame,
        config: dict[str, Any],
        start_date: str,
        end_date: str,
    ) -> None:
        """Cache factor scores.

        Args:
            scores: Factor scores DataFrame to cache
            returns: Returns matrix (for hash computation)
            config: Configuration dict
            start_date: Start date for cache key
            end_date: End date for cache key

        """
        if not self.enabled:
            return

        dataset_hash = self._compute_dataset_hash(returns)
        config_hash = self._compute_config_hash(config)
        cache_key = self._compute_cache_key(
            dataset_hash,
            config_hash,
            start_date,
            end_date,
            "factor_scores",
        )

        metadata = CacheMetadata(
            cache_key=cache_key,
            dataset_hash=dataset_hash,
            config_hash=config_hash,
            start_date=start_date,
            end_date=end_date,
            created_at=datetime.now().isoformat(),
            entry_type="factor_scores",
            params=config,
        )

        # Write metadata
        metadata_path = self.metadata_dir / f"{cache_key}.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata.to_dict(), f, indent=2)

        # Write data
        data_path = self.data_dir / f"{cache_key}.pkl"
        with open(data_path, "wb") as f:
            pickle.dump(scores, f, protocol=pickle.HIGHEST_PROTOCOL)

        self._stats["puts"] += 1
        logger.info(
            f"Cached factor scores (key: {cache_key[:8]}..., "
            f"config: {config.get('method', 'unknown')})",
        )

    def get_pit_eligibility(
        self,
        returns: pd.DataFrame,
        config: dict[str, Any],
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame | None:
        """Retrieve cached PIT eligibility mask.

        Args:
            returns: Returns matrix
            config: Configuration dict (min_history_days, min_price_rows)
            start_date: Start date for cache key
            end_date: End date for cache key

        Returns:
            Cached boolean DataFrame if found and valid, None otherwise

        """
        if not self.enabled:
            return None

        dataset_hash = self._compute_dataset_hash(returns)
        config_hash = self._compute_config_hash(config)
        cache_key = self._compute_cache_key(
            dataset_hash,
            config_hash,
            start_date,
            end_date,
            "pit_eligibility",
        )

        metadata_path = self.metadata_dir / f"{cache_key}.json"
        data_path = self.data_dir / f"{cache_key}.pkl"

        if not metadata_path.exists() or not data_path.exists():
            self._stats["misses"] += 1
            logger.debug(f"Cache miss for PIT eligibility (key: {cache_key[:8]}...)")
            return None

        # Load and validate metadata
        with open(metadata_path) as f:
            metadata = CacheMetadata.from_dict(json.load(f))

        if not self._is_cache_valid(metadata):
            logger.debug(f"Cache expired for PIT eligibility (key: {cache_key[:8]}...)")
            self._stats["misses"] += 1
            return None

        # Load cached data
        try:
            with open(data_path, "rb") as f:
                cached_data = pickle.load(f)
            self._stats["hits"] += 1
            logger.info(f"Cache hit for PIT eligibility (key: {cache_key[:8]}...)")
            return cached_data
        except Exception as e:
            logger.warning(f"Failed to load cached PIT eligibility: {e}")
            self._stats["misses"] += 1
            return None

    def put_pit_eligibility(
        self,
        eligibility: pd.DataFrame,
        returns: pd.DataFrame,
        config: dict[str, Any],
        start_date: str,
        end_date: str,
    ) -> None:
        """Cache PIT eligibility mask.

        Args:
            eligibility: Boolean DataFrame to cache
            returns: Returns matrix (for hash computation)
            config: Configuration dict
            start_date: Start date for cache key
            end_date: End date for cache key

        """
        if not self.enabled:
            return

        dataset_hash = self._compute_dataset_hash(returns)
        config_hash = self._compute_config_hash(config)
        cache_key = self._compute_cache_key(
            dataset_hash,
            config_hash,
            start_date,
            end_date,
            "pit_eligibility",
        )

        metadata = CacheMetadata(
            cache_key=cache_key,
            dataset_hash=dataset_hash,
            config_hash=config_hash,
            start_date=start_date,
            end_date=end_date,
            created_at=datetime.now().isoformat(),
            entry_type="pit_eligibility",
            params=config,
        )

        # Write metadata
        metadata_path = self.metadata_dir / f"{cache_key}.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata.to_dict(), f, indent=2)

        # Write data
        data_path = self.data_dir / f"{cache_key}.pkl"
        with open(data_path, "wb") as f:
            pickle.dump(eligibility, f, protocol=pickle.HIGHEST_PROTOCOL)

        self._stats["puts"] += 1
        logger.info(f"Cached PIT eligibility (key: {cache_key[:8]}...)")

    def clear(self) -> int:
        """Clear all cache entries.

        Returns:
            Number of entries deleted

        """
        if not self.enabled:
            return 0

        count = 0
        for path in self.metadata_dir.glob("*.json"):
            path.unlink()
            count += 1
        for path in self.data_dir.glob("*.pkl"):
            path.unlink()

        logger.info(f"Cleared {count} cache entries")
        self._stats = {"hits": 0, "misses": 0, "puts": 0}
        return count

    def get_stats(self) -> dict[str, int]:
        """Get cache statistics."""
        return self._stats.copy()

    def print_stats(self) -> None:
        """Print cache statistics."""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total * 100 if total > 0 else 0
        logger.info(
            f"Cache statistics: {self._stats['hits']} hits, "
            f"{self._stats['misses']} misses, "
            f"{self._stats['puts']} puts "
            f"(hit rate: {hit_rate:.1f}%)",
        )
