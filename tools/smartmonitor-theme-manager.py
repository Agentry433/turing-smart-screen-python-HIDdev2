#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

import argparse
import hashlib
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from library.pythoncheck import check_python_version
from library.smartmonitor_compile import compile_theme_file

check_python_version()

try:
    from ruamel.yaml import YAML
except ModuleNotFoundError:
    YAML = None
    import yaml as pyyaml


REPO_ROOT = Path(__file__).resolve().parents[1]
THEMES_ROOT = REPO_ROOT / "res" / "smartmonitor" / "themes"
CONFIG_PATH = REPO_ROOT / "config.yaml"
DEFAULT_VENDOR_ROOT = (
    REPO_ROOT / "vendor" / "themefor3.5"
    if (REPO_ROOT / "vendor" / "themefor3.5").is_dir()
    else REPO_ROOT / "vendor" / "themefor3.5"
)
SMARTMONITOR_VID_PID = "0483:0065"


def _yaml():
    if YAML is None:
        return None

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    return yaml


def _yaml_load(stream):
    yaml = _yaml()
    if yaml is not None:
        return yaml.load(stream)
    return pyyaml.safe_load(stream)


def _yaml_dump(data, stream):
    yaml = _yaml()
    if yaml is not None:
        yaml.dump(data, stream)
    else:
        pyyaml.safe_dump(data, stream, sort_keys=False, allow_unicode=True)


def ensure_theme_root():
    THEMES_ROOT.mkdir(parents=True, exist_ok=True)


def sanitize_theme_name(name: str) -> str:
    name = name.strip()
    if not name:
        raise SystemExit("Theme name cannot be empty")

    safe = []
    for ch in name:
        if ch.isalnum() or ch in ("-", "_", ".", " "):
            safe.append(ch)
        else:
            safe.append("_")
    sanitized = "".join(safe).strip()
    if not sanitized:
        raise SystemExit("Theme name becomes empty after sanitization")
    return sanitized


def compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def metadata_path(theme_dir: Path) -> Path:
    return theme_dir / "metadata.yaml"


def img_path(theme_dir: Path) -> Path:
    return theme_dir / "img.dat"


def bundled_dat_path(theme_name: str) -> Path:
    return REPO_ROOT / "res" / "themes" / f"{theme_name}.dat"


def list_installed_themes():
    ensure_theme_root()
    themes = []
    for theme_dir in sorted(path for path in THEMES_ROOT.iterdir() if path.is_dir()):
        image = img_path(theme_dir)
        meta = metadata_path(theme_dir)
        if not image.is_file():
            continue
        info = {
            "name": theme_dir.name,
            "path": theme_dir,
            "img": image,
            "size": image.stat().st_size,
            "sha256": compute_sha256(image),
            "metadata": meta if meta.is_file() else None,
        }
        if meta.is_file():
            with meta.open("r", encoding="utf-8") as stream:
                info["meta"] = _yaml_load(stream) or {}
        else:
            info["meta"] = {}
        themes.append(info)
    return themes


def read_config():
    with CONFIG_PATH.open("r", encoding="utf-8") as stream:
        return _yaml_load(stream)


def write_config(config_data):
    with CONFIG_PATH.open("w", encoding="utf-8") as stream:
        _yaml_dump(config_data, stream)


def active_theme_path_from_config() -> Path | None:
    config = read_config()
    display = config.get("display", {})
    value = display.get("SMARTMONITOR_HID_THEME_FILE", "") or ""
    if not value:
        return None
    return Path(value).expanduser()


def find_theme(theme_name: str):
    wanted = sanitize_theme_name(theme_name)
    for theme in list_installed_themes():
        if theme["name"] == wanted:
            return theme
    raise SystemExit(f"Theme not found: {wanted}")


def import_theme(theme_name: str, source_img: Path):
    ensure_theme_root()
    if not source_img.is_file():
        raise SystemExit(f"Theme file not found: {source_img}")

    target_dir = THEMES_ROOT / sanitize_theme_name(theme_name)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_img = img_path(target_dir)
    shutil.copy2(source_img, target_img)
    shutil.copy2(source_img, bundled_dat_path(target_dir.name))

    metadata = {
        "name": target_dir.name,
        "source_file": str(source_img.resolve()),
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "size": target_img.stat().st_size,
        "sha256": compute_sha256(target_img),
    }
    with metadata_path(target_dir).open("w", encoding="utf-8") as stream:
        _yaml_dump(metadata, stream)

    print(f"Imported theme '{target_dir.name}' -> {target_img}")


def activate_theme(theme_name: str):
    theme = find_theme(theme_name)
    config = read_config()
    display = config.setdefault("display", {})
    display["REVISION"] = "A_HID"
    display["SMARTMONITOR_HID_RUNTIME"] = True
    display["SMARTMONITOR_HID_THEME_FILE"] = str(theme["img"].resolve())
    write_config(config)
    print(f"Activated theme '{theme['name']}' in {CONFIG_PATH}")


