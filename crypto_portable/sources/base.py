"""Source adapter interfaces."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Iterable

import pandas as pd


class SourceAdapter(ABC):
    """Base class for data source adapters."""

    @abstractmethod
    def fetch_candles(
        self,
        pair: str,
        start_ms: int,
        end_ms: int,
        limit: int = 1000,
    ) -> Iterable[pd.DataFrame]:
        """Yield candle data frames inclusive of the requested range."""

    @abstractmethod
    def last_closed_second(self) -> datetime:
        """Return the latest fully closed second for the source."""
