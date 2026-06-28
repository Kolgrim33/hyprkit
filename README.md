# hyprkit

A companion CLI for Hyprland. v0.1 focuses on one real pain point:
configuring monitors without hand-editing `hyprland.conf`.

## Install (dev mode)

```bash
pip install --break-system-packages -e .
```

## Usage

```bash
hyprkit monitors            # list current monitors
hyprkit monitors set eDP-1  # interactively reconfigure a monitor
```

`monitors set` walks you through:
1. Picking a resolution/refresh combo from modes Hyprland actually reports as supported
2. Setting scale and position
3. Applying live via `hyprctl keyword monitor` so you can see the change before committing
4. On confirmation, backing up `hyprland.conf` (timestamped) and writing the new `monitor=` line

If you don't confirm, nothing is written to disk — the live change just
reverts on your next Hyprland reload/restart.

## Roadmap

- Waybar module management
- `hyprkit doctor` — health checks for Hyprland setup
- Theme installer with safe, validated config merging