def upload_theme(theme_name: str, port: str):
    try:
        from library.lcd.lcd_comm_rev_a_hid import LcdCommRevAHid
        from library.log import logger
    except ModuleNotFoundError as exc:
        raise SystemExit(
            f"Missing Python dependency: {exc.name}. Install the project requirements before using this tool."
        ) from exc

    theme = find_theme(theme_name)
    lcd = LcdCommRevAHid(com_port=port)
    try:
        lcd.openSerial()
        lcd.smartmonitor_upload_theme(str(theme["img"]))
        logger.info("Uploaded SmartMonitor theme '%s'", theme["name"])
    finally:
        lcd.closeSerial()


def print_installed():
    themes = list_installed_themes()
    active = active_theme_path_from_config()
    if not themes:
        print("No installed SmartMonitor themes")
        return

    for theme in themes:
        marker = "*" if active and theme["img"].resolve() == active.resolve() else " "
        print(f"{marker} {theme['name']}")
        print(f"  img: {theme['img']}")
        print(f"  size: {theme['size']} bytes")
        print(f"  sha256: {theme['sha256']}")
        source_file = theme["meta"].get("source_file")
        if source_file:
            print(f"  source: {source_file}")


def print_current():
    active = active_theme_path_from_config()
    if not active:
        print("No SmartMonitor theme configured in config.yaml")
        return

    print(active)


def print_vendor_refs(vendor_root: Path):
    if not vendor_root.is_dir():
        raise SystemExit(f"Vendor theme root not found: {vendor_root}")

    for theme_dir in sorted(path for path in vendor_root.iterdir() if path.is_dir() and path.name.startswith("theme")):
        print(theme_dir.name)
        print(f"  path: {theme_dir}")


def find_vendor_theme_dir(vendor_root: Path, theme_name: str) -> Path:
    wanted = sanitize_theme_name(theme_name)
    candidates = [vendor_root / wanted, vendor_root / f"theme_{wanted}"]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate

    for candidate in vendor_root.iterdir():
        if candidate.is_dir() and sanitize_theme_name(candidate.name) == wanted:
            return candidate
    raise SystemExit(f"Vendor theme not found under {vendor_root}: {theme_name}")


def find_vendor_ui(vendor_dir: Path) -> Path:
    ui_files = sorted(vendor_dir.glob("*.ui"))
    if not ui_files:
        raise SystemExit(f"No .ui file found in vendor theme directory: {vendor_dir}")
    return ui_files[0]


def compile_vendor_theme(vendor_root: Path, vendor_theme: str, output_img: Path):
    vendor_dir = find_vendor_theme_dir(vendor_root, vendor_theme)
    ui_path = find_vendor_ui(vendor_dir)
    compiled = compile_theme_file(ui_path)
    output_img.parent.mkdir(parents=True, exist_ok=True)
    output_img.write_bytes(compiled)
    print(f"Compiled vendor theme '{vendor_dir.name}' -> {output_img}")
    print(f"  ui: {ui_path}")


def import_compiled_vendor_theme(installed_name: str, vendor_root: Path, vendor_theme: str):
    temp_output = THEMES_ROOT / sanitize_theme_name(installed_name) / "img.dat"
    compile_vendor_theme(vendor_root, vendor_theme, temp_output)
    shutil.copy2(temp_output, bundled_dat_path(sanitize_theme_name(installed_name)))

    vendor_dir = find_vendor_theme_dir(vendor_root, vendor_theme)
    ui_path = find_vendor_ui(vendor_dir)
    target_dir = THEMES_ROOT / sanitize_theme_name(installed_name)
    meta_path = metadata_path(target_dir)
    metadata = {}
    if meta_path.is_file():
        with meta_path.open("r", encoding="utf-8") as stream:
            metadata = _yaml_load(stream) or {}

    metadata.update(
        {
            "name": target_dir.name,
            "source_vendor_theme": vendor_dir.name,
            "source_ui": str(ui_path.resolve()),
            "compiled_at": datetime.now(timezone.utc).isoformat(),
            "compiler": "experimental_ui_to_imgdat",
            "size": temp_output.stat().st_size,
            "sha256": compute_sha256(temp_output),
        }
    )
    with meta_path.open("w", encoding="utf-8") as stream:
        _yaml_dump(metadata, stream)

    print(f"Imported compiled vendor theme '{vendor_dir.name}' as '{target_dir.name}'")


