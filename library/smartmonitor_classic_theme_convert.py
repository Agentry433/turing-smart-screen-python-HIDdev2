# SPDX-License-Identifier: GPL-3.0-or-later
#
# Minimal classic turing-smart-screen theme -> SmartMonitor UI converter.
# This is intentionally conservative: it only maps parts of classic themes
# that can be represented reasonably well on SmartMonitor themes.

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import shutil
from typing import Any
from PIL import Image
import yaml

from library.smartmonitor_ui import (
    FontSpec,
    Geometry,
    SensorSpec,
    StyleSpec,
    SmartMonitorTheme,
    SmartMonitorThemeBundle,
    StartupPicSpec,
    Widget,
    WidgetParent,
    write_theme_file,
)


CLASSIC_THEME_FAST_SENSORS: dict[tuple[str, ...], tuple[int, str, str, str, bool]] = {
    ("CPU", "PERCENTAGE"): (3, "Usage", "CPU", "CPU Total", False),
    ("CPU", "TEMPERATURE"): (1, "Temperature", "CPU", "CPU Package", False),
    ("CPU", "FREQUENCY"): (2, "Frequency", "CPU", "Core Clock", False),
    ("CPU", "FAN_SPEED"): (4, "Fan", "CPU", "CPU Fan", False),
    ("GPU", "PERCENTAGE"): (7, "Usage", "GPU", "GPU Load", False),
    ("GPU", "TEMPERATURE"): (5, "Temperature", "GPU", "GPU Temperature", False),
    ("GPU", "FREQUENCY"): (6, "Frequency", "GPU", "Core Clock", False),
    ("GPU", "FAN_SPEED"): (10, "Fan", "GPU", "GPU Fan", False),
    ("GPU", "MEMORY"): (11, "Usage", "GPU", "GPU Memory", False),
    ("GPU", "MEMORY_PERCENT"): (11, "Usage", "GPU", "GPU Memory", False),
    ("GPU", "MEMORY", "USED"): (9, "Other", "GPU", "GPU Memory Used", False),
    ("MEMORY", "VIRTUAL"): (12, "Other", "System", "Physical Memory Load", False),
    ("MEMORY", "VIRTUAL", "USED"): (13, "Other", "System", "Physical Memory Used", False),
    ("MEMORY", "VIRTUAL", "FREE"): (14, "Other", "System", "Physical Memory Free", False),
    ("MEMORY", "VIRTUAL", "TOTAL"): (21, "Other", "System", "Physical Memory Total", False),
    ("DISK", "USED"): (15, "Other", "Disk", "Disk Used", False),
    ("DISK", "FREE"): (16, "Other", "Disk", "Disk Free", False),
    ("DISK", "PERCENTAGE"): (17, "Other", "Disk", "Disk Load", False),
    ("DISK", "TOTAL"): (8, "Other", "Disk", "Disk Total", False),
    ("NET", "UPLOAD"): (18, "Other", "Network:Auto", "Current UP rate", False),
    ("NET", "DOWNLOAD"): (19, "Other", "Network:Auto", "Current DL rate", False),
    ("UPTIME", "FORMATTED"): (22, "Other", "System", "System Uptime Hours", False),
}

DATE_FORMAT_MAP = {
    ("DAY", "short"): "yy-mm-dd",
    ("DAY", "medium"): "yyyy-mm-dd",
    ("DAY", "long"): "yyyy-mm-dd",
    ("DAY", "full"): "yyyy-mm-dd",
    ("HOUR", "short"): "hh:nn",
    ("HOUR", "medium"): "hh:nn:ss",
    ("HOUR", "long"): "hh:nn:ss",
    ("HOUR", "full"): "hh:nn:ss",
}


def _map_datetime_format(date_key: str, raw_format: Any) -> str | None:
    value = str(raw_format or "medium").strip()
    mapped = DATE_FORMAT_MAP.get((date_key, value.lower()))
    if mapped:
        return mapped
    upper = value.upper()
    if date_key == "HOUR":
        if "S" in upper:
            return "hh:nn:ss"
        if "H" in upper or "M" in upper:
            return "hh:nn"
    if date_key == "DAY":
        if "Y" in upper and "M" in upper and "D" in upper:
            return "yyyy-mm-dd"
    return None


@dataclass(slots=True)
class ClassicThemeConversionResult:
    bundle: SmartMonitorThemeBundle
    output_dir: Path
    ui_path: Path
    copied_assets: list[Path]
    skipped_items: list[str]
    placeholder_items: list[str] = field(default_factory=list)
    preview_path: Path | None = None

    @property
    def widget_count(self) -> int:
        return len(self.bundle.theme.widgets)

    @property
    def status(self) -> str:
        if self.skipped_items or self.placeholder_items:
            return "skipped"
        return "converted"


