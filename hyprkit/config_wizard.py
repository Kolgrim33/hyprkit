import re
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich import box

from hyprkit.lint import lint_config, DEFAULT_CONFIG
from hyprkit.result import Severity

console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _backup(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = path.with_suffix(path.suffix + f".bak-{timestamp}")
    shutil.copy2(path, backup)
    return backup


def _which_any(*cmds: str) -> list[str]:
    """Return which of the given commands are available in PATH."""
    return [c for c in cmds if shutil.which(c)]


def _read_config(path: Path) -> list[str]:
    return path.read_text().splitlines(keepends=True)


def _write_config(path: Path, lines: list[str]) -> None:
    path.write_text("".join(lines))


def _show_diff(original: list[str], updated: list[str]) -> None:
    console.print("\n[bold]Changes to be made:[/bold]")
    for i, (old, new) in enumerate(zip(original, updated), start=1):
        if old != new:
            console.print(f"  [red]- {i}: {old.rstrip()}[/red]")
            console.print(f"  [green]+ {i}: {new.rstrip()}[/green]")
    added = updated[len(original):]
    for line in added:
        console.print(f"  [green]+ {line.rstrip()}[/green]")
    removed_count = max(0, len(original) - len(updated))
    if removed_count:
        console.print(f"  [red]({removed_count} line(s) removed)[/red]")


# ---------------------------------------------------------------------------
# Individual fix steps
# ---------------------------------------------------------------------------

def fix_mainmod(lines: list[str]) -> tuple[list[str], bool]:
    """Insert $mainMod at the top if missing."""
    content = "".join(lines)
    if re.search(r"^\$mainMod\s*=", content, re.MULTILINE):
        return lines, False

    console.print("\n[yellow]⚠[/yellow]  No [bold]$mainMod[/bold] defined.")
    console.print("  Currently SUPER is hardcoded — defining $mainMod makes your config easier to manage.\n")

    choices = ["SUPER", "ALT", "CTRL", "SUPER ALT", "skip"]
    for i, c in enumerate(choices, 1):
        console.print(f"  {i}. {c}")

    pick = Prompt.ask("Choose modifier", choices=[str(i) for i in range(1, len(choices) + 1)], default="1")
    choice = choices[int(pick) - 1]

    if choice == "skip":
        return lines, False

    new_line = f"$mainMod = {choice}\n"
    console.print(f"  → Will insert: [green]{new_line.strip()}[/green]")
    return [new_line] + lines, True


def fix_duplicate_keybinds(lines: list[str]) -> tuple[list[str], bool]:
    """Detect and let user resolve duplicate keybinds."""
    seen: dict[str, int] = {}   # combo -> first line index (0-based)
    duplicates: list[tuple[int, str, str]] = []  # (line_idx, combo, raw_line)

    for i, line in enumerate(lines):
        stripped = line.strip()
        m = re.match(r"bind[mrtne]*\s*=\s*(.+)", stripped)
        if m:
            parts = [p.strip() for p in m.group(1).split(",")]
            if len(parts) >= 2:
                combo = f"{parts[0].upper()}+{parts[1].upper()}"
                if combo in seen:
                    duplicates.append((i, combo, stripped))
                else:
                    seen[combo] = i

    if not duplicates:
        return lines, False

    console.print(f"\n[yellow]⚠[/yellow]  Found [bold]{len(duplicates)} duplicate keybind(s)[/bold]:")
    changed = False
    lines = list(lines)

    for i, combo, raw in duplicates:
        console.print(f"\n  Line {i+1}: [dim]{raw}[/dim]")
        first_line = lines[seen[combo]].strip()
        console.print(f"  Conflicts with line {seen[combo]+1}: [dim]{first_line}[/dim]")
        console.print("  1. Remove this duplicate (keep the first)")
        console.print("  2. Keep this one (remove the first)")
        console.print("  3. Keep both")
        pick = Prompt.ask("  Choice", choices=["1", "2", "3"], default="1")
        if pick == "1":
            lines[i] = ""
            changed = True
        elif pick == "2":
            lines[seen[combo]] = ""
            seen[combo] = i
            changed = True

    return [l for l in lines if l != ""], changed


def fix_dead_execs(lines: list[str]) -> tuple[list[str], bool]:
    """Find exec lines with missing binaries and offer to remove them."""
    changed = False
    result = []

    for line in lines:
        stripped = line.strip()
        if re.match(r"exec(?:-once)?\s*=", stripped):
            m = re.match(r"exec(?:-once)?\s*=\s*(.+)", stripped)
            if m:
                tokens = m.group(1).strip().split()
                cmd = next((t for t in tokens if "=" not in t), None)
                if cmd and "/" not in cmd and not shutil.which(cmd):
                    console.print(f"\n[yellow]⚠[/yellow]  Binary not found: [bold]{cmd}[/bold]")
                    console.print(f"  Line: [dim]{stripped}[/dim]")
                    if Confirm.ask("  Remove this line?", default=True):
                        changed = True
                        continue
        result.append(line)

    return result, changed


def fix_missing_blocks(lines: list[str]) -> tuple[list[str], bool]:
    """Offer to append missing common config blocks."""
    content = "".join(lines)
    changed = False
    additions: list[str] = []

    # Animations
    if "animations {" not in content:
        console.print("\n[yellow]⚠[/yellow]  No [bold]animations[/bold] block found.")
        if Confirm.ask("  Add smooth default animations?", default=True):
            additions.append("""
animations {
    enabled = yes
    bezier = myBezier, 0.05, 0.9, 0.1, 1.05
    animation = windows, 1, 7, myBezier
    animation = windowsOut, 1, 7, default, popin 80%
    animation = fade, 1, 7, default
    animation = workspaces, 1, 6, default
}
""")
            changed = True

    # Gaps / decoration
    if "decoration {" not in content:
        console.print("\n[yellow]⚠[/yellow]  No [bold]decoration[/bold] block found.")
        if Confirm.ask("  Add rounded corners + gaps?", default=True):
            additions.append("""
general {
    gaps_in = 5
    gaps_out = 10
    border_size = 2
    col.active_border = rgba(33ccffee) rgba(0099ffaa) 45deg
    col.inactive_border = rgba(595959aa)
    layout = dwindle
}

decoration {
    rounding = 10
    blur {
        enabled = true
        size = 3
        passes = 1
    }
    drop_shadow = yes
    shadow_range = 4
    shadow_render_power = 3
}
""")
            changed = True

    # Input block
    if "input {" not in content:
        console.print("\n[yellow]⚠[/yellow]  No [bold]input[/bold] block found.")
        if Confirm.ask("  Add default input settings (keyboard repeat, touchpad)?", default=True):
            additions.append("""
input {
    kb_layout = us
    follow_mouse = 1
    touchpad {
        natural_scroll = yes
    }
    sensitivity = 0
}
""")
            changed = True

    return lines + [l + "\n" if not l.endswith("\n") else l for l in additions], changed


# ---------------------------------------------------------------------------
# Main wizard entry point
# ---------------------------------------------------------------------------

def run_wizard(path: Path = DEFAULT_CONFIG) -> int:
    console.print(Panel.fit(
        "[bold cyan]hyprkit config wizard[/bold cyan]\n"
        "[dim]Improves your existing hyprland.conf interactively[/dim]",
        box=box.ROUNDED,
    ))

    if not path.exists():
        console.print(f"[red]Config not found:[/red] {path}")
        return 1

    console.print(f"\nConfig: [dim]{path}[/dim]")

    # Step 1: lint first so user knows what's broken
    console.print("\n[cyan]Step 1/5 — Running lint...[/cyan]")
    issues = lint_config(path)
    if issues:
        table = Table(box=box.SIMPLE)
        table.add_column("Line", justify="right")
        table.add_column("Severity")
        table.add_column("Issue")
        sev_color = {"High": "[red]HIGH[/red]", "Medium": "[yellow]MED[/yellow]", "Low": "[dim]LOW[/dim]"}
        for issue in issues:
            table.add_row(
                str(issue.line_no) if issue.line_no else "—",
                sev_color.get(issue.severity.value, issue.severity.value),
                issue.message,
            )
        console.print(table)
    else:
        console.print("[green]✓ No lint issues found.[/green]")

    if not Confirm.ask("\nProceed with the improvement wizard?", default=True):
        return 0

    original_lines = _read_config(path)
    lines = list(original_lines)

    # Step 2-5: fixes
    console.print("\n[cyan]Step 2/5 — $mainMod[/cyan]")
    lines, _ = fix_mainmod(lines)

    console.print("\n[cyan]Step 3/5 — Duplicate keybinds[/cyan]")
    lines, _ = fix_duplicate_keybinds(lines)

    console.print("\n[cyan]Step 4/5 — Dead exec binaries[/cyan]")
    lines, _ = fix_dead_execs(lines)

    console.print("\n[cyan]Step 5/5 — Missing config blocks[/cyan]")
    lines, _ = fix_missing_blocks(lines)

    # Show diff
    if lines == original_lines:
        console.print("\n[green]✓ No changes needed.[/green]")
        return 0

    _show_diff(original_lines, lines)

    if not Confirm.ask("\nSave these changes?", default=True):
        console.print("[yellow]Not saved.[/yellow]")
        return 0

    backup = _backup(path)
    _write_config(path, lines)
    console.print(f"\n[green]✓ Saved.[/green] Backup at: [dim]{backup}[/dim]")

    # Re-run lint
    console.print("\n[cyan]Re-running lint on improved config...[/cyan]")
    new_issues = lint_config(path)
    if not new_issues:
        console.print("[green]✓ All clear — no issues remaining.[/green]")
    else:
        console.print(f"[yellow]{len(new_issues)} issue(s) remaining — run `hyprkit lint` for details.[/yellow]")

    console.print("\n[dim]Run `hyprctl reload` to apply changes.[/dim]\n")
    return 0
