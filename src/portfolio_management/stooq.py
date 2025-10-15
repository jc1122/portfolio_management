from __future__ import annotations

import logging
import os
from pathlib import Path

from .models import StooqFile
from .utils import _run_in_parallel

LOGGER = logging.getLogger(__name__)

# Constants for path parsing
DAILY_INDEX_OFFSET = 1
DAILY_CATEGORY_OFFSET = 2
MIN_PARTS_FOR_CATEGORY = 2


def _collect_relative_paths(base_dir: Path, max_workers: int) -> list[str]:
    """Collect relative TXT file paths within the Stooq tree using parallel os.walk scanning."""

    def _scan_directory(start_dir: Path) -> list[str]:
        local_paths: list[str] = []
        try:
            for root, dirs, files in os.walk(start_dir, followlinks=False):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for file_name in files:
                    if file_name.startswith(".") or not file_name.lower().endswith(
                        ".txt",
                    ):
                        continue
                    full_path = Path(root) / file_name
                    try:
                        relative = full_path.relative_to(base_dir)
                    except ValueError:
                        continue
                    if any(part.startswith(".") for part in relative.parts):
                        continue
                    local_paths.append(relative.as_posix())
        except OSError as exc:
            LOGGER.warning("Unable to scan %s: %s", start_dir, exc)
        return local_paths

    try:
        top_level_entries = [
            entry for entry in base_dir.iterdir() if not entry.name.startswith(".")
        ]
    except OSError as exc:
        LOGGER.warning("Unable to iterate %s: %s", base_dir, exc)
        return []

    rel_paths = [
        entry.relative_to(base_dir).as_posix()
        for entry in top_level_entries
        if entry.is_file() and entry.suffix.lower() == ".txt"
    ]
    top_level_dirs = [entry for entry in top_level_entries if entry.is_dir()]

    results = _run_in_parallel(
        _scan_directory,
        [(d,) for d in top_level_dirs],
        max_workers,
    )
    for result in results:
        rel_paths.extend(result)

    rel_paths.sort()
    return rel_paths


def derive_region_and_category(rel_path: Path) -> tuple[str, str]:
    """Infer region and category from the relative path within the Stooq tree."""
    parts = list(rel_path.parts)
    region = ""
    category = ""
    if "daily" in parts:
        idx = parts.index("daily")
        if idx + DAILY_INDEX_OFFSET < len(parts):
            region = parts[idx + DAILY_INDEX_OFFSET]
        if idx + DAILY_CATEGORY_OFFSET < len(parts):
            category = "/".join(parts[idx + DAILY_CATEGORY_OFFSET : -1])
    else:
        if parts:
            region = parts[0]
        if len(parts) > MIN_PARTS_FOR_CATEGORY:
            category = "/".join(parts[1:-1])
    return region, category


def build_stooq_index(data_dir: Path, *, max_workers: int = 1) -> list[StooqFile]:
    """Create an index describing all unpacked Stooq price files."""
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    relative_paths = _collect_relative_paths(data_dir, max_workers)
    relative_paths.sort()

    entries = [
        StooqFile(
            ticker=(rel_path := Path(rel_path_str)).stem.upper(),
            stem=rel_path.stem.upper(),
            rel_path=rel_path_str,
            region=(region_category := derive_region_and_category(rel_path))[0],
            category=region_category[1],
        )
        for rel_path_str in relative_paths
    ]
    LOGGER.info("Indexed %s Stooq files", len(entries))
    return entries
