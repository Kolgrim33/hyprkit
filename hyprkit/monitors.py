import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

DEFAULT_CONFIG = Path.home() / ".config" / "hypr" / "hyprland.conf"


class HyprctlError(Exception):
    pass


def _run_hyprctl(args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["hyprctl"] + args, capture_output=True, text=True, timeout=5
        )
    except FileNotFoundError:
        raise HyprctlError("hyprctl not found — is Hyprland running?")
    if result.returncode != 0:
        raise HyprctlError(result.stderr.strip() or "hyprctl command failed")
    return result.stdout


def get_monitors() -> list[dict]:
    """Return live monitor info from `hyprctl monitors -j`, including
    each monitor's available modes for safe selection."""
    out = _run_hyprctl(["monitors", "-j"])
    return json.loads(out)


def find_monitor(name: str) -> dict | None:
    for mon in get_monitors():
        if mon["name"] == name:
            return mon
    return None


def available_modes(monitor: dict) -> list[str]:
    """Return supported resolution@refresh combos for a monitor, deduped."""
    modes = monitor.get("availableModes", [])
    # availableModes look like "1920x1080@60.00Hz" - normalize a bit
    seen = []
    for m in modes:
        if m not in seen:
            seen.append(m)
    return seen


def apply_live(name: str, resolution: str, position: str, scale: float) -> None:
    """Apply a monitor change immediately via hyprctl, with no config
    file changes yet — lets the user preview before persisting."""
    value = f"{name},{resolution},{position},{scale}"
    _run_hyprctl(["keyword", "monitor", value])


def backup_config(config_path: Path = DEFAULT_CONFIG) -> Path:
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found at {config_path}")
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = config_path.with_suffix(config_path.suffix + f".bak-{timestamp}")
    shutil.copy2(config_path, backup_path)
    return backup_path


def persist_monitor_line(
    name: str,
    resolution: str,
    position: str,
    scale: float,
    config_path: Path = DEFAULT_CONFIG,
) -> Path:
    """Write/replace the `monitor=` line for this monitor in the config
    file. Always backs up first. Returns the backup path."""
    backup_path = backup_config(config_path)

    new_line = f"monitor={name},{resolution},{position},{scale}\n"
    lines = config_path.read_text().splitlines(keepends=True)

    replaced = False
    out_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("monitor=") and stripped.split(",")[0] == f"monitor={name}":
            out_lines.append(new_line)
            replaced = True
        else:
            out_lines.append(line)

    if not replaced:
        out_lines.append(new_line)

    config_path.write_text("".join(out_lines))
    return backup_path
