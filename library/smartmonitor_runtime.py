# SPDX-License-Identifier: GPL-3.0-or-later
#
# Runtime integration for the 3.5" HID SmartMonitor that uses an uploaded
# vendor theme (`img.dat`) plus live tag/value packets instead of a raw
# framebuffer.

import math
import threading
import time
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from library import config
from library.log import logger

_LAST_VALID_VALUES: dict[str, int] = {}
_RUNTIME_READY = True
_RUNTIME_DISABLED_REASON: str | None = None
_DISK_IO_SAMPLE: tuple[float, float] | None = None
_RUNTIME_THREADS: list[threading.Thread] = []
_WEATHER_CACHE: tuple[float, dict[str, float]] | None = None
_THEME_DEFAULT_TAGS: dict[str, dict[str, int]] = {
    "theme_science fiction.dat": {
        "CPU_PERCENT": 3,
        "CPU_TEMP": 1,
        "GPU_PERCENT": 7,
        "GPU_TEMP": 5,
        "RAM_PERCENT": 12,
        "DISK_PERCENT": 17,
        "NET_UP_KBPS": 18,
        "NET_DOWN_KBPS": 19,
        "CPU_FAN": 4,
    },
    "rog03-compiled.dat": {
        "CPU_TEMP": 1,
        "GPU_TEMP": 5,
        "CPU_PERCENT": 3,
    },
}
_THEME_DEFAULT_FLAGS: dict[str, dict[str, bool]] = {
    "theme_science fiction.dat": {
        "SMARTMONITOR_HID_SEND_TIME": False,
    },
}
_METRIC_LABELS: dict[str, str] = {
    "CPU_TEMP": "CPU temperature",
    "CPU_PERCENT": "CPU usage",
    "CPU_FREQ_MHZ": "CPU frequency",
    "CPU_FAN": "CPU fan",
    "GPU_TEMP": "GPU temperature",
    "GPU_PERCENT": "GPU usage",
    "GPU_FPS": "GPU FPS",
    "GPU_MEM_PERCENT": "GPU memory %",
    "GPU_MEM_USED_MB": "GPU memory used",
    "GPU_FREQ_MHZ": "GPU frequency",
    "RAM_PERCENT": "RAM usage",
    "RAM_USED_GB": "RAM used",
    "RAM_FREE_GB": "RAM free",
    "RAM_TOTAL_GB": "RAM total",
    "DISK_PERCENT": "Disk activity",
    "DISK_USED_GB": "Disk used",
    "DISK_FREE_GB": "Disk free",
    "DISK_TOTAL_GB": "Disk total",
    "NET_UP_KBPS": "Upload KB/s",
    "NET_DOWN_KBPS": "Download KB/s",
    "SOUND_VOLUME": "Sound volume",
    "UPTIME_HOURS": "Uptime hours",
    "WEATHER_TEMP": "Weather temperature",
    "WEATHER_FEELS_LIKE": "Weather feels like",
    "WEATHER_HUMIDITY": "Weather humidity",
}


def _normalized_theme_path(value: str | Path | None) -> str:
    if not value:
        return ""
    try:
        return str(Path(value).expanduser().resolve())
    except Exception:
        return str(Path(value).expanduser())


def is_enabled() -> bool:
    display_config = config.CONFIG_DATA.get("display", {})
    return display_config.get("REVISION") == "A_HID" and display_config.get("SMARTMONITOR_HID_RUNTIME", False)


def _display_config():
    return config.CONFIG_DATA.get("display", {})


def _active_theme_name() -> str:
    return Path(_display_config().get("SMARTMONITOR_HID_THEME_FILE", "") or "").name.lower()


def _active_theme_stem() -> str:
    return Path(_display_config().get("SMARTMONITOR_HID_THEME_FILE", "") or "").stem


@lru_cache(maxsize=32)
def _theme_metadata(theme_stem: str) -> dict | None:
    if not theme_stem:
        return None
    metadata_path = Path(config.MAIN_DIRECTORY) / "res" / "smartmonitor" / "themes" / theme_stem / "metadata.yaml"
    if not metadata_path.is_file():
        return None
    try:
        return config.load_yaml(metadata_path) or {}
    except Exception:
        return None