@dataclass(slots=True)
class ClassicThemeBatchItem:
    theme_name: str
    theme_path: Path
    status: str
    ui_path: Path | None = None
    dat_path: Path | None = None
    preview_path: Path | None = None
    widget_count: int = 0
    skipped_items: list[str] = field(default_factory=list)
    placeholder_items: list[str] = field(default_factory=list)
    error: str = ""


@dataclass(slots=True)
class _ScaleTransform:
    source_width: int
    source_height: int
    target_width: int = 480
    target_height: int = 320

    @property
    def x_ratio(self) -> float:
        return self.target_width / max(1, self.source_width)

    @property
    def y_ratio(self) -> float:
        return self.target_height / max(1, self.source_height)

    def scale_x(self, value: Any) -> int:
        return int(round(float(value or 0) * self.x_ratio))

    def scale_y(self, value: Any) -> int:
        return int(round(float(value or 0) * self.y_ratio))

    def scale_w(self, value: Any) -> int:
        return max(1, int(round(float(value or 0) * self.x_ratio)))

    def scale_h(self, value: Any) -> int:
        return max(1, int(round(float(value or 0) * self.y_ratio)))

    def scale_font(self, value: Any) -> int:
        base = max(1.0, min(self.x_ratio, self.y_ratio))
        return max(8, int(round(float(value or 20) * base)))


def _load_classic_theme(theme_path: str | Path) -> tuple[dict[str, Any], Path]:
    theme_file = Path(theme_path)
    if theme_file.is_dir():
        theme_file = theme_file / "theme.yaml"
    with open(theme_file, "rt", encoding="utf-8") as stream:
        theme_data = yaml.safe_load(stream)
    theme_dir = theme_file.parent
    return theme_data, theme_dir


def _argb_from_rgb_triplet(value: Any, default: str = "0xffffffff") -> str:
    if isinstance(value, str):
        return value if value.startswith("0x") else default
    if not isinstance(value, (list, tuple)) or len(value) < 3:
        return default
    red, green, blue = (max(0, min(255, int(v))) for v in value[:3])
    return f"0xff{red:02x}{green:02x}{blue:02x}"


def _font_from_classic(node: dict[str, Any], transform: _ScaleTransform, fallback_text: str = "") -> FontSpec:
    return FontSpec(
        text=str(node.get("TEXT", fallback_text) or fallback_text),
        name="Arial",
        color_raw=_argb_from_rgb_triplet(node.get("FONT_COLOR"), "0xffffffff"),
        color=int(_argb_from_rgb_triplet(node.get("FONT_COLOR"), "0xffffffff"), 16),
        size=transform.scale_font(node.get("FONT_SIZE", 20) or 20),
        bold_value=1,
        italic_value=0,
        bold=True,
        italic=False,
    )


def _default_box(node: dict[str, Any], font_size: int) -> tuple[int, int]:
    width = int(node.get("WIDTH", max(80, int(font_size * 3.5))) or max(80, int(font_size * 3.5)))
    height = int(node.get("HEIGHT", max(font_size + 10, int(font_size * 1.6))) or max(font_size + 10, int(font_size * 1.6)))
    return width, height


def _background_path(theme_data: dict[str, Any], theme_dir: Path) -> Path | None:
    static_images = theme_data.get("static_images", {}) or {}
    background = static_images.get("BACKGROUND") or next(iter(static_images.values()), None)
    if isinstance(background, dict) and background.get("PATH"):
        return theme_dir / str(background["PATH"])
    for candidate in ("background.png", "background.jpg", "background.jpeg"):
        path = theme_dir / candidate
        if path.is_file():
            return path
    return None


def _display_geometry(theme_data: dict[str, Any]) -> tuple[int, int]:
    display = theme_data.get("display", {}) or {}
    size = display.get("DISPLAY_SIZE", '3.5"')
    orientation = display.get("DISPLAY_ORIENTATION", "portrait")
    known_sizes = {
        '3.5"': (320, 480),
        '5"': (480, 800),
        '8.8"': (480, 1920),
        '2.1"': (480, 480),
        '0.96"': (80, 160),
    }
    base = known_sizes.get(size, (320, 480))
    if orientation == "landscape":
        return max(base), min(base)
    return min(base), max(base)


def _source_canvas(theme_data: dict[str, Any]) -> tuple[int, int]:
    static_images = theme_data.get("static_images", {}) or {}
    background = static_images.get("BACKGROUND") or next(iter(static_images.values()), None)
    if isinstance(background, dict):
        width = int(background.get("WIDTH", 0) or 0)
        height = int(background.get("HEIGHT", 0) or 0)
        if width > 0 and height > 0:
            return width, height
    return _display_geometry(theme_data)


