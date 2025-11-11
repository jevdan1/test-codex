"""Application entry points for the portable crypto data collector."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from .config import ConfigBundle, load_config_bundle
from .logging_config import configure_logging
from .paths import PortablePaths
from .ingestion import IngestionManager

try:
    from .gui.main_window import run_gui
except Exception:  # pragma: no cover - GUI optional in headless builds
    run_gui = None  # type: ignore


LOGGER = logging.getLogger(__name__)


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Portable crypto data collector")
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=None,
        help=(
            "Portable root directory (defaults to executable directory when frozen, "
            "otherwise the current working directory)"
        ),
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Optional configuration directory; defaults to <base>/config",
    )
    parser.add_argument(
        "--library-dir",
        type=Path,
        default=None,
        help="Optional library directory; defaults to <base>/library",
    )
    parser.add_argument(
        "--mode",
        choices=["resume", "backfill", "rebuild", "status"],
        default="status",
        help="Ingestion mode when running in CLI mode",
    )
    parser.add_argument("--pair", help="Trading pair symbol, e.g. BTCUSDT", default=None)
    parser.add_argument(
        "--source",
        help="Source identifier defined in config/sources.yaml",
        default=None,
    )
    parser.add_argument(
        "--start",
        help="Start date (YYYY-MM-DD) for backfill/status modes",
        default=None,
    )
    parser.add_argument(
        "--end",
        help="End date (YYYY-MM-DD) for backfill/status modes",
        default=None,
    )
    parser.add_argument(
        "--day",
        help="Specific day (YYYY-MM-DD) for rebuild mode",
        default=None,
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch the graphical interface (default when no CLI arguments are provided)",
    )
    return parser.parse_args(argv)


def run_cli(paths: PortablePaths, config: ConfigBundle, args: argparse.Namespace) -> None:
    manager = IngestionManager(paths, config)

    if args.mode == "resume":
        if not args.pair or not args.source:
            raise SystemExit("--pair and --source are required for resume mode")
        manager.resume_fill_gaps(args.source, args.pair)
    elif args.mode == "backfill":
        if not args.pair or not args.source or not args.start or not args.end:
            raise SystemExit("--pair, --source, --start and --end are required for backfill mode")
        manager.backfill_range(args.source, args.pair, args.start, args.end)
    elif args.mode == "rebuild":
        if not args.pair or not args.source or not args.day:
            raise SystemExit("--pair, --source and --day are required for rebuild mode")
        manager.rebuild_day(args.source, args.pair, args.day)
    else:
        if not args.pair or not args.source:
            raise SystemExit("--pair and --source are required for status mode")
        status = manager.status(args.source, args.pair, args.start, args.end)
        for row in status:
            LOGGER.info(
                "%s %s rows=%s first=%s last=%s complete=%s part_until=%s gaps=%s",
                row.date,
                row.state,
                row.rows,
                row.first_ms,
                row.last_ms,
                row.complete,
                row.part_until,
                row.gaps,
            )


def main(argv: Optional[list[str]] = None) -> None:
    args = parse_args(argv)

    if args.base_dir is not None:
        base_dir = args.base_dir
    elif getattr(sys, "frozen", False):  # PyInstaller or similar frozen build
        base_dir = Path(sys.executable).resolve().parent
    else:
        base_dir = Path.cwd()

    paths = PortablePaths(base_dir=base_dir)
    configure_logging(paths.logs_dir)
    config_dir = args.config_dir or paths.config_dir
    library_dir = args.library_dir or paths.library_dir
    bundle = load_config_bundle(config_dir)
    paths.ensure_portable_layout(library_dir)

    launch_gui = False
    if args.gui:
        launch_gui = True
    else:
        no_cli_args_provided = (
            args.pair is None
            and args.source is None
            and args.start is None
            and args.end is None
            and args.day is None
            and args.mode == "status"
        )
        if no_cli_args_provided and run_gui is not None:
            launch_gui = True

    if launch_gui:
        if run_gui is None:
            raise SystemExit("GUI dependencies are not available in this environment")
        run_gui(paths, bundle)
    else:
        run_cli(paths, bundle, args)


if __name__ == "__main__":  # pragma: no cover
    main()