@lru_cache(maxsize=32)
def _resolve_theme_source_ui_path(theme_stem: str) -> Path | None:
    metadata = _theme_metadata(theme_stem)
    if not isinstance(metadata, dict):
        return None

    source_ui = metadata.get("source_ui")
    if source_ui:
        source_ui_path = Path(source_ui).expanduser()
        if source_ui_path.is_file():
            return source_ui_path

    vendor_theme = metadata.get("source_vendor_theme")
    candidate_dirs: list[Path] = []
    if vendor_theme:
        candidate_dirs.extend([
            Path(config.MAIN_DIRECTORY) / "vendor" / "themefor3.5" / str(vendor_theme),
            Path(config.MAIN_DIRECTORY) / "WIND" / "3.5 Inch SmartMonitor" / "themefor3.5" / str(vendor_theme),
        ])

    candidate_dirs.extend([
        Path(config.MAIN_DIRECTORY) / "res" / "smartmonitor" / "projects" / theme_stem,
        Path(config.MAIN_DIRECTORY) / "res" / "smartmonitor" / "themes" / theme_stem,
    ])

    for directory in candidate_dirs:
        if not directory.is_dir():
            continue
        ui_files = sorted(directory.glob("*.ui"))
        if ui_files:
            return ui_files[0]

    return None


@lru_cache(maxsize=32)
def _theme_bundle(theme_stem: str):
    source_ui_path = _resolve_theme_source_ui_path(theme_stem)
    if source_ui_path is None:
        return None
    try:
        from library.smartmonitor_ui import parse_theme_bundle
        return parse_theme_bundle(source_ui_path)
    except Exception:
        return None


def _theme_flag(name: str, default: bool) -> bool:
    theme_file = _active_theme_name()
    theme_defaults = _THEME_DEFAULT_FLAGS.get(theme_file, {})
    if name in theme_defaults:
        return bool(theme_defaults[name])
    if name == "SMARTMONITOR_HID_SEND_TIME":
        theme_bundle = _theme_bundle(_active_theme_stem())
        if theme_bundle is not None and any(widget.widget_type == 6 for widget in theme_bundle.theme.widgets):
            return True
    if name in _display_config():
        return bool(_display_config().get(name))
    return default


def _derive_metric_name(sensor_type_name: str, sensor_name: str, reading_name: str) -> str | None:
    sensor_type = (sensor_type_name or "").strip().lower()
    sensor = (sensor_name or "").strip().lower()
    reading = (reading_name or "").strip().lower()

    if sensor_type == "temperature" and "cpu" in reading:
        return "CPU_TEMP"
    if sensor_type == "temperature" and ("gpu" in reading or "graphics" in reading):
        return "GPU_TEMP"
    if sensor_type == "usage" and "cpu" in reading:
        return "CPU_PERCENT"
    if sensor_type == "usage" and "gpu memory" in reading:
        return "GPU_MEM_PERCENT"
    if sensor_type == "usage" and "gpu" in reading:
        return "GPU_PERCENT"
    if sensor_type == "other" and "fps" in reading:
        return "GPU_FPS"
    if sensor_type == "other" and "physical memory load" in reading:
        return "RAM_PERCENT"
    if sensor_type == "other" and "physical memory used" in reading:
        return "RAM_USED_GB"
    if sensor_type == "other" and "physical memory free" in reading:
        return "RAM_FREE_GB"
    if sensor_type == "other" and "physical memory total" in reading:
        return "RAM_TOTAL_GB"
    if sensor_type == "other" and "disk load" in reading:
        return "DISK_PERCENT"
    if sensor_type == "other" and "disk used" in reading:
        return "DISK_USED_GB"
    if sensor_type == "other" and "disk free" in reading:
        return "DISK_FREE_GB"
    if sensor_type == "other" and "disk total" in reading:
        return "DISK_TOTAL_GB"
    if sensor_type == "other" and "gpu memory used" in reading:
        return "GPU_MEM_USED_MB"
    if sensor_type == "fan" and "cpu" in reading:
        return "CPU_FAN"
    if sensor_type == "frequency" and "core clock" in reading and "gpu" in sensor:
        return "GPU_FREQ_MHZ"
    if sensor_type == "frequency" and "core clock" in reading:
        return "CPU_FREQ_MHZ"
    if sensor_type == "other" and "sound volume" in reading:
        return "SOUND_VOLUME"
    if sensor_type == "other" and "system uptime hours" in reading:
        return "UPTIME_HOURS"
    if sensor_type == "other" and "weather temperature" in reading:
        return "WEATHER_TEMP"
    if sensor_type == "other" and "weather feels like" in reading:
        return "WEATHER_FEELS_LIKE"
    if sensor_type == "other" and "weather humidity" in reading:
        return "WEATHER_HUMIDITY"
    if "network:" in sensor and "current up rate" in reading:
        return "NET_UP_KBPS"
    if "network:" in sensor and "current dl rate" in reading:
        return "NET_DOWN_KBPS"
    return None