def _copy_asset(src: Path, output_images_dir: Path, resize_to: tuple[int, int] | None = None) -> Path:
    output_images_dir.mkdir(parents=True, exist_ok=True)
    target = output_images_dir / src.name
    if resize_to is not None:
        with Image.open(src) as image:
            resized = image.convert("RGB").resize(resize_to, Image.Resampling.LANCZOS)
            resized.save(target)
    elif src.resolve() != target.resolve():
        shutil.copy2(src, target)
    return target


def render_classic_theme_preview(theme_path: str | Path, output_path: str | Path | None = None) -> Image.Image:
    theme_data, theme_dir = _load_classic_theme(theme_path)
    source_width, source_height = _source_canvas(theme_data)
    transform = _ScaleTransform(source_width=source_width, source_height=source_height)
    canvas = Image.new("RGB", (transform.target_width, transform.target_height), color="#0f1720")

    background_src = _background_path(theme_data, theme_dir)
    if background_src and background_src.is_file():
        with Image.open(background_src) as image:
            bg = image.convert("RGB").resize((transform.target_width, transform.target_height), Image.Resampling.LANCZOS)
            canvas.paste(bg)

    for name, node in (theme_data.get("static_images", {}) or {}).items():
        if str(name).upper() == "BACKGROUND" or not isinstance(node, dict):
            continue
        image_path = node.get("PATH")
        if not image_path:
            continue
        src = theme_dir / str(image_path)
        if not src.is_file():
            continue
        try:
            with Image.open(src) as image:
                rendered = image.convert("RGBA").resize(
                    (
                        transform.scale_w(node.get("WIDTH", image.width)),
                        transform.scale_h(node.get("HEIGHT", image.height)),
                    ),
                    Image.Resampling.LANCZOS,
                )
                canvas.paste(
                    rendered.convert("RGB"),
                    (
                        transform.scale_x(node.get("X", 0) or 0),
                        transform.scale_y(node.get("Y", 0) or 0),
                    ),
                )
        except Exception:
            continue

    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(target)
    return canvas


def _widget_parent(width: int, height: int, background_asset: Path | None) -> WidgetParent:
    bg_path = f"./images/{background_asset.name}" if background_asset else ""
    return WidgetParent(
        object_name="background",
        widget_type=1,
        geometry=Geometry(x=0, y=0, width=width, height=height),
        background_type=1,
        background_color_raw="0xff000000",
        background_color=0xFF000000,
        background_image_path=bg_path,
        image_delay=100,
    )


def _image_widget(
    widget_id: int,
    object_name: str,
    node: dict[str, Any],
    asset: Path,
    transform: _ScaleTransform,
) -> Widget | None:
    width = transform.scale_w(node.get("WIDTH", 80) or 80)
    height = transform.scale_h(node.get("HEIGHT", 80) or 80)
    return Widget(
        global_id=widget_id,
        same_type_id=widget_id,
        parent_name="background",
        object_name=object_name,
        widget_type=4,
        geometry=Geometry(
            x=transform.scale_x(node.get("X", 0) or 0),
            y=transform.scale_y(node.get("Y", 0) or 0),
            width=width,
            height=height,
        ),
        style=StyleSpec(
            show_type=0,
            bg_color_raw="0x00000000",
            bg_color=0,
            fg_color_raw="0x00000000",
            fg_color=0,
            frame_color_raw="0x00000000",
            frame_color=0,
            bg_image_path="",
            fg_image_path="",
        ),
        raw_fields={"imagePath": f"./images/{asset.name}", "imageDelay": 100},
    )


def _static_text_widget(widget_id: int, object_name: str, node: dict[str, Any], transform: _ScaleTransform) -> Widget | None:
    if not node.get("SHOW", True):
        return None
    font = _font_from_classic(node, transform)
    width, height = _default_box(node, font.size)
    return Widget(
        global_id=widget_id,
        same_type_id=widget_id,
        parent_name="background",
        object_name=object_name,
        widget_type=2,
        geometry=Geometry(
            x=transform.scale_x(node.get("X", 0) or 0),
            y=transform.scale_y(node.get("Y", 0) or 0),
            width=transform.scale_w(width),
            height=transform.scale_h(height),
        ),
        font=font,
    )


def _placeholder_static_text_widget(
    widget_id: int,
    object_name: str,
    node: dict[str, Any],
    transform: _ScaleTransform,
    label: str,
) -> Widget:
    placeholder_node = dict(node)
    placeholder_node["TEXT"] = placeholder_node.get("TEXT") or label
    return _static_text_widget(widget_id, object_name, placeholder_node, transform)


