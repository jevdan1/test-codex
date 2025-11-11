"""Indicator computation stubs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable

import numpy as np
import pandas as pd


@dataclass(slots=True)
class Indicator:
    name: str
    window_sec: int
    expression: str
    inputs: list[str]
    compute: Callable[[pd.DataFrame], pd.Series]


def rolling_sma(column: str, window: int) -> Callable[[pd.DataFrame], pd.Series]:
    def _func(frame: pd.DataFrame) -> pd.Series:
        return frame[column].rolling(window=window, min_periods=window).mean()

    return _func


def register_default_indicators() -> Dict[str, Indicator]:
    return {
        "SMA_60": Indicator(
            name="SMA_60",
            window_sec=60,
            expression="SMA(close, 60)",
            inputs=["close"],
            compute=rolling_sma("close", 60),
        )
    }


def compute_indicators(frame: pd.DataFrame, indicators: Iterable[Indicator]) -> pd.DataFrame:
    result = frame.copy()
    for indicator in indicators:
        result[indicator.name] = indicator.compute(frame)
    return result