def get_runtime_metric_choices() -> list[str]:
    return sorted(_METRIC_LABELS.keys())


def get_runtime_metric_label(metric_name: str) -> str:
    return _METRIC_LABELS.get(metric_name, metric_name.replace("_", " ").title())


def _theme_runtime_rows_from_bundle(theme_bundle) -> list[dict]:
    rows: list[dict] = []
    if theme_bundle is None:
        return rows

    for widget in theme_bundle.theme.widgets:
        if widget.sensor is None or widget.sensor.fast_sensor < 0:
            continue
        metric_name = _derive_metric_name(
            widget.sensor.sensor_type_name,
            widget.sensor.sensor_name,
            widget.sensor.reading_name,
        )
        rows.append({
            "tag": int(widget.sensor.fast_sensor),
            "metric": metric_name or "",
            "metric_label": get_runtime_metric_label(metric_name) if metric_name else "",
            "sensor_type_name": widget.sensor.sensor_type_name or "",
            "sensor_name": widget.sensor.sensor_name or "",
            "reading_name": widget.sensor.reading_name or "",
            "object_name": widget.object_name or "",
            "widget_type": int(widget.widget_type),
        })

    rows.sort(key=lambda item: (item["tag"], item["object_name"]))
    return rows


def get_theme_runtime_rows(theme_name_or_path: str | Path) -> list[dict]:
    identifier = str(theme_name_or_path or "").strip()
    if not identifier:
        return []
    theme_stem = Path(identifier).stem
    return _theme_runtime_rows_from_bundle(_theme_bundle(theme_stem))


def _theme_sensor_mapping() -> dict[str, int]:
    theme_bundle = _theme_bundle(_active_theme_stem())
    if theme_bundle is None:
        return {}

    resolved: dict[str, int] = {}
    for widget in theme_bundle.theme.widgets:
        if widget.sensor is None:
            continue
        metric_name = _derive_metric_name(
            widget.sensor.sensor_type_name,
            widget.sensor.sensor_name,
            widget.sensor.reading_name,
        )
        if metric_name and widget.sensor.fast_sensor >= 0:
            resolved.setdefault(metric_name, int(widget.sensor.fast_sensor))
    return resolved


def _tag_mapping() -> dict[str, int]:
    mapping = _display_config().get("SMARTMONITOR_HID_TAGS", {}) or {}
    resolved = {str(key): int(value) for key, value in mapping.items() if value is not None}

    theme_file = _active_theme_name()
    derived = _theme_sensor_mapping()
    for key, value in derived.items():
        resolved.setdefault(key, int(value))

    defaults = _THEME_DEFAULT_TAGS.get(theme_file, {})
    for key, value in defaults.items():
        resolved.setdefault(key, int(value))

    return resolved


def _active_theme_runtime_supported() -> bool:
    theme_stem = _active_theme_stem()
    if not theme_stem:
        return True

    metadata = _theme_metadata(theme_stem)
    if not isinstance(metadata, dict):
        return True

    if metadata.get("compiler") != "experimental_ui_to_imgdat":
        return True
    if not bool(_display_config().get("SMARTMONITOR_HID_ALLOW_EXPERIMENTAL_RUNTIME", True)):
        return False
    if _theme_bundle(theme_stem) is not None:
        return True
    if _tag_mapping():
        return True
    logger.warning(
        "SmartMonitor theme '%s' has no resolved source UI for runtime mapping; using best-effort runtime mode",
        _active_theme_name(),
    )
    return True


def _post_upload_runtime_delay() -> float:
    metadata = _theme_metadata(_active_theme_stem())
    if isinstance(metadata, dict) and metadata.get("compiler") == "experimental_ui_to_imgdat":
        return float(_display_config().get("SMARTMONITOR_HID_POST_UPLOAD_DELAY", 6.0))
    return 1.0