def _number_widget(widget_id: int, object_name: str, node: dict[str, Any], sensor_key: tuple[str, ...], transform: _ScaleTransform) -> Widget | None:
    if not node.get("SHOW", True):
        return None
    sensor_tuple = CLASSIC_THEME_FAST_SENSORS.get(sensor_key)
    if sensor_tuple is None:
        return None
    fast_sensor, sensor_type_name, sensor_name, reading_name, is_div_1204 = sensor_tuple
    font = _font_from_classic(node, transform, fallback_text="42")
    width, height = _default_box(node, font.size)
    return Widget(
        global_id=widget_id,
        same_type_id=widget_id,
        parent_name="background",
        object_name=object_name,
        widget_type=5,
        geometry=Geometry(
            x=transform.scale_x(node.get("X", 0) or 0),
            y=transform.scale_y(node.get("Y", 0) or 0),
            width=transform.scale_w(width),
            height=transform.scale_h(height),
        ),
        font=font,
        sensor=SensorSpec(
            fast_sensor=fast_sensor,
            sensor_type_name=sensor_type_name,
            sensor_name=sensor_name,
            reading_name=reading_name,
            is_div_1204=is_div_1204,
        ),
        raw_fields={"hAlign": 1},
    )


def _direct_number_widget(widget_id: int, object_name: str, node: dict[str, Any], sensor_key: tuple[str, ...], transform: _ScaleTransform) -> Widget | None:
    if "SHOW" not in node or "FONT_SIZE" not in node:
        return None
    return _number_widget(widget_id, object_name, node, sensor_key, transform)


def _progress_bar_widget(widget_id: int, object_name: str, node: dict[str, Any], sensor_key: tuple[str, ...], transform: _ScaleTransform) -> Widget | None:
    if not node.get("SHOW", True):
        return None
    sensor_tuple = CLASSIC_THEME_FAST_SENSORS.get(sensor_key)
    if sensor_tuple is None:
        return None
    fast_sensor, sensor_type_name, sensor_name, reading_name, is_div_1204 = sensor_tuple
    bar_color_raw = _argb_from_rgb_triplet(node.get("BAR_COLOR"), "0xffffaa00")
    bg_color_raw = _argb_from_rgb_triplet(node.get("BAR_BACKGROUND_COLOR"), "0xff101010")
    frame_color_raw = bar_color_raw if node.get("BAR_OUTLINE", False) else bg_color_raw
    width = transform.scale_w(node.get("WIDTH", 120) or 120)
    height = transform.scale_h(node.get("HEIGHT", 14) or 14)
    return Widget(
        global_id=widget_id,
        same_type_id=widget_id,
        parent_name="background",
        object_name=object_name,
        widget_type=3,
        geometry=Geometry(
            x=transform.scale_x(node.get("X", 0) or 0),
            y=transform.scale_y(node.get("Y", 0) or 0),
            width=width,
            height=height,
        ),
        style=StyleSpec(
            show_type=0,
            bg_color_raw=bg_color_raw,
            bg_color=int(bg_color_raw, 16),
            fg_color_raw=bar_color_raw,
            fg_color=int(bar_color_raw, 16),
            frame_color_raw=frame_color_raw,
            frame_color=int(frame_color_raw, 16),
            bg_image_path="",
            fg_image_path="",
        ),
        sensor=SensorSpec(
            fast_sensor=fast_sensor,
            sensor_type_name=sensor_type_name,
            sensor_name=sensor_name,
            reading_name=reading_name,
            is_div_1204=is_div_1204,
        ),
        raw_fields={"isHide": "0"},
    )


def _placeholder_progress_widget(
    widget_id: int,
    object_name: str,
    node: dict[str, Any],
    transform: _ScaleTransform,
) -> Widget | None:
    if not node.get("SHOW", True):
        return None
    bar_color_raw = _argb_from_rgb_triplet(node.get("BAR_COLOR"), "0xff808080")
    bg_color_raw = _argb_from_rgb_triplet(node.get("BAR_BACKGROUND_COLOR"), "0xff202020")
    frame_color_raw = _argb_from_rgb_triplet(node.get("AXIS_COLOR"), bar_color_raw)
    return Widget(
        global_id=widget_id,
        same_type_id=widget_id,
        parent_name="background",
        object_name=object_name,
        widget_type=3,
        geometry=Geometry(
            x=transform.scale_x(node.get("X", 0) or 0),
            y=transform.scale_y(node.get("Y", 0) or 0),
            width=transform.scale_w(node.get("WIDTH", 120) or 120),
            height=max(8, transform.scale_h(node.get("HEIGHT", 14) or 14)),
        ),
        style=StyleSpec(
            show_type=0,
            bg_color_raw=bg_color_raw,
            bg_color=int(bg_color_raw, 16),
            fg_color_raw=bar_color_raw,
            fg_color=int(bar_color_raw, 16),
            frame_color_raw=frame_color_raw,
            frame_color=int(frame_color_raw, 16),
            bg_image_path="",
            fg_image_path="",
        ),
        raw_fields={"isHide": "0"},
    )


