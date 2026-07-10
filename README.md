# hyprkit
<img width="1222" height="798" alt="hyprkit" src="https://github.com/user-attachments/assets/ce030084-27c5-49f7-badc-7b6bf4a91b17" />

A companion CLI for managing and improving your Hyprland setup.

![Python](https://img.shields.io/badge/python-3.11+-blue)
![Platform](https://img.shields.io/badge/platform-Arch%20Linux-blue)

## What it does

`hyprkit monitors`  List and configure monitors without hand-editing config 

`hyprkit waybar` Toggle Waybar modules on/off and reload instantly 
 `
 hyprkit doctor`  Health check your Hyprland setup with a scored report 
 
 `hyprkit lint`  Catch config bugs before they break your session 
 
 `hyprkit config` |Interactively improve your existing or generate a new`hyprland.conf` 

## Install

```bash
git clone https://github.com/Kolgrim33/hyprkit.git
cd hyprkit
pip install --break-system-packages -e .
```

## Commands

### `hyprkit monitors`

```bash
hyprkit monitors            # list active monitors
hyprkit monitors set eDP-1  # interactively reconfigure a monitor
```

`monitors set` walks you through:
1. Picking a resolution/refresh from modes Hyprland actually reports as supported
2. Setting scale and position
3. Applying a live preview via `hyprctl keyword monitor` — see the change before committing
4. On confirmation, backs up `hyprland.conf` and writes the new `monitor=` line

If you don't confirm, nothing is written to disk — the live change reverts on next reload.


### `hyprkit waybar`

```bash
hyprkit waybar                        # list active modules
hyprkit waybar toggle clock           # toggle a module on/off
hyprkit waybar toggle network --array modules-left
```

Finds your Waybar config automatically, toggles the module, saves, and restarts Waybar.
<img width="1056" height="567" alt="hyprkit1" src="https://github.com/user-attachments/assets/2195b5bf-d619-4cdd-b467-3c7d8700d085" />


### `hyprkit doctor`

```bash
hyprkit doctor
```

Runs health checks across your Hyprland session and gives you an overall health score:

- Hyprland running
- Waybar installed and running
- Nerd Font installed
- Audio server (PipeWire/PulseAudio) active
- Network connectivity
- Clipboard (wl-clipboard) available



### `hyprkit lint`

```bash
hyprkit lint
```

Reads your `hyprland.conf` and flags issues before they silently break things:

- `$VAR` used before it's defined
- Duplicate keybinds (reports both conflicting line numbers)
- Missing `$mainMod` definition
- Dead binaries in `exec` / `exec-once` lines
- Malformed `monitor=` lines
- Unclosed braces
- Missing `source=` files

On first run against the author's own config it caught 5 real issues including 4 duplicate `ALT+Tab` binds and a dead binary.
<img width="1837" height="945" alt="hyprkit2" src="https://github.com/user-attachments/assets/efbb52ab-4908-4a7b-883e-a73f6659b2ed" />


### `hyprkit config`

```bash
hyprkit config
```

Interactively improves your existing `hyprland.conf`:

1. Runs `hyprkit lint` first so you know what's broken
2. Walks through each issue and asks what to do:
   - Missing `$mainMod` → pick your modifier key, it gets inserted
   - Duplicate keybinds → choose which one wins
   - Dead `exec` binaries → optionally remove them
   - Missing `animations`, `decoration`, `input` blocks → inject sensible defaults
3. Shows a diff of every change before saving
4. Backs up your original config with a timestamp
5. Re-runs lint on the improved config to confirm issues resolved

Nothing is written without your confirmation.


## Requirements

- Python 3.11+
- Hyprland (running session for `monitors` and `doctor`)
- `rich` (`pip install rich`)

## Roadmap

- `hyprkit config --fresh` — generate a new config from scratch
- `hyprkit switch` — hyprswitch integration for window management
- XDG portal and screen sharing checks in `doctor`
- Lua config support (Hyprland v0.55+)