def _network_rates_kbps(update_interval: float) -> tuple[float, float]:
    import library.stats as stats
    import psutil

    config_section = config.CONFIG_DATA.get("config", {})
    interfaces = [config_section.get("WLO", "") or "", config_section.get("ETH", "") or ""]
    if not any(interfaces):
        for if_name, if_stats in psutil.net_if_stats().items():
            if if_name == "lo" or not if_stats.isup:
                continue
            interfaces = [if_name]
            break
    upload_rate = math.nan
    download_rate = math.nan

    for if_name in interfaces:
        if not if_name:
            continue
        up_bps, _, down_bps, _ = stats.sensors.Net.stats(if_name, update_interval)
        if up_bps >= 0:
            upload_rate = up_bps / 1024.0
        if down_bps >= 0:
            download_rate = down_bps / 1024.0
        if not math.isnan(upload_rate) or not math.isnan(download_rate):
            break

    return upload_rate, download_rate


def _disk_used_gb() -> float:
    import library.stats as stats

    used_bytes = stats.sensors.Disk.disk_used()
    if used_bytes < 0:
        return math.nan
    return used_bytes / (1024.0 ** 3)


def _disk_free_gb() -> float:
    import library.stats as stats

    free_bytes = stats.sensors.Disk.disk_free()
    if free_bytes < 0:
        return math.nan
    return free_bytes / (1024.0 ** 3)


def _disk_total_gb() -> float:
    import library.stats as stats

    used_bytes = stats.sensors.Disk.disk_used()
    free_bytes = stats.sensors.Disk.disk_free()
    if used_bytes < 0 or free_bytes < 0:
        return math.nan
    return (used_bytes + free_bytes) / (1024.0 ** 3)


def _ram_used_gb() -> float:
    import library.stats as stats

    used_bytes = stats.sensors.Memory.virtual_used()
    if used_bytes < 0:
        return math.nan
    return used_bytes / (1024.0 ** 3)


def _ram_free_gb() -> float:
    import library.stats as stats

    free_bytes = stats.sensors.Memory.virtual_free()
    if free_bytes < 0:
        return math.nan
    return free_bytes / (1024.0 ** 3)


def _ram_total_gb() -> float:
    import library.stats as stats

    used_bytes = stats.sensors.Memory.virtual_used()
    free_bytes = stats.sensors.Memory.virtual_free()
    if used_bytes < 0 or free_bytes < 0:
        return math.nan
    return (used_bytes + free_bytes) / (1024.0 ** 3)


def _uptime_hours() -> float:
    import psutil

    return max(0.0, (time.time() - psutil.boot_time()) / 3600.0)


def _disk_busy_percent(update_interval: float) -> float:
    import psutil

    global _DISK_IO_SAMPLE
    counters = psutil.disk_io_counters()
    if counters is None or not hasattr(counters, "busy_time"):
        return math.nan

    now = time.monotonic()
    busy_time = float(counters.busy_time)
    previous = _DISK_IO_SAMPLE
    _DISK_IO_SAMPLE = (now, busy_time)
    if previous is None:
        return math.nan

    prev_now, prev_busy = previous
    elapsed = max(now - prev_now, update_interval, 0.001)
    busy_delta = max(0.0, busy_time - prev_busy)
    return min(100.0, (busy_delta / (elapsed * 1000.0)) * 100.0)


def _cpu_freq_mhz() -> float:
    import library.stats as stats

    return stats.sensors.Cpu.frequency()


def _gpu_percent() -> float:
    import library.stats as stats

    gpu_load, _, _, _, _ = stats.sensors.Gpu.stats()
    return gpu_load


def _gpu_mem_percent() -> float:
    import library.stats as stats

    _, gpu_mem_load, _, _, _ = stats.sensors.Gpu.stats()
    return gpu_mem_load


def _gpu_mem_used_mb() -> float:
    import library.stats as stats

    _, _, gpu_mem_used_mb, _, _ = stats.sensors.Gpu.stats()
    return gpu_mem_used_mb


def _gpu_freq_mhz() -> float:
    import library.stats as stats

    return stats.sensors.Gpu.frequency()


def _gpu_fps() -> float:
    import library.stats as stats

    return stats.sensors.Gpu.fps()


def _cpu_fan_percent() -> float:
    import library.stats as stats

    cpu_fan_name = config.CONFIG_DATA.get("config", {}).get("CPU_FAN", "AUTO")
    if cpu_fan_name == "AUTO":
        return stats.sensors.Cpu.fan_percent()
    return stats.sensors.Cpu.fan_percent(cpu_fan_name)


