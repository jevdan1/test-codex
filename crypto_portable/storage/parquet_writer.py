"""Utilities for writing parquet files."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .manifest import Manifest, ManifestEntry, save_manifest

LOGGER = logging.getLogger(__name__)

SCHEMA_COLUMNS = [
    "open_time_ms",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time_ms",
    "quote_volume",
    "trades",
    "taker_buy_volume",
    "taker_buy_quote",
]


def _validate_timestamps(frame: pd.DataFrame) -> None:
    deltas = np.diff(frame["open_time_ms"].to_numpy())
    if not np.all(deltas == 1000):
        raise ValueError("Timestamps must increase by exactly 1000 ms")


def dataframe_to_table(frame: pd.DataFrame) -> pa.Table:
    _validate_timestamps(frame)
    return pa.Table.from_pandas(frame, preserve_index=False)


def write_daily_parquet(
    table: pa.Table,
    output_dir: Path,
    day: datetime,
    complete: bool,
    manifest: Manifest,
    zstd_level: int = 4,
) -> ManifestEntry:
    day_str = f"day={day:%d}"
    part_name = f"{day_str}.parquet.part"
    final_name = f"{day_str}.parquet" if complete else f"{day_str}__PART_until_{day:%Hh%Mm%Ss}.parquet"
    output_dir.mkdir(parents=True, exist_ok=True)
    part_path = output_dir / part_name
    final_path = output_dir / final_name

    pq.write_table(
        table,
        part_path,
        compression="zstd",
        compression_level=zstd_level,
        use_dictionary=False,
    )
    part_path.replace(final_path)

    frame = table.to_pandas()
    entry = ManifestEntry(
        date=day.date(),
        rows=len(frame),
        first_ms=int(frame["open_time_ms"].iloc[0]),
        last_ms=int(frame["open_time_ms"].iloc[-1]),
        complete=complete,
        part_until=None if complete else day.strftime("%H:%M:%S"),
        gaps=[],
    )
    manifest.update_entry(entry)
    save_manifest(output_dir.parents[2] / "manifests" / f"{manifest.pair}_{manifest.granularity}.json", manifest)
    LOGGER.info("Wrote %s rows to %s", len(frame), final_path)
    return entry


def append_batches(
    batches: Iterable[pd.DataFrame],
    pair: str,
    granularity: str,
    output_dir: Path,
    last_closed: datetime,
    manifest: Manifest,
) -> List[ManifestEntry]:
    entries: List[ManifestEntry] = []
    for frame in batches:
        frame = frame.sort_values("open_time_ms").reset_index(drop=True)
        table = dataframe_to_table(frame[SCHEMA_COLUMNS])
        day = datetime.fromtimestamp(frame["open_time_ms"].iloc[-1] / 1000, tz=timezone.utc)
        complete = day.hour == 23 and day.minute == 59 and day.second == 59 and last_closed >= day
        entries.append(write_daily_parquet(table, output_dir, day, complete, manifest))
    return entries
