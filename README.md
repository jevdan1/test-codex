# Portable Crypto Data Collector and Chart Viewer

This repository provides a reference implementation of a portable crypto market data toolkit. The application is designed to collect one-second candle data, store it in a USB-friendly folder layout, and deliver a Qt-based user interface for managing ingestion, exports, and chart analysis.

## Features

- **Portable layout** – all assets live under a single directory with sub-folders for `library/`, `config/`, `exports/`, and `logs/`.
- **Config-driven sources** – add or modify REST/WebSocket sources via YAML without changing code.
- **Daily Parquet storage** – data is persisted as ZSTD-compressed Parquet files with Hive-style partitions.
- **Manifest tracking** – per-pair manifests summarize daily completeness and highlight gaps.
- **GUI management console** – PySide6 interface to trigger resume, backfill, rebuild, and status operations.
- **Chart viewer skeleton** – dedicated dialog prepared for multi-pair visualization, indicator overlays, and exports.
- **Cross-platform packaging hooks** – ready for PyInstaller (Windows) and Linux AppImage/zip workflows.

## Getting Started

1. Create a virtual environment and install dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```

2. Ensure the portable layout exists. When the app starts it will create missing folders automatically, but you can also prepare them manually:

   ```bash
   python -m crypto_portable.app --base-dir CryptoPortable --mode status --pair BTCUSDT --source binance
   ```

3. Launch the graphical interface:

   ```bash
   python -m crypto_portable.app --gui --base-dir CryptoPortable
   ```

   The GUI presents controls for selecting sources, managing periods, launching ingestion tasks, and opening the chart viewer.

## Configuration

The application reads YAML files from `config/` inside the portable root.

- `sources.yaml` – defines exchange adapters, endpoints, credentials, and throttling settings.
- `pipelines.yaml` – selects pairs and granularities to ingest by default.
- `indicators.yaml` – declares indicator expressions available in the chart viewer.

Example files are provided in this repository to bootstrap Binance futures data.

## Storage Layout

Data lives under `library/` using Hive-style folders:

```
library/
  raw/
    pair=BTCUSDT/
      gran=1s/
        year=2024/
          month=05/
            day=07.parquet
  features/
  manifests/
```

Partial days are written with a `__PART_until_HHmmSs` suffix until the UTC day is complete. Manifests are stored in `library/manifests/<PAIR>_<gran>.json`.

## Packaging

- **Windows** – Use PyInstaller to produce a single-file executable:

  ```bash
  pyinstaller --onefile -n app crypto_portable/app.py
  ```

- **Linux** – Bundle into an AppImage or ship as a zipped folder containing the `crypto_portable` package and virtual environment. Documented build steps will be added in future revisions.

## Roadmap

- Implement real one-second candle ingestion using exchange-native endpoints.
  :::task-stub{title="Replace 1m derived candles with true 1s data"}
  Investigate Binance or alternative exchanges that expose 1-second klines or aggregate trades API. Extend `BinanceSource.fetch_candles` to stitch true 1-second data while maintaining manifest guarantees.
  :::
- Complete CSV/PNG export workflows.
- Render interactive charts (e.g., using PySide6 Graphical components or embedded web view).
- Enhance indicator engine with expression parsing and rolling-window optimizations.