def _sound_volume_percent() -> float:
    import re
    import shutil
    import subprocess

    candidates = [
        ["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"],
        ["pamixer", "--get-volume"],
        ["amixer", "get", "Master"],
    ]
    for command in candidates:
        if shutil.which(command[0]) is None:
            continue
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=2.0)
        except Exception:
            continue
        output = (result.stdout or "") + "\n" + (result.stderr or "")
        if command[0] == "wpctl":
            match = re.search(r"Volume:\s*([0-9]*\.?[0-9]+)", output)
            if match:
                return float(match.group(1)) * 100.0
        else:
            match = re.search(r"([0-9]{1,3})%", output)
            if match:
                return float(match.group(1))
    return math.nan


def _weather_metrics() -> dict[str, float]:
    global _WEATHER_CACHE
    now = time.monotonic()
    if _WEATHER_CACHE is not None:
        cached_at, cached_values = _WEATHER_CACHE
        if now - cached_at < 300.0:
            return dict(cached_values)

    values = {
        "WEATHER_TEMP": math.nan,
        "WEATHER_FEELS_LIKE": math.nan,
        "WEATHER_HUMIDITY": math.nan,
    }

    try:
        import requests
    except Exception:
        _WEATHER_CACHE = (now, values)
        return dict(values)

    config_section = config.CONFIG_DATA.get("config", {})
    lat = config_section.get("WEATHER_LATITUDE", "")
    lon = config_section.get("WEATHER_LONGITUDE", "")
    api_key = config_section.get("WEATHER_API_KEY", "")
    units = config_section.get("WEATHER_UNITS", "metric")
    lang = config_section.get("WEATHER_LANGUAGE", "en")

    if not api_key or not lat or not lon:
        _WEATHER_CACHE = (now, values)
        return dict(values)

    url = (
        "https://api.openweathermap.org/data/3.0/onecall"
        f"?lat={lat}&lon={lon}&exclude=minutely,hourly,daily,alerts"
        f"&appid={api_key}&units={units}&lang={lang}"
    )
    try:
        response = requests.get(url, timeout=5.0)
        if response.status_code == 200:
            data = response.json().get("current", {})
            values["WEATHER_TEMP"] = float(data.get("temp", math.nan))
            values["WEATHER_FEELS_LIKE"] = float(data.get("feels_like", math.nan))
            values["WEATHER_HUMIDITY"] = float(data.get("humidity", math.nan))
    except Exception:
        pass

    _WEATHER_CACHE = (now, values)
    return dict(values)


