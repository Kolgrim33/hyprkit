import shutil
from pathlib import Path
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import box

from hyprkit import monitors as mon
from hyprkit.lint import lint_config, DEFAULT_CONFIG

console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _backup(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = path.with_suffix(path.suffix + f".bak-{timestamp}")
    shutil.copy2(path, backup)
    return backup


def _detect(candidates: list[str]) -> list[str]:
    """Return which candidates are available in PATH."""
    return [c for c in candidates if shutil.which(c)]


# ---------------------------------------------------------------------------
# Questions
# ---------------------------------------------------------------------------

def _ask_terminal() -> str:
    candidates = ["kitty", "foot", "alacritty", "wezterm", "ghostty", "konsole"]
    found = _detect(candidates)

    if not found:
        console.print("[yellow]⚠[/yellow]  No known terminal found in PATH.")
        return Prompt.ask("Enter your terminal command manually")

    console.print("\n[bold]Terminals detected:[/bold]")
    for i, t in enumerate(found, 1):
        console.print(f"  {i}. {t}")
    if len(found) == 1:
        if Confirm.ask(f"  Use [bold]{found[0]}[/bold]?", default=True):
            return found[0]
    pick = Prompt.ask("Pick a terminal", choices=[str(i) for i in range(1, len(found) + 1)], default="1")
    return found[int(pick) - 1]


def _ask_mainmod() -> str:
    console.print("\n[bold]Main modifier key:[/bold]")
    options = ["SUPER", "ALT", "SUPER ALT", "CTRL SUPER"]
    for i, o in enumerate(options, 1):
        console.print(f"  {i}. {o}")
    pick = Prompt.ask("Pick modifier", choices=[str(i) for i in range(1, len(options) + 1)], default="1")
    return options[int(pick) - 1]


def _ask_launcher() -> str | None:
    candidates = ["rofi", "wofi", "walker", "fuzzel", "tofi"]
    found = _detect(candidates)

    if not found:
        console.print("\n[yellow]⚠[/yellow]  No app launcher found in PATH.")
        console.print("  [dim]Install rofi-wayland: paru -S rofi-wayland[/dim]")
        if Confirm.ask("  Skip launcher keybind for now?", default=True):
            return None
        return Prompt.ask("  Enter launcher command manually")

    console.print("\n[bold]App launchers detected:[/bold]")
    for i, l in enumerate(found, 1):
        console.print(f"  {i}. {l}")
    options = found + ["none"]
    for i, o in enumerate(options, 1):
        console.print(f"  {i}. {o}") if o == "none" else None
    console.print(f"  {len(options)}. none")
    pick = Prompt.ask("Pick launcher", choices=[str(i) for i in range(1, len(options) + 1)], default="1")
    chosen = options[int(pick) - 1]
    return None if chosen == "none" else chosen


def _ask_bar() -> str | None:
    candidates = ["waybar", "hyprpanel"]
    found = _detect(candidates)

    console.print("\n[bold]Status bar:[/bold]")
    options = found + ["none"]
    for i, o in enumerate(options, 1):
        console.print(f"  {i}. {o}" + (" [dim](installed)[/dim]" if o in found else ""))
    pick = Prompt.ask("Pick bar", choices=[str(i) for i in range(1, len(options) + 1)], default="1")
    chosen = options[int(pick) - 1]
    return None if chosen == "none" else chosen


def _ask_wallpaper() -> str | None:
    candidates = ["hyprpaper", "swww", "awww"]
    found = _detect(candidates)

    console.print("\n[bold]Wallpaper tool:[/bold]")
    options = found + ["none"]
    for i, o in enumerate(options, 1):
        console.print(f"  {i}. {o}" + (" [dim](installed)[/dim]" if o in found else ""))
    pick = Prompt.ask("Pick wallpaper tool", choices=[str(i) for i in range(1, len(options) + 1)], default="1")
    chosen = options[int(pick) - 1]
    return None if chosen == "none" else chosen


def _ask_style() -> str:
    console.print("\n[bold]Config style:[/bold]")
    console.print("  1. minimal   — just the essentials, no animations or blur")
    console.print("  2. balanced  — animations + rounded corners, no heavy blur")
    console.print("  3. full      — animations, blur, shadows, rounded corners")
    pick = Prompt.ask("Pick style", choices=["1", "2", "3"], default="2")
    return ["minimal", "balanced", "full"][int(pick) - 1]


# ---------------------------------------------------------------------------
# Config generation
# ---------------------------------------------------------------------------

def _monitor_lines(mons: list[dict]) -> str:
    if not mons:
        return "monitor=,preferred,auto,1"
    lines = []
    for m in mons:
        res = f'{m["width"]}x{m["height"]}@{m["refreshRate"]:.2f}Hz'
        pos = f'{m["x"]},{m["y"]}'
        scale = m.get("scale", 1)
        lines.append(f'monitor={m["name"]},{res},{pos},{scale}')
    return "\n".join(lines)


def _generate(
    mainmod: str,
    terminal: str,
    launcher: str | None,
    bar: str | None,
    wallpaper_tool: str | None,
    style: str,
    monitor_block: str,
) -> str:

    launcher_bind = (
        f"bind = $mainMod, R, exec, {launcher} -show drun"
        if launcher == "rofi"
        else f"bind = $mainMod, R, exec, {launcher}"
        if launcher
        else "# bind = $mainMod, R, exec, <your-launcher>  # no launcher detected"
    )

    bar_exec = (
        f"exec-once = {bar}"
        if bar
        else "# exec-once = waybar  # no bar selected"
    )

    wallpaper_exec = (
        f"exec-once = {wallpaper_tool}-daemon" if wallpaper_tool in ("swww", "awww")
        else f"exec-once = {wallpaper_tool}" if wallpaper_tool == "hyprpaper"
        else "# exec-once = hyprpaper  # no wallpaper tool selected"
    )

    decoration_block = ""
    if style == "minimal":
        decoration_block = """
decoration {
    rounding = 0
}
"""
    elif style == "balanced":
        decoration_block = """
decoration {
    rounding = 8
    drop_shadow = yes
    shadow_range = 4
    shadow_render_power = 3
}
"""
    else:  # full
        decoration_block = """
decoration {
    rounding = 10
    drop_shadow = yes
    shadow_range = 4
    shadow_render_power = 3
    blur {
        enabled = true
        size = 5
        passes = 2
        new_optimizations = true
    }
}
"""

    animations_block = ""
    if style == "minimal":
        animations_block = """
animations {
    enabled = no
}
"""
    else:
        animations_block = """
animations {
    enabled = yes
    bezier = myBezier, 0.05, 0.9, 0.1, 1.05
    animation = windows, 1, 7, myBezier
    animation = windowsOut, 1, 7, default, popin 80%
    animation = fade, 1, 7, default
    animation = workspaces, 1, 6, default
}
"""

    return f"""# hyprland.conf — generated by hyprkit config --fresh
# Edit freely. Run `hyprkit lint` to check for issues.

################
# Variables
################
$mainMod = {mainmod}
$terminal = {terminal}

################
# Monitors
################
{monitor_block}

################
# Autostart
################
{bar_exec}
{wallpaper_exec}
exec-once = /usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1

################
# Input
################
input {{
    kb_layout = us
    follow_mouse = 1
    sensitivity = 0
    touchpad {{
        natural_scroll = yes
        disable_while_typing = true
    }}
}}

################
# General
################
general {{
    gaps_in = 5
    gaps_out = 10
    border_size = 2
    col.active_border = rgba(33ccffee) rgba(0099ffaa) 45deg
    col.inactive_border = rgba(595959aa)
    layout = dwindle
}}
{decoration_block}
{animations_block}
################
# Layouts
################
dwindle {{
    pseudotile = yes
    preserve_split = yes
}}

################
# Keybinds
################
# Terminal
bind = $mainMod, Q, exec, $terminal
# Kill focused window
bind = $mainMod, C, killactive
# Exit Hyprland
bind = $mainMod SHIFT, E, exit
# Toggle floating
bind = $mainMod, V, togglefloating
# App launcher
{launcher_bind}
# Move focus
bind = $mainMod, left, movefocus, l
bind = $mainMod, right, movefocus, r
bind = $mainMod, up, movefocus, u
bind = $mainMod, down, movefocus, d
# Move windows
bind = $mainMod SHIFT, left, movewindow, l
bind = $mainMod SHIFT, right, movewindow, r
bind = $mainMod SHIFT, up, movewindow, u
bind = $mainMod SHIFT, down, movewindow, d
# Workspaces
bind = $mainMod, 1, workspace, 1
bind = $mainMod, 2, workspace, 2
bind = $mainMod, 3, workspace, 3
bind = $mainMod, 4, workspace, 4
bind = $mainMod, 5, workspace, 5
bind = $mainMod, 6, workspace, 6
bind = $mainMod, 7, workspace, 7
bind = $mainMod, 8, workspace, 8
bind = $mainMod, 9, workspace, 9
# Move window to workspace
bind = $mainMod SHIFT, 1, movetoworkspace, 1
bind = $mainMod SHIFT, 2, movetoworkspace, 2
bind = $mainMod SHIFT, 3, movetoworkspace, 3
bind = $mainMod SHIFT, 4, movetoworkspace, 4
bind = $mainMod SHIFT, 5, movetoworkspace, 5
# Screenshot
bind = , Print, exec, grim -g "$(slurp)" ~/Pictures/$(date +"%Y-%m-%d_%H-%M-%S").png
bind = SHIFT, Print, exec, grim ~/Pictures/$(date +"%Y-%m-%d_%H-%M-%S").png
# Brightness
bindel = , XF86MonBrightnessUp, exec, brightnessctl set +5%
bindel = , XF86MonBrightnessDown, exec, brightnessctl set 5%-
# Volume
bindel = , XF86AudioRaiseVolume, exec, wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%+
bindel = , XF86AudioLowerVolume, exec, wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-
bindel = , XF86AudioMute, exec, wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle

################
# Window Rules
################
windowrulev2 = float, class:^(pavucontrol)$
windowrulev2 = float, title:^(Open File)(.*)$
windowrulev2 = float, title:^(Save As)(.*)$
"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_fresh(path: Path = DEFAULT_CONFIG) -> int:
    console.print(Panel.fit(
        "[bold cyan]hyprkit config --fresh[/bold cyan]\n"
        "[dim]Generate a new hyprland.conf tailored to your hardware[/dim]",
        box=box.ROUNDED,
    ))

    # Detect monitors
    console.print("\n[cyan]Detecting monitors...[/cyan]")
    try:
        mons = mon.get_monitors()
        for m in mons:
            console.print(f"  ✓ [green]{m['name']}[/green] {m['width']}x{m['height']}@{m['refreshRate']:.2f}Hz")
        monitor_block = _monitor_lines(mons)
    except mon.HyprctlError:
        console.print("  [yellow]⚠ Could not detect monitors (Hyprland not running?) — using preferred/auto fallback[/yellow]")
        monitor_block = "monitor=,preferred,auto,1"

    # Ask questions
    terminal = _ask_terminal()
    mainmod = _ask_mainmod()
    launcher = _ask_launcher()
    bar = _ask_bar()
    wallpaper_tool = _ask_wallpaper()
    style = _ask_style()

    # Generate
    config = _generate(mainmod, terminal, launcher, bar, wallpaper_tool, style, monitor_block)

    # Preview
    console.print("\n[bold]Preview (first 30 lines):[/bold]")
    for i, line in enumerate(config.splitlines()[:30], 1):
        console.print(f"  [dim]{i:3}[/dim]  {line}")
    console.print("  [dim]... (run `hyprkit lint` after saving to check the full file)[/dim]")

    if not Confirm.ask("\nSave to ~/.config/hypr/hyprland.conf?", default=True):
        console.print("[yellow]Not saved.[/yellow]")
        return 0

    # Backup existing
    if path.exists():
        backup = _backup(path)
        console.print(f"[dim]Backed up existing config to {backup}[/dim]")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(config)
    console.print(f"\n[green]✓ Saved to {path}[/green]")

    # Lint check
    console.print("\n[cyan]Running lint on generated config...[/cyan]")
    issues = lint_config(path)
    if not issues:
        console.print("[green]✓ Clean — no issues found.[/green]")
    else:
        console.print(f"[yellow]{len(issues)} issue(s) — run `hyprkit lint` for details.[/yellow]")

    console.print("\n[dim]Run `hyprctl reload` to apply, or log out and back in.[/dim]\n")
    return 0
