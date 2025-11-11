"""Ingestion orchestration."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd

from .config import ConfigBundle
from .paths import PortablePaths
from .storage.manifest import Manifest, ManifestEntry, load_manifest, save_manifest
from .storage.parquet_writer import append_batches
from .sources.base import SourceAdapter
from .sources import binance

LOGGER = logging.getLogger(__name__)

SOURCE_BUILDERS = {
    "binance": binance.build_source,
}


@dataclass(slots=True)
class StatusRow:
    date: str
    rows: int
    first_ms: int
    last_ms: int
    complete: bool
    part_until: Optional[str]
    gaps: List[Dict[str, int]]

    @property
    def state(self) -> str:
        return "complete" if self.complete else "partial"


class IngestionManager:
    def __init__(self, paths: PortablePaths, config: ConfigBundle) -> None:
        self.paths = paths
        self.config = config
        self._adapters: Dict[str, SourceAdapter] = {}

    def _get_source(self, source_id: str) -> SourceAdapter:
        if source_id in self._adapters:
            return self._adapters[source_id]
        definition = self.config.sources.get(source_id)
        if not definition:
            raise ValueError(f"Unknown source: {source_id}")
        builder = SOURCE_BUILDERS.get(source_id)
        if not builder:
            raise ValueError(f"No builder registered for {source_id}")
        adapter = builder(definition)
        self._adapters[source_id] = adapter
        return adapter

    def _load_manifest(self, pair: str, granularity: str) -> Manifest:
        manifest_path = self.paths.manifest_path(pair, granularity)
        return load_manifest(manifest_path, pair, granularity)

    def _save_manifest(self, manifest: Manifest) -> None:
        manifest_path = self.paths.manifest_path(manifest.pair, manifest.granularity)
        save_manifest(manifest_path, manifest)

    def _partition_dir(self, pair: str, granularity: str, timestamp_ms: int) -> Path:
        return self.paths.partition_path(pair, granularity, timestamp_ms)

    def _day_bounds(self, day: date) -> tuple[int, int]:
        start = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
        end = start + timedelta(days=1) - timedelta(milliseconds=1000)
        return int(start.timestamp() * 1000), int(end.timestamp() * 1000)

    def _fetch_batches(
        self,
        adapter: SourceAdapter,
        pair: str,
        start_ms: int,
        end_ms: int,
    ) -> Iterable[pd.DataFrame]:
        step = 1000 * 1000
        cursor = start_ms
        while cursor <= end_ms:
            batch_end = min(cursor + step - 1000, end_ms)
            for frame in adapter.fetch_candles(pair, cursor, batch_end):
                yield frame
            cursor = batch_end + 1000

    def resume_fill_gaps(self, source_id: str, pair: str, granularity: str = "1s") -> List[ManifestEntry]:
        adapter = self._get_source(source_id)
        manifest = self._load_manifest(pair, granularity)
        last_closed = adapter.last_closed_second()
        last_closed_ms = int(last_closed.timestamp() * 1000)
        entries: List[ManifestEntry] = []

        today = datetime.now(tz=timezone.utc).date()
        yesterday = today - timedelta(days=1)
        for day in (yesterday, today):
            start_ms, end_ms = self._day_bounds(day)
            batches = list(self._fetch_batches(adapter, pair, start_ms, min(end_ms, last_closed_ms)))
            if not batches:
                continue
            partition_dir = self._partition_dir(pair, granularity, start_ms)
            entries.extend(append_batches(batches, pair, granularity, partition_dir, last_closed, manifest))
        self._save_manifest(manifest)
        return entries

    def backfill_range(
        self,
        source_id: str,
        pair: str,
        start_date: str,
        end_date: str,
        granularity: str = "1s",
    ) -> List[ManifestEntry]:
        adapter = self._get_source(source_id)
        manifest = self._load_manifest(pair, granularity)
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        entries: List[ManifestEntry] = []
        current = start
        last_closed = adapter.last_closed_second()
        last_closed_ms = int(last_closed.timestamp() * 1000)
        while current <= end:
            start_ms, end_ms = self._day_bounds(current)
            batches = list(self._fetch_batches(adapter, pair, start_ms, min(end_ms, last_closed_ms)))
            if batches:
                partition_dir = self._partition_dir(pair, granularity, start_ms)
                entries.extend(append_batches(batches, pair, granularity, partition_dir, last_closed, manifest))
            current += timedelta(days=1)
        self._save_manifest(manifest)
        return entries

    def rebuild_day(
        self,
        source_id: str,
        pair: str,
        day: str,
        granularity: str = "1s",
    ) -> List[ManifestEntry]:
        adapter = self._get_source(source_id)
        manifest = self._load_manifest(pair, granularity)
        target = date.fromisoformat(day)
        start_ms, end_ms = self._day_bounds(target)
        partition_dir = self._partition_dir(pair, granularity, start_ms)
        if partition_dir.exists():
            for item in partition_dir.glob(f"day={target:%d}*.parquet"):
                item.unlink()
        batches = list(self._fetch_batches(adapter, pair, start_ms, end_ms))
        entries = append_batches(batches, pair, granularity, partition_dir, adapter.last_closed_second(), manifest)
        self._save_manifest(manifest)
        return entries

    def status(
        self,
        source_id: str,
        pair: str,
        start_date: Optional[str],
        end_date: Optional[str],
        granularity: str = "1s",
    ) -> List[StatusRow]:
        manifest = self._load_manifest(pair, granularity)
        entries: List[StatusRow] = []
        if not manifest.entries:
            return entries
        keys = sorted(manifest.entries.keys())
        if start_date:
            keys = [k for k in keys if k >= start_date]
        if end_date:
            keys = [k for k in keys if k <= end_date]
        for key in keys:
            entry = manifest.entries[key]
            entries.append(
                StatusRow(
                    date=key,
                    rows=entry.rows,
                    first_ms=entry.first_ms,
                    last_ms=entry.last_ms,
                    complete=entry.complete,
                    part_until=entry.part_until,
                    gaps=entry.gaps,
                )
            )
        return entries
