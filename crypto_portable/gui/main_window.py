"""Main GUI window."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtWidgets

from ..config import ConfigBundle
from ..ingestion import IngestionManager
from ..paths import PortablePaths
from .chart_viewer import ChartViewerDialog
from .utils import BusyContext

LOGGER = logging.getLogger(__name__)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, paths: PortablePaths, config: ConfigBundle, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.paths = paths
        self.config = config
        self.manager = IngestionManager(paths, config)
        self.busy = BusyContext()
        self.busy.busy_changed.connect(self._on_busy_changed)
        self._build_ui()
        self._populate_sources()

    def _build_ui(self) -> None:
        self.setWindowTitle("Crypto Data Collector")
        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)
        layout.setSpacing(12)

        # Top bar
        top_group = QtWidgets.QGroupBox("Top bar")
        top_layout = QtWidgets.QHBoxLayout(top_group)
        self.library_path_edit = QtWidgets.QLineEdit(str(self.paths.library_dir))
        browse_button = QtWidgets.QPushButton("Browse…")
        browse_button.clicked.connect(self._choose_library)
        self.summary_label = QtWidgets.QLabel("Library not scanned yet")
        top_layout.addWidget(QtWidgets.QLabel("Library:"))
        top_layout.addWidget(self.library_path_edit)
        top_layout.addWidget(browse_button)
        top_layout.addWidget(self.summary_label)
        layout.addWidget(top_group)

        # Source and pair
        source_group = QtWidgets.QGroupBox("Source and Pair")
        source_layout = QtWidgets.QGridLayout(source_group)
        self.source_combo = QtWidgets.QComboBox()
        self.pair_combo = QtWidgets.QComboBox()
        self.pair_combo.setEditable(True)
        gear_button = QtWidgets.QPushButton("⚙")
        gear_button.clicked.connect(self._edit_pairs)
        self.just_update_checkbox = QtWidgets.QCheckBox("Just update library (no chart)")
        source_layout.addWidget(QtWidgets.QLabel("Source:"), 0, 0)
        source_layout.addWidget(self.source_combo, 0, 1)
        source_layout.addWidget(QtWidgets.QLabel("Pair:"), 1, 0)
        source_layout.addWidget(self.pair_combo, 1, 1)
        source_layout.addWidget(gear_button, 1, 2)
        source_layout.addWidget(self.just_update_checkbox, 2, 0, 1, 3)
        layout.addWidget(source_group)

        # Period controls
        period_group = QtWidgets.QGroupBox("Period")
        period_layout = QtWidgets.QGridLayout(period_group)
        self.period_buttons = QtWidgets.QButtonGroup(self)
        self.period_today = QtWidgets.QRadioButton("Today")
        self.period_yesterday = QtWidgets.QRadioButton("Yesterday")
        self.period_last_n = QtWidgets.QRadioButton("Last N days")
        self.period_custom = QtWidgets.QRadioButton("Custom range")
        self.period_buttons.addButton(self.period_today)
        self.period_buttons.addButton(self.period_yesterday)
        self.period_buttons.addButton(self.period_last_n)
        self.period_buttons.addButton(self.period_custom)
        self.period_today.setChecked(True)
        self.last_n_spin = QtWidgets.QSpinBox()
        self.last_n_spin.setRange(1, 365)
        self.last_n_spin.setValue(7)
        self.from_datetime = QtWidgets.QDateTimeEdit(datetime.utcnow())
        self.from_datetime.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.to_datetime = QtWidgets.QDateTimeEdit(datetime.utcnow())
        self.to_datetime.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.lock_range_checkbox = QtWidgets.QCheckBox("Lock range")
        self.update_current_checkbox = QtWidgets.QCheckBox("Update current day first")
        period_layout.addWidget(self.period_today, 0, 0)
        period_layout.addWidget(self.period_yesterday, 0, 1)
        period_layout.addWidget(self.period_last_n, 1, 0)
        period_layout.addWidget(self.last_n_spin, 1, 1)
        period_layout.addWidget(self.period_custom, 2, 0)
        period_layout.addWidget(QtWidgets.QLabel("From UTC"), 3, 0)
        period_layout.addWidget(self.from_datetime, 3, 1)
        period_layout.addWidget(QtWidgets.QLabel("To UTC"), 4, 0)
        period_layout.addWidget(self.to_datetime, 4, 1)
        period_layout.addWidget(self.lock_range_checkbox, 5, 0)
        period_layout.addWidget(self.update_current_checkbox, 5, 1)
        layout.addWidget(period_group)

        # Action controls
        action_group = QtWidgets.QGroupBox("Action")
        action_layout = QtWidgets.QVBoxLayout(action_group)
        self.action_buttons = QtWidgets.QButtonGroup(self)
        self.resume_radio = QtWidgets.QRadioButton("Resume/Fill gaps")
        self.backfill_radio = QtWidgets.QRadioButton("Backfill")
        self.rebuild_radio = QtWidgets.QRadioButton("Rebuild day")
        self.status_radio = QtWidgets.QRadioButton("Status only")
        self.resume_radio.setChecked(True)
        for button in (self.resume_radio, self.backfill_radio, self.rebuild_radio, self.status_radio):
            self.action_buttons.addButton(button)
            action_layout.addWidget(button)
        self.autofill_checkbox = QtWidgets.QCheckBox("Autofill gaps (try API)")
        action_layout.addWidget(self.autofill_checkbox)
        layout.addWidget(action_group)

        # Buttons row
        buttons_layout = QtWidgets.QHBoxLayout()
        self.run_button = QtWidgets.QPushButton("Run")
        self.run_button.clicked.connect(self._run_action)
        self.open_chart_button = QtWidgets.QPushButton("Open chart")
        self.open_chart_button.clicked.connect(self._open_chart)
        self.export_button = QtWidgets.QPushButton("Export")
        self.export_button.clicked.connect(self._export)
        self.open_exports_button = QtWidgets.QPushButton("Open exports")
        self.open_exports_button.clicked.connect(lambda: self._open_path(self.paths.exports_dir))
        self.open_library_button = QtWidgets.QPushButton("Open library")
        self.open_library_button.clicked.connect(lambda: self._open_path(self.paths.library_dir))
        buttons_layout.addWidget(self.run_button)
        buttons_layout.addWidget(self.open_chart_button)
        buttons_layout.addWidget(self.export_button)
        buttons_layout.addWidget(self.open_exports_button)
        buttons_layout.addWidget(self.open_library_button)
        layout.addLayout(buttons_layout)

        # Bottom area
        bottom_group = QtWidgets.QGroupBox("Activity")
        bottom_layout = QtWidgets.QVBoxLayout(bottom_group)
        self.log_widget = QtWidgets.QPlainTextEdit()
        self.log_widget.setReadOnly(True)
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.status_label = QtWidgets.QLabel("Ready")
        bottom_layout.addWidget(self.log_widget)
        bottom_layout.addWidget(self.progress_bar)
        bottom_layout.addWidget(self.status_label)
        layout.addWidget(bottom_group)

        layout.addStretch()
        self.setCentralWidget(central)

    def _populate_sources(self) -> None:
        self.source_combo.clear()
        for source_id, source in self.config.sources.items():
            self.source_combo.addItem(source.name, source_id)
        if self.source_combo.count():
            self.source_combo.setCurrentIndex(0)

    def _choose_library(self) -> None:
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Select library", str(self.paths.library_dir))
        if directory:
            self.library_path_edit.setText(directory)

    def _edit_pairs(self) -> None:
        QtWidgets.QMessageBox.information(self, "Pairs", "Pair shortlist editing is not yet implemented.")

    def _open_path(self, path: Path) -> None:
        QtGui = QtWidgets.QDesktopWidget  # type: ignore[attr-defined]
        QtGui()
        QtWidgets.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(path)))

    def _run_action(self) -> None:
        source_id = self.source_combo.currentData()
        pair = self.pair_combo.currentText().strip()
        if not source_id or not pair:
            QtWidgets.QMessageBox.warning(self, "Missing data", "Select a source and enter a pair symbol.")
            return
        self._append_log(f"Running {self._selected_action()} for {pair}")
        with self.busy:
            try:
                if self.resume_radio.isChecked():
                    self.manager.resume_fill_gaps(source_id, pair)
                elif self.backfill_radio.isChecked():
                    start = self.from_datetime.date().toString("yyyy-MM-dd")
                    end = self.to_datetime.date().toString("yyyy-MM-dd")
                    self.manager.backfill_range(source_id, pair, start, end)
                elif self.rebuild_radio.isChecked():
                    day = self.from_datetime.date().toString("yyyy-MM-dd")
                    self.manager.rebuild_day(source_id, pair, day)
                else:
                    status_rows = self.manager.status(source_id, pair, None, None)
                    self._append_log("Status rows: " + str(len(status_rows)))
            except Exception as exc:  # pragma: no cover - GUI feedback
                LOGGER.exception("Action failed")
                QtWidgets.QMessageBox.critical(self, "Error", str(exc))
        self._append_log("Action complete")

    def _selected_action(self) -> str:
        if self.resume_radio.isChecked():
            return "Resume/Fill gaps"
        if self.backfill_radio.isChecked():
            return "Backfill"
        if self.rebuild_radio.isChecked():
            return "Rebuild day"
        return "Status"

    def _open_chart(self) -> None:
        dialog = ChartViewerDialog(self.paths, self.config, self)
        dialog.exec()

    def _export(self) -> None:
        QtWidgets.QMessageBox.information(self, "Export", "CSV export will be implemented in a future version.")

    def _append_log(self, message: str) -> None:
        self.log_widget.appendPlainText(message)

    def _on_busy_changed(self, busy: bool) -> None:
        self.status_label.setText("Fetching" if busy else "Ready")
        self.progress_bar.setRange(0, 0 if busy else 1)


class QtLogHandler(logging.Handler):
    def __init__(self, widget: QtWidgets.QPlainTextEdit) -> None:
        super().__init__()
        self.widget = widget

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - GUI only
        msg = self.format(record)
        self.widget.appendPlainText(msg)


def run_gui(paths: PortablePaths, config: ConfigBundle) -> None:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MainWindow(paths, config)
    handler = QtLogHandler(window.log_widget)
    logging.getLogger().addHandler(handler)
    window.show()
    app.exec()
