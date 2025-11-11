"""Utilities for working with the portable folder layout."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class PortablePaths:
    base_dir: Path

    def __post_init__(self) -> None:
        self.base_dir = self.base_dir.resolve()

    @property
    def config_dir(self) -> Path:
        return self.base_dir / "config"

    @property
    def library_dir(self) -> Path:
        return self.base_dir / "library"

    @property
    def exports_dir(self) -> Path:
        return self.base_dir / "exports"

    @property
    def logs_dir(self) -> Path:
        return self.base_dir / "logs"

    def ensure_portable_layout(self, library_dir: Path | None = None) -> None:
        config_dir = self.config_dir
        config_dir.mkdir(parents=True, exist_ok=True)
        (self.base_dir / "library").mkdir(parents=True, exist_ok=True)
        (self.base_dir / "exports").mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        lib_dir = library_dir or self.library_dir
        (lib_dir / "raw").mkdir(parents=True, exist_ok=True)
        (lib_dir / "features").mkdir(parents=True, exist_ok=True)
        (lib_dir / "manifests").mkdir(parents=True, exist_ok=True)

    def resolve_library(self, library_dir: Path | None = None) -> Path:
        if library_dir is None:
            return self.library_dir
        return library_dir

    def partition_path(
        self,
        pair: str,
        granularity: str,
        timestamp_ms: int,
        library_dir: Path | None = None,
    ) -> Path:
        from datetime import datetime, timezone

        dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
        lib_dir = self.resolve_library(library_dir)
        return (
            lib_dir
            / "raw"
            / f"pair={pair}"
            / f"gran={granularity}"
            / f"year={dt:%Y}"
            / f"month={dt:%m}"
        )

    def manifest_path(self, pair: str, granularity: str, library_dir: Path | None = None) -> Path:
        lib_dir = self.resolve_library(library_dir)
        return lib_dir / "manifests" / f"{pair}_{granularity}.json"
