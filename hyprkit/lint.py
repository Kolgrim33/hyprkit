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

    for i, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("#"):
            continue

        # Track brace depth
        for _ in range(line.count("{")):
            brace_open_lines.append(i)
            brace_depth += 1
        for _ in range(line.count("}")):
            if brace_depth > 0:
                brace_open_lines.pop()
                brace_depth -= 1
            else:
                issues.append(LintIssue(i, "Unexpected closing brace '}'", Severity.HIGH))

        # source = <file> — check the file actually exists
        if line.startswith("source"):
            m = re.match(r"source\s*=\s*(.+)", line)
            if m:
                src = Path(m.group(1).strip().replace("~", str(Path.home())))
                if not src.exists():
                    issues.append(LintIssue(i, f"Sourced file not found: {src}", Severity.MEDIUM))

        # monitor= — check for duplicates and malformed lines
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
                    issues.append(
                        LintIssue(i, "monitor= needs 4 fields: name,resolution,position,scale", Severity.MEDIUM)
                    )

        # exec / exec-once — check binary exists in PATH
        if re.match(r"exec(?:-once)?\s*=", line):
            m = re.match(r"exec(?:-once)?\s*=\s*(.+)", line)
            if m:
                tokens = m.group(1).strip().split()
                # Skip past any VAR=value env prefixes
                cmd = next((t for t in tokens if "=" not in t), None)
                if cmd and "/" not in cmd and not shutil.which(cmd):
                    issues.append(LintIssue(i, f"Binary not found in PATH: '{cmd}'", Severity.LOW))

        # bind lines — must have at least MODS, KEY, dispatcher
        if re.match(r"bind[mrtne]*\s*=", line):
            has_bind = True
            m = re.match(r"bind[mrtne]*\s*=\s*(.+)", line)
            if m:
                parts = [p.strip() for p in m.group(1).split(",")]
                if len(parts) < 3:
                    issues.append(
                        LintIssue(i, "bind line needs at least 3 fields: MODS, KEY, dispatcher", Severity.MEDIUM)
                    )

    # Unclosed braces
    for line_no in brace_open_lines:
        issues.append(LintIssue(line_no, "Unclosed opening brace '{'", Severity.HIGH))

    # Whole-file sanity
    if not has_monitor:
        issues.append(LintIssue(None, "No monitor= line found — display won't be configured", Severity.HIGH))
    if not has_bind:
        issues.append(LintIssue(None, "No bind= lines found — you have no keybindings", Severity.MEDIUM))

    return issues