def _collect_metric_value(metric_name: str, update_interval: float):
    metric_readers = {
        "CPU_TEMP": lambda: _sticky_metric_value("CPU_TEMP", __import__("library.stats", fromlist=[""]).sensors.Cpu.temperature(), min_valid=1),
        "CPU_PERCENT": lambda: _sticky_metric_value("CPU_PERCENT", __import__("library.stats", fromlist=[""]).sensors.Cpu.percentage(interval=None)),
        "CPU_FREQ_MHZ": lambda: _sticky_metric_value("CPU_FREQ_MHZ", _cpu_freq_mhz(), min_valid=1),
        "CPU_FAN": lambda: _sticky_metric_value("CPU_FAN", _cpu_fan_percent(), min_valid=1),
        "GPU_TEMP": lambda: _sticky_metric_value("GPU_TEMP", __import__("library.stats", fromlist=[""]).sensors.Gpu.stats()[4], min_valid=1),
        "GPU_PERCENT": lambda: _sticky_metric_value("GPU_PERCENT", _gpu_percent(), min_valid=0),
        "GPU_FPS": lambda: _sticky_metric_value("GPU_FPS", _gpu_fps(), min_valid=0),
        "GPU_MEM_PERCENT": lambda: _sticky_metric_value("GPU_MEM_PERCENT", _gpu_mem_percent(), min_valid=0),
        "GPU_MEM_USED_MB": lambda: _sticky_metric_value("GPU_MEM_USED_MB", _gpu_mem_used_mb(), min_valid=0),
        "GPU_FREQ_MHZ": lambda: _sticky_metric_value("GPU_FREQ_MHZ", _gpu_freq_mhz(), min_valid=1),
        "RAM_PERCENT": lambda: _sticky_metric_value("RAM_PERCENT", __import__("library.stats", fromlist=[""]).sensors.Memory.virtual_percent()),
        "RAM_USED_GB": lambda: _sticky_metric_value("RAM_USED_GB", _ram_used_gb(), min_valid=0),
        "RAM_FREE_GB": lambda: _sticky_metric_value("RAM_FREE_GB", _ram_free_gb(), min_valid=0),
        "RAM_TOTAL_GB": lambda: _sticky_metric_value("RAM_TOTAL_GB", _ram_total_gb(), min_valid=1),
        "DISK_PERCENT": lambda: _sticky_metric_value("DISK_PERCENT", _disk_busy_percent(update_interval)),
        "DISK_USED_GB": lambda: _sticky_metric_value("DISK_USED_GB", _disk_used_gb(), min_valid=0),
        "DISK_FREE_GB": lambda: _sticky_metric_value("DISK_FREE_GB", _disk_free_gb(), min_valid=0),
        "DISK_TOTAL_GB": lambda: _sticky_metric_value("DISK_TOTAL_GB", _disk_total_gb(), min_valid=1),
        "NET_UP_KBPS": lambda: _sticky_metric_value("NET_UP_KBPS", _network_rates_kbps(update_interval)[0], min_valid=0),
        "NET_DOWN_KBPS": lambda: _sticky_metric_value("NET_DOWN_KBPS", _network_rates_kbps(update_interval)[1], min_valid=0),
        "SOUND_VOLUME": lambda: _sticky_metric_value("SOUND_VOLUME", _sound_volume_percent(), min_valid=0),
        "UPTIME_HOURS": lambda: _sticky_metric_value("UPTIME_HOURS", _uptime_hours(), min_valid=0),
        "WEATHER_TEMP": lambda: _sticky_metric_value("WEATHER_TEMP", _weather_metrics()["WEATHER_TEMP"]),
        "WEATHER_FEELS_LIKE": lambda: _sticky_metric_value("WEATHER_FEELS_LIKE", _weather_metrics()["WEATHER_FEELS_LIKE"]),
        "WEATHER_HUMIDITY": lambda: _sticky_metric_value("WEATHER_HUMIDITY", _weather_metrics()["WEATHER_HUMIDITY"], min_valid=0),
    }
    reader = metric_readers.get(metric_name)
    if reader is None:
        return None
    return reader()


def _disable_runtime(reason: str):
    global _RUNTIME_READY, _RUNTIME_DISABLED_REASON
    _RUNTIME_READY = False
    _RUNTIME_DISABLED_REASON = reason


def _clear_upload_on_start_flag():
    display_config = config.CONFIG_DATA.setdefault("display", {})
    if not display_config.get("SMARTMONITOR_HID_UPLOAD_ON_START", False):
        return

    display_config["SMARTMONITOR_HID_UPLOAD_ON_START"] = False
    with open(Path(config.MAIN_DIRECTORY) / "config.yaml", "w", encoding="utf-8") as stream:
        import yaml
        yaml.safe_dump(config.CONFIG_DATA, stream, sort_keys=False, allow_unicode=True)


def _mark_uploaded_theme(theme_path: Path):
    display_config = config.CONFIG_DATA.setdefault("display", {})
    display_config["SMARTMONITOR_HID_LAST_UPLOAD_ATTEMPTED_THEME"] = _normalized_theme_path(theme_path)
    display_config["SMARTMONITOR_HID_LAST_UPLOADED_THEME"] = _normalized_theme_path(theme_path)
    with open(Path(config.MAIN_DIRECTORY) / "config.yaml", "w", encoding="utf-8") as stream:
        import yaml
        yaml.safe_dump(config.CONFIG_DATA, stream, sort_keys=False, allow_unicode=True)


def _mark_upload_attempted_theme(theme_path: Path):
    display_config = config.CONFIG_DATA.setdefault("display", {})
    display_config["SMARTMONITOR_HID_LAST_UPLOAD_ATTEMPTED_THEME"] = _normalized_theme_path(theme_path)
    display_config["SMARTMONITOR_HID_UPLOAD_ON_START"] = False
    with open(Path(config.MAIN_DIRECTORY) / "config.yaml", "w", encoding="utf-8") as stream:
        import yaml
        yaml.safe_dump(config.CONFIG_DATA, stream, sort_keys=False, allow_unicode=True)


def _sleep_until_stopped(seconds: float):
    import library.scheduler as scheduler

    deadline = time.monotonic() + seconds
    while not scheduler.STOPPING and time.monotonic() < deadline:
        time.sleep(min(0.2, deadline - time.monotonic()))


