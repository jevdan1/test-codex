"""Chart viewer dialog."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from PySide6 import QtCore, QtWidgets

from ..config import ConfigBundle
from ..paths import PortablePaths


class ChartViewerDialog(QtWidgets.QDialog):
    def __init__(self, paths: PortablePaths, config: ConfigBundle, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.paths = paths
        self.config = config
        self.setWindowTitle("Chart Viewer")
        self.resize(1024, 768)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QHBoxLayout(self)

        left_panel = QtWidgets.QGroupBox("Controls")
        left_layout = QtWidgets.QFormLayout(left_panel)
        self.source_label = QtWidgets.QLabel("Source")
        self.pairs_list = QtWidgets.QListWidget()
        self.pairs_list.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        self.add_pair_button = QtWidgets.QPushButton("+")
        self.from_edit = QtWidgets.QDateTimeEdit(datetime.utcnow())
        self.from_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.to_edit = QtWidgets.QDateTimeEdit(datetime.utcnow())
        self.to_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.lock_range = QtWidgets.QCheckBox("Lock range")
        self.lookback_spin = QtWidgets.QSpinBox()
        self.lookback_spin.setRange(60, 86_400)
        self.lookback_spin.setValue(900)
        self.reload_button = QtWidgets.QPushButton("Reload data")
        self.aggregation_combo = QtWidgets.QComboBox()
        self.aggregation_combo.addItems(["Show raw 1s", "Aggregate 1m", "Aggregate 5m", "Aggregate 1h"])
        self.sync_y_checkbox = QtWidgets.QCheckBox("Sync Y-axis for all pairs")
        self.indicators_list = QtWidgets.QListWidget()
        for indicator in self.config.indicators:
            item = QtWidgets.QListWidgetItem(indicator.name)
            item.setCheckState(QtCore.Qt.Unchecked)
            self.indicators_list.addItem(item)
        self.predictability_checkbox = QtWidgets.QCheckBox("Predictability band")
        self.predictability_window = QtWidgets.QSpinBox()
        self.predictability_window.setRange(60, 86_400)
        self.predictability_window.setValue(300)
        self.predictability_metric = QtWidgets.QComboBox()
        self.predictability_metric.addItems(["R2", "|slope|/noise", "volatility_gap"])
        self.thresholds_edit = QtWidgets.QLineEdit("g=0.8,y=0.6")
        self.export_csv_button = QtWidgets.QPushButton("Export CSV")
        self.export_png_button = QtWidgets.QPushButton("Export image")

        sources_path = self.paths.config_dir / "sources.yaml"
        source_names = list(self.config.sources.values())
        if source_names:
            self.source_label.setText(source_names[0].name)
        self.source_label.setToolTip(f"Edit sources in: {sources_path}")
        left_layout.addRow("Source", self.source_label)
        for pair in self.config.pair_shortlist:
            item = QtWidgets.QListWidgetItem(pair)
            item.setCheckState(QtCore.Qt.Unchecked)
            self.pairs_list.addItem(item)
        pairs_path = self.paths.config_dir / "pipelines.yaml"
        self.pairs_list.setToolTip(f"Pairs shortlist is defined in: {pairs_path}")
        left_layout.addRow("Pairs", self.pairs_list)
        left_layout.addRow("Add pair", self.add_pair_button)
        left_layout.addRow("From", self.from_edit)
        left_layout.addRow("To", self.to_edit)
        left_layout.addRow(self.lock_range)
        left_layout.addRow("Lookback (sec)", self.lookback_spin)
        left_layout.addRow(self.reload_button)
        left_layout.addRow("Display", self.aggregation_combo)
        left_layout.addRow(self.sync_y_checkbox)
        left_layout.addRow("Indicators", self.indicators_list)
        left_layout.addRow(self.predictability_checkbox)
        left_layout.addRow("Window", self.predictability_window)
        left_layout.addRow("Metric", self.predictability_metric)
        left_layout.addRow("Thresholds", self.thresholds_edit)
        left_layout.addRow(self.export_csv_button)
        left_layout.addRow(self.export_png_button)

        layout.addWidget(left_panel, 0)

        placeholder = QtWidgets.QLabel("Chart rendering will be provided by a future update.")
        placeholder.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(placeholder, 1)

        right_panel = QtWidgets.QGroupBox("Library overview")
        right_layout = QtWidgets.QVBoxLayout(right_panel)
        self.library_table = QtWidgets.QTableWidget(0, 5)
        self.library_table.setHorizontalHeaderLabels(["Date", "Rows", "Complete", "Part until", "Gaps"])
        self.library_table.horizontalHeader().setStretchLastSection(True)
        right_layout.addWidget(self.library_table)
        self.open_day_button = QtWidgets.QPushButton("Open day")
        self.export_day_button = QtWidgets.QPushButton("Export day")
        self.jump_day_button = QtWidgets.QPushButton("Jump to day")
        right_layout.addWidget(self.open_day_button)
        right_layout.addWidget(self.export_day_button)
        right_layout.addWidget(self.jump_day_button)
        layout.addWidget(right_panel, 0)
