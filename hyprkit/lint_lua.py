import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from hyprkit.result import Severity

DEFAULT_LUA_CONFIG = Path.home() / ".config" / "hypr" / "hyprland.lua"


@dataclass
class LintIssue:
    line_no: int | None
    message: str
    severity: Severity = Severity.LOW


def lint_lua_config(path: Path = DEFAULT_LUA_CONFIG) -> list[LintIssue]:
    issues: list[LintIssue] = []

    if not path.exists():
        issues.append(LintIssue(None, f"Lua config not found: {path}", Severity.HIGH))
        return issues

    lines = path.read_text().splitlines()

    defined_locals: dict[str, int] = {}   # varname -> line defined
    used_locals: set[str] = set()
    binds: dict[str, int] = {}            # "combo" -> first line
    has_monitor = False

    for i, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("--"):
            continue

        # --- local VAR = ... definitions ---
        local_def = re.match(r"local\s+(\w+)\s*=", line)
        if local_def:
            varname = local_def.group(1)
            defined_locals[varname] = i

        # --- track usage of locals ---
        for varname in defined_locals:
            # count usage outside the definition line
            if i != defined_locals[varname] and varname in line:
                used_locals.add(varname)

        # --- require() — check file exists ---
        req = re.match(r'require\s*\(\s*["\'](.+)["\']\s*\)', line)
        if req:
            mod = req.group(1).replace(".", "/")
            lua_path = path.parent / (mod + ".lua")
            if not lua_path.exists():
                issues.append(LintIssue(
                    i,
                    f"require('{req.group(1)}') — file not found: {lua_path}",
                    Severity.MEDIUM,
                ))

        # --- hl.monitor() present ---
        if "hl.monitor(" in line:
            has_monitor = True

        # --- hl.exec_cmd() — check binary exists ---
        exec_matches = re.findall(r'hl\.exec_cmd\s*\(\s*["\']([^"\']+)["\']', line)
        for cmd_str in exec_matches:
            # grab the first token as the binary
            tokens = cmd_str.strip().split()
            cmd = next((t for t in tokens if "=" not in t and not t.startswith("-")), None)
            if cmd and "/" not in cmd and not shutil.which(cmd):
                issues.append(LintIssue(
                    i,
                    f"Binary not found in PATH: '{cmd}'",
                    Severity.LOW,
                ))

        # --- hl.bind() duplicate detection ---
        bind_match = re.match(r'hl\.bind\s*\(\s*(.+?)\s*,', line)
        if bind_match:
            combo_raw = bind_match.group(1).strip().strip('"\'')
            # normalise: remove spaces around +, uppercase
            combo = re.sub(r'\s*\+\s*', '+', combo_raw).upper()
            if combo in binds:
                issues.append(LintIssue(
                    i,
                    f"Duplicate keybind '{combo_raw}' — also bound on line {binds[combo]}",
                    Severity.MEDIUM,
                ))
            else:
                binds[combo] = i

    # --- Unused locals ---
    for varname, line_no in defined_locals.items():
        if varname not in used_locals:
            issues.append(LintIssue(
                line_no,
                f"Local variable '{varname}' is defined but never used",
                Severity.LOW,
            ))

    # --- No monitor defined ---
    if not has_monitor:
        issues.append(LintIssue(
            None,
            "No hl.monitor() found — display won't be configured",
            Severity.HIGH,
        ))

    return issues