def _safe_int(value, default: int = 0) -> int:
    if value is None:
        return default
    try:
        if math.isnan(value):
            return default
    except TypeError:
        pass
    return int(round(value))


def _sticky_metric_value(metric_name: str, raw_value, default: int = 0, min_valid: int | None = None) -> int:
    value = _safe_int(raw_value, default=default)

    if raw_value is None:
        return _LAST_VALID_VALUES.get(metric_name, default)

    try:
        if math.isnan(raw_value):
            return _LAST_VALID_VALUES.get(metric_name, default)
    except TypeError:
        pass

    if min_valid is not None and value < min_valid:
        return _LAST_VALID_VALUES.get(metric_name, default)

    _LAST_VALID_VALUES[metric_name] = value
    return value


def _collect_runtime_pairs() -> list[tuple[int, int]]:
    tag_mapping = _tag_mapping()
    pairs: list[tuple[int, int]] = []
    update_interval = float(_display_config().get("SMARTMONITOR_HID_UPDATE_INTERVAL", 2.0))

    for metric_name, tag in tag_mapping.items():
        if not tag:
            continue
        value = _collect_metric_value(metric_name, update_interval)
        if value is None:
            continue
        pairs.append((int(tag), int(value)))

    return pairs


def _log_theme_runtime_fields():
    rows = get_theme_runtime_rows(_active_theme_name())
    if not rows:
        logger.info("SmartMonitor theme fields: no runtime-capable sensor widgets resolved for '%s'", _active_theme_name())
        return

    preview = "; ".join(
        f"tag {row['tag']} -> {row['metric'] or 'unmapped'} [{row['sensor_name']}/{row['reading_name']}]"
        for row in rows[:12]
    )
    if len(rows) > 12:
        preview += "; ..."
    logger.info("SmartMonitor theme fields (%d): %s", len(rows), preview)


def _send_runtime_snapshot(lcd, log_label: str | None = None):
    pairs = _collect_runtime_pairs()
    last_error = None

    for attempt in range(1, 3):
        try:
            if _theme_flag("SMARTMONITOR_HID_SEND_TIME", True):
                lcd.smartmonitor_send_datetime(datetime.now())
            if pairs:
                lcd.smartmonitor_send_raw_command(int(_display_config().get("SMARTMONITOR_HID_CMD", 2)), pairs)
                if log_label:
                    logger.info("%s SmartMonitor runtime values: %s", log_label, pairs)
            return pairs
        except Exception as exc:
            last_error = exc
            if attempt == 2:
                break
            logger.warning("SmartMonitor runtime snapshot failed, recovering device and retrying once: %s", exc)
            lcd.recoverSerial(attempts=5, wait_after_close=1.0)

    if last_error is not None:
        raise last_error
    return pairs


