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

Follow these steps the first time you run the toolkit on a development machine. The same layout applies when you copy the portable folder to another computer.

1. **Install dependencies**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -e .
   ```

2. **Choose a base folder**

   Pick or create the directory that will hold the portable layout (e.g., `CryptoPortable`). Every command references it through the `--base-dir` option. Missing sub-folders are created automatically at runtime.

3. **Seed configuration (optional)**

   Copy the sample YAML files into your base directory if you want editable configs next to the executable:

   ```bash
   cp -r config CryptoPortable/
   ```

4. **Run a quick status check**

   ```bash
   python -m crypto_portable.app --base-dir CryptoPortable --mode status --pair BTCUSDT --source binance
   ```

   This creates the initial `library/`, `logs/`, and `exports/` folders and prints the manifest summary for the chosen pair.

5. **Launch the GUI**

   ```bash
   python -m crypto_portable.app --gui --base-dir CryptoPortable
   ```

   Use the top-left **Source** and **Pair** selectors to target a market, configure the **Period** section, and click **Run** for ingestion or **Open chart** for analysis. The status bar and log box reflect progress in real time.

6. **Command-line ingestion (headless)**

   To automate ingestion without the GUI, switch off the `--gui` flag and pass a mode:

   ```bash
   python -m crypto_portable.app \
       --base-dir CryptoPortable \
       --mode resume \
       --pair BTCUSDT \
       --source binance \
       --update-current-day
   ```

   Available modes: `resume`, `backfill`, `rebuild`, and `status`. Combine them with date arguments (`--start`, `--end`, `--date`) to control coverage.

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
- **Portable ZIP** – Generate a ready-to-run portable folder layout:

  ```bash
  python scripts/create_portable_bundle.py
  unzip dist/CryptoPortable.zip -d /path/to/usb
  ```

  The archive contains `CryptoPortable/app/run_portable.py` which launches the CLI/GUI entrypoint along with pre-created `library/`, `exports/`, and `logs/` directories. Double-click `run_portable.py` (or run it with `python`) to start the GUI; append CLI flags for automated tasks, for example:

  ```bash
  python run_portable.py --mode backfill --start 2024-05-01 --end 2024-05-07
  ```

  When distributing the app, copy or unzip the `CryptoPortable/` folder to the target computer. Deleting the `library/` directory simply resets stored data; the application recreates it on the next launch.

## Roadmap

- Implement real one-second candle ingestion using exchange-native endpoints.
  :::task-stub{title="Replace 1m derived candles with true 1s data"}
  Investigate Binance or alternative exchanges that expose 1-second klines or aggregate trades API. Extend `BinanceSource.fetch_candles` to stitch true 1-second data while maintaining manifest guarantees.
  :::
- Complete CSV/PNG export workflows.
- Render interactive charts (e.g., using PySide6 Graphical components or embedded web view).
- Enhance indicator engine with expression parsing and rolling-window optimizations.

