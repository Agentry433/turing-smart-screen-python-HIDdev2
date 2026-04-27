#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later
#
# turing-smart-screen-python - a Python system monitor and library for USB-C displays like Turing Smart Screen or XuanFang
# https://github.com/mathoudebine/turing-smart-screen-python/
#
# Copyright (C) 2021 Matthieu Houdebine (mathoudebine)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# This file is the system monitor configuration GUI

from library.pythoncheck import check_python_version
check_python_version()

import glob
import hashlib
import os
import platform
import shlex
import shutil
import subprocess
import sys
import webbrowser
import requests
import babel
from typing import Any
from datetime import datetime, timezone
from library.smartmonitor_compile import compile_theme_file
from library.smartmonitor_classic_theme_convert import (
    convert_classic_theme_to_smartmonitor_project,
    find_classic_theme_files,
)
from library.smartmonitor_ui import encode_ui_file, parse_theme_bundle, resolve_theme_path

try:
    import tkinter.ttk as ttk
    from tkinter import *
    from tkinter import filedialog, messagebox, simpledialog
    from PIL import ImageTk
    import psutil
    import ruamel.yaml
    import sv_ttk
    from pathlib import Path
    from PIL import Image
    from serial.tools.list_ports import comports
    from tktooltip import ToolTip
except Exception as e:
    print("""Import error: %s
Please follow start guide to install required packages: https://github.com/mathoudebine/turing-smart-screen-python/wiki/System-monitor-:-how-to-start
Or the troubleshooting page: https://github.com/mathoudebine/turing-smart-screen-python/wiki/Troubleshooting#all-os-tkinter-dependency-not-installed""" % str(
        e))
    try:
        sys.exit(0)
    except:
        os._exit(0)

from library.sensors.sensors_python import sensors_fans, is_cpu_fan

TURING_MODEL = "Turing Smart Screen"
USBPCMONITOR_MODEL = "UsbPCMonitor"
XUANFANG_MODEL = "XuanFang rev. B & flagship"
KIPYE_MODEL = "Kipye Qiye Smart Display"
USB_HID_MODEL = "SmartMonitor HID (experimental)"
WEACT_MODEL = "WeAct Studio Display FS V1"
SIMULATED_MODEL = "Simulated screen"

SIZE_3_5_INCH = "3.5\""
SIZE_5_INCH = "5\""
SIZE_8_8_INCH = "8.8\""
SIZE_2_1_INCH = "2.1\""  # Only for retro compatibility
SIZE_2_x_INCH = "2.1\" / 2.8\""
SIZE_0_96_INCH = "0.96\""

size_list = (SIZE_0_96_INCH, SIZE_2_x_INCH, SIZE_3_5_INCH, SIZE_5_INCH, SIZE_8_8_INCH)

# Maps between config.yaml values and GUI description
revision_and_size_to_model_map = {
    ('A', SIZE_3_5_INCH): TURING_MODEL,  # Can also be UsbPCMonitor 3.5, does not matter since protocol is the same
    ('A_HID', SIZE_3_5_INCH): USB_HID_MODEL,
    ('A', SIZE_5_INCH): USBPCMONITOR_MODEL,
    ('B', SIZE_3_5_INCH): XUANFANG_MODEL,
    ('C', SIZE_2_x_INCH): TURING_MODEL,
    ('C', SIZE_5_INCH): TURING_MODEL,
    ('C', SIZE_8_8_INCH): TURING_MODEL,
    ('D', SIZE_3_5_INCH): KIPYE_MODEL,
    ('WEACT_A', SIZE_3_5_INCH): WEACT_MODEL,
    ('WEACT_B', SIZE_0_96_INCH): WEACT_MODEL,
    ('SIMU', SIZE_0_96_INCH): SIMULATED_MODEL,
    ('SIMU', SIZE_2_x_INCH): SIMULATED_MODEL,
    ('SIMU', SIZE_3_5_INCH): SIMULATED_MODEL,
    ('SIMU', SIZE_5_INCH): SIMULATED_MODEL,
    ('SIMU', SIZE_8_8_INCH): SIMULATED_MODEL,
}
model_and_size_to_revision_map = {
    (TURING_MODEL, SIZE_3_5_INCH): 'A',
    (USBPCMONITOR_MODEL, SIZE_3_5_INCH): 'A',
    (USB_HID_MODEL, SIZE_3_5_INCH): 'A_HID',
    (USBPCMONITOR_MODEL, SIZE_5_INCH): 'A',
    (XUANFANG_MODEL, SIZE_3_5_INCH): 'B',
    (TURING_MODEL, SIZE_2_x_INCH): 'C',
    (TURING_MODEL, SIZE_5_INCH): 'C',
    (TURING_MODEL, SIZE_8_8_INCH): 'C',
    (KIPYE_MODEL, SIZE_3_5_INCH): 'D',
    (WEACT_MODEL, SIZE_3_5_INCH): 'WEACT_A',
    (WEACT_MODEL, SIZE_0_96_INCH): 'WEACT_B',
    (SIMULATED_MODEL, SIZE_0_96_INCH): 'SIMU',
    (SIMULATED_MODEL, SIZE_2_x_INCH): 'SIMU',
    (SIMULATED_MODEL, SIZE_3_5_INCH): 'SIMU',
    (SIMULATED_MODEL, SIZE_5_INCH): 'SIMU',
    (SIMULATED_MODEL, SIZE_8_8_INCH): 'SIMU',
}
hw_lib_map = {"AUTO": "Automatic", "LHM": "LibreHardwareMonitor (admin.)", "PYTHON": "Python libraries",
              "STUB": "Fake random data", "STATIC": "Fake static data"}
reverse_map = {False: "classic", True: "reverse"}
weather_unit_map = {"metric": "metric - °C", "imperial": "imperial - °F", "standard": "standard - °K"}
weather_lang_map = {"sq": "Albanian", "af": "Afrikaans", "ar": "Arabic", "az": "Azerbaijani", "eu": "Basque",
                    "be": "Belarusian", "bg": "Bulgarian", "ca": "Catalan", "zh_cn": "Chinese Simplified",
                    "zh_tw": "Chinese Traditional", "hr": "Croatian", "cz": "Czech", "da": "Danish", "nl": "Dutch",
                    "en": "English", "fi": "Finnish", "fr": "French", "gl": "Galician", "de": "German", "el": "Greek",
                    "he": "Hebrew", "hi": "Hindi", "hu": "Hungarian", "is": "Icelandic", "id": "Indonesian",
                    "it": "Italian", "ja": "Japanese", "kr": "Korean", "ku": "Kurmanji (Kurdish)", "la": "Latvian",
                    "lt": "Lithuanian", "mk": "Macedonian", "no": "Norwegian", "fa": "Persian (Farsi)", "pl": "Polish",
                    "pt": "Portuguese", "pt_br": "Português Brasil", "ro": "Romanian", "ru": "Russian", "sr": "Serbian",
                    "sk": "Slovak", "sl": "Slovenian", "sp": "Spanish", "sv": "Swedish", "th": "Thai", "tr": "Turkish",
                    "ua": "Ukrainian", "vi": "Vietnamese", "zu": "Zulu"}

MAIN_DIRECTORY = str(Path(__file__).parent.resolve()) + "/"
THEMES_DIR = MAIN_DIRECTORY + 'res/themes'
SMARTMONITOR_THEMES_DIR = MAIN_DIRECTORY + 'res/smartmonitor/themes'
AUTOSTART_SERVICE_NAME = "turing-smart-screen-python.service"
PREFERRED_VENV_PYTHON = Path(MAIN_DIRECTORY) / "venv" / "bin" / "python"
CONFIGURE_RUN_MONITOR_EXIT_CODE = 42
DEFAULT_SMARTMONITOR_PROJECTS_DIR = os.path.join(MAIN_DIRECTORY, "res", "smartmonitor", "projects")
DEFAULT_SMARTMONITOR_VENDOR_THEME_ROOT = (
    os.path.join(MAIN_DIRECTORY, "vendor", "themefor3.5")
    if os.path.isdir(os.path.join(MAIN_DIRECTORY, "vendor", "themefor3.5"))
    else (
        os.path.join(MAIN_DIRECTORY, "WIND", "3.5 Inch SmartMonitor", "themefor3.5")
        if os.path.isdir(os.path.join(MAIN_DIRECTORY, "WIND", "3.5 Inch SmartMonitor", "themefor3.5"))
        else DEFAULT_SMARTMONITOR_PROJECTS_DIR
    )
)

SMARTMONITOR_UI_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<ui>
  <widgetParent objectName="background" type="1">
    <geometry>
      <x>0</x>
      <y>0</y>
      <width>480</width>
      <height>320</height>
    </geometry>
    <backgroundType>1</backgroundType>
    <backgroundColor>0xff0f1720</backgroundColor>
    <backgroundImagePath>./images/background.png</backgroundImagePath>
    <imageDelay>100</imageDelay>
  </widgetParent>
  <widget globalID="0" sameTypeID="0" parentName="background" objectName="DateTime 0" type="6">
    <geometry>
      <x>24</x>
      <y>18</y>
      <width>150</width>
      <height>28</height>
    </geometry>
    <font>
      <text>12:00:00</text>
      <fontName>Arial</fontName>
      <fontColor>0xffffffff</fontColor>
      <fontSize>18</fontSize>
      <bold>1</bold>
      <italic>0</italic>
    </font>
    <dateTimeFormat>hh:nn:ss</dateTimeFormat>
    <hAlign>1</hAlign>
  </widget>
  <widget globalID="1" sameTypeID="1" parentName="background" objectName="DateTime 1" type="6">
    <geometry>
      <x>24</x>
      <y>50</y>
      <width>170</width>
      <height>24</height>
    </geometry>
    <font>
      <text>2026-01-01</text>
      <fontName>Arial</fontName>
      <fontColor>0xffcbd5e1</fontColor>
      <fontSize>14</fontSize>
      <bold>1</bold>
      <italic>0</italic>
    </font>
    <dateTimeFormat>yyyy-mm-dd</dateTimeFormat>
    <hAlign>1</hAlign>
  </widget>
  <widget globalID="2" sameTypeID="0" parentName="background" objectName="Number 0" type="5">
    <geometry>
      <x>32</x>
      <y>110</y>
      <width>96</width>
      <height>48</height>
    </geometry>
    <font>
      <text>42</text>
      <fontName>Arial</fontName>
      <fontColor>0xffffffff</fontColor>
      <fontSize>26</fontSize>
      <bold>1</bold>
      <italic>0</italic>
    </font>
    <sensor>
      <fastSensor>1</fastSensor>
      <sensorTypeName>Temperature</sensorTypeName>
      <sensorName>CPU</sensorName>
      <readingName>CPU Package</readingName>
      <isDiv1204>0</isDiv1204>
    </sensor>
    <hAlign>1</hAlign>
  </widget>
  <widget globalID="3" sameTypeID="1" parentName="background" objectName="Number 1" type="5">
    <geometry>
      <x>176</x>
      <y>110</y>
      <width>96</width>
      <height>48</height>
    </geometry>
    <font>
      <text>42</text>
      <fontName>Arial</fontName>
      <fontColor>0xffffffff</fontColor>
      <fontSize>26</fontSize>
      <bold>1</bold>
      <italic>0</italic>
    </font>
    <sensor>
      <fastSensor>5</fastSensor>
      <sensorTypeName>Temperature</sensorTypeName>
      <sensorName>GPU</sensorName>
      <readingName>GPU Temperature</readingName>
      <isDiv1204>0</isDiv1204>
    </sensor>
    <hAlign>1</hAlign>
  </widget>
  <widget globalID="4" sameTypeID="2" parentName="background" objectName="Number 2" type="5">
    <geometry>
      <x>320</x>
      <y>110</y>
      <width>96</width>
      <height>48</height>
    </geometry>
    <font>
      <text>42</text>
      <fontName>Arial</fontName>
      <fontColor>0xffffffff</fontColor>
      <fontSize>26</fontSize>
      <bold>1</bold>
      <italic>0</italic>
    </font>
    <sensor>
      <fastSensor>12</fastSensor>
      <sensorTypeName>Other</sensorTypeName>
      <sensorName>System</sensorName>
      <readingName>Physical Memory Load</readingName>
      <isDiv1204>0</isDiv1204>
    </sensor>
    <hAlign>1</hAlign>
  </widget>
  <widget globalID="5" sameTypeID="3" parentName="background" objectName="Number 3" type="5">
    <geometry>
      <x>32</x>
      <y>220</y>
      <width>96</width>
      <height>48</height>
    </geometry>
    <font>
      <text>42</text>
      <fontName>Arial</fontName>
      <fontColor>0xffffffff</fontColor>
      <fontSize>26</fontSize>
      <bold>1</bold>
      <italic>0</italic>
    </font>
    <sensor>
      <fastSensor>3</fastSensor>
      <sensorTypeName>Usage</sensorTypeName>
      <sensorName>CPU</sensorName>
      <readingName>Total CPU Usage</readingName>
      <isDiv1204>0</isDiv1204>
    </sensor>
    <hAlign>1</hAlign>
  </widget>
