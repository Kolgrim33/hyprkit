import shutil
import subprocess

from hyprkit.result import CheckResult, Status, Severity


def _proc_running(name: str) -> bool:
    result = subprocess.run(["pgrep", "-x", name], capture_output=True, text=True)
    return result.returncode == 0


def check_hyprland_running() -> CheckResult:
    if _proc_running("Hyprland"):
        return CheckResult(name="Hyprland", status=Status.OK, detail="Running")
    return CheckResult(
        name="Hyprland",
        status=Status.FAIL,
        detail="Not detected",
        severity=Severity.HIGH,
        why_it_matters="If Hyprland itself isn't running, nothing else here matters — you're likely not in a Hyprland session right now.",
        recommendation="Make sure you're running this from within an active Hyprland session.",
        score_penalty=30,
    )


def check_waybar() -> CheckResult:
    if not shutil.which("waybar"):
        return CheckResult(
            name="Waybar",
            status=Status.WARN,
            detail="Not installed",
            severity=Severity.LOW,
            why_it_matters="Waybar is optional, but most Hyprland setups use it as the status bar.",
            recommendation="Install with: sudo pacman -S waybar",
            score_penalty=3,
        )
    if _proc_running("waybar"):
        return CheckResult(name="Waybar", status=Status.OK, detail="Running")
    return CheckResult(
        name="Waybar",
        status=Status.WARN,
        detail="Installed but not running",
        severity=Severity.MEDIUM,
        why_it_matters="Waybar is installed but not currently running, so you likely have no status bar visible.",
        recommendation="Start it with: waybar & (or add `exec-once = waybar` to your hyprland.conf)",
        score_penalty=8,
    )


def check_hyprpaper() -> CheckResult:
    if not shutil.which("hyprpaper"):
        return CheckResult(
            name="hyprpaper",
            status=Status.WARN,
            detail="Not installed",
            severity=Severity.LOW,
            why_it_matters="hyprpaper is optional — only needed if you want a wallpaper manager.",
            recommendation="Install with: sudo pacman -S hyprpaper",
            score_penalty=2,
        )
    if _proc_running("hyprpaper"):
        return CheckResult(name="hyprpaper", status=Status.OK, detail="Running")
    return CheckResult(
        name="hyprpaper",
        status=Status.WARN,
        detail="Installed but stopped",
        severity=Severity.LOW,
        why_it_matters="hyprpaper is installed but not running, so your wallpaper may not be set.",
        recommendation="Start it with: hyprpaper & (or add `exec-once = hyprpaper` to your hyprland.conf)",
        score_penalty=5,
    )


def check_nerd_font() -> CheckResult:
    if not shutil.which("fc-list"):
        return CheckResult(
            name="Nerd Font",
            status=Status.WARN,
            detail="Cannot check (fc-list not found)",
            severity=Severity.LOW,
            recommendation="Install fontconfig: sudo pacman -S fontconfig",
            score_penalty=2,
        )
    result = subprocess.run(["fc-list"], capture_output=True, text=True)
    if "Nerd Font" in result.stdout:
        return CheckResult(name="Nerd Font", status=Status.OK, detail="Installed")
    return CheckResult(
        name="Nerd Font",
        status=Status.WARN,
        detail="No Nerd Font detected",
        severity=Severity.LOW,
        why_it_matters="Waybar icons and many terminal prompts rely on Nerd Font glyphs. Without one you'll see broken icons.",
        recommendation="Install one, e.g.: sudo pacman -S ttf-jetbrains-mono-nerd",
        score_penalty=5,
    )


def check_audio() -> CheckResult:
    if shutil.which("wpctl"):
        result = subprocess.run(["wpctl", "status"], capture_output=True, text=True)
        if result.returncode == 0:
            return CheckResult(name="Audio", status=Status.OK, detail="PipeWire active")
    elif shutil.which("pactl"):
        result = subprocess.run(["pactl", "info"], capture_output=True, text=True)
        if result.returncode == 0:
            return CheckResult(name="Audio", status=Status.OK, detail="PulseAudio active")
    return CheckResult(
        name="Audio",
        status=Status.WARN,
        detail="No working audio server detected",
        severity=Severity.MEDIUM,
        why_it_matters="Without a running audio server, sound won't work in any application.",
        recommendation="Check status with: systemctl --user status pipewire pipewire-pulse",
        score_penalty=8,
    )


