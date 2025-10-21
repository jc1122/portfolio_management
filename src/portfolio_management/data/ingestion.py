"""Stooq data ingestion and indexing."""

from __future__ import annotations

import logging
from pathlib import Path

from portfolio_management.data.models import StooqFile

LOGGER = logging.getLogger(__name__)


def build_stooq_index(
    data_dir: Path,
    max_workers: int | None = None,
) -> list[StooqFile]:
    """Build an index of available Stooq price files.
    
    Args:
        data_dir: Root directory containing unpacked Stooq data
        max_workers: Maximum number of threads for directory scanning
        
    Returns:
        List of StooqFile entries describing available price files
    """
    # This is a stub implementation that needs to be properly implemented
    # The actual implementation should scan the directory tree and build
    # an index of all available .txt price files
    raise NotImplementedError(
        "build_stooq_index needs to be implemented - missing from grafted repository"
    )
