import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

CONFIG_CANDIDATES = [
    Path.home() / ".config" / "waybar" / "config.jsonc",
    Path.home() / ".config" / "waybar" / "config",
]

MODULE_ARRAYS = ["modules-left", "modules-center", "modules-right"]


class WaybarConfigError(Exception):
    pass


def find_config() -> Path:
    for path in CONFIG_CANDIDATES:
        if path.exists():
            return path
    raise WaybarConfigError(
        f"No waybar config found. Checked: {', '.join(str(p) for p in CONFIG_CANDIDATES)}"
    )


def _strip_jsonc_comments(text: str) -> str:
    """Strip // line comments, /* */ block comments, and trailing
    commas so the standard json module can parse waybar's config.jsonc.
    Naive but sufficient for waybar's typical config style (no // or /*
    inside string values in practice, though this could misfire on edge
    cases)."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"(?<!:)//.*", "", text)
    # Remove trailing commas before a closing ] or } (valid in jsonc,
    # invalid in strict json)
    text = re.sub(r",(\s*[\]}])", r"\1", text)
    return text


def load_config(path: Path | None = None) -> dict:
    path = path or find_config()
    raw = path.read_text()
    try:
        return json.loads(_strip_jsonc_comments(raw))
    except json.JSONDecodeError as e:
        raise WaybarConfigError(f"Could not parse {path}: {e}")


def list_modules(config: dict) -> dict:
    """Return {array_name: [module, ...]} for each of the three module
    position arrays present in the config."""
    return {key: config.get(key, []) for key in MODULE_ARRAYS if key in config}


def all_enabled_modules(config: dict) -> list[str]:
    enabled = []
    for key in MODULE_ARRAYS:
        enabled.extend(config.get(key, []))
    return enabled


def backup_config(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = path.with_suffix(path.suffix + f".bak-{timestamp}")
    shutil.copy2(path, backup_path)
    return backup_path


def toggle_module(config: dict, module: str, array: str = "modules-right") -> tuple[dict, bool]:
    """Add or remove `module` from the given array. Returns the updated
    config and whether the module ended up enabled (True) or disabled (False)."""
    enabled_now = module in all_enabled_modules(config)

    if enabled_now:
        for key in MODULE_ARRAYS:
            if key in config and module in config[key]:
                config[key] = [m for m in config[key] if m != module]
        return config, False
    else:
        config.setdefault(array, [])
        config[array].append(module)
        return config, True


def save_config(config: dict, path: Path) -> Path:
    """Backs up the original file, then writes the new config as plain
    JSON. Note: this discards comments/formatting from the original
    .jsonc — acceptable for v0.1, worth a known-limitation callout."""
    backup_path = backup_config(path)
    path.write_text(json.dumps(config, indent=2) + "\n")
    return backup_path


def reload_waybar() -> None:
    """Restart waybar so the config change takes effect."""
    subprocess.run(["killall", "waybar"], capture_output=True)
    subprocess.Popen(
        ["waybar"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
