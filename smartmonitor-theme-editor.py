#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import copy
from datetime import datetime
from pathlib import Path
import tempfile
import time
import sys

from library.pythoncheck import check_python_version

check_python_version()

try:
    import tkinter.ttk as ttk
    from tkinter import *
    from tkinter import filedialog, messagebox, TclError
    from PIL import Image, ImageTk
except Exception as exc:
    raise SystemExit(f"Tkinter import failed: {exc}") from exc

from library.smartmonitor_ui import (
    FontSpec,
    Geometry,
    SensorSpec,
    SmartMonitorTheme,
    Widget,
    WidgetParent,
    parse_ui_file,
    write_theme_file,
    _hex_to_int,
)


SENSOR_PRESETS = [
    ("CPU temperature", 1, "Temperature", "CPU", "CPU Package"),
    ("CPU usage", 3, "Usage", "CPU", "CPU Total"),
    ("CPU frequency", 2, "Frequency", "CPU", "Core Clock"),
    ("CPU fan", 4, "Fan", "CPU", "CPU Fan"),
    ("GPU temperature", 5, "Temperature", "GPU", "GPU Temperature"),
    ("GPU usage", 7, "Usage", "GPU", "GPU Load"),
    ("GPU FPS", 23, "Other", "GPU", "FPS"),
    ("GPU memory %", 11, "Usage", "GPU", "GPU Memory"),
    ("GPU memory used", 9, "Other", "GPU", "GPU Memory Used"),
    ("GPU frequency", 6, "Frequency", "GPU", "Core Clock"),
    ("RAM usage", 12, "Other", "System", "Physical Memory Load"),
    ("RAM used", 13, "Other", "System", "Physical Memory Used"),
    ("RAM free", 14, "Other", "System", "Physical Memory Free"),
    ("RAM total", 21, "Other", "System", "Physical Memory Total"),
    ("Disk activity", 17, "Other", "Disk", "Disk Load"),
    ("Disk used", 15, "Other", "Disk", "Disk Used"),
    ("Disk free", 16, "Other", "Disk", "Disk Free"),
    ("Disk total", 8, "Other", "Disk", "Disk Total"),
    ("Net upload", 18, "Other", "Network:Auto", "Current UP rate"),
    ("Net download", 19, "Other", "Network:Auto", "Current DL rate"),
    ("Sound volume", 20, "Other", "System", "Sound Volume"),
    ("Uptime hours", 22, "Other", "System", "System Uptime Hours"),
    ("Weather temp", 24, "Other", "Weather", "Weather Temperature"),
    ("Weather feels like", 25, "Other", "Weather", "Weather Feels Like"),
    ("Weather humidity", 26, "Other", "Weather", "Weather Humidity"),
]
RESIZE_HANDLE_SIZE = 8


def _safe_int(value: str, default: int = 0) -> int:
    try:
        return int(value.strip())
    except Exception:
        return default


