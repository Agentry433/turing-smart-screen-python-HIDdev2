# turing-smart-screen-python-HIDdev

`turing-smart-screen-python-HIDdev` is a modified fork of `turing-smart-screen-python` with added support for 3.5" SmartMonitor devices that appear on Linux as USB HID (`0483:0065`) instead of serial/TTY displays.

Based on the original project:

- https://github.com/mathoudebine/turing-smart-screen-python

## Features

- Linux `hidraw` backend for SmartMonitor
- Theme upload over HID/YMODEM
- Live runtime metrics for CPU, GPU, RAM, disk and network
- Vendor theme support (`.dat`)
- Vendor UI conversion (`.ui -> .dat`)
- SmartMonitor GUI integration in `configure.py`
- Dedicated SmartMonitor theme editor with 480x320 canvas preview

## Main Files

- `main.py` — start the monitor runtime
- `configure.py` — GUI configuration, theme selection, import and conversion
- `smartmonitor-theme-editor.py` — SmartMonitor UI editor
- `tools/smartmonitor-theme-manager.py` — CLI theme manager

## Recommended First Theme

For the most stable out-of-the-box setup, use:

- `res/themes/rog03-vendor.dat`

## Quick Start

Recommended:

```bash
chmod +x install.sh
./install.sh
source venv/bin/activate
python3 configure.py
```

Manual:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 configure.py
```

Then:

1. Select `SmartMonitor HID (experimental)`
2. Select a theme
3. Click `Save and run`

## First-Run Diagnostics

If the monitor is not detected or themes do not upload, run:

```bash
python3 tools/smartmonitor-theme-manager.py doctor
```

For Linux HID permissions, install the included udev rule:

```bash
sudo cp tools/99-smartmonitor-hiddev.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Then unplug and replug the monitor.

## Licensing

The original project is licensed under `GNU GPL v3`.

That means this fork can be modified and redistributed, but:

- the GPL-3.0 license must be preserved
- copyright and license notices must remain intact
- modified versions must be clearly marked as modified
- source code for distributed modifications must remain available under GPL terms

See [LICENSE](./LICENSE).

## Russian Documentation

Russian overview and usage notes are available in [README_RU.md](./README_RU.md).

## Changelog

Release history is available in [CHANGELOG.md](./CHANGELOG.md).

## 💰 Support the Project

If you find this project useful, you can support the development with a donation:

TON Wallet:

`UQD-RzivaF2yxBF81Zzf44WE84Y3pS24QL751Z5nYC3PosRJ`

Donate TON

Every donation helps keep the project alive and motivates further development. Thank you! ❤️