def check_network() -> CheckResult:
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "2", "archlinux.org"], capture_output=True, text=True
        )
    except FileNotFoundError:
        return CheckResult(
            name="Network",
            status=Status.WARN,
            detail="Cannot check (ping not found)",
            severity=Severity.LOW,
            recommendation="Install iputils: sudo pacman -S iputils",
            score_penalty=2,
        )
    if result.returncode == 0:
        return CheckResult(name="Network", status=Status.OK, detail="Connected")
    return CheckResult(
        name="Network",
        status=Status.WARN,
        detail="No connectivity detected",
        severity=Severity.MEDIUM,
        recommendation="Check your network/Wi-Fi connection.",
        score_penalty=8,
    )


def check_clipboard() -> CheckResult:
    if shutil.which("wl-copy") and shutil.which("wl-paste"):
        return CheckResult(name="Clipboard", status=Status.OK, detail="wl-clipboard installed")
    return CheckResult(
        name="Clipboard",
        status=Status.WARN,
        detail="wl-clipboard not found",
        severity=Severity.LOW,
        why_it_matters="Without wl-clipboard, copy/paste integrations won't work under Wayland.",
        recommendation="Install with: sudo pacman -S wl-clipboard",
        score_penalty=3,
    )


def check_xdg_portal() -> CheckResult:
    portal_running = _proc_running("xdg-desktop-portal-hyprland") or _proc_running("xdg-desktop-portal")
    binary_exists = shutil.which("xdg-desktop-portal-hyprland")

    if not binary_exists:
        return CheckResult(
            name="XDG Portal",
            status=Status.FAIL,
            detail="xdg-desktop-portal-hyprland not installed",
            severity=Severity.HIGH,
            why_it_matters="Without this, screen sharing, file pickers, and browser camera/mic access won't work under Wayland.",
            recommendation="Install with: sudo pacman -S xdg-desktop-portal-hyprland",
            score_penalty=15,
        )
    if not portal_running:
        return CheckResult(
            name="XDG Portal",
            status=Status.WARN,
            detail="Installed but not running",
            severity=Severity.MEDIUM,
            why_it_matters="Screen sharing and file pickers won't work until the portal is running.",
            recommendation="Add to hyprland.conf: exec-once = /usr/lib/xdg-desktop-portal-hyprland",
            score_penalty=10,
        )
    return CheckResult(name="XDG Portal", status=Status.OK, detail="Running")


def check_hypridle() -> CheckResult:
    if not shutil.which("hypridle"):
        return CheckResult(
            name="Idle Daemon",
            status=Status.WARN,
            detail="hypridle not installed",
            severity=Severity.LOW,
            why_it_matters="Without an idle daemon your screen will never lock or turn off automatically.",
            recommendation="Install with: sudo pacman -S hypridle",
            score_penalty=3,
        )
    if _proc_running("hypridle"):
        return CheckResult(name="Idle Daemon", status=Status.OK, detail="hypridle running")
    return CheckResult(
        name="Idle Daemon",
        status=Status.WARN,
        detail="hypridle installed but not running",
        severity=Severity.LOW,
        why_it_matters="Your screen won't auto-lock or turn off without an idle daemon running.",
        recommendation="Add to hyprland.conf: exec-once = hypridle",
        score_penalty=3,
    )


def check_hyprlock() -> CheckResult:
    if not shutil.which("hyprlock"):
        return CheckResult(
            name="Screen Lock",
            status=Status.WARN,
            detail="hyprlock not installed",
            severity=Severity.LOW,
            why_it_matters="Without a screen locker your session is unprotected when idle.",
            recommendation="Install with: sudo pacman -S hyprlock",
            score_penalty=3,
        )
    return CheckResult(name="Screen Lock", status=Status.OK, detail="hyprlock installed")


CHECKS = [
    check_hyprland_running,
    check_xdg_portal,
    check_waybar,
    check_hyprpaper,
    check_nerd_font,
    check_audio,
    check_network,
    check_clipboard,
    check_hypridle,
    check_hyprlock,
]


def run_all() -> list[CheckResult]:
    return [check() for check in CHECKS]
