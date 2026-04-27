# Changelog

All notable changes to this fork are documented here.

The format is based on a simple chronological release history.

## v0.3.7 - Launcher and Save+Run Flow

- Added `run-configure.sh` for launching the configuration GUI without manual virtualenv activation.
- Added `run-monitor.sh` for launching `main.py` directly from the managed virtualenv.
- Updated `install.sh` to recommend the new launcher scripts instead of `source venv/bin/activate`.
- Fixed the `Save + run` flow so `./run-configure.sh` can continue directly into `main.py` after closing the configurator.

## v0.3.6 - Precise Canvas Dragging

- Improved SmartMonitor editor dragging and resizing for precise pixel positioning on the canvas.
- Grid snapping is no longer forced during drag when the grid is disabled.
- Holding `Shift` while dragging or resizing now temporarily bypasses snap-to-grid for fine adjustment.

## v0.3.5 - SmartMonitor Theme Editor Polish

- Added multi-side resize handles in the SmartMonitor theme editor.
- Added `Add Image` and `Add Progress` creation actions in the editor toolbar.
- Added `Undo` / `Redo` support in the SmartMonitor theme editor.
- Added arrow-key nudging for selected widgets, with optional grid snapping.
- Added basic multi-select, group alignment tools, and batch duplicate/delete behavior for widgets.
- Added sensor preset selection for quickly mapping `fastSensor` and sensor fields.
- Added live canvas preview values for sensors, datetime, weather, and basic custom placeholders.
- Added `Compile DAT` and `Compile+Upload` actions directly from the editor.

## v0.3.4 - Runtime Mapping and Tag Overrides

- Added a visible SmartMonitor runtime tag table to `configure.py`.
- Added manual runtime mapping overrides from theme sensor tags to runtime metrics.
- Added runtime metric choices and per-tag override editing for SmartMonitor themes.
- Added startup logging that reports which runtime-capable fields the active theme contains.
- Added best-effort runtime support for GPU FPS, sound volume, and numeric weather metrics where available.
- Improved the SmartMonitor runtime-tag GUI with full-width layout and easier single-row selection.
- Fixed runtime tag popup behavior and double-click mapping in the SmartMonitor configuration workflow.

## v0.3.3 - Classic Theme Batch Conversion

- Added batch conversion of classic `theme.yaml` themes into SmartMonitor HID themes.
- Added compatibility-style statuses for classic conversion results: converted, skipped features, unsupported.
- Added classic preview rendering before conversion with a preview-only CLI mode.
- Added JSON and Markdown compatibility reports for batch classic conversion runs.
- Improved `LINE_GRAPH` and `RADIAL` fallbacks for classic themes.
- Added static placeholder handling for unsupported runtime-driven fields such as weather, custom values, swap, and GPU FPS.
- Added a `Classic batch` action to `configure.py` for converting and importing many classic themes at once.
- Fixed the SmartMonitor GUI batch conversion path and synced the same workflow into the GitHub package.

## v0.3.2 - SmartMonitor GUI Workflow Refinements

- Added separate SmartMonitor GUI actions for vendor `.ui` conversion and classic theme conversion.
- Added a `Force upload` button to upload the selected SmartMonitor theme immediately.
- Added a `Doctor` button in the GUI to run first-launch diagnostics without using the terminal.
- Added live HID status in `configure.py` with periodic refresh.
- Added a SmartMonitor info box showing theme kind, runtime mode, compiler/source details, linked UI, and runtime tags.
- Added SmartMonitor preview rendering from linked `.ui` projects using background and image widgets when available.
- Added tooltip descriptions for SmartMonitor GUI buttons.
- Reworked the SmartMonitor lower control area to avoid text/button overlap and improve readability.

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
