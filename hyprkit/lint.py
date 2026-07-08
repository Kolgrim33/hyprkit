import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from hyprkit.result import Severity

DEFAULT_CONFIG = Path.home() / ".config" / "hypr" / "hyprland.conf"


@dataclass
class LintIssue:
    line_no: int | None
    message: str
    severity: Severity = Severity.LOW


def lint_config(path: Path = DEFAULT_CONFIG) -> list[LintIssue]:
    issues: list[LintIssue] = []

    if not path.exists():
        issues.append(LintIssue(None, f"Config not found: {path}", Severity.HIGH))
        return issues

    lines = path.read_text().splitlines()

    brace_depth = 0
    brace_open_lines: list[int] = []
    monitor_names: list[str] = []
    has_monitor = False
    has_bind = False

    # For new checks
    defined_vars: dict[str, int] = {}       # varname -> line it was defined on
    keybinds: dict[str, int] = {}           # "MODS+KEY" -> first line seen
    mainmod_defined = False

    for i, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("#"):
            continue

        # --- Variable definitions: $VAR = value ---
        var_def = re.match(r"\$(\w+)\s*=\s*(.+)", line)
        if var_def:
            varname = var_def.group(1)
            defined_vars[varname] = i
            if varname == "mainMod":
                mainmod_defined = True

        # --- Variable usage before definition ---
        # Find all $VAR references in the line
        used_vars = re.findall(r"\$(\w+)", line)
        for var in used_vars:
            if var not in defined_vars:
                issues.append(LintIssue(
                    i,
                    f"Variable '${var}' used before being defined",
                    Severity.HIGH,
                ))

        # --- Brace depth tracking ---
        for _ in range(line.count("{")):
            brace_open_lines.append(i)
            brace_depth += 1
        for _ in range(line.count("}")):
            if brace_depth > 0:
                brace_open_lines.pop()
                brace_depth -= 1
            else:
                issues.append(LintIssue(i, "Unexpected closing brace '}'", Severity.HIGH))

        # --- source = <file> ---
        if line.startswith("source"):
            m = re.match(r"source\s*=\s*(.+)", line)
            if m:
                src = Path(m.group(1).strip().replace("~", str(Path.home())))
                if not src.exists():
                    issues.append(LintIssue(i, f"Sourced file not found: {src}", Severity.MEDIUM))

        # --- monitor= ---
        if line.startswith("monitor"):
            m = re.match(r"monitor\s*=\s*(.+)", line)
            if m:
                has_monitor = True
                parts = [p.strip() for p in m.group(1).split(",")]
                name = parts[0]
                if name in monitor_names:
                    issues.append(LintIssue(i, f"Duplicate monitor definition: '{name}'", Severity.MEDIUM))
                else:
                    monitor_names.append(name)
                if len(parts) < 4:
                    issues.append(LintIssue(
                        i,
                        "monitor= needs 4 fields: name,resolution,position,scale",
                        Severity.MEDIUM,
                    ))
                # Check resolution format e.g. 1920x1080@60.00Hz
                if len(parts) >= 2:
                    res = parts[1].strip()
                    if res not in ("preferred", "highrr", "highres") and not re.match(r"\d+x\d+@[\d.]+Hz", res):
                        issues.append(LintIssue(
                            i,
                            f"Unusual monitor resolution format: '{res}' (expected e.g. 1920x1080@60.00Hz)",
                            Severity.LOW,
                        ))

        # --- exec / exec-once ---
        if re.match(r"exec(?:-once)?\s*=", line):
            m = re.match(r"exec(?:-once)?\s*=\s*(.+)", line)
            if m:
                tokens = m.group(1).strip().split()
                cmd = next((t for t in tokens if "=" not in t), None)
                if cmd and "/" not in cmd and not shutil.which(cmd):
                    issues.append(LintIssue(i, f"Binary not found in PATH: '{cmd}'", Severity.LOW))

        # --- bind lines ---
        if re.match(r"bind[mrtne]*\s*=", line):
            has_bind = True
            m = re.match(r"bind[mrtne]*\s*=\s*(.+)", line)
            if m:
                parts = [p.strip() for p in m.group(1).split(",")]
                if len(parts) < 3:
                    issues.append(LintIssue(
                        i,
                        "bind line needs at least 3 fields: MODS, KEY, dispatcher",
                        Severity.MEDIUM,
                    ))
                else:
                    # Duplicate keybind check — normalise MODS+KEY as the key
                    mods = parts[0].upper().strip()
                    key = parts[1].upper().strip()
                    combo = f"{mods}+{key}"
                    if combo in keybinds:
                        issues.append(LintIssue(
                            i,
                            f"Duplicate keybind '{combo}' — also bound on line {keybinds[combo]}",
                            Severity.MEDIUM,
                        ))
                    else:
                        keybinds[combo] = i

    # --- Unclosed braces ---
    for line_no in brace_open_lines:
        issues.append(LintIssue(line_no, "Unclosed opening brace '{'", Severity.HIGH))

    # --- Whole-file sanity ---
    if not has_monitor:
        issues.append(LintIssue(None, "No monitor= line found — display won't be configured", Severity.HIGH))
    if not has_bind:
        issues.append(LintIssue(None, "No bind= lines found — you have no keybindings", Severity.MEDIUM))
    if not mainmod_defined:
        issues.append(LintIssue(None, "No $mainMod defined — most bind lines will fail", Severity.HIGH))

    return issues
