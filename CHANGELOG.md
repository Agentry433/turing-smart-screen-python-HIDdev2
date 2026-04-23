# Changelog

All notable changes to this fork are documented here.

The format is based on a simple chronological release history.

## v0.3.1 - Installer and First-Run Diagnostics

- Added `install.sh` to create a virtual environment, install Python requirements, and run first-run checks.
- Added `tools/smartmonitor-theme-manager.py doctor` for environment, config, HID device, and theme diagnostics.
- Added a Linux `udev` rule template for SmartMonitor HID access without manual `chmod`.
- Updated `README.md` and `README_RU.md` with installer-first setup and first-run troubleshooting steps.

## v0.3.0 - Classic Theme Conversion Workflow

- Added an MVP converter for classic `theme.yaml` themes to SmartMonitor HID `.dat` themes.
- Added GUI integration for converting classic framebuffer themes into SmartMonitor-compatible themes.
- Generated editable SmartMonitor `.ui` projects are now preserved next to converted themes.
- Added `Open/Edit UI` support for converted classic themes through linked `source_ui` metadata.
- Added conversion support for backgrounds, static images, static text, number widgets, datetime widgets, progress bars, line graph fallbacks, and radial fallbacks.
- Added scaling from classic theme canvas sizes to the SmartMonitor HID `480x320` target canvas.
- Extended runtime mapping for RAM used/free/total, disk free, GPU memory, uptime hours, and additional classic-theme sensor aliases.
- Reworked `configure.py` SmartMonitor action buttons into a two-row layout with shorter labels.

## v0.2.1 - Autostart and Broader Runtime Support

- Added Linux user autostart support via `systemd --user`.
- Added `Enable autostart` / `Disable autostart` controls to `configure.py`.
- Broadened SmartMonitor runtime support across more themes.
- Added runtime fallback logic for themes with recoverable `source_ui` metadata.

## v0.2.0 - Shutdown Handling Improvements

- Improved application shutdown behavior.
- Stopped background runtime workers more cleanly on exit.
- Reduced cases where the process stayed alive after close or `Ctrl+C`.

## v0.1.0 - Initial Public HIDdev Release

- First public GitHub release of the SmartMonitor HID fork.
- Linux SmartMonitor HID support published in a cleaned repository package.
- Vendor `.dat` theme upload workflow included.
- Runtime integration available for supported SmartMonitor themes.
