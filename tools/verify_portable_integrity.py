"""Run integrity checks for the portable Crypto toolkit.

Execute with::

    python tools/verify_portable_integrity.py

The script inspects the environment relative to its location, validates that the
project layout, configuration files, Python runtime, and dependencies look
healthy, and performs a lightweight write probe inside the library folder.
"""
from __future__ import annotations

import importlib
import importlib.util
import os
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Iterable, List

REQUIRED_MODULES = [
    "pyarrow",
    "pandas",
    "duckdb",
    "polars",
    "PySide6",
    "requests",
    "httpx",
    "yaml",
]

EXPECTED_PAIRS = ["BTCUSDC", "ETHUSDC", "SOLUSDC"]


@dataclass
class CheckResult:
    """Represents the outcome of an individual integrity check."""

    name: str
    ok: bool
    details: str | None = None


def detect_base_dir() -> Path:
    """Return the portable root directory (parent of this script)."""

    return Path(__file__).resolve().parent.parent


def python_version_check() -> CheckResult:
    version = sys.version_info
    ok = (version.major, version.minor) >= (3, 10)
    details = f"Detected Python {version.major}.{version.minor}.{version.micro}"
    if not ok:
        details += " (requires >= 3.10)"
    return CheckResult("Python runtime", ok, details)


def layout_check(base_dir: Path) -> CheckResult:
    package_dir = base_dir / "crypto_portable"
    main_entry = package_dir / "app.py"
    if package_dir.is_dir() and main_entry.is_file():
        return CheckResult("Project layout", True, f"Package folder at {package_dir}")
    return CheckResult(
        "Project layout",
        False,
        "Expected 'crypto_portable/app.py' relative to base directory.",
    )


def _strip_comments(lines: Iterable[str]) -> List[str]:
    cleaned: List[str] = []
    for raw in lines:
        stripped = raw.split("#", 1)[0].rstrip()
        if stripped:
            cleaned.append(stripped)
    return cleaned


def sources_check(config_dir: Path) -> CheckResult:
    sources_path = config_dir / "sources.yaml"
    if not sources_path.is_file():
        return CheckResult("sources.yaml", False, f"Missing file: {sources_path}")

    lines = _strip_comments(sources_path.read_text(encoding="utf-8").splitlines())
    if not lines or lines[0].strip() != "binance:":
        return CheckResult("sources.yaml", False, "First entry must define 'binance'.")

    has_kind = any(line.strip().startswith("kind:") for line in lines[1:])
    has_market = any(line.strip().startswith("market:") for line in lines[1:])
    if not (has_kind and has_market):
        return CheckResult(
            "sources.yaml",
            False,
            "Missing 'kind' or 'market' entries for binance source.",
        )

    return CheckResult("sources.yaml", True, f"Validated at {sources_path}")


def _collect_block_items(lines: Iterable[str], header: str) -> List[str]:
    items: List[str] = []
    inside = False
    base_indent = ""
    for line in lines:
        if not inside:
            if line.strip() == f"{header}:":
                inside = True
                base_indent = " " * (len(line) - len(line.lstrip()))
            continue
        if line.startswith(base_indent + "-"):
            value = line.split("-", 1)[1].strip()
            if value:
                items.append(value)
        elif line.strip().endswith(":") and not line.startswith(base_indent + " "):
            break
    return items


def pipelines_check(config_dir: Path) -> CheckResult:
    pipelines_path = config_dir / "pipelines.yaml"
    if not pipelines_path.is_file():
        return CheckResult("pipelines.yaml", False, f"Missing file: {pipelines_path}")

    lines = _strip_comments(pipelines_path.read_text(encoding="utf-8").splitlines())
    shortlist = _collect_block_items(lines, "shortlist")
    default_pairs = _collect_block_items(lines, "pairs")
    errors: List[str] = []

    if shortlist != EXPECTED_PAIRS:
        errors.append("shortlist must contain BTCUSDC, ETHUSDC, SOLUSDC in order")
    if default_pairs != EXPECTED_PAIRS:
        errors.append("default_1s pairs must match the shortlist")

    has_pipeline = any(line.strip() == "default_1s:" for line in lines)
    has_source = any(line.strip() == "source: binance" for line in lines)
    has_granularity = any(line.strip() == "granularity: 1s" for line in lines)

    if not has_pipeline:
        errors.append("missing 'default_1s' pipeline definition")
    if not has_source:
        errors.append("default_1s pipeline must use source 'binance'")
    if not has_granularity:
        errors.append("default_1s pipeline must define granularity '1s'")

    if errors:
        return CheckResult("pipelines.yaml", False, "; ".join(errors))

    return CheckResult("pipelines.yaml", True, f"Validated at {pipelines_path}")


