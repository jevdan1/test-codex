"""Create a portable ZIP bundle matching the expected folder layout."""
from __future__ import annotations

import shutil
from pathlib import Path
import zipfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = PROJECT_ROOT / "dist"
BUNDLE_ROOT = DIST_DIR / "CryptoPortable"
ZIP_PATH = DIST_DIR / "CryptoPortable.zip"

COPY_ROOT_FILES = [
    PROJECT_ROOT / "README.md",
]
COPY_APP_FILES = [
    PROJECT_ROOT / "pyproject.toml",
]
COPY_DIRS_TO_APP = [
    PROJECT_ROOT / "crypto_portable",
]
COPY_DIRS_TO_ROOT = [
    PROJECT_ROOT / "config",
]

ENTRYPOINT_TEMPLATE = """#!/usr/bin/env python3
\"\"\"Entry script for the portable crypto collector.\"\"\"
from crypto_portable.app import main as app_main


def main() -> None:
    app_main()


if __name__ == "__main__":
    main()
"""


LIBRARY_SUBDIRS = [
    "raw",
    "features",
    "manifests",
]


def clean_bundle_root() -> None:
    if BUNDLE_ROOT.exists():
        shutil.rmtree(BUNDLE_ROOT)
    BUNDLE_ROOT.mkdir(parents=True, exist_ok=True)


def copy_tree(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def prepare_bundle() -> None:
    clean_bundle_root()

    for file_path in COPY_ROOT_FILES:
        shutil.copy2(file_path, BUNDLE_ROOT / file_path.name)

    for dir_path in COPY_DIRS_TO_ROOT:
        copy_tree(dir_path, BUNDLE_ROOT / dir_path.name)

    app_dir = BUNDLE_ROOT / "app"
    app_dir.mkdir(parents=True, exist_ok=True)

    for file_path in COPY_APP_FILES:
        shutil.copy2(file_path, app_dir / file_path.name)

    for dir_path in COPY_DIRS_TO_APP:
        copy_tree(dir_path, app_dir / dir_path.name)

    entrypoint = app_dir / "run_portable.py"
    entrypoint.write_text(ENTRYPOINT_TEMPLATE)
    entrypoint.chmod(0o755)

    library_root = BUNDLE_ROOT / "library"
    for sub in LIBRARY_SUBDIRS:
        (library_root / sub).mkdir(parents=True, exist_ok=True)

    (BUNDLE_ROOT / "exports").mkdir(parents=True, exist_ok=True)
    (BUNDLE_ROOT / "logs").mkdir(parents=True, exist_ok=True)


def build_zip() -> None:
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()

    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
        for path in sorted(BUNDLE_ROOT.rglob("*")):
            if path.is_dir():
                continue
            arcname = path.relative_to(BUNDLE_ROOT.parent)
            zipf.write(path, arcname)


def cleanup_bundle_root() -> None:
    if BUNDLE_ROOT.exists():
        shutil.rmtree(BUNDLE_ROOT)


def main() -> None:
    DIST_DIR.mkdir(exist_ok=True)
    prepare_bundle()
    build_zip()
    cleanup_bundle_root()


if __name__ == "__main__":
    main()
