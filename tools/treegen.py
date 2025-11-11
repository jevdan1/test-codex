#!/usr/bin/env python3
"""Print a simple directory tree listing."""
from __future__ import annotations

import argparse
from pathlib import Path


def walk_tree(path: Path, prefix: str = "") -> list[str]:
    entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    lines: list[str] = []
    total = len(entries)
    for index, entry in enumerate(entries):
        connector = "└── " if index == total - 1 else "├── "
        lines.append(f"{prefix}{connector}{entry.name}")
        if entry.is_dir():
            extension = "    " if index == total - 1 else "│   "
            lines.extend(walk_tree(entry, prefix + extension))
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description="Print a directory tree")
    parser.add_argument(
        "path",
        type=Path,
        nargs="?",
        default=Path.cwd(),
        help="Directory to list (defaults to current working directory)",
    )
    args = parser.parse_args()
    root = args.path.resolve()
    if not root.exists():
        raise SystemExit(f"Path not found: {root}")
    if not root.is_dir():
        raise SystemExit(f"Path is not a directory: {root}")

    print(root.name)
    for line in walk_tree(root):
        print(line)


if __name__ == "__main__":
    main()