def _line_graph_fallback_widget(widget_id: int, object_name: str, node: dict[str, Any], sensor_key: tuple[str, ...], transform: _ScaleTransform) -> Widget | None:
    if not node.get("SHOW", True):
        return None
    sensor_tuple = CLASSIC_THEME_FAST_SENSORS.get(sensor_key)
    if sensor_tuple is None:
        return None
    fast_sensor, sensor_type_name, sensor_name, reading_name, is_div_1204 = sensor_tuple
    fg_raw = _argb_from_rgb_triplet(node.get("LINE_COLOR"), "0xffffffff")
    axis_raw = _argb_from_rgb_triplet(node.get("AXIS_COLOR"), fg_raw)
    source_height = int(node.get("HEIGHT", 60) or 60)
    width = transform.scale_w(node.get("WIDTH", 120) or 120)
    height = max(8, min(transform.scale_h(18), transform.scale_h(max(10, source_height // 4))))
    y = transform.scale_y(int(node.get("Y", 0) or 0) + max(0, (source_height - max(10, source_height // 4)) // 2))
    return Widget(
        global_id=widget_id,
        same_type_id=widget_id,
        parent_name="background",
        object_name=object_name,
        widget_type=3,
        geometry=Geometry(
            x=transform.scale_x(node.get("X", 0) or 0),
            y=y,
            width=width,
            height=height,
        ),
        style=StyleSpec(
            show_type=0,
            bg_color_raw="0xff000000",
            bg_color=0xFF000000 if node.get("AXIS", False) else 0x00000000,
            fg_color_raw=fg_raw,
            fg_color=int(fg_raw, 16),
            frame_color_raw=axis_raw,
            frame_color=int(axis_raw, 16),
            bg_image_path="",
            fg_image_path="",
        ),
        sensor=SensorSpec(
            fast_sensor=fast_sensor,
            sensor_type_name=sensor_type_name,
            sensor_name=sensor_name,
            reading_name=reading_name,
            is_div_1204=is_div_1204,
        ),
        raw_fields={"isHide": "0"},
    )


def _datetime_widget(widget_id: int, object_name: str, node: dict[str, Any], date_key: str, transform: _ScaleTransform) -> Widget | None:
    if not node.get("SHOW", True):
        return None
    smart_fmt = _map_datetime_format(date_key, node.get("FORMAT", "medium"))
    if not smart_fmt:
        return None
    preview_text = "2026-01-01" if date_key == "DAY" else "12:00:00"
    font = _font_from_classic(node, transform, fallback_text=preview_text)
    width, height = _default_box(node, font.size)
    return Widget(
        global_id=widget_id,
        same_type_id=widget_id,
        parent_name="background",
        object_name=object_name,
        widget_type=6,
        geometry=Geometry(
            x=transform.scale_x(node.get("X", 0) or 0),
            y=transform.scale_y(node.get("Y", 0) or 0),
            width=transform.scale_w(width),
            height=transform.scale_h(height),
        ),
        font=font,
        datetime_format=smart_fmt,
        raw_fields={"hAlign": 1},
    )


def _radial_progress_geometry(node: dict[str, Any], transform: _ScaleTransform) -> Geometry:
    center_x = transform.scale_x(node.get("X", 0) or 0)
    center_y = transform.scale_y(node.get("Y", 0) or 0)
    radius = max(10, transform.scale_w(node.get("RADIUS", 40) or 40))
    bar_thickness = max(8, transform.scale_h(node.get("WIDTH", 14) or 14))
    custom_bbox = node.get("CUSTOM_BBOX")

    if isinstance(custom_bbox, (list, tuple)) and len(custom_bbox) == 4:
        bbox_width = max(60, transform.scale_w(custom_bbox[2]))
        bbox_height = max(10, transform.scale_h(custom_bbox[3]))
        x = max(0, center_x - bbox_width // 2)
        y = max(0, center_y - bbox_height // 2)
        return Geometry(x=x, y=y, width=bbox_width, height=min(max(bar_thickness, 12), bbox_height))

    width = max(90, radius * 2)
    height = max(12, min(24, bar_thickness))
    x = max(0, center_x - width // 2)
    y = max(0, center_y + radius - height // 2)
    return Geometry(x=x, y=y, width=width, height=height)


def _radial_text_geometry(node: dict[str, Any], font_size: int, transform: _ScaleTransform) -> Geometry:
    center_x = transform.scale_x(node.get("X", 0) or 0)
    center_y = transform.scale_y(node.get("Y", 0) or 0)
    text_offset = node.get("TEXT_OFFSET")
    offset_x = 0
    offset_y = 0
    if isinstance(text_offset, (list, tuple)) and len(text_offset) >= 2:
        offset_x = transform.scale_x(text_offset[0])
        offset_y = transform.scale_y(text_offset[1])
    width = max(80, int(font_size * 3.5))
    height = max(font_size + 10, int(font_size * 1.6))
    x = max(0, center_x - width // 2 + offset_x)
    y = max(0, center_y - height // 2 + offset_y)
    return Geometry(x=x, y=y, width=width, height=height)


def _radial_progress_widget(widget_id: int, object_name: str, node: dict[str, Any], sensor_key: tuple[str, ...], transform: _ScaleTransform) -> Widget | None:
    if not node.get("SHOW", True):
        return None
    sensor_tuple = CLASSIC_THEME_FAST_SENSORS.get(sensor_key)
    if sensor_tuple is None:
        return None
    fast_sensor, sensor_type_name, sensor_name, reading_name, is_div_1204 = sensor_tuple
    bar_color_raw = _argb_from_rgb_triplet(node.get("BAR_COLOR"), "0xffffaa00")
    bg_color_raw = _argb_from_rgb_triplet(node.get("BAR_BACKGROUND_COLOR"), "0xff101010")
    draw_bg = bool(node.get("DRAW_BAR_BACKGROUND", False))
    frame_color_raw = bar_color_raw
    geometry = _radial_progress_geometry(node, transform)
    return Widget(
        global_id=widget_id,
        same_type_id=widget_id,
        parent_name="background",
        object_name=object_name,
        widget_type=3,
        geometry=geometry,
        style=StyleSpec(
            show_type=0,
            bg_color_raw=bg_color_raw,
            bg_color=int(bg_color_raw, 16) if draw_bg else 0x00000000,
            fg_color_raw=bar_color_raw,
            fg_color=int(bar_color_raw, 16),
            frame_color_raw=frame_color_raw,
            frame_color=int(frame_color_raw, 16),
            bg_image_path="",
            fg_image_path="",
        ),
        sensor=SensorSpec(
            fast_sensor=fast_sensor,
            sensor_type_name=sensor_type_name,
            sensor_name=sensor_name,
            reading_name=reading_name,
            is_div_1204=is_div_1204,
        ),
        raw_fields={"isHide": "0"},
    )


def _radial_number_widget(widget_id: int, object_name: str, node: dict[str, Any], sensor_key: tuple[str, ...], transform: _ScaleTransform) -> Widget | None:
    if not node.get("SHOW", True) or not node.get("SHOW_TEXT", False):
        return None
    sensor_tuple = CLASSIC_THEME_FAST_SENSORS.get(sensor_key)
    if sensor_tuple is None:
        return None
    fast_sensor, sensor_type_name, sensor_name, reading_name, is_div_1204 = sensor_tuple
    font = _font_from_classic(node, transform, fallback_text="42")
    geometry = _radial_text_geometry(node, font.size, transform)
    return Widget(
        global_id=widget_id,
        same_type_id=widget_id,
        parent_name="background",
        object_name=object_name,
        widget_type=5,
        geometry=geometry,
        font=font,
        sensor=SensorSpec(
            fast_sensor=fast_sensor,
            sensor_type_name=sensor_type_name,
            sensor_name=sensor_name,
            reading_name=reading_name,
            is_div_1204=is_div_1204,
        ),
        raw_fields={"hAlign": 1},
    )


def convert_classic_theme_to_smartmonitor_project(
    theme_path: str | Path,
    output_dir: str | Path,
    project_name: str | None = None,
) -> ClassicThemeConversionResult:
    theme_data, theme_dir = _load_classic_theme(theme_path)
    source_width, source_height = _source_canvas(theme_data)
    transform = _ScaleTransform(source_width=source_width, source_height=source_height)
    width, height = transform.target_width, transform.target_height
    output_dir = Path(output_dir)
    project_name = project_name or theme_dir.name
    project_dir = output_dir / project_name
    images_dir = project_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    copied_assets: list[Path] = []
    skipped_items: list[str] = []
    placeholder_items: list[str] = []
    preview_path = project_dir / "preview.png"

    background_src = _background_path(theme_data, theme_dir)
    background_asset = None
    if background_src and background_src.is_file():
        background_asset = _copy_asset(background_src, images_dir, resize_to=(width, height))
        copied_assets.append(background_asset)

    try:
        render_classic_theme_preview(theme_dir, preview_path)
    except Exception:
        preview_path = None

    widgets: list[Widget] = []
    widget_id = 0

    for name, node in (theme_data.get("static_images", {}) or {}).items():
        if str(name).upper() == "BACKGROUND" or not isinstance(node, dict):
            continue
        image_path = node.get("PATH")
        if not image_path:
            skipped_items.append(f"static_images/{name}")
            continue
        src = (theme_dir / str(image_path)).resolve()
        if not src.is_file():
            skipped_items.append(f"static_images/{name}")
            continue
        asset = _copy_asset(
            src,
            images_dir,
            resize_to=(
                transform.scale_w(node.get("WIDTH", 80) or 80),
                transform.scale_h(node.get("HEIGHT", 80) or 80),
            ),
        )
        copied_assets.append(asset)
        widget = _image_widget(widget_id, f"IMG_{name}", node, asset, transform)
        if widget is not None:
            widgets.append(widget)
            widget_id += 1

    for name, node in (theme_data.get("static_text", {}) or {}).items():
        if not isinstance(node, dict):
            continue
        widget = _static_text_widget(widget_id, str(name), node, transform)
        if widget is not None:
            widgets.append(widget)
            widget_id += 1

    stats_root = theme_data.get("STATS", {}) or {}
    for section_name, section_node in stats_root.items():
        if not isinstance(section_node, dict):
            continue

        if section_name == "DATE":
            for date_key in ("DAY", "HOUR"):
                date_node = section_node.get(date_key, {}) if isinstance(section_node.get(date_key, {}), dict) else {}
                text_node = date_node.get("TEXT", {}) if isinstance(date_node.get("TEXT", {}), dict) else {}
                widget = _datetime_widget(widget_id, f"{date_key.title()} {widget_id}", text_node, date_key, transform)
                if widget is not None:
                    widgets.append(widget)
                    widget_id += 1
                elif text_node and text_node.get("SHOW", True):
                    skipped_items.append(f"DATE/{date_key}/TEXT")
            continue

        for metric_name, metric_node in section_node.items():
            if not isinstance(metric_node, dict):
                continue

            direct_widget = _direct_number_widget(
                widget_id,
                f"{section_name}_{metric_name}_DIRECT_{widget_id}",
                metric_node,
                (str(section_name), str(metric_name)),
                transform,
            )
            if direct_widget is not None:
                widgets.append(direct_widget)
                widget_id += 1

            for text_variant in ("TEXT", "PERCENT_TEXT"):
                text_node = metric_node.get(text_variant, {}) if isinstance(metric_node.get(text_variant, {}), dict) else {}
                if not text_node:
                    continue
                widget = _number_widget(
                    widget_id,
                    f"{section_name}_{metric_name}_{text_variant}_{widget_id}",
                    text_node,
                    (str(section_name), str(metric_name)),
                    transform,
                )
                if widget is not None:
                    widgets.append(widget)
                    widget_id += 1
                elif text_node.get("SHOW", True):
                    placeholder = _placeholder_static_text_widget(
                        widget_id,
                        f"{section_name}_{metric_name}_{text_variant}_PLACEHOLDER_{widget_id}",
                        text_node,
                        transform,
                        f"{section_name} {metric_name}".replace("_", " "),
                    )
                    widgets.append(placeholder)
                    widget_id += 1
                    placeholder_items.append(f"{section_name}/{metric_name}/{text_variant}")

            for nested_metric_name in ("USED", "FREE", "TOTAL"):
                nested_node = metric_node.get(nested_metric_name, {}) if isinstance(metric_node.get(nested_metric_name, {}), dict) else {}
                if not nested_node:
                    continue
                widget = _number_widget(
                    widget_id,
                    f"{section_name}_{metric_name}_{nested_metric_name}_{widget_id}",
                    nested_node,
                    (str(section_name), str(metric_name), str(nested_metric_name)),
                    transform,
                )
                if widget is not None:
                    widgets.append(widget)
                    widget_id += 1
                elif nested_node.get("SHOW", True):
                    placeholder = _placeholder_static_text_widget(
                        widget_id,
                        f"{section_name}_{metric_name}_{nested_metric_name}_PLACEHOLDER_{widget_id}",
                        nested_node,
                        transform,
                        f"{metric_name} {nested_metric_name}".replace("_", " "),
                    )
                    widgets.append(placeholder)
                    widget_id += 1
                    placeholder_items.append(f"{section_name}/{metric_name}/{nested_metric_name}")

            graph_node = metric_node.get("GRAPH", {}) if isinstance(metric_node.get("GRAPH", {}), dict) else {}
            if graph_node:
                widget = _progress_bar_widget(
                    widget_id,
                    f"{section_name}_{metric_name}_GRAPH_{widget_id}",
                    graph_node,
                    (str(section_name), str(metric_name)),
                    transform,
                )
                if widget is not None:
                    widgets.append(widget)
                    widget_id += 1
                elif graph_node.get("SHOW", True):
                    placeholder = _placeholder_progress_widget(
                        widget_id,
                        f"{section_name}_{metric_name}_GRAPH_PLACEHOLDER_{widget_id}",
                        graph_node,
                        transform,
                    )
                    if placeholder is not None:
                        widgets.append(placeholder)
                        widget_id += 1
                        placeholder_items.append(f"{section_name}/{metric_name}/GRAPH")
                    else:
                        skipped_items.append(f"{section_name}/{metric_name}/GRAPH")

            line_graph_node = metric_node.get("LINE_GRAPH", {}) if isinstance(metric_node.get("LINE_GRAPH", {}), dict) else {}
            if line_graph_node and not graph_node:
                widget = _line_graph_fallback_widget(
                    widget_id,
                    f"{section_name}_{metric_name}_LINE_GRAPH_{widget_id}",
                    line_graph_node,
                    (str(section_name), str(metric_name)),
                    transform,
                )
                if widget is not None:
                    widgets.append(widget)
                    widget_id += 1
                elif line_graph_node.get("SHOW", True):
                    placeholder = _placeholder_progress_widget(
                        widget_id,
                        f"{section_name}_{metric_name}_LINE_GRAPH_PLACEHOLDER_{widget_id}",
                        line_graph_node,
                        transform,
                    )
                    if placeholder is not None:
                        widgets.append(placeholder)
                        widget_id += 1
                        placeholder_items.append(f"{section_name}/{metric_name}/LINE_GRAPH")
                    else:
                        skipped_items.append(f"{section_name}/{metric_name}/LINE_GRAPH")

            radial_node = metric_node.get("RADIAL", {}) if isinstance(metric_node.get("RADIAL", {}), dict) else {}
            if radial_node:
                widget = _radial_progress_widget(
                    widget_id,
                    f"{section_name}_{metric_name}_RADIAL_BAR_{widget_id}",
                    radial_node,
                    (str(section_name), str(metric_name)),
                    transform,
                )
                if widget is not None:
                    widgets.append(widget)
                    widget_id += 1
                elif radial_node.get("SHOW", True):
                    placeholder = _placeholder_progress_widget(
                        widget_id,
                        f"{section_name}_{metric_name}_RADIAL_PLACEHOLDER_{widget_id}",
                        radial_node,
                        transform,
                    )
                    if placeholder is not None:
                        widgets.append(placeholder)
                        widget_id += 1
                        placeholder_items.append(f"{section_name}/{metric_name}/RADIAL_BAR")
                    else:
                        skipped_items.append(f"{section_name}/{metric_name}/RADIAL_BAR")

                text_widget = _radial_number_widget(
                    widget_id,
                    f"{section_name}_{metric_name}_RADIAL_TEXT_{widget_id}",
                    radial_node,
                    (str(section_name), str(metric_name)),
                    transform,
                )
                if text_widget is not None:
                    widgets.append(text_widget)
                    widget_id += 1

    theme = SmartMonitorTheme(
        path=str(project_dir / f"{project_name}.ui"),
        widget_parents=[_widget_parent(width, height, background_asset)],
        widgets=widgets,
    )
    ui_path = project_dir / f"{project_name}.ui"
    write_theme_file(ui_path, theme)

    config_ini = project_dir / "config.ini"
    config_ini.write_text("[StartupPic]\n", encoding="utf-8")

    bundle = SmartMonitorThemeBundle(
        ui_path=str(ui_path),
        base_dir=str(project_dir),
        theme=theme,
        startup_pic=StartupPicSpec(),
    )
    return ClassicThemeConversionResult(
        bundle=bundle,
        output_dir=project_dir,
        ui_path=ui_path,
        copied_assets=copied_assets,
        skipped_items=skipped_items,
        placeholder_items=placeholder_items,
        preview_path=preview_path,
    )


def find_classic_theme_files(root: str | Path) -> list[Path]:
    root_path = Path(root)
    return sorted(root_path.rglob("theme.yaml"))


def batch_convert_classic_themes(
    root: str | Path,
    output_root: str | Path,
    compile_root: str | Path | None = None,
    preview_root: str | Path | None = None,
) -> list[ClassicThemeBatchItem]:
    from library.smartmonitor_compile import compile_theme_file

    results: list[ClassicThemeBatchItem] = []
    output_root = Path(output_root)
    compile_root = Path(compile_root) if compile_root else None
    preview_root = Path(preview_root) if preview_root else None

    for theme_file in find_classic_theme_files(root):
        theme_name = theme_file.parent.name
        item = ClassicThemeBatchItem(theme_name=theme_name, theme_path=theme_file, status="unsupported")
        try:
            result = convert_classic_theme_to_smartmonitor_project(theme_file, output_root, project_name=theme_name)
            item.ui_path = result.ui_path
            item.preview_path = result.preview_path
            item.widget_count = result.widget_count
            item.skipped_items = list(result.skipped_items)
            item.placeholder_items = list(result.placeholder_items)
            item.status = result.status

            if preview_root and result.preview_path and result.preview_path.is_file():
                preview_target = Path(preview_root) / f"{theme_name}.png"
                preview_target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(result.preview_path, preview_target)
                item.preview_path = preview_target

            if compile_root is not None:
                payload = compile_theme_file(result.ui_path)
                dat_path = Path(compile_root) / f"{theme_name}.dat"
                dat_path.parent.mkdir(parents=True, exist_ok=True)
                dat_path.write_bytes(payload)
                item.dat_path = dat_path
        except Exception as exc:
            item.error = str(exc)
            item.status = "unsupported"
        results.append(item)
    return results