def find_config_dir(base_dir: Path) -> Path | None:
    preferred = base_dir / "CryptoPortable" / "config"
    fallback = base_dir / "config"
    if preferred.is_dir():
        return preferred
    if fallback.is_dir():
        return fallback
    return None


def config_check(base_dir: Path) -> list[CheckResult]:
    results: list[CheckResult] = []
    config_dir = find_config_dir(base_dir)
    if config_dir is None:
        return [
            CheckResult(
                "Config directory",
                False,
                "Expected 'CryptoPortable/config' or top-level 'config' directory.",
            )
        ]

    results.append(CheckResult("Config directory", True, f"Found at {config_dir}"))
    results.append(sources_check(config_dir))
    results.append(pipelines_check(config_dir))
    return results


def dependency_check() -> CheckResult:
    missing = [name for name in REQUIRED_MODULES if importlib.util.find_spec(name) is None]
    if missing:
        return CheckResult("Python dependencies", False, "Missing modules: " + ", ".join(missing))
    return CheckResult("Python dependencies", True, "All required modules available")


def package_import_check(base_dir: Path) -> CheckResult:
    sys.path.insert(0, str(base_dir))
    try:
        importlib.import_module("crypto_portable")
    except Exception as exc:  # pragma: no cover - diagnostic output only
        return CheckResult("Package import", False, f"Failed to import crypto_portable: {exc}")
    finally:
        try:
            sys.path.remove(str(base_dir))
        except ValueError:
            pass
    return CheckResult("Package import", True, "crypto_portable imported successfully")


def data_dirs_check(base_dir: Path) -> CheckResult:
    required = ["library", "exports", "logs"]
    missing = [name for name in required if not (base_dir / name).is_dir()]
    if missing:
        return CheckResult(
            "Data directories",
            False,
            "Missing directories: " + ", ".join(missing),
        )
    return CheckResult("Data directories", True, "library, exports, logs are present")


def library_write_probe(base_dir: Path) -> CheckResult:
    library_dir = base_dir / "library"
    probe_dir = library_dir / "_integrity_probe"
    probe_file = probe_dir / "touch.tmp"
    try:
        probe_dir.mkdir(parents=True, exist_ok=True)
        probe_file.write_text("ok", encoding="utf-8")
        probe_file.unlink(missing_ok=True)
    except Exception as exc:  # pragma: no cover - diagnostic output only
        return CheckResult("Library write probe", False, f"Write test failed: {exc}")
    finally:
        if probe_dir.is_dir() and not any(probe_dir.iterdir()):
            try:
                probe_dir.rmdir()
            except OSError:
                pass
    return CheckResult("Library write probe", True, f"Writable at {library_dir}")


def run_checks() -> list[CheckResult]:
    base_dir = detect_base_dir()
    results: list[CheckResult] = [python_version_check(), layout_check(base_dir)]
    results.extend(config_check(base_dir))
    results.append(dependency_check())
    results.append(package_import_check(base_dir))
    results.append(data_dirs_check(base_dir))
    results.append(library_write_probe(base_dir))
    return results


def print_summary(results: Iterable[CheckResult]) -> None:
    print("=== Portable Integrity Report ===")
    failures = 0
    for result in results:
        status = "OK" if result.ok else "FAIL"
        print(f"[{status}] {result.name}")
        if result.details:
            print(f"    {result.details}")
        if not result.ok:
            failures += 1
    print("=================================")
    if failures:
        print(f"Integrity check completed with {failures} issue(s).")
    else:
        print("All integrity checks passed.")


def main() -> int:
    results = run_checks()
    print_summary(results)
    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
