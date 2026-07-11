# Contributing to hyprkit

First off — thanks for considering a contribution. hyprkit is a small project and every PR counts.

## Setup

```bash
git clone https://github.com/Kolgrim33/hyprkit.git
cd hyprkit
pip install --break-system-packages -e .
```

That's it. No build step, no virtual environment required. The `-e` flag means your local changes reflect immediately when you run `hyprkit`.

**Dependencies:**
- Python 3.11+
- `rich` — `pip install --break-system-packages rich`
- A running Hyprland session (for `monitors` and `doctor` commands)

## Project structurehyprkit/
├── main.py            # CLI entry point, argument parsing, command dispatch
├── monitors.py        # Monitor detection and configuration via hyprctl
├── waybar.py          # Waybar config parsing, module toggling
├── doctor.py          # Health checks (each check is an independent function)
├── lint.py            # hyprland.conf static analysis
├── config_wizard.py   # Interactive config improvement wizard
├── fresh_config.py    # Fresh config generator (hyprkit config --fresh)
└── result.py          # Shared CheckResult / Status / Severity dataclasses

## Adding a new doctor check

`doctor.py` is the easiest place to start. Each check is a standalone function that returns a `CheckResult`:

```python
from hyprkit.result import CheckResult, Status, Severity

def check_something() -> CheckResult:
    if everything_is_fine:
        return CheckResult(name="Something", status=Status.OK, detail="All good")
    return CheckResult(
        name="Something",
        status=Status.WARN,
        detail="Not found",
        severity=Severity.MEDIUM,
        why_it_matters="Explain why this matters to the user.",
        recommendation="Tell them exactly how to fix it.",
        score_penalty=5,
    )
```

Then register it at the bottom of `doctor.py`:

```python
CHECKS = [
    ...
    check_something,
]
```

That's all — it shows up automatically in `hyprkit doctor`.

## Adding a new lint check

Lint checks live inside the `lint_config()` function in `lint.py`. Each check appends to the `issues` list:

```python
issues.append(LintIssue(
    line_no=i,           # or None for whole-file issues
    message="Describe the problem clearly",
    severity=Severity.MEDIUM,
))
```

Severity guide:
- `HIGH` — will likely break the session or prevent startup
- `MEDIUM` — silent misbehaviour, things that won't work as expected
- `LOW` — missing tools, style issues, dead config lines

## Code style

- Plain Python, no type checker required but type hints are appreciated
- `rich` for all terminal output — no raw `print()` in modules, only in `main.py`
- Keep modules independent — `lint.py` should never import from `waybar.py`
- One function per check in `doctor.py` — keep them small and focused
- Always back up config files before writing (`backup_config()` helpers exist in `monitors.py` and `waybar.py`)

## Submitting a PR

1. Fork the repo
2. Create a branch: `git checkout -b feat/your-feature`
3. Make your changes
4. Test manually: `hyprkit doctor`, `hyprkit lint`, `hyprkit config`
5. Open a PR against `main` with a clear description of what it does and why

If you're not sure whether an idea fits, open an issue first and we can discuss it.

## Good first issues

Looking for somewhere to start? These are well-scoped and don't require deep knowledge of the codebase:

- Add a `check_xdg_portal()` to `doctor.py` — detect if `xdg-desktop-portal-hyprland` is running (fixes screen sharing issues)
- Add a `check_hypridle()` to `doctor.py` — detect if an idle daemon is configured
- Add a lint check for `exec` vs `exec-once` misuse (waybar in `exec` respawns on every reload)
- Add a lint check for undefined `$variables` referenced in `windowrule` lines