def initialize_display():
    from library.display import display
    global _RUNTIME_READY, _RUNTIME_DISABLED_REASON

    lcd = display.lcd
    _RUNTIME_READY = True
    _RUNTIME_DISABLED_REASON = None
    try:
        lcd.recoverSerial(attempts=5, wait_after_close=0.5)
    except Exception:
        try:
            lcd.openSerial()
        except Exception:
            pass
    theme_file = _display_config().get("SMARTMONITOR_HID_THEME_FILE", "") or ""
    theme_path = Path(theme_file).expanduser() if theme_file else None
    runtime_supported = _active_theme_runtime_supported()
    upload_on_start = bool(_display_config().get("SMARTMONITOR_HID_UPLOAD_ON_START", False))
    last_uploaded_theme = _normalized_theme_path(_display_config().get("SMARTMONITOR_HID_LAST_UPLOADED_THEME", ""))
    last_attempted_theme = _normalized_theme_path(_display_config().get("SMARTMONITOR_HID_LAST_UPLOAD_ATTEMPTED_THEME", ""))
    normalized_theme_path = _normalized_theme_path(theme_path) if theme_path else ""
    if (
        theme_path
        and normalized_theme_path != last_uploaded_theme
        and normalized_theme_path != last_attempted_theme
    ):
        upload_on_start = True
    if theme_path and not runtime_supported:
        upload_on_start = True
    uploaded_theme = False

    if theme_path and upload_on_start:
        if not theme_path.is_file():
            logger.error("SmartMonitor runtime theme file not found: %s", theme_path)
            raise SystemExit(1)
        logger.info("Uploading SmartMonitor runtime theme from %s", theme_path)
        _mark_upload_attempted_theme(theme_path)
        try:
            lcd.openSerial()
            lcd.smartmonitor_upload_theme(str(theme_path))
            uploaded_theme = True
            _mark_uploaded_theme(theme_path)
            _clear_upload_on_start_flag()
        except Exception as exc:
            logger.warning("SmartMonitor theme upload failed, continuing with existing theme: %s", exc)
            try:
                lcd.closeSerial()
            except Exception:
                pass
            time.sleep(1.0)
            lcd.recoverSerial(attempts=5, wait_after_close=1.0)
    else:
        lcd.openSerial()

    metadata = _theme_metadata(_active_theme_stem())
    if isinstance(metadata, dict) and metadata.get("compiler") == "experimental_ui_to_imgdat":
        logger.info("SmartMonitor runtime is running in experimental mode for compiled theme '%s'", _active_theme_name())

    if not runtime_supported:
        _disable_runtime("theme-only mode for experimental compiled theme")
        logger.info("SmartMonitor live runtime is disabled for the active compiled theme; theme-only mode is active")
        return

    _log_theme_runtime_fields()
    logger.info("SmartMonitor runtime tag mapping: %s", _tag_mapping())

    warmup_cycles = 3 if uploaded_theme else 1
    warmup_delay = _post_upload_runtime_delay() if uploaded_theme else 1.0
    last_pairs = []

    try:
        for cycle in range(warmup_cycles):
            if cycle:
                time.sleep(warmup_delay)
            last_pairs = _send_runtime_snapshot(
                lcd,
                log_label="Sent initial" if cycle == 0 else f"Sent warmup #{cycle + 1}",
            )
    except Exception as exc:
        _disable_runtime(str(exc))
        logger.warning("SmartMonitor live runtime is not available for the active theme/device state: %s", exc)
        return

    if not last_pairs:
        logger.warning("No SmartMonitor runtime values were available during initialization")


def _time_worker():
    from library.display import display
    import library.scheduler as scheduler

    lcd = display.lcd
    interval = float(_display_config().get("SMARTMONITOR_HID_TIME_INTERVAL", 1.0))
    if not _theme_flag("SMARTMONITOR_HID_SEND_TIME", True):
        logger.info("SmartMonitor time updates are disabled for the active theme")
        return
    while not scheduler.STOPPING:
        try:
            lcd.smartmonitor_send_datetime(datetime.now())
        except Exception as exc:
            logger.warning("SmartMonitor time update failed: %s", exc)
        _sleep_until_stopped(interval)


def _metrics_worker():
    from library.display import display
    import library.scheduler as scheduler

    lcd = display.lcd
    command = int(_display_config().get("SMARTMONITOR_HID_CMD", 2))
    interval = float(_display_config().get("SMARTMONITOR_HID_UPDATE_INTERVAL", 2.0))
    while not scheduler.STOPPING:
        try:
            pairs = _collect_runtime_pairs()
            if pairs:
                lcd.smartmonitor_send_raw_command(command, pairs)
        except Exception as exc:
            logger.warning("SmartMonitor metrics update failed: %s", exc)
        _sleep_until_stopped(interval)


def start():
    global _RUNTIME_THREADS
    if not _RUNTIME_READY:
        if _RUNTIME_DISABLED_REASON:
            logger.warning("SmartMonitor runtime workers are disabled: %s", _RUNTIME_DISABLED_REASON)
        else:
            logger.warning("SmartMonitor runtime workers are disabled because initialization failed")
        return []

    logger.info("Starting SmartMonitor HID runtime mode")

    time_thread = threading.Thread(target=_time_worker, name="SmartMonitor_Time", daemon=True)
    metrics_thread = threading.Thread(target=_metrics_worker, name="SmartMonitor_Metrics", daemon=True)
    time_thread.start()
    metrics_thread.start()
    _RUNTIME_THREADS = [time_thread, metrics_thread]
    return list(_RUNTIME_THREADS)


def stop(timeout: float = 3.0):
    import library.scheduler as scheduler

    scheduler.STOPPING = True
    deadline = time.monotonic() + max(0.0, timeout)
    for thread in list(_RUNTIME_THREADS):
        remaining = max(0.0, deadline - time.monotonic())
        if remaining <= 0:
            break
        if thread.is_alive():
            thread.join(remaining)
