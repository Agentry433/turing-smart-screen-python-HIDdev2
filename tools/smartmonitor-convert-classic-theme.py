#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from library.smartmonitor_classic_theme_convert import (
    convert_classic_theme_to_smartmonitor_project,
)
from library.smartmonitor_compile import compile_theme_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert a classic turing-smart-screen theme.yaml to a SmartMonitor UI project and optionally compile it to .dat",
    )
    parser.add_argument("theme", help="Path to classic theme directory or theme.yaml")
    parser.add_argument(
        "--output-root",
        default="res/smartmonitor/projects",
        help="Directory where the generated SmartMonitor UI project will be written",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Output SmartMonitor project name (defaults to classic theme directory name)",
    )
    parser.add_argument(
        "--compile-dat",
        default=None,
        help="Optional output path for compiled .dat theme",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    result = convert_classic_theme_to_smartmonitor_project(
        args.theme,
        args.output_root,
        project_name=args.name,
    )
    print(f"Generated UI project: {result.output_dir}")
    print(f"UI file: {result.ui_path}")
    if result.copied_assets:
        print("Copied assets:")
        for asset in result.copied_assets:
            print(f"  - {asset}")
    if result.skipped_items:
        print("Skipped items:")
        for item in result.skipped_items:
            print(f"  - {item}")

    if args.compile_dat:
        payload = compile_theme_file(result.ui_path)
        output_path = Path(args.compile_dat)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(payload)
        print(f"Compiled DAT: {output_path}")


if __name__ == "__main__":
    main()