class SmartMonitorThemeEditor:
    def __init__(self, ui_path: str):
        self.ui_path = Path(ui_path).expanduser().resolve()
        self.theme: SmartMonitorTheme = parse_ui_file(self.ui_path)
        self.window = Tk()
        self.window.title(f"SmartMonitor Theme Editor - {self.ui_path.name}")
        self.window.geometry("1680x780")
        self.selection = None
        self.selected_widgets: set[int] = set()
        self.canvas_item_map = {}
        self.canvas_background_image = None
        self.canvas_widget_images = []
        self.drag_start = None
        self.drag_mode = None
        self.preview_metric_cache = {}
        self.preview_metric_cache_time = 0.0
        self.undo_stack: list[tuple[SmartMonitorTheme, tuple | None, set[int]]] = []
        self.redo_stack: list[tuple[SmartMonitorTheme, tuple | None, set[int]]] = []

        self.items_list = Listbox(self.window, exportselection=False, selectmode=EXTENDED)
        self.items_list.place(x=10, y=10, width=260, height=620)
        self.items_list.bind("<<ListboxSelect>>", self.on_select)
        self.window.bind("<Left>", lambda e: self.on_nudge(-1, 0))
        self.window.bind("<Right>", lambda e: self.on_nudge(1, 0))
        self.window.bind("<Up>", lambda e: self.on_nudge(0, -1))
        self.window.bind("<Down>", lambda e: self.on_nudge(0, 1))
        self.window.bind("<Control-z>", lambda e: self.on_undo())
        self.window.bind("<Control-y>", lambda e: self.on_redo())
        self.window.bind("<Control-a>", lambda e: self.on_select_all())

        self.path_label = ttk.Label(self.window, text=str(self.ui_path))
        self.path_label.place(x=280, y=10)

        self.name_var = StringVar()
        self.type_var = StringVar()
        self.x_var = StringVar()
        self.y_var = StringVar()
        self.w_var = StringVar()
        self.h_var = StringVar()
        self.text_var = StringVar()
        self.font_name_var = StringVar()
        self.font_size_var = StringVar()
        self.font_color_var = StringVar()
        self.datetime_var = StringVar()
        self.sensor_fast_var = StringVar()
        self.sensor_preset_var = StringVar()
        self.sensor_type_var = StringVar()
        self.sensor_name_var = StringVar()
        self.sensor_reading_var = StringVar()
        self.bg_image_var = StringVar()
        self.image_path_var = StringVar()
        self.bg_color_var = StringVar()
        self.grid_enabled_var = IntVar(value=0)
        self.grid_size_var = StringVar(value="10")

        self._entry("Object name", self.name_var, 280, 50)
        self._entry("Type", self.type_var, 280, 85, readonly=True)
        self._entry("X", self.x_var, 280, 120, width=55)
        self._entry("Y", self.y_var, 370, 120, width=55)
        self._entry("Width", self.w_var, 560, 120, width=45)
        self._entry("Height", self.h_var, 760, 120, width=45)
        self._entry("Text", self.text_var, 280, 160, width=360)
        self._entry("Font name", self.font_name_var, 280, 195, width=140)
        self._entry("Size", self.font_size_var, 570, 195, width=40)
        self._entry("Color", self.font_color_var, 760, 195, width=90)
        self._entry("Date/time fmt", self.datetime_var, 280, 230, width=180)
        self._entry("Fast sensor", self.sensor_fast_var, 280, 265, width=60)
        ttk.Label(self.window, text="Sensor preset").place(x=380, y=265)
        self.sensor_preset_cb = ttk.Combobox(
            self.window,
            textvariable=self.sensor_preset_var,
            values=[item[0] for item in SENSOR_PRESETS],
            state="readonly",
        )
        self.sensor_preset_cb.place(x=490, y=265, width=210)
        self.sensor_preset_cb.bind("<<ComboboxSelected>>", self.on_sensor_preset_selected)
        self._entry("Sensor type", self.sensor_type_var, 720, 265, width=100)
        self._entry("Sensor name", self.sensor_name_var, 940, 265, width=150)
        self._entry("Reading", self.sensor_reading_var, 280, 300, width=470)
        self._entry("Background image", self.bg_image_var, 280, 335, width=430)
        ttk.Button(self.window, text="Browse BG", command=self.on_pick_background_image).place(x=825, y=332, width=95, height=28)
        self._entry("Image path", self.image_path_var, 280, 370, width=430)
        ttk.Button(self.window, text="Browse Img", command=self.on_pick_widget_image).place(x=825, y=367, width=95, height=28)
        self._entry("Background color", self.bg_color_var, 280, 405, width=140)
        ttk.Checkbutton(self.window, text="Snap to grid", variable=self.grid_enabled_var).place(x=450, y=405)
        ttk.Label(self.window, text="Grid").place(x=590, y=405)
        ttk.Entry(self.window, textvariable=self.grid_size_var).place(x=625, y=405, width=45)

        toolbar = ttk.LabelFrame(self.window, text="Toolbar")
        toolbar.place(x=280, y=445, width=1380, height=110)
        ttk.Button(toolbar, text="Apply", command=self.on_apply).place(x=10, y=10, width=90, height=32)
        ttk.Button(toolbar, text="Save UI", command=self.on_save).place(x=110, y=10, width=90, height=32)
        ttk.Button(toolbar, text="Save As", command=self.on_save_as).place(x=210, y=10, width=90, height=32)
        ttk.Button(toolbar, text="Undo", command=self.on_undo).place(x=310, y=10, width=80, height=32)
        ttk.Button(toolbar, text="Redo", command=self.on_redo).place(x=400, y=10, width=80, height=32)
        ttk.Button(toolbar, text="Compile DAT", command=self.on_compile_dat).place(x=490, y=10, width=110, height=32)
        ttk.Button(toolbar, text="Compile+Upload", command=self.on_compile_upload).place(x=610, y=10, width=130, height=32)
        ttk.Button(toolbar, text="Add Number", command=self.on_add_number).place(x=10, y=52, width=100, height=32)
        ttk.Button(toolbar, text="Add DateTime", command=self.on_add_datetime).place(x=120, y=52, width=110, height=32)
        ttk.Button(toolbar, text="Add Image", command=self.on_add_image).place(x=240, y=52, width=100, height=32)
        ttk.Button(toolbar, text="Add Progress", command=self.on_add_progress).place(x=350, y=52, width=110, height=32)
        ttk.Button(toolbar, text="Duplicate", command=self.on_duplicate).place(x=470, y=52, width=100, height=32)
        ttk.Button(toolbar, text="Delete", command=self.on_delete).place(x=580, y=52, width=90, height=32)
        ttk.Button(toolbar, text="Align Left", command=lambda: self.on_align("left")).place(x=680, y=10, width=100, height=32)
        ttk.Button(toolbar, text="Align Top", command=lambda: self.on_align("top")).place(x=680, y=52, width=100, height=32)
        ttk.Button(toolbar, text="Align HCenter", command=lambda: self.on_align("hcenter")).place(x=790, y=10, width=110, height=32)
        ttk.Button(toolbar, text="Align VCenter", command=lambda: self.on_align("vcenter")).place(x=790, y=52, width=110, height=32)
        ttk.Button(toolbar, text="Center X", command=lambda: self.on_center_axis("x")).place(x=910, y=10, width=90, height=32)
        ttk.Button(toolbar, text="Center Y", command=lambda: self.on_center_axis("y")).place(x=910, y=52, width=90, height=32)
        ttk.Button(toolbar, text="Bring Front", command=lambda: self.on_reorder("front")).place(x=1010, y=10, width=100, height=32)
        ttk.Button(toolbar, text="Send Back", command=lambda: self.on_reorder("back")).place(x=1010, y=52, width=100, height=32)
        ttk.Button(toolbar, text="Center Both", command=lambda: self.on_center_axis("both")).place(x=1120, y=10, width=110, height=32)
        ttk.Button(toolbar, text="Select All", command=self.on_select_all).place(x=1240, y=10, width=90, height=32)
        ttk.Button(toolbar, text="Dist. H", command=lambda: self.on_distribute("h")).place(x=1120, y=52, width=100, height=32)
        ttk.Button(toolbar, text="Dist. V", command=lambda: self.on_distribute("v")).place(x=1230, y=52, width=100, height=32)

        self.canvas = Canvas(self.window, width=480, height=320, bg="#111827", highlightthickness=1, highlightbackground="#64748b")
        self.canvas.place(x=1160, y=50)
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)

        self.canvas_hint = ttk.Label(
            self.window,
            text="Canvas preview 480x320. Drag to move, drag bottom-right handle to resize, grid snap optional.",
        )
        self.canvas_hint.place(x=1160, y=380)

        note = (
            "Editor: move/resize widgets on canvas, duplicate widgets, choose sensor presets, preview live values,\n"
            "save .ui, compile to .dat, or compile and upload directly to the monitor."
        )
        ttk.Label(self.window, text=note).place(x=280, y=560)

        self.refresh_items()
        if self.items_list.size():
            self.items_list.selection_set(0)
            self.on_select()

    def _show_info(self, title: str, text: str):
        try:
            if self.window.winfo_exists():
                messagebox.showinfo(title, text, parent=self.window)
                return
        except TclError:
            pass
        print(f"{title}: {text}", file=sys.stderr)

    def _show_error(self, title: str, text: str):
        try:
            if self.window.winfo_exists():
                messagebox.showerror(title, text, parent=self.window)
                return
        except TclError:
            pass
        print(f"{title}: {text}", file=sys.stderr)

    def _push_undo_state(self):
        self.undo_stack.append((copy.deepcopy(self.theme), self.selection, set(self.selected_widgets)))
        if len(self.undo_stack) > 50:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def _restore_state(self, snapshot):
        theme, selection, selected_widgets = snapshot
        self.theme = copy.deepcopy(theme)
        self.selection = selection
        self.selected_widgets = set(selected_widgets)
        self.refresh_items()
        if self.selection is not None:
            self._populate_form_from_selection()

    def on_undo(self):
        if not self.undo_stack:
            return
        self.redo_stack.append((copy.deepcopy(self.theme), self.selection, set(self.selected_widgets)))
        self._restore_state(self.undo_stack.pop())

    def on_redo(self):
        if not self.redo_stack:
            return
        self.undo_stack.append((copy.deepcopy(self.theme), self.selection, set(self.selected_widgets)))
        self._restore_state(self.redo_stack.pop())

    def _entry(self, label: str, var: StringVar, x: int, y: int, width: int = 160, readonly: bool = False):
        ttk.Label(self.window, text=label).place(x=x, y=y)
        state = "readonly" if readonly else "normal"
        ttk.Entry(self.window, textvariable=var, state=state).place(x=x + 110, y=y, width=width)

    def refresh_items(self):
        self.items_list.delete(0, END)
        for index, parent in enumerate(self.theme.widget_parents):
            self.items_list.insert(END, f"BG {index}: {parent.object_name}")
        for index, widget in enumerate(self.theme.widgets):
            self.items_list.insert(END, f"W {index}: {widget.object_name} (type {widget.widget_type})")
        self.items_list.selection_clear(0, END)
        for index in sorted(self.selected_widgets):
            self.items_list.selection_set(len(self.theme.widget_parents) + index)
        if self.selection is not None:
            list_index = self._selection_to_list_index()
            if list_index is not None:
                self.items_list.selection_set(list_index)
                self.items_list.activate(list_index)
        self.render_canvas()

    def _selected_obj(self):
        if self.selection is None:
            return None
        kind, index = self.selection
        if kind == "parent":
            return self.theme.widget_parents[index]
        return self.theme.widgets[index]

    def _selection_to_list_index(self):
        if self.selection is None:
            return None
        kind, index = self.selection
        if kind == "parent":
            return index
        return len(self.theme.widget_parents) + index

    def _set_selection(self, kind: str, index: int):
        self.selection = (kind, index)
        if kind == "widget":
            self.selected_widgets = {index}
        else:
            self.selected_widgets.clear()
        list_index = self._selection_to_list_index()
        if list_index is not None:
            self.items_list.selection_clear(0, END)
            self.items_list.selection_set(list_index)
            self.items_list.activate(list_index)
        self._populate_form_from_selection()
        self.render_canvas()

    def _theme_base_dir(self) -> Path:
        return self.ui_path.parent

    def _resolve_asset_path(self, raw_path: str) -> Path:
        path = Path(raw_path)
        if path.is_absolute():
            return path
        raw = raw_path[2:] if raw_path.startswith("./") else raw_path
        return self._theme_base_dir() / raw

    def _relative_asset_path(self, path: Path) -> str:
        try:
            relative = path.resolve().relative_to(self._theme_base_dir().resolve())
            return "./" + relative.as_posix()
        except Exception:
            return str(path.resolve())

    def _populate_form_from_selection(self):
        obj = self._selected_obj()
        if obj is None:
            return
        if isinstance(obj, WidgetParent):
            self.name_var.set(obj.object_name)
            self.type_var.set("background")
            self.x_var.set(str(obj.geometry.x))
            self.y_var.set(str(obj.geometry.y))
            self.w_var.set(str(obj.geometry.width))
            self.h_var.set(str(obj.geometry.height))
            self.text_var.set("")
            self.font_name_var.set("")
            self.font_size_var.set("")
            self.font_color_var.set("")
            self.datetime_var.set("")
            self.sensor_fast_var.set("")
            self.sensor_type_var.set("")
            self.sensor_name_var.set("")
            self.sensor_reading_var.set("")
            self.sensor_preset_var.set("")
            self.bg_image_var.set(obj.background_image_path)
            self.image_path_var.set("")
            self.bg_color_var.set(obj.background_color_raw)
            return

        self.name_var.set(obj.object_name)
        self.type_var.set(str(obj.widget_type))
        self.x_var.set(str(obj.geometry.x))
        self.y_var.set(str(obj.geometry.y))
        self.w_var.set(str(obj.geometry.width))
        self.h_var.set(str(obj.geometry.height))
        self.text_var.set(obj.font.text if obj.font else "")
        self.font_name_var.set(obj.font.name if obj.font else "")
        self.font_size_var.set(str(obj.font.size if obj.font else 0))
        self.font_color_var.set(obj.font.color_raw if obj.font else "")
        self.datetime_var.set(obj.datetime_format)
        self.sensor_fast_var.set(str(obj.sensor.fast_sensor if obj.sensor else -1))
        self.sensor_type_var.set(obj.sensor.sensor_type_name if obj.sensor else "")
        self.sensor_name_var.set(obj.sensor.sensor_name if obj.sensor else "")
        self.sensor_reading_var.set(obj.sensor.reading_name if obj.sensor else "")
        self.sensor_preset_var.set(self._matching_sensor_preset(obj.sensor))
        self.bg_image_var.set("")
        self.image_path_var.set(str(obj.raw_fields.get("imagePath", "")))
        self.bg_color_var.set("")

    def _matching_sensor_preset(self, sensor: SensorSpec | None) -> str:
        if sensor is None:
            return ""
        for label, fast, sensor_type, sensor_name, reading in SENSOR_PRESETS:
            if (
                int(sensor.fast_sensor) == int(fast)
                and sensor.sensor_type_name == sensor_type
                and sensor.sensor_name == sensor_name
                and sensor.reading_name == reading
            ):
                return label
        return ""

    def on_sensor_preset_selected(self, _event=None):
        preset_name = self.sensor_preset_var.get().strip()
        for label, fast, sensor_type, sensor_name, reading in SENSOR_PRESETS:
            if label != preset_name:
                continue
            self.sensor_fast_var.set(str(fast))
            self.sensor_type_var.set(sensor_type)
            self.sensor_name_var.set(sensor_name)
            self.sensor_reading_var.set(reading)
            return

    def _grid_size(self) -> int:
        return max(1, _safe_int(self.grid_size_var.get(), 10))

    def _grid_snap_active(self, event_state: int = 0) -> bool:
        # Hold Shift while dragging to temporarily bypass grid snapping.
        if event_state & 0x0001:
            return False
        return bool(self.grid_enabled_var.get())

    def _snap(self, value: int, event_state: int = 0) -> int:
        if not self._grid_snap_active(event_state):
            return value
        grid = self._grid_size()
        return int(round(value / grid) * grid)

    def _draw_grid(self):
        if not self._grid_snap_active():
            return
        grid = self._grid_size()
        for x in range(grid, 480, grid):
            self.canvas.create_line(x, 0, x, 320, fill="#1f2937", width=1)
        for y in range(grid, 320, grid):
            self.canvas.create_line(0, y, 480, y, fill="#1f2937", width=1)

    def _draw_snap_guides(self, x1: int, y1: int, x2: int, y2: int):
        if not self._grid_snap_active():
            return
        guide = "#38bdf8"
        self.canvas.create_line(x1, 0, x1, 320, fill=guide, dash=(4, 3))
        self.canvas.create_line(x2, 0, x2, 320, fill=guide, dash=(4, 3))
        self.canvas.create_line(0, y1, 480, y1, fill=guide, dash=(4, 3))
        self.canvas.create_line(0, y2, 480, y2, fill=guide, dash=(4, 3))

    def _format_datetime_preview(self, pattern: str) -> str:
        now = datetime.now()
        fmt = (pattern or "").lower()
        if fmt == "hh:nn:ss":
            return now.strftime("%H:%M:%S")
        if fmt == "hh:nn":
            return now.strftime("%H:%M")
        if fmt == "yyyy-mm-dd":
            return now.strftime("%Y-%m-%d")
        if fmt == "yy-mm-dd":
            return now.strftime("%y-%m-%d")
        return now.strftime("%H:%M:%S")

    def _weather_preview_values(self) -> dict[str, str]:
        try:
            from library import smartmonitor_runtime as sm_runtime
            temp = sm_runtime._weather_metrics()  # type: ignore[attr-defined]
        except Exception:
            return {}
        values = {}
        if temp.get("WEATHER_TEMP") is not None and not isinstance(temp.get("WEATHER_TEMP"), str):
            try:
                values["weather temperature"] = f"{float(temp['WEATHER_TEMP']):.1f}"
            except Exception:
                pass
        if temp.get("WEATHER_FEELS_LIKE") is not None:
            try:
                values["weather feels like"] = f"{float(temp['WEATHER_FEELS_LIKE']):.1f}"
            except Exception:
                pass
        if temp.get("WEATHER_HUMIDITY") is not None:
            try:
                values["weather humidity"] = f"{int(round(float(temp['WEATHER_HUMIDITY'])))}%"
            except Exception:
                pass
        return values

    def _metric_preview_value(self, metric_name: str) -> str:
        now = time.monotonic()
        if now - self.preview_metric_cache_time > 1.0:
            self.preview_metric_cache = {}
            self.preview_metric_cache_time = now
        if metric_name in self.preview_metric_cache:
            return self.preview_metric_cache[metric_name]

        preview = "--"
        try:
            from library import smartmonitor_runtime as sm_runtime
            raw_value = sm_runtime._collect_metric_value(metric_name, 1.0)  # type: ignore[attr-defined]
            if raw_value is None:
                preview = "--"
            elif metric_name.endswith("_GB"):
                preview = f"{raw_value}"
            elif metric_name == "GPU_MEM_USED_MB":
                preview = f"{raw_value}"
            else:
                preview = str(int(raw_value))
        except Exception:
            preview = "--"
        self.preview_metric_cache[metric_name] = preview
        return preview

    def _sensor_text_preview(self, sensor: SensorSpec) -> str | None:
        reading = (sensor.reading_name or "").strip().lower()
        sensor_name = (sensor.sensor_name or "").strip().lower()
        if "weather" in sensor_name:
            weather = self._weather_preview_values()
            if reading in weather:
                return weather[reading]
            if "description" in reading:
                return "Cloudy"
            if "update time" in reading:
                return datetime.now().strftime("@%H:%M")
        if "custom" in sensor_name:
            if sensor.reading_name:
                return sensor.reading_name
            return "Custom"
        return None

    def _widget_preview_text(self, widget: Widget) -> str:
        if widget.widget_type == 6:
            return self._format_datetime_preview(widget.datetime_format)
        if widget.sensor is not None:
            sensor_text = self._sensor_text_preview(widget.sensor)
            if sensor_text is not None:
                return sensor_text
            try:
                from library import smartmonitor_runtime as sm_runtime
                metric_name = sm_runtime._derive_metric_name(  # type: ignore[attr-defined]
                    widget.sensor.sensor_type_name,
                    widget.sensor.sensor_name,
                    widget.sensor.reading_name,
                )
            except Exception:
                metric_name = None
            if metric_name:
                return self._metric_preview_value(metric_name)
        if widget.font and widget.font.text:
            return widget.font.text
        return widget.object_name or f"type {widget.widget_type}"

    def render_canvas(self):
        self.canvas.delete("all")
        self.canvas_item_map = {}
        self.canvas_widget_images = []

        background = self.theme.widget_parents[0] if self.theme.widget_parents else None
        if background is not None:
            if background.background_image_path:
                try:
                    image_path = self._resolve_asset_path(background.background_image_path)
                    image = Image.open(image_path).convert("RGB")
                    if image.size != (480, 320):
                        image = image.resize((480, 320), Image.Resampling.LANCZOS)
                    self.canvas_background_image = ImageTk.PhotoImage(image)
                    self.canvas.create_image(0, 0, anchor=NW, image=self.canvas_background_image)
                except Exception:
                    self.canvas_background_image = None
                    self.canvas.create_rectangle(0, 0, 480, 320, fill="#0f1720", outline="")
            else:
                self.canvas_background_image = None
                fill = background.background_color_raw if background.background_color_raw else "#0f1720"
                self.canvas.create_rectangle(0, 0, 480, 320, fill=fill, outline="")

        self._draw_grid()

        selected = self.selection
        selected_widgets = set(self.selected_widgets)
        for index, widget in enumerate(self.theme.widgets):
            x1 = widget.geometry.x
            y1 = widget.geometry.y
            x2 = x1 + widget.geometry.width
            y2 = y1 + widget.geometry.height
            outline = "#22c55e"
            fill = ""
            width = 2
            if index in selected_widgets or selected == ("widget", index):
                outline = "#f59e0b"
                width = 3
            if widget.widget_type == 4 and widget.raw_fields.get("imagePath"):
                try:
                    image_path = self._resolve_asset_path(str(widget.raw_fields.get("imagePath", "")))
                    image = Image.open(image_path)
                    if image.size != (widget.geometry.width, widget.geometry.height):
                        image = image.resize((widget.geometry.width, widget.geometry.height), Image.Resampling.LANCZOS)
                    tk_image = ImageTk.PhotoImage(image)
                    self.canvas_widget_images.append(tk_image)
                    image_id = self.canvas.create_image(x1, y1, anchor=NW, image=tk_image)
                    self.canvas_item_map[image_id] = ("widget", index)
                except Exception:
                    pass
            if widget.widget_type == 3 and widget.sensor is not None:
                try:
                    from library import smartmonitor_runtime as sm_runtime
                    metric_name = sm_runtime._derive_metric_name(  # type: ignore[attr-defined]
                        widget.sensor.sensor_type_name,
                        widget.sensor.sensor_name,
                        widget.sensor.reading_name,
                    )
                except Exception:
                    metric_name = None
                if metric_name:
                    try:
                        current_value = float(self._metric_preview_value(metric_name))
                    except Exception:
                        current_value = 0.0
                    ratio = max(0.0, min(1.0, current_value / 100.0))
                    fill_width = int(widget.geometry.width * ratio)
                    fill_id = self.canvas.create_rectangle(
                        x1,
                        y1,
                        x1 + fill_width,
                        y2,
                        fill="#38bdf8",
                        outline="",
                    )
                    self.canvas_item_map[fill_id] = ("widget", index)
            rect_id = self.canvas.create_rectangle(x1, y1, x2, y2, outline=outline, width=width, fill=fill)
            label = self._widget_preview_text(widget)
            text = self.canvas.create_text(x1 + 4, y1 + 4, anchor=NW, text=label, fill=outline, font=("Arial", 9, "bold"))
            self.canvas_item_map[rect_id] = ("widget", index)
            self.canvas_item_map[text] = ("widget", index)
            if selected == ("widget", index):
                self._draw_snap_guides(x1, y1, x2, y2)
                handle_map = {
                    "n": (x1 + widget.geometry.width // 2 - RESIZE_HANDLE_SIZE // 2, y1 - RESIZE_HANDLE_SIZE // 2, x1 + widget.geometry.width // 2 + RESIZE_HANDLE_SIZE // 2, y1 + RESIZE_HANDLE_SIZE // 2),
                    "s": (x1 + widget.geometry.width // 2 - RESIZE_HANDLE_SIZE // 2, y2 - RESIZE_HANDLE_SIZE // 2, x1 + widget.geometry.width // 2 + RESIZE_HANDLE_SIZE // 2, y2 + RESIZE_HANDLE_SIZE // 2),
                    "w": (x1 - RESIZE_HANDLE_SIZE // 2, y1 + widget.geometry.height // 2 - RESIZE_HANDLE_SIZE // 2, x1 + RESIZE_HANDLE_SIZE // 2, y1 + widget.geometry.height // 2 + RESIZE_HANDLE_SIZE // 2),
                    "e": (x2 - RESIZE_HANDLE_SIZE // 2, y1 + widget.geometry.height // 2 - RESIZE_HANDLE_SIZE // 2, x2 + RESIZE_HANDLE_SIZE // 2, y1 + widget.geometry.height // 2 + RESIZE_HANDLE_SIZE // 2),
                    "nw": (x1 - RESIZE_HANDLE_SIZE // 2, y1 - RESIZE_HANDLE_SIZE // 2, x1 + RESIZE_HANDLE_SIZE // 2, y1 + RESIZE_HANDLE_SIZE // 2),
                    "ne": (x2 - RESIZE_HANDLE_SIZE // 2, y1 - RESIZE_HANDLE_SIZE // 2, x2 + RESIZE_HANDLE_SIZE // 2, y1 + RESIZE_HANDLE_SIZE // 2),
                    "sw": (x1 - RESIZE_HANDLE_SIZE // 2, y2 - RESIZE_HANDLE_SIZE // 2, x1 + RESIZE_HANDLE_SIZE // 2, y2 + RESIZE_HANDLE_SIZE // 2),
                    "se": (x2 - RESIZE_HANDLE_SIZE // 2, y2 - RESIZE_HANDLE_SIZE // 2, x2 + RESIZE_HANDLE_SIZE // 2, y2 + RESIZE_HANDLE_SIZE // 2),
                }
                for mode, coords in handle_map.items():
                    handle_id = self.canvas.create_rectangle(*coords, fill=outline, outline=outline)
                    self.canvas_item_map[handle_id] = ("handle", index, mode)

    def _canvas_select_current(self, selection):
        if selection is None:
            return
        kind, index = selection
        self._set_selection(kind, index)

    def _selected_widget_indexes(self) -> list[int]:
        if self.selected_widgets:
            return sorted(self.selected_widgets)
        if self.selection and self.selection[0] == "widget":
            return [self.selection[1]]
        return []

    def on_select(self, _event=None):
        selection = self.items_list.curselection()
        if not selection:
            return
        widget_indexes = []
        parent_indexes = []
        for index in selection:
            if index < len(self.theme.widget_parents):
                parent_indexes.append(index)
            else:
                widget_indexes.append(index - len(self.theme.widget_parents))
        if widget_indexes:
            self.selection = ("widget", widget_indexes[0])
            self.selected_widgets = set(widget_indexes)
            self._populate_form_from_selection()
            self.render_canvas()
        elif parent_indexes:
            self._set_selection("parent", parent_indexes[0])

    def on_apply(self):
        obj = self._selected_obj()
        if obj is None:
            return
        self._push_undo_state()

        obj.object_name = self.name_var.get().strip() or obj.object_name
        obj.geometry = Geometry(
            x=self._snap(_safe_int(self.x_var.get(), obj.geometry.x)),
            y=self._snap(_safe_int(self.y_var.get(), obj.geometry.y)),
            width=max(1, self._snap(_safe_int(self.w_var.get(), obj.geometry.width))),
            height=max(1, self._snap(_safe_int(self.h_var.get(), obj.geometry.height))),
        )

        if isinstance(obj, WidgetParent):
            obj.background_image_path = self.bg_image_var.get().strip()
            obj.background_color_raw = self.bg_color_var.get().strip() or obj.background_color_raw
            obj.background_color = _hex_to_int(obj.background_color_raw, obj.background_color)
        else:
            if obj.font is None:
                obj.font = FontSpec()
            obj.font.text = self.text_var.get()
            obj.font.name = self.font_name_var.get().strip() or obj.font.name
            obj.font.size = _safe_int(self.font_size_var.get(), obj.font.size)
            obj.font.color_raw = self.font_color_var.get().strip() or obj.font.color_raw
            obj.font.color = _hex_to_int(obj.font.color_raw, obj.font.color)
            obj.datetime_format = self.datetime_var.get().strip()
            image_path = self.image_path_var.get().strip()
            if image_path:
                obj.raw_fields["imagePath"] = image_path
            elif "imagePath" in obj.raw_fields:
                del obj.raw_fields["imagePath"]

            sensor_fast = self.sensor_fast_var.get().strip()
            if sensor_fast or self.sensor_type_var.get().strip() or self.sensor_name_var.get().strip() or self.sensor_reading_var.get().strip():
                obj.sensor = SensorSpec(
                    fast_sensor=_safe_int(sensor_fast, obj.sensor.fast_sensor if obj.sensor else -1),
                    sensor_type_name=self.sensor_type_var.get().strip(),
                    sensor_name=self.sensor_name_var.get().strip(),
                    reading_name=self.sensor_reading_var.get().strip(),
                    is_div_1204=bool(obj.sensor.is_div_1204) if obj.sensor else False,
                )
            else:
                obj.sensor = None

        self.refresh_items()
        self._populate_form_from_selection()

    def _next_ids(self, widget_type: int) -> tuple[int, int]:
        global_id = max([widget.global_id for widget in self.theme.widgets] + [-1]) + 1
        same_type_id = sum(1 for widget in self.theme.widgets if widget.widget_type == widget_type)
        return global_id, same_type_id

    def on_add_number(self):
        self._push_undo_state()
        global_id, same_type_id = self._next_ids(5)
        widget = Widget(
            global_id=global_id,
            same_type_id=same_type_id,
            parent_name="background",
            object_name=f"Number {same_type_id}",
            widget_type=5,
            geometry=Geometry(40, 40, 100, 40),
            font=FontSpec(text="42", name="Arial", color_raw="0xffffffff", color=0xFFFFFFFF, size=20, bold_value=1, italic_value=0, bold=True, italic=False),
            sensor=SensorSpec(fast_sensor=1, sensor_type_name="Temperature", sensor_name="CPU", reading_name="CPU Package"),
            raw_fields={"hAlign": "1"},
        )
        self.theme.widgets.append(widget)
        self.refresh_items()
        self._set_selection("widget", len(self.theme.widgets) - 1)

    def on_add_datetime(self):
        self._push_undo_state()
        global_id, same_type_id = self._next_ids(6)
        widget = Widget(
            global_id=global_id,
            same_type_id=same_type_id,
            parent_name="background",
            object_name=f"DateTime {same_type_id}",
            widget_type=6,
            geometry=Geometry(40, 40, 160, 30),
            font=FontSpec(text="12:00:00", name="Arial", color_raw="0xffffffff", color=0xFFFFFFFF, size=18, bold_value=1, italic_value=0, bold=True, italic=False),
            datetime_format="hh:nn:ss",
            raw_fields={"hAlign": "1"},
        )
        self.theme.widgets.append(widget)
        self.refresh_items()
        self._set_selection("widget", len(self.theme.widgets) - 1)

    def on_add_image(self):
        self._push_undo_state()
        global_id, same_type_id = self._next_ids(4)
        widget = Widget(
            global_id=global_id,
            same_type_id=same_type_id,
            parent_name="background",
            object_name=f"Image {same_type_id}",
            widget_type=4,
            geometry=Geometry(40, 40, 80, 80),
            raw_fields={"imagePath": "./images/background.png", "imageDelay": 100},
        )
        self.theme.widgets.append(widget)
        self.refresh_items()
        self._set_selection("widget", len(self.theme.widgets) - 1)

    def on_add_progress(self):
        self._push_undo_state()
        global_id, same_type_id = self._next_ids(3)
        widget = Widget(
            global_id=global_id,
            same_type_id=same_type_id,
            parent_name="background",
            object_name=f"ProgressBar {same_type_id}",
            widget_type=3,
            geometry=Geometry(40, 40, 160, 20),
            sensor=SensorSpec(fast_sensor=3, sensor_type_name="Usage", sensor_name="CPU", reading_name="CPU Total"),
        )
        self.theme.widgets.append(widget)
        self.refresh_items()
        self._set_selection("widget", len(self.theme.widgets) - 1)

    def on_delete(self):
        indexes = self._selected_widget_indexes()
        if self.selection is None and not indexes:
            return
        if self.selection and self.selection[0] == "parent":
            self._show_error("Delete blocked", "Background root cannot be deleted.")
            return
        self._push_undo_state()
        for index in reversed(indexes):
            del self.theme.widgets[index]
        self.selection = None
        self.selected_widgets.clear()
        self.refresh_items()

    def on_duplicate(self):
        indexes = self._selected_widget_indexes()
        if not indexes:
            return
        self._push_undo_state()
        new_indexes = []
        for index in indexes:
            source = self.theme.widgets[index]
            widget = copy.deepcopy(source)
            global_id, same_type_id = self._next_ids(widget.widget_type)
            widget.global_id = global_id
            widget.same_type_id = same_type_id
            widget.object_name = f"{source.object_name} Copy"
            widget.geometry.x = min(480 - widget.geometry.width, source.geometry.x + self._grid_size())
            widget.geometry.y = min(320 - widget.geometry.height, source.geometry.y + self._grid_size())
            self.theme.widgets.append(widget)
            new_indexes.append(len(self.theme.widgets) - 1)
        self.refresh_items()
        if new_indexes:
            self.selection = ("widget", new_indexes[0])
            self.selected_widgets = set(new_indexes)
            self.refresh_items()

    def on_pick_background_image(self):
        obj = self._selected_obj()
        if not isinstance(obj, WidgetParent):
            self._show_info(
                "Select background",
                "Choose the background item in the list first, then pick an image.",
            )
            return

        initial_dir = str((self._theme_base_dir() / "images").resolve())
        image_path = filedialog.askopenfilename(
            parent=self.window,
            title="Choose background image",
            initialdir=initial_dir if Path(initial_dir).is_dir() else str(self._theme_base_dir()),
            filetypes=(
                ("Images", "*.png *.jpg *.jpeg *.bmp"),
                ("All files", "*.*"),
            ),
        )
        if not image_path:
            return

        raw_path = self._relative_asset_path(Path(image_path))
        self.bg_image_var.set(raw_path)
        obj.background_image_path = raw_path
        self.render_canvas()

    def on_pick_widget_image(self):
        obj = self._selected_obj()
        if not isinstance(obj, Widget) or obj.widget_type != 4:
            self._show_info(
                "Select image widget",
                "Choose an image widget in the list or on the canvas first, then pick an image.",
            )
            return

        initial_dir = str((self._theme_base_dir() / "images").resolve())
        image_path = filedialog.askopenfilename(
            parent=self.window,
            title="Choose widget image",
            initialdir=initial_dir if Path(initial_dir).is_dir() else str(self._theme_base_dir()),
            filetypes=(
                ("Images", "*.png *.jpg *.jpeg *.bmp"),
                ("All files", "*.*"),
            ),
        )
        if not image_path:
            return

        raw_path = self._relative_asset_path(Path(image_path))
        self.image_path_var.set(raw_path)
        obj.raw_fields["imagePath"] = raw_path
        self.render_canvas()

    def on_canvas_press(self, event):
        canvas_item = self.canvas.find_closest(event.x, event.y)
        if not canvas_item:
            return
        selection = self.canvas_item_map.get(canvas_item[0])
        if selection is None:
            if self.theme.widget_parents:
                self._set_selection("parent", 0)
            return
        if selection[0] == "handle":
            _, index, mode = selection
            self._set_selection("widget", index)
            obj = self._selected_obj()
            self.drag_mode = mode
        else:
            kind, index = selection
            if kind == "widget" and (event.state & 0x0001):
                if index in self.selected_widgets:
                    self.selected_widgets.remove(index)
                else:
                    self.selected_widgets.add(index)
                self.selection = ("widget", index)
                self.refresh_items()
            else:
                self._canvas_select_current(selection)
            obj = self._selected_obj()
            self.drag_mode = "move"
        if isinstance(obj, Widget):
            self.drag_start = (
                event.x,
                event.y,
                obj.geometry.x,
                obj.geometry.y,
                obj.geometry.width,
                obj.geometry.height,
            )

    def on_canvas_drag(self, event):
        if self.drag_start is None or self.selection is None:
            return
        obj = self._selected_obj()
        if not isinstance(obj, Widget):
            return
        start_x, start_y, base_x, base_y, base_w, base_h = self.drag_start
        delta_x = event.x - start_x
        delta_y = event.y - start_y
        mode = self.drag_mode or "move"
        if mode != "move":
            if getattr(self, "_drag_undo_pushed", False) is False:
                self._push_undo_state()
                self._drag_undo_pushed = True
            new_x = base_x
            new_y = base_y
            new_w = base_w
            new_h = base_h
            if "e" in mode:
                new_w = max(20, self._snap(base_w + delta_x, event.state))
            if "s" in mode:
                new_h = max(20, self._snap(base_h + delta_y, event.state))
            if "w" in mode:
                new_x = self._snap(base_x + delta_x, event.state)
                new_w = max(20, self._snap(base_w - delta_x, event.state))
            if "n" in mode:
                new_y = self._snap(base_y + delta_y, event.state)
                new_h = max(20, self._snap(base_h - delta_y, event.state))

            if new_x < 0:
                new_w += new_x
                new_x = 0
            if new_y < 0:
                new_h += new_y
                new_y = 0
            new_w = max(20, min(new_w, 480 - new_x))
            new_h = max(20, min(new_h, 320 - new_y))
            obj.geometry.x = new_x
            obj.geometry.y = new_y
            obj.geometry.width = new_w
            obj.geometry.height = new_h
        else:
            targets = self._selected_widget_indexes() or [self.selection[1]]
            if len(targets) == 1:
                obj.geometry.x = max(0, min(480 - obj.geometry.width, self._snap(base_x + delta_x, event.state)))
                obj.geometry.y = max(0, min(320 - obj.geometry.height, self._snap(base_y + delta_y, event.state)))
            else:
                # Push one undo entry per drag gesture.
                if getattr(self, "_drag_undo_pushed", False) is False:
                    self._push_undo_state()
                    self._drag_undo_pushed = True
                primary_index = self.selection[1]
                dx = self._snap(base_x + delta_x, event.state) - base_x
                dy = self._snap(base_y + delta_y, event.state) - base_y
                for idx in targets:
                    widget = self.theme.widgets[idx]
                    if idx == primary_index:
                        widget.geometry.x = max(0, min(480 - widget.geometry.width, base_x + dx))
                        widget.geometry.y = max(0, min(320 - widget.geometry.height, base_y + dy))
                    else:
                        widget.geometry.x = max(0, min(480 - widget.geometry.width, widget.geometry.x + dx))
                        widget.geometry.y = max(0, min(320 - widget.geometry.height, widget.geometry.y + dy))
        self.x_var.set(str(obj.geometry.x))
        self.y_var.set(str(obj.geometry.y))
        self.w_var.set(str(obj.geometry.width))
        self.h_var.set(str(obj.geometry.height))
        self.render_canvas()

    def on_canvas_release(self, _event):
        self.drag_start = None
        self.drag_mode = None
        self._drag_undo_pushed = False

    def on_nudge(self, dx: int, dy: int):
        if self.window.focus_get() not in (self.canvas, self.items_list, self.window):
            return
        indexes = self._selected_widget_indexes()
        if not indexes:
            return
        step = self._grid_size() if self.grid_enabled_var.get() else 1
        self._push_undo_state()
        for idx in indexes:
            widget = self.theme.widgets[idx]
            widget.geometry.x = max(0, min(480 - widget.geometry.width, widget.geometry.x + dx * step))
            widget.geometry.y = max(0, min(320 - widget.geometry.height, widget.geometry.y + dy * step))
        obj = self._selected_obj()
        if isinstance(obj, Widget):
            self.x_var.set(str(obj.geometry.x))
            self.y_var.set(str(obj.geometry.y))
        self.refresh_items()

    def on_align(self, mode: str):
        indexes = self._selected_widget_indexes()
        if len(indexes) < 2:
            self._show_info("Align", "Select at least two widgets first.")
            return
        self._push_undo_state()
        anchor = self.theme.widgets[indexes[0]]
        for idx in indexes[1:]:
            widget = self.theme.widgets[idx]
            if mode == "left":
                widget.geometry.x = anchor.geometry.x
            elif mode == "top":
                widget.geometry.y = anchor.geometry.y
            elif mode == "hcenter":
                widget.geometry.x = anchor.geometry.x + (anchor.geometry.width - widget.geometry.width) // 2
            elif mode == "vcenter":
                widget.geometry.y = anchor.geometry.y + (anchor.geometry.height - widget.geometry.height) // 2
            widget.geometry.x = max(0, min(480 - widget.geometry.width, self._snap(widget.geometry.x)))
            widget.geometry.y = max(0, min(320 - widget.geometry.height, self._snap(widget.geometry.y)))
        self.refresh_items()

    def on_center_axis(self, axis: str):
        indexes = self._selected_widget_indexes()
        if not indexes:
            self._show_info("Center", "Select one or more widgets first.")
            return
        self._push_undo_state()
        for idx in indexes:
            widget = self.theme.widgets[idx]
            if axis in ("x", "both"):
                widget.geometry.x = self._snap((480 - widget.geometry.width) // 2)
                widget.geometry.x = max(0, min(480 - widget.geometry.width, widget.geometry.x))
            if axis in ("y", "both"):
                widget.geometry.y = self._snap((320 - widget.geometry.height) // 2)
                widget.geometry.y = max(0, min(320 - widget.geometry.height, widget.geometry.y))
        self.refresh_items()

    def on_select_all(self):
        if not self.theme.widgets:
            return
        self.selected_widgets = set(range(len(self.theme.widgets)))
        self.selection = ("widget", 0)
        self.refresh_items()
        self._populate_form_from_selection()

    def on_distribute(self, axis: str):
        indexes = self._selected_widget_indexes()
        if len(indexes) < 3:
            self._show_info("Distribute", "Select at least three widgets first.")
            return
        self._push_undo_state()
        widgets = [self.theme.widgets[idx] for idx in indexes]
        if axis == "h":
            ordered = sorted(zip(indexes, widgets), key=lambda item: item[1].geometry.x)
            first = ordered[0][1]
            last = ordered[-1][1]
            usable = (last.geometry.x - first.geometry.x) - sum(item[1].geometry.width for item in ordered[1:-1])
            gap = usable // max(1, len(ordered) - 1)
            cursor = first.geometry.x + first.geometry.width + gap
            for _, widget in ordered[1:-1]:
                widget.geometry.x = max(0, min(480 - widget.geometry.width, self._snap(cursor)))
                cursor = widget.geometry.x + widget.geometry.width + gap
        else:
            ordered = sorted(zip(indexes, widgets), key=lambda item: item[1].geometry.y)
            first = ordered[0][1]
            last = ordered[-1][1]
            usable = (last.geometry.y - first.geometry.y) - sum(item[1].geometry.height for item in ordered[1:-1])
            gap = usable // max(1, len(ordered) - 1)
            cursor = first.geometry.y + first.geometry.height + gap
            for _, widget in ordered[1:-1]:
                widget.geometry.y = max(0, min(320 - widget.geometry.height, self._snap(cursor)))
                cursor = widget.geometry.y + widget.geometry.height + gap
        self.refresh_items()

    def on_reorder(self, mode: str):
        indexes = self._selected_widget_indexes()
        if not indexes:
            self._show_info("Reorder", "Select one or more widgets first.")
            return
        self._push_undo_state()
        selected = [self.theme.widgets[idx] for idx in indexes]
        remaining = [widget for idx, widget in enumerate(self.theme.widgets) if idx not in set(indexes)]
        if mode == "front":
            self.theme.widgets = remaining + selected
            new_indexes = list(range(len(remaining), len(remaining) + len(selected)))
        else:
            self.theme.widgets = selected + remaining
            new_indexes = list(range(len(selected)))
        self.selection = ("widget", new_indexes[0])
        self.selected_widgets = set(new_indexes)
        self.refresh_items()

    def on_save(self):
        self.on_apply()
        write_theme_file(self.ui_path, self.theme)
        self._show_info("Saved", f"Saved UI source:\n{self.ui_path}")

    def on_save_as(self):
        self.on_apply()
        target = filedialog.asksaveasfilename(
            parent=self.window,
            title="Save SmartMonitor UI As",
            defaultextension=".ui",
            filetypes=(("Vendor UI", "*.ui"), ("All files", "*.*")),
            initialfile=self.ui_path.name,
        )
        if not target:
            return
        self.ui_path = Path(target).expanduser().resolve()
        write_theme_file(self.ui_path, self.theme)
        self.path_label.config(text=str(self.ui_path))
        self._show_info("Saved", f"Saved UI source:\n{self.ui_path}")

    def _write_current_ui(self):
        self.on_apply()
        write_theme_file(self.ui_path, self.theme)

    def on_compile_dat(self):
        self._write_current_ui()
        try:
            from library.smartmonitor_compile import compile_theme_file
        except Exception as exc:
            self._show_error("Compile failed", str(exc))
            return

        target = filedialog.asksaveasfilename(
            parent=self.window,
            title="Save compiled SmartMonitor DAT",
            defaultextension=".dat",
            filetypes=(("SmartMonitor theme", "*.dat"), ("All files", "*.*")),
            initialfile=self.ui_path.with_suffix(".dat").name,
        )
        if not target:
            return
        try:
            payload = compile_theme_file(self.ui_path)
            Path(target).write_bytes(payload)
        except Exception as exc:
            self._show_error("Compile failed", str(exc))
            return
        self._show_info("Compiled", f"Compiled DAT:\n{target}")

    def on_compile_upload(self):
        self._write_current_ui()
        try:
            from library.smartmonitor_compile import compile_theme_file
            from library.lcd.lcd_comm_rev_a_hid import LcdCommRevAHid
        except Exception as exc:
            self._show_error("Upload unavailable", str(exc))
            return

        temp_path = Path(tempfile.gettempdir()) / f"{self.ui_path.stem}.dat"
        lcd = None
        try:
            payload = compile_theme_file(self.ui_path)
            temp_path.write_bytes(payload)
            lcd = LcdCommRevAHid(com_port="AUTO")
            lcd.openSerial()
            lcd.smartmonitor_upload_theme(str(temp_path))
            lcd.closeSerial()
        except Exception as exc:
            try:
                if lcd is not None:
                    lcd.closeSerial()
            except Exception:
                pass
            self._show_error("Compile+Upload failed", str(exc))
            return
        self._show_info("Uploaded", f"Compiled and uploaded theme:\n{temp_path}")

    def run(self):
        self.window.mainloop()


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: smartmonitor-theme-editor.py <path-to-ui>")
    editor = SmartMonitorThemeEditor(sys.argv[1])
    editor.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
