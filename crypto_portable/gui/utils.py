"""Shared GUI helpers."""
from __future__ import annotations

from PySide6 import QtCore


class BusyContext(QtCore.QObject):
    """Simple busy-state context manager for the status bar."""

    busy_changed = QtCore.Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        self._busy = False

    def __enter__(self) -> "BusyContext":
        self.set_busy(True)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.set_busy(False)

    def set_busy(self, value: bool) -> None:
        if self._busy != value:
            self._busy = value
            self.busy_changed.emit(value)