def import_all_compiled_vendor_themes(vendor_root: Path):
    if not vendor_root.is_dir():
        raise SystemExit(f"Vendor theme root not found: {vendor_root}")

    imported = []
    failed = []
    for theme_dir in sorted(path for path in vendor_root.iterdir() if path.is_dir() and path.name.startswith("theme")):
        theme_name = sanitize_theme_name(theme_dir.name)
        try:
            import_compiled_vendor_theme(theme_name, vendor_root, theme_dir.name)
            imported.append(theme_name)
        except Exception as exc:
            failed.append((theme_dir.name, str(exc)))

    print(f"Imported {len(imported)} vendor themes")
    if failed:
        print(f"Failed {len(failed)} vendor themes")
        for name, error in failed:
            print(f"  {name}: {error}")


def _check_line(ok: bool, message: str, detail: str = "") -> bool:
    marker = "OK" if ok else "WARN"
    print(f"[{marker}] {message}")
    if detail and not ok:
        print(f"      {detail}")
    return ok


def _find_hidraw_candidates() -> list[Path]:
    candidates = []
    for path in sorted(Path("/dev").glob("hidraw*")):
        if path.exists():
            candidates.append(path)
    return candidates


def _lsusb_contains_smartmonitor() -> bool | None:
    try:
        import subprocess

        result = subprocess.run(
            ["lsusb"],
            text=True,
            capture_output=True,
            timeout=3,
            check=False,
        )
    except Exception:
        return None
    return SMARTMONITOR_VID_PID.lower() in result.stdout.lower()


def run_doctor():
    print("SmartMonitor HIDdev doctor")
    print("==========================")
    all_ok = True

    all_ok &= _check_line(sys.version_info >= (3, 10), f"Python version: {sys.version.split()[0]}")
    all_ok &= _check_line(CONFIG_PATH.is_file(), f"config.yaml present: {CONFIG_PATH}")
    all_ok &= _check_line((REPO_ROOT / "requirements.txt").is_file(), "requirements.txt present")

    try:
        import PIL  # noqa: F401
        import psutil  # noqa: F401
        import ruamel.yaml  # noqa: F401
        deps_ok = True
    except ModuleNotFoundError as exc:
        deps_ok = False
        all_ok = False
        _check_line(False, "Python dependencies installed", f"Missing module: {exc.name}")
    else:
        _check_line(True, "Python dependencies installed")

    config_ok = False
    active_theme = None
    if CONFIG_PATH.is_file() and deps_ok:
        try:
            config_data = read_config()
            display = config_data.get("display", {})
            revision = display.get("REVISION")
            active_theme = Path(display.get("SMARTMONITOR_HID_THEME_FILE", "") or "")
            config_ok = revision == "A_HID"
            all_ok &= _check_line(config_ok, f"display.REVISION = {revision!r}", "Expected 'A_HID' for this fork")
        except Exception as exc:
            all_ok = False
            _check_line(False, "config.yaml can be parsed", str(exc))

    themes = list_installed_themes()
    all_ok &= _check_line(bool(themes), f"installed SmartMonitor themes: {len(themes)}")

    if active_theme:
        if not active_theme.is_absolute():
            active_theme = REPO_ROOT / active_theme
        all_ok &= _check_line(active_theme.is_file(), f"active theme file exists: {active_theme}")

    lsusb_state = _lsusb_contains_smartmonitor()
    if lsusb_state is None:
        _check_line(False, "lsusb check skipped", "Install usbutils if you want VID:PID detection")
    else:
        all_ok &= _check_line(
            lsusb_state,
            f"USB device {SMARTMONITOR_VID_PID} visible" if lsusb_state else f"USB device {SMARTMONITOR_VID_PID} not visible",
            "Connect/replug the SmartMonitor or check USB permissions.",
        )

    hidraw_candidates = _find_hidraw_candidates()
    all_ok &= _check_line(bool(hidraw_candidates), f"hidraw devices visible: {', '.join(str(p) for p in hidraw_candidates) or 'none'}")
    if hidraw_candidates:
        readable = [path for path in hidraw_candidates if os.access(path, os.R_OK | os.W_OK)]
        if readable:
            _check_line(True, f"hidraw read/write permission: {', '.join(str(p) for p in readable)}")
        else:
            all_ok = False
            _check_line(
                False,
                "hidraw read/write permission",
                "Install the udev rule from tools/99-smartmonitor-hiddev.rules or run with adjusted permissions.",
            )

    print()
    if all_ok:
        print("Doctor result: ready")
    else:
        print("Doctor result: attention needed")
        print("Recommended next steps:")
        print("  1. Run ./install.sh")
        print("  2. Replug the SmartMonitor")
        print("  3. Run python3 tools/smartmonitor-theme-manager.py doctor")
    return 0 if all_ok else 1


