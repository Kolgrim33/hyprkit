import argparse
import sys

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm, FloatPrompt

from hyprkit import monitors as mon
from hyprkit import waybar as wb
from hyprkit import doctor
from hyprkit import lint as lint_mod
from hyprkit import config_wizard
from hyprkit import fresh_config
from hyprkit.result import Status

console = Console()


def cmd_doctor() -> int:
    console.print("[cyan]Running Hyprland health checks...[/cyan]\n")
    results = doctor.run_all()

    table = Table(title="Hyprland Doctor")
    table.add_column("Check", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Detail")

    icon = {Status.OK: "[green]✓[/green]", Status.WARN: "[yellow]⚠[/yellow]", Status.FAIL: "[red]✗[/red]"}
    score = 100
    for r in results:
        table.add_row(r.name, icon[r.status], r.detail)
        score -= r.score_penalty
    score = max(score, 0)

    console.print(table)

    issues = [r for r in results if r.status != Status.OK]
    if issues:
        console.print("\n[bold]Recommendations[/bold]")
        for r in issues:
            console.print(f"  • [bold]{r.name}[/bold] ({r.severity.value}): {r.recommendation}")
            if r.why_it_matters:
                console.print(f"    [dim]{r.why_it_matters}[/dim]")

    console.print(f"\n[bold]Overall Health[/bold]: {score}%\n")
    return 0


def cmd_lint() -> int:
    from hyprkit.lint import DEFAULT_CONFIG
    path = DEFAULT_CONFIG
    console.print(f"[cyan]Linting[/cyan] [dim]{path}[/dim]\n")

    issues = lint_mod.lint_config(path)

    if not issues:
        console.print("[green]✓ No issues found.[/green]")
        return 0

    table = Table(title="hyprkit lint")
    table.add_column("Line", no_wrap=True, justify="right")
    table.add_column("Severity", no_wrap=True)
    table.add_column("Issue")

    severity_color = {
        "High": "[red]HIGH[/red]",
        "Medium": "[yellow]MEDIUM[/yellow]",
        "Low": "[dim]LOW[/dim]",
    }

    for issue in issues:
        line_str = str(issue.line_no) if issue.line_no else "—"
        sev = severity_color.get(issue.severity.value, issue.severity.value)
        table.add_row(line_str, sev, issue.message)

    console.print(table)
    console.print(f"\n[bold]{len(issues)} issue(s) found.[/bold]\n")

    highs = sum(1 for i in issues if i.severity.value == "High")
    return 1 if highs > 0 else 0


def cmd_config() -> int:
    return config_wizard.run_wizard()


def cmd_list() -> int:
    try:
        mons = mon.get_monitors()
    except mon.HyprctlError as e:
        console.print(f"[red]Error:[/red] {e}")
        return 1

    table = Table(title="Monitors", expand=False)
    table.add_column("Name", no_wrap=True)
    table.add_column("Resolution", no_wrap=True)
    table.add_column("Refresh", no_wrap=True)
    table.add_column("Scale", no_wrap=True)
    table.add_column("Position", no_wrap=True)

    for m in mons:
        table.add_row(
            m["name"],
            f'{m["width"]}x{m["height"]}',
            f'{m["refreshRate"]:.2f}Hz',
            str(m.get("scale", "?")),
            f'{m["x"]},{m["y"]}',
        )
    console.print(table)
    return 0


def cmd_waybar_list() -> int:
    try:
        path = wb.find_config()
        config = wb.load_config(path)
    except wb.WaybarConfigError as e:
        console.print(f"[red]Error:[/red] {e}")
        return 1

    console.print(f"Config: [dim]{path}[/dim]\n")
    modules = wb.list_modules(config)
    for array, mods in modules.items():
        console.print(f"[bold]{array}[/bold]")
        if not mods:
            console.print("  (none)")
        for m in mods:
            console.print(f"  ✓ {m}")
        console.print()
    return 0


def cmd_waybar_toggle(module: str, array: str) -> int:
    try:
        path = wb.find_config()
        config = wb.load_config(path)
    except wb.WaybarConfigError as e:
        console.print(f"[red]Error:[/red] {e}")
        return 1

    config, enabled = wb.toggle_module(config, module, array)
    state = "[green]enabled[/green]" if enabled else "[yellow]disabled[/yellow]"
    console.print(f"{module} will be {state}.")

    if not Confirm.ask("Save and reload waybar?"):
        console.print("[yellow]Not saved.[/yellow]")
        return 0

    backup_path = wb.save_config(config, path)
    wb.reload_waybar()
    console.print(f"[green]Saved and reloaded.[/green] Backup: {backup_path}")
    console.print("[dim]Note: saving rewrites the file as plain JSON, so any comments in config.jsonc are not preserved.[/dim]")
    return 0


def cmd_set(name: str) -> int:
    monitor = mon.find_monitor(name)
    if monitor is None:
        console.print(f"[red]No monitor named '{name}' found.[/red] Run `hyprkit monitors` to see available monitors.")
        return 1

    modes = mon.available_modes(monitor)
    if not modes:
        console.print("[yellow]No available modes reported by hyprctl — falling back to free text input.[/yellow]")
        resolution = Prompt.ask("Resolution@refresh (e.g. 1920x1080@60.00Hz)")
    else:
        console.print(f"Supported modes for [bold]{name}[/bold]:")
        for i, m in enumerate(modes, start=1):
            console.print(f"  {i}. {m}")
        choice = Prompt.ask("Pick a mode number", choices=[str(i) for i in range(1, len(modes) + 1)])
        resolution = modes[int(choice) - 1]

    scale = FloatPrompt.ask("Scale", default=monitor.get("scale", 1.0))
    position = Prompt.ask("Position (x,y)", default=f'{monitor["x"]}x{monitor["y"]}'.replace("x", ","))

    console.print("\n[cyan]Applying live preview... check your screen now.[/cyan]")
    try:
        mon.apply_live(name, resolution, position, scale)
    except mon.HyprctlError as e:
        console.print(f"[red]Failed to apply live preview:[/red] {e}")
        return 1

    if not Confirm.ask("Does this look correct? Save permanently?"):
        console.print("[yellow]Not saved.[/yellow] The live change will revert on next Hyprland reload/restart.")
        return 0

    try:
        backup_path = mon.persist_monitor_line(name, resolution, position, scale)
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        return 1

    console.print(f"[green]Saved.[/green] Backup created at: {backup_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="hyprkit", description="A companion CLI for managing Hyprland.")
    sub = parser.add_subparsers(dest="command")

    config_parser = sub.add_parser("config", help="Interactively improve or generate hyprland.conf")
    config_parser.add_argument("--fresh", action="store_true", help="Generate a brand new config from scratch")
    sub.add_parser("lint", help="Lint your hyprland.conf for common issues")
    sub.add_parser("doctor", help="Run Hyprland health checks")

    monitors_parser = sub.add_parser("monitors", help="List or configure monitors")
    monitors_sub = monitors_parser.add_subparsers(dest="monitors_command")
    set_parser = monitors_sub.add_parser("set", help="Interactively configure a monitor")
    set_parser.add_argument("name", help="Monitor name (e.g. eDP-1)")

    waybar_parser = sub.add_parser("waybar", help="Manage Waybar modules")
    waybar_sub = waybar_parser.add_subparsers(dest="waybar_command")
    toggle_parser = waybar_sub.add_parser("toggle", help="Enable/disable a module")
    toggle_parser.add_argument("module", help="Module name (e.g. clock, battery, network)")
    toggle_parser.add_argument(
        "--array",
        default="modules-right",
        choices=["modules-left", "modules-center", "modules-right"],
    )

    args = parser.parse_args()

    if args.command == "config":
        return cmd_config()

    if args.command == "lint":
        return cmd_lint()

    if args.command == "doctor":
        return cmd_doctor()

    if args.command == "monitors":
        if args.monitors_command == "set":
            return cmd_set(args.name)
        return cmd_list()

    if args.command == "waybar":
        if args.waybar_command == "toggle":
            return cmd_waybar_toggle(args.module, args.array)
        return cmd_waybar_list()

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
