"""Utility to bootstrap USDC-only configuration files.

Run with:
    python tools/bootstrap_usdc_config.py

The script detects the portable base directory relative to itself, ensures the
configuration folder exists, writes the expected YAML content for sources and
pipelines, performs lightweight sanity checks, and reports the generated file
paths.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

SOURCES_YAML_CONTENT = """binance:
  kind: binance
  market: spot
  # Public REST base. Keep minimal to match the current adapter.
  # Do not add auth keys or extra fields here.
  # Other free public exchanges (placeholders only, not used by the app yet):
  # kraken:   public REST (spot)  - https://api.kraken.com
  # coinbase: public REST (spot)  - https://api.exchange.coinbase.com
  # bitfinex: public REST (spot)  - https://api-pub.bitfinex.com
  # okx:      public REST (spot)  - https://www.okx.com
"""

PIPELINES_YAML_CONTENT = """shortlist:
  - BTCUSDC
  - ETHUSDC
  - SOLUSDC

pipelines:
  default_1s:
    source: binance
    granularity: 1s
    pairs:
      - BTCUSDC
      - ETHUSDC
      - SOLUSDC
"""

EXPECTED_PAIRS = ["BTCUSDC", "ETHUSDC", "SOLUSDC"]


def detect_base_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def atomic_write(path: Path, text: str) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(text, encoding="utf-8")
    os.replace(tmp_path, path)


def _strip_comments(lines: Iterable[str]) -> list[str]:
    cleaned: list[str] = []
    for line in lines:
        stripped = line.split("#", 1)[0].rstrip()
        if stripped:
            cleaned.append(stripped)
    return cleaned


def sanity_check_sources(text: str) -> None:
    lines = _strip_comments(text.splitlines())
    if not lines or lines[0].strip() != "binance:":
        raise ValueError("sources.yaml must start with 'binance:'")

    kind_found = any(line.strip() == "kind: binance" for line in lines[1:])
    market_found = any(line.strip() == "market: spot" for line in lines[1:])
    if not kind_found or not market_found:
        raise ValueError("sources.yaml missing required 'kind' or 'market' entries")



def _collect_block_items(lines: Iterable[str], header: str) -> list[str]:
    items: list[str] = []
    inside_block = False
    indent_prefix = ""
    for line in lines:
        if not inside_block:
            if line.strip() == f"{header}:":
                inside_block = True
                indent_prefix = " " * (len(line) - len(line.lstrip()))
            continue
        if line.startswith(indent_prefix + "-"):
            value = line.split("-", 1)[1].strip()
            if value:
                items.append(value)
        elif line.strip().endswith(":") and not line.startswith(indent_prefix + " "):
            break
    return items


def sanity_check_pipelines(text: str) -> None:
    lines = _strip_comments(text.splitlines())
    if "shortlist:" not in (line.strip() for line in lines):
        raise ValueError("pipelines.yaml missing 'shortlist:' block")

    shortlist = _collect_block_items(lines, "shortlist")
    if shortlist != EXPECTED_PAIRS:
        raise ValueError("pipelines.yaml shortlist must contain the three USDC pairs in order")

    if "pipelines:" not in (line.strip() for line in lines):
        raise ValueError("pipelines.yaml missing 'pipelines:' block")

    if "default_1s:" not in (line.strip() for line in lines):
        raise ValueError("pipelines.yaml missing 'default_1s:' pipeline")

    default_pairs = _collect_block_items(lines, "pairs")
    if default_pairs != EXPECTED_PAIRS:
        raise ValueError("pipelines.yaml default_1s pairs must match the USDC shortlist")

    source_ok = any(line.strip() == "source: binance" for line in lines)
    gran_ok = any(line.strip() == "granularity: 1s" for line in lines)
    if not (source_ok and gran_ok):
        raise ValueError("pipelines.yaml default_1s pipeline missing source or granularity")



def main() -> None:
    base_dir = detect_base_dir()
    cfg_dir = base_dir / "CryptoPortable" / "config"
    ensure_dir(cfg_dir)

    sources_path = cfg_dir / "sources.yaml"
    pipelines_path = cfg_dir / "pipelines.yaml"

    atomic_write(sources_path, SOURCES_YAML_CONTENT)
    atomic_write(pipelines_path, PIPELINES_YAML_CONTENT)

    sanity_check_sources(SOURCES_YAML_CONTENT)
    sanity_check_pipelines(PIPELINES_YAML_CONTENT)

    print(f"Wrote sources.yaml to: {sources_path}")
    print(f"Wrote pipelines.yaml to: {pipelines_path}")
    print("USDC bootstrap complete.")


if __name__ == "__main__":
    main()
