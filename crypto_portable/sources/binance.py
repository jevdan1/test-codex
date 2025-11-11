"""Binance source adapter."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Iterable, List

import httpx
import pandas as pd

from ..config import SourceDefinition
from .base import SourceAdapter

LOGGER = logging.getLogger(__name__)

BINANCE_ENDPOINT = "/fapi/v1/continuousKlines"


class BinanceSource(SourceAdapter):
    """Fetch one-second candles from Binance Futures aggregate klines."""

    def __init__(self, definition: SourceDefinition) -> None:
        self.definition = definition
        self.base_url = definition.base_url.rstrip("/")
        self.client = httpx.Client(timeout=30)

    def _request(self, params: dict) -> List[List[float]]:
        url = f"{self.base_url}{BINANCE_ENDPOINT}"
        response = self.client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            raise ValueError(f"Unexpected response: {data}")
        return data

    def fetch_candles(
        self,
        pair: str,
        start_ms: int,
        end_ms: int,
        limit: int = 1000,
    ) -> Iterable[pd.DataFrame]:
        # Binance does not natively provide one-second candles; this call approximates
        # using continuous contract klines with interval "1m" and expands. Users may
        # swap the adapter for a true one-second source when available.
        params = {
            "pair": pair,
            "contractType": "PERPETUAL",
            "interval": "1m",
            "startTime": start_ms,
            "endTime": end_ms,
            "limit": limit,
        }
        raw = self._request(params)
        rows = []
        for item in raw:
            open_time = int(item[0])
            close_time = int(item[6])
            rows.append(
                {
                    "open_time_ms": open_time,
                    "open": float(item[1]),
                    "high": float(item[2]),
                    "low": float(item[3]),
                    "close": float(item[4]),
                    "volume": float(item[5]),
                    "close_time_ms": close_time,
                    "quote_volume": float(item[7]),
                    "trades": int(item[8]),
                    "taker_buy_volume": float(item[9]),
                    "taker_buy_quote": float(item[10]),
                }
            )
        frame = pd.DataFrame(rows)
        if frame.empty:
            return []
        frame.sort_values("open_time_ms", inplace=True)
        # Expand to pseudo one-second candles by forward-filling values.
        expanded_frames: List[pd.DataFrame] = []
        for _, row in frame.iterrows():
            base_time = int(row["open_time_ms"])
            seconds = []
            for offset in range(60):
                timestamp = base_time + offset * 1000
                if timestamp > end_ms:
                    break
                seconds.append({**row.to_dict(), "open_time_ms": timestamp})
            expanded_frames.append(pd.DataFrame(seconds))
        merged = pd.concat(expanded_frames, ignore_index=True)
        mask = (merged["open_time_ms"] >= start_ms) & (merged["open_time_ms"] <= end_ms)
        yield merged.loc[mask, :].reset_index(drop=True)

    def last_closed_second(self) -> datetime:
        now = datetime.now(tz=timezone.utc)
        closed = now.replace(microsecond=0)
        return closed


def build_source(definition: SourceDefinition) -> SourceAdapter:
    return BinanceSource(definition)
