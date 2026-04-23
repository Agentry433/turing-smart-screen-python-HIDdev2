#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from library.smartmonitor_classic_theme_convert import (
    batch_convert_classic_themes,
    convert_classic_theme_to_smartmonitor_project,
    render_classic_theme_preview,
)
from library.smartmonitor_compile import compile_theme_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert a classic turing-smart-screen theme.yaml to a SmartMonitor UI project and optionally compile it to .dat",
    )
    parser.add_argument("theme", nargs="?", help="Path to classic theme directory or theme.yaml")
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
    parser.add_argument(
        "--preview-only",
        action="store_true",
        help="Render a 480x320 preview from the classic theme without converting it",
    )
    parser.add_argument(
        "--preview-out",
        default=None,
        help="Optional output path for preview image in single-theme mode",
    )
    parser.add_argument(
        "--batch-root",
        default=None,
        help="Convert every theme.yaml found under this root directory",
    )
    parser.add_argument(
        "--compile-root",
        default=None,
        help="When using --batch-root, write compiled .dat files to this directory",
    )
    parser.add_argument(
        "--preview-root",
        default=None,
        help="When using --batch-root, copy generated preview images to this directory",
    )
    parser.add_argument(
        "--report-json",
        default=None,
        help="Optional JSON compatibility report path",
    )
    parser.add_argument(
        "--report-md",
        default=None,
        help="Optional Markdown compatibility report path",
    )
    return parser


def _write_markdown_report(report_path: Path, results) -> None:
    converted = sum(1 for item in results if item.status == "converted")
    skipped = sum(1 for item in results if item.status == "skipped")
    unsupported = sum(1 for item in results if item.status == "unsupported")

    lines = [
        "# Classic Theme Conversion Report",
        "",
        f"- Converted: {converted}",
        f"- Skipped features: {skipped}",
        f"- Unsupported: {unsupported}",
        "",
        "| Theme | Status | Widgets | DAT | Preview | Notes |",
        "| --- | --- | ---: | --- | --- | --- |",
    ]
    for item in results:
        notes: list[str] = []
        if item.placeholder_items:
            notes.append(f"placeholders: {len(item.placeholder_items)}")
        if item.skipped_items:
            notes.append(f"skipped: {len(item.skipped_items)}")
        if item.error:
            notes.append(item.error)
        lines.append(
            "| "
            + " | ".join(
                [
                    item.theme_name.replace("|", "\\|"),
                    item.status,
                    str(item.widget_count),
                    "`yes`" if item.dat_path else "",
                    "`yes`" if item.preview_path else "",
                    ", ".join(notes).replace("|", "\\|"),
                ]
            )
            + " |"
        )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.batch_root:
        results = batch_convert_classic_themes(
            args.batch_root,
            args.output_root,
            compile_root=args.compile_root,
            preview_root=args.preview_root,
        )
        converted = sum(1 for item in results if item.status == "converted")
        skipped = sum(1 for item in results if item.status == "skipped")
        unsupported = sum(1 for item in results if item.status == "unsupported")

        for item in results:
            print(f"[{item.status}] {item.theme_name}")
            if item.ui_path:
                print(f"  ui: {item.ui_path}")
            if item.dat_path:
                print(f"  dat: {item.dat_path}")
            if item.preview_path:
                print(f"  preview: {item.preview_path}")
            if item.placeholder_items:
                preview = ", ".join(item.placeholder_items[:6])
                if len(item.placeholder_items) > 6:
                    preview += ", ..."
                print(f"  placeholders: {preview}")
            if item.skipped_items:
                preview = ", ".join(item.skipped_items[:6])
                if len(item.skipped_items) > 6:
                    preview += ", ..."
                print(f"  skipped: {preview}")
            if item.error:
                print(f"  error: {item.error}")

        print()
        print(f"Converted: {converted}")
        print(f"Skipped features: {skipped}")
        print(f"Unsupported: {unsupported}")

        if args.report_json:
            report_path = Path(args.report_json)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(
                json.dumps(
                    [
                        {
                            "theme_name": item.theme_name,
                            "theme_path": str(item.theme_path),
                            "status": item.status,
                            "ui_path": str(item.ui_path) if item.ui_path else "",
                            "dat_path": str(item.dat_path) if item.dat_path else "",
                            "preview_path": str(item.preview_path) if item.preview_path else "",
                            "widget_count": item.widget_count,
                            "placeholder_items": item.placeholder_items,
                            "skipped_items": item.skipped_items,
                            "error": item.error,
                        }
                        for item in results
                    ],
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            print(f"Report JSON: {report_path}")
        if args.report_md:
            report_path = Path(args.report_md)
            _write_markdown_report(report_path, results)
            print(f"Report Markdown: {report_path}")
        return

    if not args.theme:
        parser.error("theme is required unless --batch-root is used")

    if args.preview_only:
        preview = render_classic_theme_preview(args.theme, args.preview_out)
        print(f"Preview size: {preview.size[0]}x{preview.size[1]}")
        if args.preview_out:
            print(f"Preview: {Path(args.preview_out)}")
        return

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
    if result.placeholder_items:
        print("Placeholder items:")
        for item in result.placeholder_items:
            print(f"  - {item}")
    if result.preview_path:
        print(f"Preview: {result.preview_path}")

    if args.compile_dat:
        payload = compile_theme_file(result.ui_path)
        output_path = Path(args.compile_dat)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(payload)
        print(f"Compiled DAT: {output_path}")


if __name__ == "__main__":
    main()