</ui>
"""

circular_mask = Image.open(MAIN_DIRECTORY + "res/backgrounds/circular-mask.png")

def get_theme_data(name: str):
    dir = os.path.join(THEMES_DIR, name)
    # checking if it is a directory
    if os.path.isdir(dir):
        # Check if a theme.yaml file exists
        theme = os.path.join(dir, 'theme.yaml')
        if os.path.isfile(theme):
            # Get display size from theme.yaml
            with open(theme, "rt", encoding='utf8') as stream:
                theme_data, ind, bsi = ruamel.yaml.util.load_yaml_guess_indent(stream)
                return theme_data
    return None


def get_themes(size: str):
    themes = []
    for filename in os.listdir(THEMES_DIR):
        theme_data = get_theme_data(filename)
        if theme_data and theme_data['display'].get("DISPLAY_SIZE", '3.5"') == size:
            themes.append(filename)
    return sorted(themes, key=str.casefold)


def get_theme_size(name: str) -> str:
    theme_data = get_theme_data(name)
    return theme_data['display'].get("DISPLAY_SIZE", '3.5"')


def get_sizes_for_model(model: str):
    return [size for size in size_list if (model, size) in model_and_size_to_revision_map]


def sanitize_smartmonitor_theme_name(name: str) -> str:
    name = name.strip()
    if not name:
        return ""

    safe = []
    for ch in name:
        if ch.isalnum() or ch in ("-", "_", ".", " "):
            safe.append(ch)
        else:
            safe.append("_")
    return "".join(safe).strip()


def autostart_supported() -> bool:
    return platform.system() == "Linux"


def autostart_service_dir() -> Path:
    return Path.home() / ".config" / "systemd" / "user"


def autostart_service_path() -> Path:
    return autostart_service_dir() / AUTOSTART_SERVICE_NAME


def autostart_service_template_path() -> Path:
    return Path(MAIN_DIRECTORY) / "tools" / AUTOSTART_SERVICE_NAME


def preferred_python_exec() -> Path:
    if PREFERRED_VENV_PYTHON.is_file() and os.access(PREFERRED_VENV_PYTHON, os.X_OK):
        return PREFERRED_VENV_PYTHON.resolve()
    return Path(sys.executable).resolve()


def render_autostart_service() -> str:
    launcher_script = (Path(MAIN_DIRECTORY) / "run-monitor.sh").resolve()
    working_dir = Path(MAIN_DIRECTORY).resolve()
    command = f"cd {shlex.quote(str(working_dir))} && exec {shlex.quote(str(launcher_script))}"
    return "\n".join([
        "[Unit]",
        "Description=Turing Smart Screen Python HIDdev",
        "After=graphical-session.target network-online.target",
        "Wants=graphical-session.target network-online.target",
        "",
        "[Service]",
        "Type=simple",
        f"WorkingDirectory={working_dir}",
        f"ExecStart=/bin/bash -lc {shlex.quote(command)}",
        "Restart=on-failure",
        "RestartSec=3",
        "Environment=PYTHONUNBUFFERED=1",
        "",
        "[Install]",
        "WantedBy=default.target",
        "",
    ])


def write_autostart_service_file() -> Path:
    service_dir = autostart_service_dir()
    service_dir.mkdir(parents=True, exist_ok=True)
    service_path = autostart_service_path()
    service_path.write_text(render_autostart_service(), encoding="utf-8")
    return service_path


def is_autostart_enabled() -> bool:
    if not autostart_supported():
        return False
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-enabled", AUTOSTART_SERVICE_NAME],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        return result.returncode == 0 and result.stdout.strip() == "enabled"
    except Exception:
        return autostart_service_path().is_file()


def enable_autostart_service():
    service_path = write_autostart_service_file()
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", "--now", AUTOSTART_SERVICE_NAME], check=True)
    return service_path


def disable_autostart_service():
    subprocess.run(["systemctl", "--user", "disable", "--now", AUTOSTART_SERVICE_NAME], check=False)
    service_path = autostart_service_path()
    if service_path.exists():
        service_path.unlink()
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)


def smartmonitor_theme_dir(name: str) -> str:
    return os.path.join(SMARTMONITOR_THEMES_DIR, name)


def smartmonitor_theme_img(name: str) -> str:
    return os.path.join(smartmonitor_theme_dir(name), "img.dat")


def smartmonitor_theme_metadata(name: str) -> str:
    return os.path.join(smartmonitor_theme_dir(name), "metadata.yaml")


def smartmonitor_bundled_dat_path(name: str) -> str:
    return os.path.join(THEMES_DIR, f"{name}.dat")


def write_smartmonitor_theme_metadata(theme_name: str, metadata: dict):
    with open(smartmonitor_theme_metadata(theme_name), "w", encoding="utf-8") as stream:
        ruamel.yaml.YAML().dump(metadata, stream)


def import_smartmonitor_img_dat(theme_name: str, source_img_path: str, metadata: dict | None = None):
    os.makedirs(smartmonitor_theme_dir(theme_name), exist_ok=True)
    target_img = smartmonitor_theme_img(theme_name)
    shutil.copy2(source_img_path, target_img)
    shutil.copy2(source_img_path, smartmonitor_bundled_dat_path(theme_name))

    info = {
        "name": theme_name,
        "source_file": str(Path(source_img_path).resolve()),
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "size": os.path.getsize(target_img),
        "sha256": compute_file_sha256(target_img),
    }
    if metadata:
        info.update(metadata)
    write_smartmonitor_theme_metadata(theme_name, info)
    return target_img


def find_vendor_theme_ui(theme_dir: str) -> str | None:
    try:
        ui_files = sorted(
            filename for filename in os.listdir(theme_dir)
            if filename.lower().endswith(".ui") and os.path.isfile(os.path.join(theme_dir, filename))
        )
    except OSError:
        return None
    if not ui_files:
        return None
    return os.path.join(theme_dir, ui_files[0])


def compile_and_import_smartmonitor_ui(theme_name: str, ui_path: str):
    compiled_dir = smartmonitor_theme_dir(theme_name)
    os.makedirs(compiled_dir, exist_ok=True)
    target_img = smartmonitor_theme_img(theme_name)
    compiled = compile_theme_file(ui_path)
    with open(target_img, "wb") as stream:
        stream.write(compiled)
    shutil.copy2(target_img, smartmonitor_bundled_dat_path(theme_name))
    write_smartmonitor_theme_metadata(
        theme_name,
        {
            "name": theme_name,
            "source_ui": str(Path(ui_path).resolve()),
            "compiled_at": datetime.now(timezone.utc).isoformat(),
            "compiler": "experimental_ui_to_imgdat",
            "size": os.path.getsize(target_img),
            "sha256": compute_file_sha256(target_img),
        },
    )
    return target_img


def compile_and_import_classic_theme(theme_name: str, classic_theme_path: str):
    project_root = Path(DEFAULT_SMARTMONITOR_PROJECTS_DIR) / "classic-converted"
    result = convert_classic_theme_to_smartmonitor_project(
        classic_theme_path,
        project_root,
        project_name=theme_name,
    )
    compiled = compile_theme_file(result.ui_path)
    theme_dir = Path(smartmonitor_theme_dir(theme_name))
    os.makedirs(theme_dir, exist_ok=True)
    target_img = smartmonitor_theme_img(theme_name)
    with open(target_img, "wb") as stream:
        stream.write(compiled)
    shutil.copy2(target_img, smartmonitor_bundled_dat_path(theme_name))

    editable_project_dir = theme_dir / "source"
    if editable_project_dir.exists():
        shutil.rmtree(editable_project_dir)
    shutil.copytree(result.output_dir, editable_project_dir)
    editable_ui_path = editable_project_dir / result.ui_path.name

    write_smartmonitor_theme_metadata(
        theme_name,
        {
            "name": theme_name,
            "source_theme": str(Path(classic_theme_path).resolve()),
            "source_ui": str(editable_ui_path.resolve()),
            "source_project": str(editable_project_dir.resolve()),
            "compiled_at": datetime.now(timezone.utc).isoformat(),
            "compiler": "classic_theme_to_imgdat",
            "size": os.path.getsize(target_img),
            "sha256": compute_file_sha256(target_img),
        },
    )
    return target_img, result


def compile_and_import_classic_theme_batch(classic_root: str) -> tuple[list[str], list[str], list[tuple[str, Any]]]:
    imported: list[str] = []
    failed: list[str] = []
    results: list[tuple[str, Any]] = []

    for theme_yaml in find_classic_theme_files(classic_root):
        theme_name = sanitize_smartmonitor_theme_name(theme_yaml.parent.name)
        try:
            _, result = compile_and_import_classic_theme(theme_name, str(theme_yaml))
            imported.append(theme_name)
            results.append((theme_name, result))
        except Exception as exc:
            failed.append(f"{theme_yaml.parent.name}: {exc}")

    return imported, failed, results


def create_smartmonitor_ui_project(project_dir: str, project_name: str):
    project_path = Path(project_dir)
    images_dir = project_path / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    background_path = images_dir / "background.png"
    if not background_path.exists():
        background = Image.new("RGB", (480, 320), color="#0f1720")
        background.save(background_path)

    config_path = project_path / "config.ini"
    if not config_path.exists():
        config_path.write_text(
            "[StartupPic]\n"
            "path=./images/background.png\n"
            "totalMs=1000\n"
            "delayMs=1000\n"
            "bgColor=0xff0f1720\n",
            encoding="utf-8",
        )

    ui_path = project_path / f"{project_name}.ui"
    encode_ui_file(ui_path, SMARTMONITOR_UI_TEMPLATE)

    readme_path = project_path / "README.txt"
    if not readme_path.exists():
        readme_path.write_text(
            "SmartMonitor custom UI project\n\n"
            "Files:\n"
            "- *.ui: encrypted vendor-style UI source\n"
            "- config.ini: startup image settings\n"
            "- images/background.png: initial background\n\n"
            "Workflow:\n"
            "1. Edit the UI source or replace images.\n"
            "2. In configure.py choose SmartMonitor HID.\n"
            "3. Click 'Convert UI->DAT' and select this .ui file.\n"
            "4. Save and run to upload the compiled theme.\n",
            encoding="utf-8",
        )

    return ui_path


def import_all_smartmonitor_vendor_themes(vendor_root: str) -> tuple[list[str], list[str]]:
    imported = []
    failed = []
    if not os.path.isdir(vendor_root):
        return imported, [f"Vendor theme root not found: {vendor_root}"]

    for entry in sorted(os.listdir(vendor_root), key=str.casefold):
        theme_dir = os.path.join(vendor_root, entry)
        if not os.path.isdir(theme_dir) or not entry.startswith("theme"):
            continue

        ui_path = find_vendor_theme_ui(theme_dir)
        if not ui_path:
            failed.append(f"{entry}: missing .ui")
            continue

        theme_name = sanitize_smartmonitor_theme_name(entry)
        try:
            compile_and_import_smartmonitor_ui(theme_name, ui_path)
            imported.append(theme_name)
        except Exception as exc:
            failed.append(f"{entry}: {exc}")

    return imported, failed


def get_smartmonitor_library_themes():
    themes = []
    if not os.path.isdir(SMARTMONITOR_THEMES_DIR):
        return themes

    for filename in os.listdir(SMARTMONITOR_THEMES_DIR):
        if os.path.isfile(smartmonitor_theme_img(filename)):
            themes.append(filename)
    return sorted(themes, key=str.casefold)


def get_smartmonitor_bundled_dat_themes():
    themes = []
    if not os.path.isdir(THEMES_DIR):
        return themes

    for filename in os.listdir(THEMES_DIR):
        full_path = os.path.join(THEMES_DIR, filename)
        if os.path.isfile(full_path) and filename.lower().endswith(".dat"):
            themes.append(filename)
    return sorted(themes, key=str.casefold)


def get_smartmonitor_themes():
    bundled = list(get_smartmonitor_bundled_dat_themes())
    bundled_stems = {Path(filename).stem.casefold() for filename in bundled}
    names = list(bundled)
    for library_name in get_smartmonitor_library_themes():
        if library_name.casefold() in bundled_stems:
            continue
        names.append(library_name)
    return sorted(names, key=str.casefold)


def resolve_smartmonitor_theme_path(name: str):
    if not name:
        return ""

    bundled_candidates = []
    if str(name).lower().endswith(".dat"):
        bundled_candidates.append(os.path.join(THEMES_DIR, name))
    else:
        bundled_candidates.append(os.path.join(THEMES_DIR, f"{name}.dat"))
        bundled_candidates.append(os.path.join(THEMES_DIR, name))

    for bundled_path in bundled_candidates:
        if os.path.isfile(bundled_path) and bundled_path.lower().endswith(".dat"):
            return bundled_path

    library_path = smartmonitor_theme_img(name)
    if os.path.isfile(library_path):
        return library_path

    return ""


def get_smartmonitor_theme_info(name: str):
    resolved_path = resolve_smartmonitor_theme_path(name)
    if not resolved_path:
        return {}

    metadata_name = Path(resolved_path).stem if resolved_path.lower().endswith(".dat") else name

    metadata_file = smartmonitor_theme_metadata(metadata_name)
    if os.path.isfile(metadata_file):
        with open(metadata_file, "rt", encoding="utf8") as stream:
            info, ind, bsi = ruamel.yaml.util.load_yaml_guess_indent(stream)
            return info or {}

    if os.path.abspath(resolved_path).startswith(os.path.abspath(SMARTMONITOR_THEMES_DIR) + os.sep):
        metadata_file = smartmonitor_theme_metadata(name)
        if not os.path.isfile(metadata_file):
            return {}
        with open(metadata_file, "rt", encoding="utf8") as stream:
            info, ind, bsi = ruamel.yaml.util.load_yaml_guess_indent(stream)
            return info or {}

    return {
        "name": name,
        "source_file": resolved_path,
        "size": os.path.getsize(resolved_path),
        "sha256": compute_file_sha256(resolved_path),
    }


def get_smartmonitor_theme_source_ui(name: str):
    info = get_smartmonitor_theme_info(name)
    source_ui = info.get("source_ui")
    if source_ui and os.path.isfile(source_ui):
        return source_ui
    return ""


def describe_smartmonitor_theme(info: dict, theme_name: str) -> tuple[str, str, str]:
    compiler = (info.get("compiler") or "").strip()
    source_vendor_theme = (info.get("source_vendor_theme") or "").strip()
    source_theme = (info.get("source_theme") or "").strip()
    source_ui = (info.get("source_ui") or "").strip()

    theme_lower = str(theme_name or "").lower()

    if compiler == "classic_theme_to_imgdat":
        kind = "classic-converted"
        runtime = "best-effort runtime"
    elif compiler == "experimental_ui_to_imgdat":
        kind = "vendor-compiled" if source_vendor_theme else "compiled"
        runtime = "experimental runtime"
    elif source_vendor_theme or "vendor" in theme_lower:
        kind = "vendor"
        runtime = "mapped runtime"
    else:
        kind = "bundled dat"
        runtime = "runtime unknown"

    details = []
    if compiler:
        details.append(f"Compiler: {compiler}")
    if source_vendor_theme:
        details.append(f"Vendor source: {source_vendor_theme}")
    elif source_theme:
        details.append(f"Classic source: {Path(source_theme).name}")
    elif info.get("source_file"):
        details.append(f"Source file: {Path(info['source_file']).name}")

    source_line = ""
    if source_ui:
        source_line = f"Linked UI: {Path(source_ui).name}"

    return f"Kind: {kind} | {runtime}", " | ".join(details), source_line


def get_smartmonitor_theme_runtime_summary(name: str) -> str:
    source_ui = get_smartmonitor_theme_source_ui(name)
    if not source_ui:
        return ""

    try:
        bundle = parse_theme_bundle(source_ui)
    except Exception:
        return ""

    metric_labels: dict[int, str] = {}
    for widget in bundle.theme.widgets:
        if widget.sensor is None or widget.sensor.fast_sensor < 0:
            continue
        label = widget.sensor.reading_name or widget.sensor.sensor_name or widget.object_name
        metric_labels.setdefault(int(widget.sensor.fast_sensor), str(label))

    if not metric_labels:
        return ""

    ordered = sorted(metric_labels.items(), key=lambda item: item[0])
    preview = ", ".join(f"{tag}:{label}" for tag, label in ordered[:8])
    if len(ordered) > 8:
        preview += ", ..."
    return f"Runtime tags: {preview}"


def build_smartmonitor_preview(theme_name: str) -> Image.Image | None:
    source_ui = get_smartmonitor_theme_source_ui(theme_name)
    if not source_ui:
        return None

    try:
        bundle = parse_theme_bundle(source_ui)
    except Exception:
        return None

    base_dir = Path(bundle.base_dir)
    width = 480
    height = 320
    if bundle.theme.widget_parents:
        width = max(1, bundle.theme.widget_parents[0].geometry.width or width)
        height = max(1, bundle.theme.widget_parents[0].geometry.height or height)

    canvas = Image.new("RGBA", (width, height), (15, 23, 32, 255))

    if bundle.theme.widget_parents:
        parent = bundle.theme.widget_parents[0]
        if parent.background_image_path:
            try:
                bg_path = resolve_theme_path(base_dir, parent.background_image_path)
                with Image.open(bg_path) as bg_image:
                    bg = bg_image.convert("RGBA").resize((width, height), Image.Resampling.LANCZOS)
                    canvas.alpha_composite(bg, (0, 0))
            except Exception:
                pass

    for widget in bundle.theme.widgets:
        if widget.widget_type != 4 or widget.style is None or not widget.style.bg_image_path:
            continue
        try:
            image_path = resolve_theme_path(base_dir, widget.style.bg_image_path)
            with Image.open(image_path) as image:
                rendered = image.convert("RGBA").resize(
                    (max(1, widget.geometry.width), max(1, widget.geometry.height)),
                    Image.Resampling.LANCZOS,
                )
                canvas.alpha_composite(rendered, (widget.geometry.x, widget.geometry.y))
        except Exception:
            continue

    return canvas.convert("RGB")


def get_smartmonitor_theme_name_from_path(path: str):
    if not path:
        return None

    try:
        wanted = Path(path).expanduser().resolve()
    except Exception:
        return None

    for theme_name in get_smartmonitor_themes():
        try:
            candidate_path = resolve_smartmonitor_theme_path(theme_name)
            if not candidate_path:
                continue
            candidate = Path(candidate_path).resolve()
        except Exception:
            continue
        if candidate == wanted:
            return theme_name
    return None


def compute_file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def get_com_ports():
    com_ports_names = ["Automatic detection"]  # Add manual entry on top for automatic detection
    com_ports = comports()
    for com_port in com_ports:
        com_ports_names.append(com_port.name)
    if platform.system() == "Linux":
        for hidraw_path in sorted(glob.glob("/dev/hidraw*")):
            com_ports_names.append(hidraw_path)
    return com_ports_names


def get_net_if():
    if_list = list(psutil.net_if_addrs().keys())
    if_list.insert(0, "None")  # Add manual entry on top for unavailable/not selected interface
    return if_list


def get_fans():
    fan_list = list()
    auto_detected_cpu_fan = "None"
    for name, entries in sensors_fans().items():
        for entry in entries:
            fan_list.append("%s/%s (%d%% - %d RPM)" % (name, entry.label, entry.percent, entry.current))
            if (is_cpu_fan(entry.label) or is_cpu_fan(name)) and auto_detected_cpu_fan == "None":
                auto_detected_cpu_fan = "Auto-detected: %s/%s" % (name, entry.label)

    fan_list.insert(0, auto_detected_cpu_fan)  # Add manual entry on top if auto-detection succeeded
    return fan_list


class TuringConfigWindow:
    def __init__(self):
        self.window = Tk()
        self.run_main_after_exit = False
        self.window.title('Turing System Monitor configuration')
        self.window.geometry("940x980")
        self.window.iconphoto(True, PhotoImage(file=MAIN_DIRECTORY + "res/icons/monitor-icon-17865/64.png"))
        # When window gets focus again, reload theme preview in case it has been updated by theme editor
        self.window.bind("<FocusIn>", self.on_theme_change)
        self.window.after(0, self.on_fan_speed_update)

        # Subwindow for weather/ping config.
        self.more_config_window = MoreConfigWindow(self)

        # Make TK look better with Sun Valley ttk theme
        sv_ttk.set_theme("light")

        self.theme_preview_img = None
        self.theme_preview = ttk.Label(self.window)
        self.theme_preview.place(x=10, y=10)

        self.theme_author = ttk.Label(self.window)
        self.smartmonitor_info_box = Text(self.window, wrap=WORD, height=7)
        self.smartmonitor_info_box.place(x=10, y=520, width=330, height=180)
        self.smartmonitor_info_box.config(state="disabled")
        self.runtime_tags_frame = ttk.LabelFrame(self.window, text="Runtime tags")
        self.runtime_tags_frame.place(x=10, y=740, width=910, height=210)
        self.runtime_tags_tree = ttk.Treeview(
            self.runtime_tags_frame,
            columns=("tag", "theme_metric", "effective_metric", "reading"),
            show="headings",
            height=6,
            selectmode="browse",
        )
        self.runtime_tags_tree.heading("tag", text="Tag")
        self.runtime_tags_tree.heading("theme_metric", text="Theme metric")
        self.runtime_tags_tree.heading("effective_metric", text="Effective metric")
        self.runtime_tags_tree.heading("reading", text="Sensor / Reading")
        self.runtime_tags_tree.column("tag", width=55, anchor="center")
        self.runtime_tags_tree.column("theme_metric", width=160, anchor="w")
        self.runtime_tags_tree.column("effective_metric", width=170, anchor="w")
        self.runtime_tags_tree.column("reading", width=455, anchor="w")
        self.runtime_tags_tree.place(x=10, y=10, width=870, height=145)
        self.runtime_tags_scroll = ttk.Scrollbar(self.runtime_tags_frame, orient="vertical", command=self.runtime_tags_tree.yview)
        self.runtime_tags_scroll.place(x=880, y=10, height=145)
        self.runtime_tags_tree.configure(yscrollcommand=self.runtime_tags_scroll.set)
        self.runtime_tags_tree.bind("<Button-1>", self.on_runtime_tag_click)
        self.runtime_tags_tree.bind("<Double-1>", self.on_map_runtime_tag_click)
        self.runtime_map_btn = ttk.Button(
            self.runtime_tags_frame,
            text="Map selected",
            command=lambda: self.on_map_runtime_tag_click(),
        )
        self.runtime_map_btn.place(x=10, y=165, width=130, height=30)
        self.runtime_map_tooltip = ToolTip(
            self.runtime_map_btn,
            msg="Assign the selected fastSensor tag to a runtime metric override.",
        )
        self.runtime_clear_btn = ttk.Button(
            self.runtime_tags_frame,
            text="Clear selected",
            command=lambda: self.on_clear_runtime_tag_click(),
        )
        self.runtime_clear_btn.place(x=150, y=165, width=120, height=30)
        self.runtime_clear_tooltip = ToolTip(
            self.runtime_clear_btn,
            msg="Remove the runtime override currently assigned to the selected fastSensor tag.",
        )
        self.runtime_tags_hint = ttk.Label(
            self.runtime_tags_frame,
            text="Theme metric comes from .ui parsing. Effective metric includes manual overrides.",
        )
        self.runtime_tags_hint.place(x=285, y=170)

        sysmon_label = ttk.Label(self.window, text='Display configuration', font='bold')
        sysmon_label.place(x=370, y=0)

        self.model_label = ttk.Label(self.window, text='Smart screen model')
        self.model_label.place(x=370, y=35)
        self.model_cb = ttk.Combobox(self.window, values=list(dict.fromkeys((revision_and_size_to_model_map.values()))),
                                     state='readonly')
        self.model_cb.bind('<<ComboboxSelected>>', self.on_model_change)
        self.model_cb.place(x=550, y=30, width=250)

        self.size_label = ttk.Label(self.window, text='Smart screen size')
        self.size_label.place(x=370, y=75)
        self.size_cb = ttk.Combobox(self.window, values=size_list, state='readonly')
        self.size_cb.bind('<<ComboboxSelected>>', self.on_size_change)
        self.size_cb.place(x=550, y=70, width=250)

        self.com_label = ttk.Label(self.window, text='COM port')
        self.com_label.place(x=370, y=115)
        self.com_cb = ttk.Combobox(self.window, values=get_com_ports(), state='readonly')
        self.com_cb.place(x=550, y=110, width=250)

        self.orient_label = ttk.Label(self.window, text='Orientation')
        self.orient_label.place(x=370, y=155)
        self.orient_cb = ttk.Combobox(self.window, values=list(reverse_map.values()), state='readonly')
        self.orient_cb.place(x=550, y=150, width=250)

        self.brightness_string = StringVar()
        self.brightness_label = ttk.Label(self.window, text='Brightness')
        self.brightness_label.place(x=370, y=195)
        self.brightness_slider = ttk.Scale(self.window, from_=0, to=100, orient=HORIZONTAL,
                                           command=self.on_brightness_change)
        self.brightness_slider.place(x=600, y=195, width=180)
        self.brightness_val_label = ttk.Label(self.window, textvariable=self.brightness_string)
        self.brightness_val_label.place(x=550, y=195)
        self.brightness_warning_label = ttk.Label(self.window,
                                                  text="⚠ Turing 3.5\" displays can get hot at high brightness!",
                                                  foreground='#ff8c00')

        sysmon_label = ttk.Label(self.window, text='System Monitor Configuration', font='bold')
        sysmon_label.place(x=370, y=260)

        self.theme_label = ttk.Label(self.window, text='Theme')
        self.theme_label.place(x=370, y=300)
        self.theme_cb = ttk.Combobox(self.window, state='readonly')
        self.theme_cb.place(x=550, y=295, width=250)
        self.theme_cb.bind('<<ComboboxSelected>>', self.on_theme_change)

        self.hwlib_label = ttk.Label(self.window, text='Hardware monitoring')
        self.hwlib_label.place(x=370, y=340)
        if sys.platform != "win32":
            del hw_lib_map["LHM"]  # LHM is for Windows platforms only
        self.hwlib_cb = ttk.Combobox(self.window, values=list(hw_lib_map.values()), state='readonly')
        self.hwlib_cb.place(x=550, y=335, width=250)
        self.hwlib_cb.bind('<<ComboboxSelected>>', self.on_hwlib_change)

        self.eth_label = ttk.Label(self.window, text='Ethernet interface')
        self.eth_label.place(x=370, y=380)
        self.eth_cb = ttk.Combobox(self.window, values=get_net_if(), state='readonly')
        self.eth_cb.place(x=550, y=375, width=250)

        self.wl_label = ttk.Label(self.window, text='Wi-Fi interface')
        self.wl_label.place(x=370, y=420)
        self.wl_cb = ttk.Combobox(self.window, values=get_net_if(), state='readonly')
        self.wl_cb.place(x=550, y=415, width=250)

        # For Windows platform only
        self.lhm_admin_warning = ttk.Label(self.window,
                                           text="❌ Restart as admin. or select another Hardware monitoring",
                                           foreground='#f00')
        # For platform != Windows
        self.cpu_fan_label = ttk.Label(self.window, text='CPU fan (？)')
        self.cpu_fan_label.config(foreground="#a3a3ff", cursor="hand2")
        self.cpu_fan_cb = ttk.Combobox(self.window, values=get_fans(), state='readonly')

        self.tooltip = ToolTip(self.cpu_fan_label,
                               msg="If \"None\" is selected, CPU fan was not auto-detected.\n"
                                   "Manually select your CPU fan from the list.\n\n"
                                   "Fans missing from the list? Install lm-sensors package\n"
                                   "and run 'sudo sensors-detect' command, then reboot.")

        self.weather_ping_btn = ttk.Button(self.window, text="Weather",
                                           command=lambda: self.on_weatherping_click())
        self.weather_ping_btn.place(x=360, y=585, height=42, width=100)
        self.weather_ping_tooltip = ToolTip(
            self.weather_ping_btn,
            msg="Open extra weather and ping configuration.",
        )

        self.open_theme_folder_btn = ttk.Button(self.window, text="Themes",
                                         command=lambda: self.on_open_theme_folder_click())
        self.open_theme_folder_btn.place(x=470, y=585, height=42, width=100)
        self.open_theme_folder_tooltip = ToolTip(
            self.open_theme_folder_btn,
            msg="Classic mode: open the themes folder.\n"
                "SmartMonitor mode: import all vendor theme_* folders.",
        )

        self.edit_theme_btn = ttk.Button(self.window, text="Edit theme", command=lambda: self.on_theme_editor_click())
        self.edit_theme_btn.place(x=580, y=585, height=42, width=100)
        self.edit_theme_tooltip = ToolTip(
            self.edit_theme_btn,
            msg="Classic mode: open the classic theme editor.\n"
                "SmartMonitor mode: import a ready .dat theme file.",
        )

        self.edit_ui_btn = ttk.Button(
            self.window,
            text="Edit UI",
            command=lambda: self.on_edit_ui_click(),
        )
        self.edit_ui_btn.place(x=690, y=585, height=42, width=100)
        self.edit_ui_tooltip = ToolTip(
            self.edit_ui_btn,
            msg="Open the linked SmartMonitor .ui source in the visual editor,\n"
                "or choose another .ui file manually.",
        )

        self.vendor_convert_btn = ttk.Button(
            self.window,
            text="Vendor UI",
            command=lambda: self.on_smartmonitor_ui_convert_click(),
        )
        self.vendor_convert_btn.place(x=800, y=585, height=42, width=110)
        self.vendor_convert_tooltip = ToolTip(
            self.vendor_convert_btn,
            msg="Compile a vendor SmartMonitor .ui project into a .dat theme\n"
                "and add it to the GUI theme list.",
        )

        self.classic_convert_btn = ttk.Button(
            self.window,
            text="Classic->DAT",
            command=lambda: self.on_smartmonitor_classic_theme_convert_click(),
        )
        self.classic_convert_btn.place(x=360, y=635, height=42, width=110)
        self.classic_convert_tooltip = ToolTip(
            self.classic_convert_btn,
            msg="Convert a classic theme.yaml theme into a SmartMonitor .dat theme.\n"
                "A linked editable .ui project is saved for later editing.",
        )

        self.classic_batch_btn = ttk.Button(
            self.window,
            text="Classic batch",
            command=lambda: self.on_smartmonitor_classic_batch_convert_click(),
        )
        self.classic_batch_btn.place(x=480, y=635, height=42, width=110)
        self.classic_batch_tooltip = ToolTip(
            self.classic_batch_btn,
            msg="Convert every classic theme.yaml found under a folder into\n"
                "SmartMonitor themes and import them into the GUI library.",
        )

        self.new_ui_btn = ttk.Button(
            self.window,
            text="New UI",
            command=lambda: self.on_new_ui_project_click(),
        )
        self.new_ui_btn.place(x=600, y=635, height=42, width=100)
        self.new_ui_tooltip = ToolTip(
            self.new_ui_btn,
            msg="Create a new starter SmartMonitor UI project with background,\n"
                "config.ini and editable encrypted .ui source.",
        )

        self.autostart_enable_btn = ttk.Button(
            self.window,
            text="Autostart ON",
            command=lambda: self.on_enable_autostart_click(),
        )
        self.autostart_enable_btn.place(x=360, y=685, height=42, width=110)
        self.autostart_enable_tooltip = ToolTip(
            self.autostart_enable_btn,
            msg="Enable Linux user autostart via systemd --user.",
        )

        self.autostart_disable_btn = ttk.Button(
            self.window,
            text="Autostart OFF",
            command=lambda: self.on_disable_autostart_click(),
        )
        self.autostart_disable_btn.place(x=480, y=685, height=42, width=110)
        self.autostart_disable_tooltip = ToolTip(
            self.autostart_disable_btn,
            msg="Disable Linux user autostart and remove the user service file.",
        )

        self.force_upload_btn = ttk.Button(
            self.window,
            text="Force upload",
            command=lambda: self.on_force_upload_click(),
        )
        self.force_upload_btn.place(x=710, y=635, height=42, width=110)
        self.force_upload_tooltip = ToolTip(
            self.force_upload_btn,
            msg="Upload the currently selected SmartMonitor .dat theme immediately,\n"
                "without waiting for Save and run.",
        )

        self.doctor_btn = ttk.Button(
            self.window,
            text="Doctor",
            command=lambda: self.on_doctor_click(),
        )
        self.doctor_btn.place(x=830, y=635, height=42, width=80)
        self.doctor_tooltip = ToolTip(
            self.doctor_btn,
            msg="Run first-launch diagnostics: Python packages, config, themes,\n"
                "USB HID visibility and hidraw access.",
        )

        self.save_btn = ttk.Button(self.window, text="Save", command=lambda: self.on_save_click())
        self.save_btn.place(x=600, y=685, height=42, width=90)
        self.save_tooltip = ToolTip(
            self.save_btn,
            msg="Save configuration changes to config.yaml.",
        )

        self.save_run_btn = ttk.Button(self.window, text="Save + run", command=lambda: self.on_saverun_click())
        self.save_run_btn.place(x=700, y=685, height=42, width=120)
        self.save_run_tooltip = ToolTip(
            self.save_run_btn,
            msg="Save config and start/restart the monitor runtime with the selected theme.",
        )

        self.hid_status_label = ttk.Label(self.window, text="")
        self.hid_status_label.place(x=360, y=955)

        self.config = None
        self.load_config_values()
        self.window.after(1500, self.poll_hid_status)

    def run(self):
        self.window.mainloop()
        return CONFIGURE_RUN_MONITOR_EXIT_CODE if self.run_main_after_exit else 0

    def is_smartmonitor_model(self):
        return self.model_cb.get() == USB_HID_MODEL

    def refresh_theme_selector(self):
        if self.is_smartmonitor_model():
            themes = get_smartmonitor_themes()
            self.theme_label.config(text='SmartMonitor theme')
            self.open_theme_folder_btn.config(text="Vendor set")
            self.edit_theme_btn.config(text="Import .dat")
            self.edit_ui_btn.config(text="Edit UI", state="normal")
            self.vendor_convert_btn.config(text="Vendor UI", state="normal")
            self.classic_convert_btn.config(text="Classic->DAT", state="normal")
            self.classic_batch_btn.config(text="Classic batch", state="normal")
            self.new_ui_btn.config(text="New UI", state="normal")
            self.force_upload_btn.config(state="normal")
        else:
            size = self.size_cb.get().replace(SIZE_2_x_INCH, SIZE_2_1_INCH)
            themes = get_themes(size)
            self.theme_label.config(text='Theme')
            self.open_theme_folder_btn.config(text="Themes")
            self.edit_theme_btn.config(text="Edit theme")
            self.edit_ui_btn.config(text="Edit UI", state="disabled")
            self.vendor_convert_btn.config(text="Vendor UI", state="disabled")
            self.classic_convert_btn.config(text="Classic->DAT", state="disabled")
            self.classic_batch_btn.config(text="Classic batch", state="disabled")
            self.new_ui_btn.config(text="New UI", state="disabled")
            self.force_upload_btn.config(state="disabled")

        self.theme_cb.config(values=themes)
        if not themes:
            self.theme_cb.set("")
        elif self.theme_cb.get() not in themes:
            self.theme_cb.set(themes[0])
        self.refresh_autostart_buttons()
        self.refresh_hid_status()

    def refresh_hid_status(self):
        if not self.is_smartmonitor_model():
            self.hid_status_label.config(text="")
            return

        hid_path = ""
        try:
            from library.lcd.lcd_comm_rev_a_hid import LcdCommRevAHid

            selected_port = self.com_cb.get().strip()
            if selected_port.startswith("/dev/hidraw") and os.path.exists(selected_port):
                hid_path = selected_port
            else:
                hid_path = LcdCommRevAHid.auto_detect_com_port() or ""
        except Exception:
            hid_path = ""

        if hid_path and os.path.exists(hid_path):
            if os.access(hid_path, os.R_OK | os.W_OK):
                self.hid_status_label.config(text=f"HID: {hid_path} ready", foreground="#228b22")
            else:
                self.hid_status_label.config(text=f"HID: {hid_path} no access", foreground="#cc8800")
        else:
            self.hid_status_label.config(text="HID: not detected", foreground="#cc0000")

    def set_smartmonitor_info_text(self, text: str):
        self.smartmonitor_info_box.config(state="normal")
        self.smartmonitor_info_box.delete("1.0", END)
        if text:
            self.smartmonitor_info_box.insert("1.0", text)
        self.smartmonitor_info_box.config(state="disabled")

    def current_runtime_tag_overrides(self) -> dict[str, int]:
        if not isinstance(self.config, dict):
            return {}
        display_cfg = self.config.setdefault("display", {})
        raw = display_cfg.get("SMARTMONITOR_HID_TAGS", {}) or {}
        resolved = {}
        for key, value in raw.items():
            try:
                resolved[str(key)] = int(value)
            except Exception:
                continue
        return resolved

    def set_runtime_tag_overrides(self, overrides: dict[str, int]):
        if not isinstance(self.config, dict):
            return
        self.config.setdefault("display", {})["SMARTMONITOR_HID_TAGS"] = dict(sorted(overrides.items()))

    def refresh_runtime_tags_table(self):
        for item_id in self.runtime_tags_tree.get_children():
            self.runtime_tags_tree.delete(item_id)

        if not self.is_smartmonitor_model():
            self.runtime_tags_frame.place_forget()
            return

        self.runtime_tags_frame.place(x=10, y=740, width=910, height=210)
        theme_name = self.theme_cb.get()
        if not theme_name:
            return

        try:
            from library import smartmonitor_runtime as sm_runtime
            rows = sm_runtime.get_theme_runtime_rows(theme_name)
            metric_choices = sm_runtime.get_runtime_metric_choices()
        except Exception:
            rows = []
            metric_choices = []

        overrides = self.current_runtime_tag_overrides()
        tag_to_override = {int(tag): metric for metric, tag in overrides.items()}

        seen_tags: set[int] = set()
        for index, row in enumerate(rows):
            tag = int(row.get("tag", -1))
            if tag < 0:
                continue
            seen_tags.add(tag)
            theme_metric = str(row.get("metric", "") or "")
            effective_metric = tag_to_override.get(tag, theme_metric)
            reading_bits = [part for part in (row.get("sensor_name", ""), row.get("reading_name", "")) if part]
            reading = " / ".join(str(part) for part in reading_bits)
            self.runtime_tags_tree.insert(
                "",
                "end",
                iid=f"tag-{tag}-{index}",
                values=(tag, theme_metric or "-", effective_metric or "-", reading or row.get("object_name", "")),
            )

        for metric_name, tag in sorted(overrides.items(), key=lambda item: (item[1], item[0])):
            tag = int(tag)
            if tag in seen_tags:
                continue
            if metric_choices and metric_name not in metric_choices:
                continue
            self.runtime_tags_tree.insert(
                "",
                "end",
                iid=f"override-{tag}-{metric_name}",
                values=(tag, "-", metric_name, "manual override"),
            )

    def runtime_tag_values_from_event(self, event=None):
        item_id = ""
        if event is not None:
            item_id = self.runtime_tags_tree.identify_row(event.y)
            if item_id:
                self.runtime_tags_tree.selection_set(item_id)
                self.runtime_tags_tree.focus(item_id)

        selection = self.runtime_tags_tree.selection()
        if not selection and item_id:
            selection = (item_id,)
        if not selection:
            return None

        values = self.runtime_tags_tree.item(selection[0], "values")
        if not values:
            return None
        return values

    def on_runtime_tag_click(self, event=None):
        self.runtime_tag_values_from_event(event)
        return "break"

    def poll_hid_status(self):
        try:
            self.refresh_hid_status()
        finally:
            if self.window.winfo_exists():
                self.window.after(2500, self.poll_hid_status)

    def load_theme_preview(self):
        if self.is_smartmonitor_model():
            theme_name = self.theme_cb.get()
            theme_preview = build_smartmonitor_preview(theme_name)
            if theme_preview is None:
                theme_preview = Image.open(MAIN_DIRECTORY + "res/docs/no-preview.png")
            theme_preview.thumbnail((320, 480), Image.Resampling.LANCZOS)
            self.theme_preview_img = ImageTk.PhotoImage(theme_preview)
            self.theme_preview.config(image=self.theme_preview_img)

            info = get_smartmonitor_theme_info(theme_name) if theme_name else {}
            if theme_name:
                source_file = info.get("source_file")
                if source_file:
                    author_text = f"SmartMonitor img.dat: {theme_name} ({Path(source_file).name})"
                else:
                    author_text = f"SmartMonitor img.dat: {theme_name}"
            else:
                author_text = "SmartMonitor img.dat theme is not selected. Import one with the GUI button."

            self.theme_author.config(text=author_text, foreground="#a3a3a3", cursor="")
            self.theme_author.unbind("<Button-1>")
            self.theme_author.place(x=10, y=self.theme_preview_img.height() + 15)

            meta_text, details_text, source_text = describe_smartmonitor_theme(info, theme_name)
            info_lines = [line for line in (meta_text, details_text, source_text) if line]
            self.set_smartmonitor_info_text("\n".join(info_lines))
            runtime_text = get_smartmonitor_theme_runtime_summary(theme_name)
            info_lines = [line for line in (meta_text, details_text, source_text, runtime_text) if line]
            self.set_smartmonitor_info_text("\n".join(info_lines))
            self.smartmonitor_info_box.place(x=10, y=520, width=330, height=180)
            self.refresh_runtime_tags_table()
            return

        theme_data = get_theme_data(self.theme_cb.get())

        try:
            theme_preview = Image.open(MAIN_DIRECTORY + "res/themes/" + self.theme_cb.get() + "/preview.png")

            if theme_data['display'].get("DISPLAY_SIZE", '3.5"') == SIZE_2_1_INCH:
                # This is a circular screen: apply a circle mask over the preview
                theme_preview.paste(circular_mask, mask=circular_mask)
        except:
            theme_preview = Image.open(MAIN_DIRECTORY + "res/docs/no-preview.png")
        finally:
            theme_preview.thumbnail((320, 480), Image.Resampling.LANCZOS)
            self.theme_preview_img = ImageTk.PhotoImage(theme_preview)
            self.theme_preview.config(image=self.theme_preview_img)

            author_name = theme_data.get('author', 'unknown')
            self.theme_author.config(text="Author: " + author_name)
            if author_name.startswith("@"):
                self.theme_author.config(foreground="#a3a3ff", cursor="hand2")
                self.theme_author.bind("<Button-1>",
                                       lambda e: webbrowser.open_new_tab("https://github.com/" + author_name[1:]))
            else:
                self.theme_author.config(foreground="#a3a3a3", cursor="")
                self.theme_author.unbind("<Button-1>")
            self.theme_author.place(x=10, y=self.theme_preview_img.height() + 15)
            self.set_smartmonitor_info_text("")
            self.smartmonitor_info_box.place_forget()
            self.runtime_tags_frame.place_forget()

    def load_config_values(self):
        with open(MAIN_DIRECTORY + "config.yaml", "rt", encoding='utf8') as stream:
            self.config, ind, bsi = ruamel.yaml.util.load_yaml_guess_indent(stream)

        revision = self.config['display']['REVISION']

        # Check if theme is valid for classic framebuffer-driven models
        if revision != "A_HID" and get_theme_data(self.config['config']['THEME']) is None:
            # Theme from config.yaml is not valid: use first theme available default size 3.5"
            self.config['config']['THEME'] = get_themes(SIZE_3_5_INCH)[0]

        try:
            self.hwlib_cb.set(hw_lib_map[self.config['config']['HW_SENSORS']])
        except:
            self.hwlib_cb.current(0)

        try:
            if self.config['config']['ETH'] == "":
                self.eth_cb.current(0)
            else:
                self.eth_cb.set(self.config['config']['ETH'])
        except:
            self.eth_cb.current(0)

        try:
            if self.config['config']['WLO'] == "":
                self.wl_cb.current(0)
            else:
                self.wl_cb.set(self.config['config']['WLO'])
        except:
            self.wl_cb.current(0)

        try:
            if self.config['config']['COM_PORT'] == "AUTO":
                self.com_cb.current(0)
            else:
                self.com_cb.set(self.config['config']['COM_PORT'])
        except:
            self.com_cb.current(0)

        # Guess display size from the configured model.
        if revision == "A_HID":
            size = SIZE_3_5_INCH
        else:
            size = get_theme_size(self.config['config']['THEME'])
            size = size.replace(SIZE_2_1_INCH, SIZE_2_x_INCH)   # If a theme is for 2.1" then it also is for 2.8"
        try:
            self.size_cb.set(size)
        except:
            self.size_cb.current(0)

        # Guess model from revision and size
        try:
            self.model_cb.set(revision_and_size_to_model_map[(revision, size)])
        except:
            self.model_cb.current(0)

        try:
            self.orient_cb.set(reverse_map[self.config['display']['DISPLAY_REVERSE']])
        except:
            self.orient_cb.current(0)

        try:
            self.brightness_slider.set(int(self.config['display']['BRIGHTNESS']))
        except:
            self.brightness_slider.set(50)

        try:
            if self.config['config']['CPU_FAN'] == "AUTO":
                self.cpu_fan_cb.current(0)
            else:
                self.cpu_fan_cb.set(self.config['config']['CPU_FAN'])
        except:
            self.cpu_fan_cb.current(0)

        # Reload content on screen
        self.on_model_change()
        self.on_size_change()
        if self.is_smartmonitor_model():
            smartmonitor_theme = get_smartmonitor_theme_name_from_path(
                self.config['display'].get('SMARTMONITOR_HID_THEME_FILE', "")
            )
            if smartmonitor_theme:
                self.theme_cb.set(smartmonitor_theme)
        else:
            try:
                self.theme_cb.set(self.config['config']['THEME'])
            except:
                self.theme_cb.set("")
        self.on_theme_change()
        self.on_brightness_change()
        self.on_hwlib_change()
        self.refresh_hid_status()

        # Load configuration to sub-window as well
        self.more_config_window.load_config_values(self.config)

    def save_config_values(self):
        previous_smartmonitor_theme = self.config['display'].get('SMARTMONITOR_HID_THEME_FILE', "") or ""
        last_uploaded_smartmonitor_theme = self.config['display'].get('SMARTMONITOR_HID_LAST_UPLOADED_THEME', "") or ""
        previous_smartmonitor_theme = os.path.abspath(previous_smartmonitor_theme) if previous_smartmonitor_theme else ""
        last_uploaded_smartmonitor_theme = os.path.abspath(last_uploaded_smartmonitor_theme) if last_uploaded_smartmonitor_theme else ""
        if not self.is_smartmonitor_model():
            self.config['config']['THEME'] = self.theme_cb.get()
        self.config['config']['HW_SENSORS'] = [k for k, v in hw_lib_map.items() if v == self.hwlib_cb.get()][0]
        if self.eth_cb.current() == 0:
            self.config['config']['ETH'] = ""
        else:
            self.config['config']['ETH'] = self.eth_cb.get()
        if self.wl_cb.current() == 0:
            self.config['config']['WLO'] = ""
        else:
            self.config['config']['WLO'] = self.wl_cb.get()
        if self.com_cb.current() == 0:
            self.config['config']['COM_PORT'] = "AUTO"
        else:
            self.config['config']['COM_PORT'] = self.com_cb.get()
        if self.cpu_fan_cb.current() == 0:
            self.config['config']['CPU_FAN'] = "AUTO"
        else:
            self.config['config']['CPU_FAN'] = self.cpu_fan_cb.get().split(' ')[0]
        self.config['display']['REVISION'] = model_and_size_to_revision_map[(self.model_cb.get(), self.size_cb.get())]
        self.config['display']['DISPLAY_REVERSE'] = [k for k, v in reverse_map.items() if v == self.orient_cb.get()][0]
        self.config['display']['BRIGHTNESS'] = int(self.brightness_slider.get())
        self.config['display']['SMARTMONITOR_HID_RUNTIME'] = self.is_smartmonitor_model()
        if self.is_smartmonitor_model() and self.theme_cb.get():
            selected_smartmonitor_theme = os.path.abspath(
                resolve_smartmonitor_theme_path(self.theme_cb.get())
            )
            self.config['display']['SMARTMONITOR_HID_THEME_FILE'] = selected_smartmonitor_theme
            self.config['display']['SMARTMONITOR_HID_UPLOAD_ON_START'] = (
                previous_smartmonitor_theme != selected_smartmonitor_theme
                or last_uploaded_smartmonitor_theme != selected_smartmonitor_theme
            )
            if previous_smartmonitor_theme != selected_smartmonitor_theme:
                self.config['display']['SMARTMONITOR_HID_LAST_UPLOAD_ATTEMPTED_THEME'] = ""
        elif self.is_smartmonitor_model():
            self.config['display']['SMARTMONITOR_HID_THEME_FILE'] = ""
            self.config['display']['SMARTMONITOR_HID_UPLOAD_ON_START'] = False
            self.config['display']['SMARTMONITOR_HID_LAST_UPLOADED_THEME'] = ""
            self.config['display']['SMARTMONITOR_HID_LAST_UPLOAD_ATTEMPTED_THEME'] = ""

        with open(MAIN_DIRECTORY + "config.yaml", "w", encoding='utf-8') as file:
            ruamel.yaml.YAML().dump(self.config, file)

    def save_additional_config(self, ping: str, api_key: str, lat: str, long: str, unit: str, lang: str):
        self.config['config']['PING'] = ping
        self.config['config']['WEATHER_API_KEY'] = api_key
        self.config['config']['WEATHER_LATITUDE'] = lat
        self.config['config']['WEATHER_LONGITUDE'] = long
        self.config['config']['WEATHER_UNITS'] = unit
        self.config['config']['WEATHER_LANGUAGE'] = lang

        with open(MAIN_DIRECTORY + "config.yaml", "w", encoding='utf-8') as file:
            ruamel.yaml.YAML().dump(self.config, file)

    def on_theme_change(self, e=None):
        self.load_theme_preview()
        self.refresh_hid_status()

    def on_map_runtime_tag_click(self, event=None):
        values = self.runtime_tag_values_from_event(event)
        if not values:
            messagebox.showinfo("Runtime tags", "Select a runtime tag row first.", parent=self.window)
            return "break"
        tag = int(values[0])

        try:
            from library import smartmonitor_runtime as sm_runtime
            metric_choices = sm_runtime.get_runtime_metric_choices()
        except Exception as exc:
            messagebox.showerror("Runtime tags", str(exc), parent=self.window)
            return "break"

        if not metric_choices:
            messagebox.showerror("Runtime tags", "No runtime metrics are available for mapping.", parent=self.window)
            return "break"

        dialog = Toplevel(self.window)
        dialog.title("Map runtime tag")
        dialog.geometry("430x165")
        dialog.transient(self.window)
        dialog.resizable(False, False)

        ttk.Label(dialog, text=f"Assign fastSensor tag {tag} to metric:").place(x=15, y=15)
        metric_cb = ttk.Combobox(dialog, values=metric_choices, state="readonly")
        current_metric = str(values[2]) if len(values) > 2 and values[2] not in ("", "-") else ""
        if current_metric in metric_choices:
            metric_cb.set(current_metric)
        elif metric_choices:
            metric_cb.set(metric_choices[0])
        metric_cb.place(x=15, y=45, width=390)

        def apply_mapping():
            metric_name = metric_cb.get().strip()
            if not metric_name:
                return
            overrides = self.current_runtime_tag_overrides()
            for existing_metric, existing_tag in list(overrides.items()):
                if existing_metric == metric_name or int(existing_tag) == tag:
                    overrides.pop(existing_metric, None)
            overrides[metric_name] = int(tag)
            self.set_runtime_tag_overrides(overrides)
            self.refresh_runtime_tags_table()
            dialog.destroy()

        ttk.Button(dialog, text="Apply", command=apply_mapping).place(x=240, y=110, width=80)
        ttk.Button(dialog, text="Cancel", command=dialog.destroy).place(x=330, y=110, width=80)
        dialog.update_idletasks()
        dialog.wait_visibility()
        dialog.grab_set()
        metric_cb.focus_set()
        dialog.wait_window()
        return "break"

    def on_clear_runtime_tag_click(self):
        values = self.runtime_tag_values_from_event(None)
        if not values:
            messagebox.showinfo("Runtime tags", "Select a runtime tag row first.", parent=self.window)
            return
        tag = int(values[0])
        overrides = self.current_runtime_tag_overrides()
        removed = False
        for metric_name, mapped_tag in list(overrides.items()):
            if int(mapped_tag) == tag:
                overrides.pop(metric_name, None)
                removed = True
        if not removed:
            messagebox.showinfo("Runtime tags", "The selected tag has no manual override.", parent=self.window)
            return
        self.set_runtime_tag_overrides(overrides)
        self.refresh_runtime_tags_table()

    def on_weatherping_click(self):
        self.more_config_window.show()

    def on_open_theme_folder_click(self):
        if self.is_smartmonitor_model():
            self.on_smartmonitor_vendor_import_click()
            return

        path = MAIN_DIRECTORY + "res/themes"
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def on_theme_editor_click(self):
        if self.is_smartmonitor_model():
            self.on_smartmonitor_theme_import_click()
            return
        editor_script = os.path.join(MAIN_DIRECTORY, glob.glob("theme-editor.*", root_dir=MAIN_DIRECTORY)[0])
        subprocess.Popen([sys.executable, editor_script, self.theme_cb.get()])

    def on_theme_convert_click(self):
        if self.is_smartmonitor_model():
            self.on_smartmonitor_ui_convert_click()
            return

    def on_new_ui_project_click(self):
        if self.is_smartmonitor_model():
            self.on_smartmonitor_new_ui_project_click()
            return

    def on_edit_ui_click(self):
        if self.is_smartmonitor_model():
            self.on_smartmonitor_edit_ui_click()
            return

    def on_save_click(self):
        self.save_config_values()

    def refresh_autostart_buttons(self):
        if not autostart_supported():
            self.autostart_enable_btn.state(["disabled"])
            self.autostart_disable_btn.state(["disabled"])
            return

        enabled = is_autostart_enabled()
        if enabled:
            self.autostart_enable_btn.state(["disabled"])
            self.autostart_disable_btn.state(["!disabled"])
        else:
            self.autostart_enable_btn.state(["!disabled"])
            self.autostart_disable_btn.state(["disabled"])

    def on_enable_autostart_click(self):
        if not autostart_supported():
            messagebox.showinfo("Autostart", "Autostart via systemd --user is available only on Linux.", parent=self.window)
            return

        try:
            service_path = enable_autostart_service()
        except subprocess.CalledProcessError as exc:
            messagebox.showerror(
                "Autostart failed",
                "Could not enable autostart via systemd --user.\n\n"
                f"Service file:\n{autostart_service_path()}\n\n"
                f"Error: {exc}",
                parent=self.window,
            )
            return
        except Exception as exc:
            messagebox.showerror("Autostart failed", str(exc), parent=self.window)
            return

        self.refresh_autostart_buttons()
        messagebox.showinfo(
            "Autostart enabled",
            "Autostart has been enabled for the current user.\n\n"
            f"Service file:\n{service_path}",
            parent=self.window,
        )

    def on_disable_autostart_click(self):
        if not autostart_supported():
            messagebox.showinfo("Autostart", "Autostart via systemd --user is available only on Linux.", parent=self.window)
            return

        try:
            disable_autostart_service()
        except Exception as exc:
            messagebox.showerror("Autostart disable failed", str(exc), parent=self.window)
            return

        self.refresh_autostart_buttons()
        messagebox.showinfo(
            "Autostart disabled",
            "Autostart has been disabled for the current user.",
            parent=self.window,
        )

    def stop_running_main_instances(self):
        main_scripts = {
            os.path.abspath(os.path.join(MAIN_DIRECTORY, script_name))
            for script_name in glob.glob("main.*", root_dir=MAIN_DIRECTORY)
        }
        if not main_scripts:
            return

        matching_processes = []
        for process in psutil.process_iter(["pid", "cmdline"]):
            if process.info["pid"] == os.getpid():
                continue

            cmdline = process.info.get("cmdline") or []
            if any(os.path.abspath(arg) in main_scripts for arg in cmdline if arg):
                matching_processes.append(process)

        for process in matching_processes:
            try:
                process.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if matching_processes:
            psutil.wait_procs(matching_processes, timeout=3)

    def on_saverun_click(self):
        self.save_config_values()
        self.stop_running_main_instances()
        self.run_main_after_exit = True
        self.window.destroy()

    def on_brightness_change(self, e=None):
        self.brightness_string.set(str(int(self.brightness_slider.get())) + "%")
        self.show_hide_brightness_warning()

    def on_model_change(self, e=None):
        self.show_hide_brightness_warning()
        model = self.model_cb.get()
        allowed_sizes = get_sizes_for_model(model)
        if allowed_sizes:
            self.size_cb.configure(values=allowed_sizes)
            if self.size_cb.get() not in allowed_sizes:
                self.size_cb.set(allowed_sizes[0])
        if model == SIMULATED_MODEL:
            self.com_cb.configure(state="disabled", foreground="#C0C0C0")
            self.orient_cb.configure(state="disabled", foreground="#C0C0C0")
            self.brightness_slider.configure(state="disabled")
            self.brightness_val_label.configure(foreground="#C0C0C0")
        else:
            self.com_cb.configure(state="readonly", foreground="#000")
            self.orient_cb.configure(state="readonly", foreground="#000")
            self.brightness_slider.configure(state="normal")
            self.brightness_val_label.configure(foreground="#000")
        self.refresh_theme_selector()
        self.on_theme_change()

    def on_size_change(self, e=None):
        self.refresh_theme_selector()
        self.show_hide_brightness_warning()
        self.on_theme_change()

    def on_hwlib_change(self, e=None):
        hwlib = [k for k, v in hw_lib_map.items() if v == self.hwlib_cb.get()][0]
        if hwlib == "STUB" or hwlib == "STATIC":
            self.eth_cb.configure(state="disabled", foreground="#C0C0C0")
            self.wl_cb.configure(state="disabled", foreground="#C0C0C0")
        else:
            self.eth_cb.configure(state="readonly", foreground="#000")
            self.wl_cb.configure(state="readonly", foreground="#000")

        if sys.platform == "win32":
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            if (hwlib == "LHM" or hwlib == "AUTO") and not is_admin:
                self.lhm_admin_warning.place(x=370, y=460)
                self.save_run_btn.state(["disabled"])
            else:
                self.lhm_admin_warning.place_forget()
                self.save_run_btn.state(["!disabled"])
        else:
            if hwlib == "PYTHON" or hwlib == "AUTO":
                self.cpu_fan_label.place(x=370, y=460)
                self.cpu_fan_cb.place(x=550, y=455, width=250)
            else:
                self.cpu_fan_label.place_forget()
                self.cpu_fan_cb.place_forget()

    def show_hide_brightness_warning(self, e=None):
        if int(self.brightness_slider.get()) > 50 and self.model_cb.get() == TURING_MODEL and self.size_cb.get() == SIZE_3_5_INCH:
            # Show warning for Turing Smart screen 3.5 with high brightness
            self.brightness_warning_label.place(x=370, y=225)
        else:
            self.brightness_warning_label.place_forget()

    def on_fan_speed_update(self):
        # Update fan speed periodically
        prev_value = self.cpu_fan_cb.current()  # Save currently selected index
        self.cpu_fan_cb.config(values=get_fans())
        if prev_value != -1:
            self.cpu_fan_cb.current(prev_value)  # Force select same index to refresh displayed value
        self.window.after(500, self.on_fan_speed_update)

    def on_smartmonitor_theme_import_click(self):
        source_path = filedialog.askopenfilename(
            parent=self.window,
            title="Import SmartMonitor .dat",
            filetypes=(
                ("SmartMonitor theme", "*.dat"),
                ("All files", "*.*"),
            ),
        )
        if not source_path:
            return

        source = Path(source_path)
        suggested_name = source.parent.name or source.stem
        theme_name = simpledialog.askstring(
            "Import SmartMonitor theme",
            "Theme name in the GUI library:",
            parent=self.window,
            initialvalue=suggested_name,
        )
        if theme_name is None:
            return

        theme_name = sanitize_smartmonitor_theme_name(theme_name)
        if not theme_name:
            messagebox.showerror("Invalid name", "Theme name cannot be empty.")
            return

        target_dir = smartmonitor_theme_dir(theme_name)
        target_img = smartmonitor_theme_img(theme_name)
        os.makedirs(target_dir, exist_ok=True)

        if os.path.isfile(target_img):
            overwrite = messagebox.askyesno(
                "Overwrite theme?",
                f"A SmartMonitor theme named '{theme_name}' already exists.\nOverwrite it?",
                parent=self.window,
            )
            if not overwrite:
                return

        try:
            import_smartmonitor_img_dat(theme_name, str(source))
            action_text = "imported"
        except Exception as exc:
            messagebox.showerror("Import failed", str(exc), parent=self.window)
            return

        self.refresh_theme_selector()
        self.theme_cb.set(theme_name)
        self.on_theme_change()
        messagebox.showinfo(
            "Theme ready",
            f"Theme '{theme_name}' was {action_text} and is now available in the GUI list.\n"
            f"Use Save or Save and run to activate it.",
            parent=self.window,
        )

    def on_smartmonitor_ui_convert_click(self):
        source_path = filedialog.askopenfilename(
            parent=self.window,
            title="Convert vendor .ui to SmartMonitor .dat",
            filetypes=(
                ("Vendor theme source", "*.ui"),
                ("All files", "*.*"),
            ),
        )
        if not source_path:
            return

        source = Path(source_path)
        suggested_name = source.parent.name or source.stem
        theme_name = simpledialog.askstring(
            "Convert SmartMonitor UI",
            "Theme name for the compiled .dat:",
            parent=self.window,
            initialvalue=suggested_name,
        )
        if theme_name is None:
            return

        theme_name = sanitize_smartmonitor_theme_name(theme_name)
        if not theme_name:
            messagebox.showerror("Invalid name", "Theme name cannot be empty.", parent=self.window)
            return

        target_img = smartmonitor_theme_img(theme_name)
        if os.path.isfile(target_img):
            overwrite = messagebox.askyesno(
                "Overwrite theme?",
                f"A SmartMonitor theme named '{theme_name}' already exists.\nOverwrite it?",
                parent=self.window,
            )
            if not overwrite:
                return

        try:
            compile_and_import_smartmonitor_ui(theme_name, str(source))
        except Exception as exc:
            messagebox.showerror("Conversion failed", str(exc), parent=self.window)
            return

        self.refresh_theme_selector()
        self.theme_cb.set(theme_name)
        self.on_theme_change()
        messagebox.showinfo(
            "Conversion complete",
            f"Theme '{theme_name}' was converted from .ui to .dat and added to the SmartMonitor theme list.\n"
            f"Use Save or Save and run to activate it.",
            parent=self.window,
        )

    def on_smartmonitor_classic_theme_convert_click(self):
        theme_dir = filedialog.askdirectory(
            parent=self.window,
            title="Choose classic theme directory to convert",
            initialdir=THEMES_DIR,
            mustexist=True,
        )
        if not theme_dir:
            return

        theme_yaml = Path(theme_dir) / "theme.yaml"
        if not theme_yaml.is_file():
            messagebox.showerror(
                "Invalid classic theme",
                "The selected directory does not contain theme.yaml",
                parent=self.window,
            )
            return

        suggested_name = f"{Path(theme_dir).name}-smartmonitor"
        theme_name = simpledialog.askstring(
            "Convert classic theme",
            "Theme name for the compiled .dat:",
            parent=self.window,
            initialvalue=suggested_name,
        )
        if theme_name is None:
            return

        theme_name = sanitize_smartmonitor_theme_name(theme_name)
        if not theme_name:
            messagebox.showerror("Invalid name", "Theme name cannot be empty.", parent=self.window)
            return

        target_img = smartmonitor_theme_img(theme_name)
        if os.path.isfile(target_img):
            overwrite = messagebox.askyesno(
                "Overwrite theme?",
                f"A SmartMonitor theme named '{theme_name}' already exists.\nOverwrite it?",
                parent=self.window,
            )
            if not overwrite:
                return

        try:
            _, result = compile_and_import_classic_theme(theme_name, str(theme_yaml))
        except Exception as exc:
            messagebox.showerror("Classic theme conversion failed", str(exc), parent=self.window)
            return

        self.refresh_theme_selector()
        self.theme_cb.set(theme_name)
        self.on_theme_change()
        skipped = ""
        if result.skipped_items:
            preview = ", ".join(result.skipped_items[:6])
            skipped = f"\n\nSkipped unsupported classic items:\n{preview}"
            if len(result.skipped_items) > 6:
                skipped += ", ..."
        messagebox.showinfo(
            "Classic theme converted",
            f"Theme '{theme_name}' was converted from a classic YAML theme to SmartMonitor .dat.\n"
            f"Use Save or Save and run to activate it.{skipped}",
            parent=self.window,
        )

    def on_smartmonitor_classic_batch_convert_click(self):
        batch_root = filedialog.askdirectory(
            parent=self.window,
            title="Choose classic themes root for batch conversion",
            initialdir=THEMES_DIR,
            mustexist=True,
        )
        if not batch_root:
            return

        overwrite = messagebox.askyesno(
            "Batch convert classic themes?",
            "This will scan the selected folder for every classic theme.yaml,\n"
            "compile each compatible theme to SmartMonitor .dat and overwrite\n"
            "existing themes in the SmartMonitor library if names match.\n\n"
            "Continue?",
            parent=self.window,
        )
        if not overwrite:
            return

        try:
            imported, failed, results = compile_and_import_classic_theme_batch(batch_root)
        except Exception as exc:
            messagebox.showerror("Classic batch conversion failed", str(exc), parent=self.window)
            return

        self.refresh_theme_selector()
        if imported:
            self.theme_cb.set(imported[0])
            self.on_theme_change()

        converted = sum(1 for _, result in results if not result.placeholder_items and not result.skipped_items)
        skipped = len(results) - converted

        message_lines = [
            f"Imported: {len(imported)}",
            f"Converted cleanly: {converted}",
            f"Imported with placeholders/skips: {skipped}",
            f"Failed: {len(failed)}",
        ]

        if imported:
            preview = ", ".join(imported[:6])
            if len(imported) > 6:
                preview += ", ..."
            message_lines.append(f"Themes: {preview}")

        skipped_entries = [
            f"{theme_name}: placeholders={len(result.placeholder_items)}, skipped={len(result.skipped_items)}"
            for theme_name, result in results
            if result.placeholder_items or result.skipped_items
        ]
        if skipped_entries:
            message_lines.append("")
            message_lines.append("Themes with placeholders/skipped features:")
            message_lines.extend(skipped_entries[:8])
            if len(skipped_entries) > 8:
                message_lines.append("...")

        if failed:
            message_lines.append("")
            message_lines.append("Errors:")
            message_lines.extend(failed[:8])
            if len(failed) > 8:
                message_lines.append("...")

        messagebox.showinfo("Classic batch conversion", "\n".join(message_lines), parent=self.window)

    def on_smartmonitor_new_ui_project_click(self):
        os.makedirs(DEFAULT_SMARTMONITOR_PROJECTS_DIR, exist_ok=True)
        parent_dir = filedialog.askdirectory(
            parent=self.window,
            title="Choose folder for a new SmartMonitor UI project",
            initialdir=DEFAULT_SMARTMONITOR_PROJECTS_DIR,
            mustexist=True,
        )
        if not parent_dir:
            return

        project_name = simpledialog.askstring(
            "New SmartMonitor UI project",
            "Project name:",
            parent=self.window,
            initialvalue="my-smartmonitor-theme",
        )
        if project_name is None:
            return

        project_name = sanitize_smartmonitor_theme_name(project_name)
        if not project_name:
            messagebox.showerror("Invalid name", "Project name cannot be empty.", parent=self.window)
            return

        project_dir = Path(parent_dir) / project_name
        if project_dir.exists() and any(project_dir.iterdir()):
            overwrite = messagebox.askyesno(
                "Overwrite project?",
                f"The project folder '{project_dir}' already exists and is not empty.\nOverwrite starter files?",
                parent=self.window,
            )
            if not overwrite:
                return

        try:
            ui_path = create_smartmonitor_ui_project(str(project_dir), project_name)
        except Exception as exc:
            messagebox.showerror("Project creation failed", str(exc), parent=self.window)
            return

        messagebox.showinfo(
            "UI project created",
            f"Created starter SmartMonitor UI project:\n{project_dir}\n\n"
            f"UI source:\n{ui_path}\n\n"
            f"Next step: click 'Convert UI->DAT' and choose this .ui file.",
            parent=self.window,
        )

    def on_smartmonitor_edit_ui_click(self):
        theme_name = self.theme_cb.get()
        source_ui = get_smartmonitor_theme_source_ui(theme_name)
        if source_ui:
            open_linked = messagebox.askyesnocancel(
                "Open linked UI?",
                f"The selected theme '{theme_name}' has a linked UI source:\n\n"
                f"{source_ui}\n\n"
                f"Yes: open this linked UI\n"
                f"No: choose another .ui file manually\n"
                f"Cancel: do nothing",
                parent=self.window,
            )
            if open_linked is None:
                return
            if not open_linked:
                source_ui = ""

        if not source_ui:
            initial_dir = DEFAULT_SMARTMONITOR_PROJECTS_DIR if os.path.isdir(DEFAULT_SMARTMONITOR_PROJECTS_DIR) \
                else MAIN_DIRECTORY
            source_ui = filedialog.askopenfilename(
                parent=self.window,
                title="Open SmartMonitor UI source for editing",
                initialdir=initial_dir,
                filetypes=(
                    ("Vendor UI", "*.ui"),
                    ("All files", "*.*"),
                ),
            )
            if not source_ui:
                return

        editor_script = os.path.join(MAIN_DIRECTORY, "smartmonitor-theme-editor.py")
        subprocess.Popen([sys.executable, editor_script, source_ui])

    def on_force_upload_click(self):
        if not self.is_smartmonitor_model():
            return

        theme_name = self.theme_cb.get()
        theme_path = resolve_smartmonitor_theme_path(theme_name)
        if not theme_name or not theme_path:
            messagebox.showerror("No theme selected", "Select a SmartMonitor theme first.", parent=self.window)
            return

        try:
            from library.lcd.lcd_comm_rev_a_hid import LcdCommRevAHid
        except Exception as exc:
            messagebox.showerror("Upload unavailable", str(exc), parent=self.window)
            return

        selected_port = self.com_cb.get().strip()
        port = "AUTO" if self.com_cb.current() == 0 or not selected_port else selected_port
        try:
            lcd = LcdCommRevAHid(com_port=port)
            lcd.openSerial()
            lcd.smartmonitor_upload_theme(str(Path(theme_path).expanduser()))
            lcd.closeSerial()
        except Exception as exc:
            try:
                lcd.closeSerial()
            except Exception:
                pass
            messagebox.showerror("Theme upload failed", str(exc), parent=self.window)
            self.refresh_hid_status()
            return

        self.refresh_hid_status()
        messagebox.showinfo(
            "Theme uploaded",
            f"Theme '{theme_name}' was uploaded to the monitor.",
            parent=self.window,
        )

    def on_doctor_click(self):
        tool = os.path.join(MAIN_DIRECTORY, "tools", "smartmonitor-theme-manager.py")
        try:
            result = subprocess.run(
                [sys.executable, tool, "doctor"],
                text=True,
                capture_output=True,
                check=False,
            )
        except Exception as exc:
            messagebox.showerror("Doctor failed", str(exc), parent=self.window)
            return

        output = (result.stdout or "").strip()
        errors = (result.stderr or "").strip()
        if errors:
            output = f"{output}\n\n{errors}".strip()
        if not output:
            output = "No output"

        if result.returncode == 0:
            messagebox.showinfo("Doctor", output, parent=self.window)
        else:
            messagebox.showwarning("Doctor", output, parent=self.window)
        self.refresh_hid_status()

    def on_smartmonitor_vendor_import_click(self):
        initial_dir = DEFAULT_SMARTMONITOR_VENDOR_THEME_ROOT if os.path.isdir(DEFAULT_SMARTMONITOR_VENDOR_THEME_ROOT) \
            else MAIN_DIRECTORY
        vendor_root = filedialog.askdirectory(
            parent=self.window,
            title="Choose vendor theme root (folder with theme_* directories)",
            initialdir=initial_dir,
            mustexist=True,
        )
        if not vendor_root:
            return

        imported, failed = import_all_smartmonitor_vendor_themes(vendor_root)
        self.refresh_theme_selector()
        if imported and self.theme_cb.get() not in imported:
            self.theme_cb.set(imported[0])
            self.on_theme_change()

        message_lines = [
            f"Imported: {len(imported)}",
            f"Failed: {len(failed)}",
        ]
        if imported:
            preview = ", ".join(imported[:6])
            if len(imported) > 6:
                preview += ", ..."
            message_lines.append(f"Themes: {preview}")
        if failed:
            message_lines.append("")
            message_lines.append("Errors:")
            message_lines.extend(failed[:8])

        messagebox.showinfo("Vendor import complete", "\n".join(message_lines), parent=self.window)


class MoreConfigWindow:
    def __init__(self, main_window: TuringConfigWindow):
        self.window = Toplevel()
        self.window.withdraw()
        self.window.title('Configure weather & ping')
        self.window.geometry("750x680")

        self.main_window = main_window

        # Make TK look better with Sun Valley ttk theme
        sv_ttk.set_theme("light")

        self.ping_label = ttk.Label(self.window, text='Hostname / IP to ping')
        self.ping_label.place(x=10, y=10)
        self.ping_entry = ttk.Entry(self.window)
        self.ping_entry.place(x=190, y=5, width=250)

        weather_label = ttk.Label(self.window, text='Weather forecast (OpenWeatherMap API)', font='bold')
        weather_label.place(x=10, y=70)

        weather_info_label = ttk.Label(self.window,
                                       text="To display weather forecast on themes that support it, you need an OpenWeatherMap \"One Call API 3.0\" key.\n"
                                            "You will get 1,000 API calls per day for free. This program is configured to stay under this threshold (~300 calls/day).")
        weather_info_label.place(x=10, y=100)
        weather_api_link_label = ttk.Label(self.window,
                                           text="Click here to subscribe to OpenWeatherMap One Call API 3.0.")
        weather_api_link_label.place(x=10, y=140)
        weather_api_link_label.config(foreground="#a3a3ff", cursor="hand2")
        weather_api_link_label.bind("<Button-1>",
                                    lambda e: webbrowser.open_new_tab("https://openweathermap.org/api"))

        self.api_label = ttk.Label(self.window, text='OpenWeatherMap API key')
        self.api_label.place(x=10, y=170)
        self.api_entry = ttk.Entry(self.window)
        self.api_entry.place(x=190, y=165, width=250)

        latlong_label = ttk.Label(self.window,
                                  text="You can use online services to get your latitude/longitude e.g. latlong.net (click here)")
        latlong_label.place(x=10, y=210)
        latlong_label.config(foreground="#a3a3ff", cursor="hand2")
        latlong_label.bind("<Button-1>",
                           lambda e: webbrowser.open_new_tab("https://www.latlong.net/"))

        self.lat_label = ttk.Label(self.window, text='Latitude')
        self.lat_label.place(x=10, y=250)
        self.lat_entry = ttk.Entry(self.window, validate='key',
                                   validatecommand=(self.window.register(self.validateCoord), '%P'))
        self.lat_entry.place(x=80, y=245, width=100)

        self.long_label = ttk.Label(self.window, text='Longitude')
        self.long_label.place(x=270, y=250)
        self.long_entry = ttk.Entry(self.window, validate='key',
                                    validatecommand=(self.window.register(self.validateCoord), '%P'))
        self.long_entry.place(x=340, y=245, width=100)

        self.unit_label = ttk.Label(self.window, text='Units')
        self.unit_label.place(x=10, y=290)
        self.unit_cb = ttk.Combobox(self.window, values=list(weather_unit_map.values()), state='readonly')
        self.unit_cb.place(x=190, y=285, width=250)

        self.lang_label = ttk.Label(self.window, text='Language')
        self.lang_label.place(x=10, y=330)
        self.lang_cb = ttk.Combobox(self.window, values=list(weather_lang_map.values()), state='readonly')
        self.lang_cb.place(x=190, y=325, width=250)

        self.citysearch1_label = ttk.Label(self.window, text='Location search', font='bold')
        self.citysearch1_label.place(x=80, y=370)

        self.citysearch2_label = ttk.Label(self.window, text="Enter location to automatically get coordinates (latitude/longitude).\n"
                                                             "For example \"Berlin\" \"London, GB\", \"London, Quebec\".\n"
                                                             "Remember to set valid API key and pick language first!")
        self.citysearch2_label.place(x=10, y=396)

        self.citysearch3_label = ttk.Label(self.window, text="Enter location")
        self.citysearch3_label.place(x=10, y=474)
        self.citysearch_entry = ttk.Entry(self.window)
        self.citysearch_entry.place(x=140, y=470, width=300)
        self.citysearch_btn = ttk.Button(self.window, text="Search", command=lambda: self.on_search_click())
        self.citysearch_btn.place(x=450, y=468, height=40, width=130)

        self.citysearch4_label = ttk.Label(self.window, text="Select location\n(use after Search)")
        self.citysearch4_label.place(x=10, y=540)
        self.citysearch_cb = ttk.Combobox(self.window, values=[], state='readonly')
        self.citysearch_cb.place(x=140, y=544, width=360)
        self.citysearch_btn2 = ttk.Button(self.window, text="Fill in lat/long", command=lambda: self.on_filllatlong_click())
        self.citysearch_btn2.place(x=520, y=540, height=40, width=130)

        self.citysearch_warn_label = ttk.Label(self.window, text="")
        self.citysearch_warn_label.place(x=20, y=600)
        self.citysearch_warn_label.config(foreground="#ff0000")

        self.save_btn = ttk.Button(self.window, text="Save settings", command=lambda: self.on_save_click())
        self.save_btn.place(x=590, y=620, height=50, width=130)

        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

        self._city_entries = []

    def validateCoord(self, coord: str):
        if not coord:
            return True
        try:
            float(coord)
        except:
            return False
        return True

    def show(self):
        self.window.deiconify()

    def on_closing(self):
        self.window.withdraw()

    def load_config_values(self, config):
        self.config = config

        try:
            self.ping_entry.insert(0, self.config['config']['PING'])
        except:
            self.ping_entry.insert(0, "8.8.8.8")

        try:
            self.api_entry.insert(0, self.config['config']['WEATHER_API_KEY'])
        except:
            pass

        try:
            self.lat_entry.insert(0, self.config['config']['WEATHER_LATITUDE'])
        except:
            self.lat_entry.insert(0, "45.75")

        try:
            self.long_entry.insert(0, self.config['config']['WEATHER_LONGITUDE'])
        except:
            self.long_entry.insert(0, "45.75")

        try:
            self.unit_cb.set(weather_unit_map[self.config['config']['WEATHER_UNITS']])
        except:
            self.unit_cb.set(0)

        try:
            self.lang_cb.set(weather_lang_map[self.config['config']['WEATHER_LANGUAGE']])
        except:
            self.lang_cb.set(weather_lang_map["en"])
    
    def citysearch_show_warning(self, warning):
        self.citysearch_warn_label.config(text=warning)
		
    def on_search_click(self):
        OPENWEATHER_GEOAPI_URL = "http://api.openweathermap.org/geo/1.0/direct"
        api_key = self.api_entry.get()
        lang = [k for k, v in weather_lang_map.items() if v == self.lang_cb.get()][0]
        city = self.citysearch_entry.get()

        if len(api_key) == 0 or len(city) == 0:
            self.citysearch_show_warning("API key and city name cannot be empty.")
            return

        try:
            request = requests.get(OPENWEATHER_GEOAPI_URL, timeout=5, params={"appid": api_key, "lang": lang, 
                                   "q": city, "limit": 10})
        except:
            self.citysearch_show_warning("Error fetching OpenWeatherMap Geo API")
            return

        if request.status_code == 401:
            self.citysearch_show_warning("Invalid OpenWeatherMap API key.")
            return
        elif request.status_code != 200:
            self.citysearch_show_warning(f"Error #{request.status_code} fetching OpenWeatherMap Geo API.")
            return
        
        self._city_entries = []
        cb_entries = []
        for entry in request.json():
            name = entry['name']
            state = entry.get('state', None)
            lat = entry['lat']
            long = entry['lon']
            country_code = entry['country'].upper()
            country = babel.Locale(lang).territories[country_code]
            if state is not None:
                full_name = f"{name}, {state}, {country}"
            else:
                full_name = f"{name}, {country}"
            self._city_entries.append({"full_name": full_name, "lat": str(lat), "long": str(long)})
            cb_entries.append(full_name)

        self.citysearch_cb.config(values = cb_entries)
        if len(cb_entries) == 0:
            self.citysearch_show_warning("No given city found.")
        else:
            self.citysearch_cb.current(0)
            self.citysearch_show_warning("Select your city now from list and apply \"Fill in lat/long\".")

    def on_filllatlong_click(self):
        if len(self._city_entries) == 0:
            self.citysearch_show_warning("No city selected or no search results.")
            return
        city = [i for i in self._city_entries if i['full_name'] == self.citysearch_cb.get()][0]
        self.lat_entry.delete(0, END)
        self.lat_entry.insert(0, city['lat'])
        self.long_entry.delete(0, END)
        self.long_entry.insert(0, city['long'])
        self.citysearch_show_warning(f"Lat/long values filled for {city['full_name']}")

    def on_save_click(self):
        self.save_config_values()
        self.on_closing()

    def save_config_values(self):
        ping = self.ping_entry.get()
        api_key = self.api_entry.get()
        lat = self.lat_entry.get()
        long = self.long_entry.get()
        unit = [k for k, v in weather_unit_map.items() if v == self.unit_cb.get()][0]
        lang = [k for k, v in weather_lang_map.items() if v == self.lang_cb.get()][0]

        self.main_window.save_additional_config(ping, api_key, lat, long, unit, lang)


if __name__ == "__main__":
    configurator = TuringConfigWindow()
    sys.exit(configurator.run())
