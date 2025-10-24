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
import warnings
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

        Raises:
            ValueError: If cache_dir is invalid or max_cache_age_days is negative
            OSError: If cache_dir is not writable

        """
        # Validate cache_dir
        if not isinstance(cache_dir, Path):
            if isinstance(cache_dir, str):
                cache_dir = Path(cache_dir)
            else:
                raise ValueError(
                    f"cache_dir must be a Path or str, got {type(cache_dir).__name__}. "
                    "To fix: use pathlib.Path or string. "
                    "Example: cache_dir = Path('.cache/factors')",
                )

        # Validate max_cache_age_days
        if max_cache_age_days is not None and max_cache_age_days < 0:
            raise ValueError(
                f"max_cache_age_days must be >= 0, got {max_cache_age_days}. "
                "To fix: use None for no age limit or a non-negative integer. "
                "Example: max_cache_age_days=7 (expire after 7 days)",
            )

        self.cache_dir = cache_dir
        self.enabled = enabled
        self.max_cache_age_days = max_cache_age_days

        if enabled:
            # Check if cache_dir is writable
            try:
                self.metadata_dir = cache_dir / "metadata"
                self.data_dir = cache_dir / "data"
                self.metadata_dir.mkdir(parents=True, exist_ok=True)
                self.data_dir.mkdir(parents=True, exist_ok=True)

                # Test write permissions
                test_file = self.data_dir / ".write_test"
                try:
                    test_file.write_text("test")
                    test_file.unlink()
                except OSError as e:
                    raise OSError(
                        f"Cache directory {cache_dir} is not writable: {e}. "
                        "To fix: ensure the directory has write permissions or choose a different directory. "
                        "Example: cache_dir = Path('~/.cache/portfolio').expanduser()",
                    ) from e

            except OSError as e:
                logger.error(
                    f"Failed to create cache directories at {cache_dir}: {e}. "
                    "Disabling cache.",
                )
                self.enabled = False
                warnings.warn(
                    f"Cache directory {cache_dir} is not accessible. "
                    "Caching has been disabled. "
                    "Performance may be degraded for large universes (>500 assets). "
                    "To fix: check directory permissions or choose a different cache location.",
                    UserWarning,
                    stacklevel=2,
                )

        self._stats = {"hits": 0, "misses": 0, "puts": 0}

    def _compute_dataset_hash(self, data: pd.DataFrame) -> str:
        """Compute hash of dataset (returns matrix).

        Uses pandas built-in hashing for robust detection of data changes.
        Falls back to shape+columns if hashing fails (e.g., unhashable dtypes).
        """
        try:
            # Use pandas built-in hashing for robust change detection
            hash_values = pd.util.hash_pandas_object(data, index=True)
            # Combine all hashes into single hash
            combined = str(hash_values.sum()) + str(hash_values.std())
            return hashlib.sha256(combined.encode()).hexdigest()[:16]
        except (TypeError, ValueError):
            # Fallback for unhashable types
            hash_components = [
                str(data.shape),
                ",".join(sorted(data.columns.astype(str))),
                str(data.index.min()),
                str(data.index.max()),
            ]
            combined = "|".join(hash_components)
            return hashlib.sha256(combined.encode()).hexdigest()[:16]

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
        try:
            with open(metadata_path) as f:
                metadata = CacheMetadata.from_dict(json.load(f))
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(
                f"Corrupted metadata for factor scores (key: {cache_key[:8]}...): {e}",
            )
            self._stats["misses"] += 1
            return None

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

        Note:
            If write fails, logs warning and continues without caching (non-fatal).

        """
        if not self.enabled:
            # Warn if cache is disabled for large universe
            if len(returns.columns) > 500:
                warnings.warn(
                    f"Caching is disabled for a large universe ({len(returns.columns)} assets > 500). "
                    "This may lead to degraded performance on subsequent runs. "
                    "Consider enabling caching for better performance. "
                    "Example: cache = FactorCache(Path('.cache/factors'), enabled=True)",
                    UserWarning,
                    stacklevel=2,
                )
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

        metadata_path = self.metadata_dir / f"{cache_key}.json"
        data_path = self.data_dir / f"{cache_key}.pkl"

        try:
            # Write metadata
            with open(metadata_path, "w") as f:
                json.dump(metadata.to_dict(), f, indent=2)

            # Write data
            with open(data_path, "wb") as f:
                pickle.dump(scores, f, protocol=pickle.HIGHEST_PROTOCOL)

            self._stats["puts"] += 1
            logger.info(
                f"Cached factor scores (key: {cache_key[:8]}..., "
                f"config: {config.get('method', 'unknown')})",
            )
        except OSError as e:
            # Clean up partial writes
            if metadata_path.exists():
                metadata_path.unlink()
            if data_path.exists():
                data_path.unlink()

            # Log warning and continue (don't crash)
            logger.warning(
                f"Failed to cache factor scores (key: {cache_key[:8]}...): {e}. "
                "Cache write failed but continuing without caching. "
                "Possible causes: disk full, permission denied, quota exceeded. "
                "Consider: checking disk space, freeing up space, or disabling cache.",
            )
            warnings.warn(
                "Cache write failed. Continuing without caching. "
                "Performance may be degraded on subsequent runs. "
                "Check logs for details.",
                UserWarning,
                stacklevel=2,
            )
            # Don't raise - continue without caching

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
        try:
            with open(metadata_path) as f:
                metadata = CacheMetadata.from_dict(json.load(f))
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(
                f"Corrupted metadata for PIT eligibility (key: {cache_key[:8]}...): {e}",
            )
            self._stats["misses"] += 1
            return None

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

        Note:
            If write fails, logs warning and continues without caching (non-fatal).

        """
        if not self.enabled:
            # Warn if cache is disabled for large universe (only for eligibility, not scores)
            # Skip warning here since it's already issued by put_factor_scores
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

        metadata_path = self.metadata_dir / f"{cache_key}.json"
        data_path = self.data_dir / f"{cache_key}.pkl"

        try:
            # Write metadata
            with open(metadata_path, "w") as f:
                json.dump(metadata.to_dict(), f, indent=2)

            # Write data
            with open(data_path, "wb") as f:
                pickle.dump(eligibility, f, protocol=pickle.HIGHEST_PROTOCOL)

            self._stats["puts"] += 1
            logger.info(f"Cached PIT eligibility (key: {cache_key[:8]}...)")
        except OSError as e:
            # Clean up partial writes
            if metadata_path.exists():
                metadata_path.unlink()
            if data_path.exists():
                data_path.unlink()

            # Log warning and continue (don't crash)
            logger.warning(
                f"Failed to cache PIT eligibility (key: {cache_key[:8]}...): {e}. "
                "Cache write failed but continuing without caching. "
                "Possible causes: disk full, permission denied, quota exceeded. "
                "Consider: checking disk space, freeing up space, or disabling cache.",
            )
            warnings.warn(
                "Cache write failed. Continuing without caching. "
                "Performance may be degraded on subsequent runs. "
                "Check logs for details.",
                UserWarning,
                stacklevel=2,
            )
            # Don't raise - continue without caching

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

    def reset_stats(self) -> None:
        """Reset cache statistics to zero.

        Useful for testing or when you want to track statistics for a specific
        time period without clearing the cache itself.
        """
        self._stats = {"hits": 0, "misses": 0, "puts": 0}

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