def main():
    parser = argparse.ArgumentParser(description="Manage vendor img.dat themes for the HID SmartMonitor")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_list = subparsers.add_parser("list", help="List installed SmartMonitor themes")
    parser_list.set_defaults(func=lambda args: print_installed())

    parser_current = subparsers.add_parser("current", help="Print active SmartMonitor theme file from config.yaml")
    parser_current.set_defaults(func=lambda args: print_current())

    parser_doctor = subparsers.add_parser("doctor", help="Check installation, config, HID device, and theme setup")
    parser_doctor.set_defaults(func=lambda args: sys.exit(run_doctor()))

    parser_vendor = subparsers.add_parser("vendor-list", help="List vendor theme directories found in unpacked app")
    parser_vendor.add_argument("--vendor-root", type=Path, default=DEFAULT_VENDOR_ROOT,
                               help=f"Vendor theme root (default: {DEFAULT_VENDOR_ROOT})")
    parser_vendor.set_defaults(func=lambda args: print_vendor_refs(args.vendor_root))

    parser_vendor_compile = subparsers.add_parser(
        "vendor-compile",
        help="Compile a vendor .ui theme directory into an img.dat file",
    )
    parser_vendor_compile.add_argument("vendor_theme", help="Vendor theme directory name")
    parser_vendor_compile.add_argument("output", type=Path, help="Output img.dat path")
    parser_vendor_compile.add_argument("--vendor-root", type=Path, default=DEFAULT_VENDOR_ROOT,
                                       help=f"Vendor theme root (default: {DEFAULT_VENDOR_ROOT})")
    parser_vendor_compile.set_defaults(
        func=lambda args: compile_vendor_theme(args.vendor_root, args.vendor_theme, args.output)
    )

    parser_vendor_import = subparsers.add_parser(
        "vendor-import",
        help="Compile a vendor theme and import it into the repo SmartMonitor theme library",
    )
    parser_vendor_import.add_argument("name", help="Installed theme name")
    parser_vendor_import.add_argument("vendor_theme", help="Vendor theme directory name")
    parser_vendor_import.add_argument("--vendor-root", type=Path, default=DEFAULT_VENDOR_ROOT,
                                      help=f"Vendor theme root (default: {DEFAULT_VENDOR_ROOT})")
    parser_vendor_import.set_defaults(
        func=lambda args: import_compiled_vendor_theme(args.name, args.vendor_root, args.vendor_theme)
    )

    parser_vendor_import_all = subparsers.add_parser(
        "vendor-import-all",
        help="Compile and import every vendor theme directory into the repo SmartMonitor library",
    )
    parser_vendor_import_all.add_argument("--vendor-root", type=Path, default=DEFAULT_VENDOR_ROOT,
                                          help=f"Vendor theme root (default: {DEFAULT_VENDOR_ROOT})")
    parser_vendor_import_all.set_defaults(
        func=lambda args: import_all_compiled_vendor_themes(args.vendor_root)
    )

    parser_vendor_import_activate = subparsers.add_parser(
        "vendor-import-activate",
        help="Compile a vendor theme, import it into the repo library, and activate it",
    )
    parser_vendor_import_activate.add_argument("name", help="Installed theme name")
    parser_vendor_import_activate.add_argument("vendor_theme", help="Vendor theme directory name")
    parser_vendor_import_activate.add_argument("--vendor-root", type=Path, default=DEFAULT_VENDOR_ROOT,
                                               help=f"Vendor theme root (default: {DEFAULT_VENDOR_ROOT})")

    def _vendor_import_activate(args):
        import_compiled_vendor_theme(args.name, args.vendor_root, args.vendor_theme)
        activate_theme(args.name)

    parser_vendor_import_activate.set_defaults(func=_vendor_import_activate)

    parser_import = subparsers.add_parser("import", help="Import a ready img.dat into the repo theme library")
    parser_import.add_argument("name", help="Installed theme name")
    parser_import.add_argument("img_dat", type=Path, help="Path to img.dat")
    parser_import.set_defaults(func=lambda args: import_theme(args.name, args.img_dat))

    parser_activate = subparsers.add_parser("activate", help="Activate installed theme in config.yaml")
    parser_activate.add_argument("name", help="Installed theme name")
    parser_activate.set_defaults(func=lambda args: activate_theme(args.name))

    parser_upload = subparsers.add_parser("upload", help="Upload installed theme to the monitor by theme name")
    parser_upload.add_argument("name", help="Installed theme name")
    parser_upload.add_argument("--port", default="AUTO", help="hidraw path or AUTO")
    parser_upload.set_defaults(func=lambda args: upload_theme(args.name, args.port))

    parser_import_activate = subparsers.add_parser(
        "import-activate",
        help="Import a ready img.dat into the repo library and activate it in config.yaml",
    )
    parser_import_activate.add_argument("name", help="Installed theme name")
    parser_import_activate.add_argument("img_dat", type=Path, help="Path to img.dat")

    def _import_activate(args):
        import_theme(args.name, args.img_dat)
        activate_theme(args.name)

    parser_import_activate.set_defaults(func=_import_activate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
