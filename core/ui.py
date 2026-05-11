"""
core/ui.py
──────────
Premium Terminal UI for JARVIS.

Provides ANSI-styled output helpers:
  - Animated ASCII boot banner
  - Styled speak / user / reminder panels
  - Colour-coded status lines  [ OK ] [ WAIT ] [ WARN ] [ ERR ]
  - Spinning progress indicator
  - Redesigned startup command menu
  - Shutdown screen
"""

import sys
import time
import threading
import datetime
import itertools
from contextlib import contextmanager

# ── ANSI Colour Palette ──────────────────────────────────────────────────────

ESC = "\033["

def _c(*codes) -> str:
    return f"{ESC}{';'.join(str(c) for c in codes)}m"

RESET   = _c(0)
BOLD    = _c(1)
DIM     = _c(2)
ITALIC  = _c(3)

# Foregrounds
FG_WHITE   = _c(97)
FG_CYAN    = _c(96)
FG_BLUE    = _c(34)
FG_GREEN   = _c(92)
FG_YELLOW  = _c(93)
FG_ORANGE  = _c(33)
FG_RED     = _c(91)
FG_MAGENTA = _c(95)
FG_GREY    = _c(90)
FG_BLACK   = _c(30)

# Backgrounds
BG_CYAN    = _c(46)
BG_BLUE    = _c(44)
BG_GREEN   = _c(42)
BG_RED     = _c(41)
BG_YELLOW  = _c(43)
BG_DARK    = _c(40)

W = 76  # terminal width


# ── Primitive helpers ─────────────────────────────────────────────────────────

def _print(text: str = ""):
    """Write to stdout and flush immediately."""
    sys.stdout.write(text + "\n")
    sys.stdout.flush()


def _write(text: str):
    sys.stdout.write(text)
    sys.stdout.flush()


def _clear_line():
    sys.stdout.write("\r\033[K")
    sys.stdout.flush()


def _pad(text: str, width: int) -> str:
    """Pad text to fit exactly <width> visible characters (ignores ANSI codes)."""
    import re
    ansi_escape = re.compile(r'\033\[[0-9;]*m')
    visible = ansi_escape.sub('', text)
    pad = max(0, width - len(visible))
    return text + " " * pad


# ── Border chars ─────────────────────────────────────────────────────────────

TL = "╔"
TR = "╗"
BL = "╚"
BR = "╝"
HL = "═"
VL = "║"
ML = "╠"
MR = "╣"
TL2 = "┌"
TR2 = "┐"
BL2 = "└"
BR2 = "┘"
HL2 = "─"
VL2 = "│"


def _hline(color: str = FG_CYAN, char: str = HL, width: int = W) -> str:
    return f"{color}{char * width}{RESET}"


def _border_top(color: str, width: int = W, thin: bool = False) -> str:
    tl, tr, h = (TL2, TR2, HL2) if thin else (TL, TR, HL)
    return f"{color}{tl}{h * (width - 2)}{tr}{RESET}"


def _border_bot(color: str, width: int = W, thin: bool = False) -> str:
    bl, br, h = (BL2, BR2, HL2) if thin else (BL, BR, HL)
    return f"{color}{bl}{h * (width - 2)}{br}{RESET}"


def _border_mid(color: str, width: int = W, thin: bool = False) -> str:
    ml, mr, h = ("├", "┤", HL2) if thin else (ML, MR, HL)
    return f"{color}{ml}{h * (width - 2)}{mr}{RESET}"


def _border_row(content: str, color: str, width: int = W, thin: bool = False) -> str:
    vl = VL2 if thin else VL
    import re
    ansi_escape = re.compile(r'\033\[[0-9;]*m')
    visible_len = len(ansi_escape.sub('', content))
    pad = max(0, width - 2 - visible_len)
    return f"{color}{vl}{RESET}{content}{' ' * pad}{color}{vl}{RESET}"


# ── JARVIS ASCII logo ─────────────────────────────────────────────────────────

_LOGO_LINES = [
    r"     ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗",
    r"     ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝",
    r"     ██║███████║██████╔╝██║   ██║██║███████╗",
    r"     ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║",
    r"     ██║██║  ██║██║  ██║ ╚████╔╝ ██║███████║",
    r"     ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝",
]


# ── Public API ────────────────────────────────────────────────────────────────

def banner(animate: bool = True):
    """
    Print the full JARVIS boot banner.
    If animate=True, each logo line types in with a brief delay.
    """
    _print()
    _print(f"{FG_CYAN}{TL}{HL * (W - 2)}{TR}{RESET}")

    # Empty line
    _print(_border_row("", FG_CYAN))

    # Logo lines
    for line in _LOGO_LINES:
        # Centre the line within the box interior
        inner = W - 2
        import re
        visible = len(re.sub(r'\033\[[0-9;]*m', '', line))
        lpad = (inner - visible) // 2
        rpad = inner - visible - lpad
        content = f"{' ' * lpad}{BOLD}{FG_CYAN}{line}{RESET}{' ' * rpad}"
        row = f"{FG_CYAN}{VL}{RESET}{content}{FG_CYAN}{VL}{RESET}"
        _print(row)
        if animate:
            time.sleep(0.07)

    _print(_border_row("", FG_CYAN))
    _print(_border_mid(FG_CYAN))

    # Subtitle lines
    subtitle = [
        f"  {BOLD}{FG_WHITE}Just A Rather Very Intelligent System{RESET}  ·  v2.0",
        f"  {FG_GREY}User: {FG_WHITE}Praneeth{FG_GREY}  │  City: {FG_WHITE}Coimbatore{FG_GREY}  │  Python 3.12+{RESET}",
        f"  {FG_GREY}Backend: {FG_WHITE}Typed I/O{FG_GREY}  │  TTS: {FG_WHITE}Deep Male Voice{FG_GREY}  │  Storage: {FG_WHITE}Local JSON{RESET}",
    ]
    for line in subtitle:
        _print(_border_row(f"  {line}", FG_CYAN))

    _print(_border_row("", FG_CYAN))
    _print(f"{FG_CYAN}{BL}{HL * (W - 2)}{BR}{RESET}")
    _print()


def boot_sequence(steps: list[tuple[str, float]] | None = None):
    """
    Animated system-check sequence, e.g.:
        boot_sequence([("Voice Engine", 0.3), ("Brain Core", 0.5)])
    """
    if steps is None:
        steps = [
            ("Voice Engine        ", 0.25),
            ("Brain Core          ", 0.35),
            ("Wake Word Detector  ", 0.25),
            ("Face Auth Module    ", 0.20),
            ("Skills Registry     ", 0.30),
            ("Command Router      ", 0.20),
        ]

    _print(f"\n{FG_GREY}  {HL2 * (W - 4)}{RESET}")
    _print(f"  {BOLD}{FG_WHITE}◈ SYSTEM INITIALISATION{RESET}")
    _print(f"{FG_GREY}  {HL2 * (W - 4)}{RESET}\n")

    for label, delay in steps:
        _write(f"  {FG_GREY}▸{RESET} {FG_WHITE}{label}{RESET}  ")
        sys.stdout.flush()
        time.sleep(delay)
        _print(f"{BOLD}{FG_GREEN}[ OK ]{RESET}")

    _print(f"\n{FG_GREY}  {HL2 * (W - 4)}{RESET}")
    _print(f"  {BOLD}{FG_GREEN}◈ All systems online{RESET}  {FG_GREY}·  JARVIS ready{RESET}")
    _print(f"{FG_GREY}  {HL2 * (W - 4)}{RESET}\n")
    time.sleep(0.3)


@contextmanager
def spinner(label: str = "Processing", color: str = FG_CYAN):
    """
    Context manager: shows an animated spinner while a block of code runs.

        with ui.spinner("Thinking"):
            response = router.handle(cmd)
    """
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    stop_event = threading.Event()

    def _spin():
        for frame in itertools.cycle(frames):
            if stop_event.is_set():
                break
            _write(f"\r  {color}{frame}{RESET}  {FG_WHITE}{label}...{RESET}  ")
            time.sleep(0.08)

    t = threading.Thread(target=_spin, daemon=True)
    t.start()
    try:
        yield
    finally:
        stop_event.set()
        t.join()
        _clear_line()


def speak_box(text: str):
    """
    Premium styled output panel for JARVIS responses.
    Uses a double-border cyan box with a labelled header.
    """
    _print()
    now = datetime.datetime.now().strftime("%H:%M:%S")

    # Header row
    label = f" {BOLD}{FG_CYAN}◈ JARVIS{RESET} {FG_GREY}·{RESET} {DIM}{FG_GREY}{now}{RESET} "
    import re
    ansi_escape = re.compile(r'\033\[[0-9;]*m')
    label_vis = len(ansi_escape.sub('', label))
    right_fill = W - 2 - label_vis
    header = f"{FG_CYAN}{TL}{RESET}{label}{FG_CYAN}{HL * right_fill}{TR}{RESET}"
    _print(header)

    # Wrap text at W-6 chars
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        if len(test) <= W - 6:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    for line in lines:
        content = f"  {BOLD}{FG_WHITE}{line}{RESET}"
        _print(_border_row(content, FG_CYAN))

    # Footer
    _print(f"{FG_CYAN}{BL}{HL * (W - 2)}{BR}{RESET}")
    _print()


def user_box(text: str):
    """
    Styled panel for user input echo.
    Uses a thin green border.
    """
    _print()
    now = datetime.datetime.now().strftime("%H:%M:%S")
    label = f" {BOLD}{FG_GREEN}▸ YOU{RESET} {FG_GREY}·{RESET} {DIM}{FG_GREY}{now}{RESET} "
    import re
    ansi_escape = re.compile(r'\033\[[0-9;]*m')
    label_vis = len(ansi_escape.sub('', label))
    right_fill = W - 2 - label_vis
    header = f"{FG_GREEN}{TL2}{RESET}{label}{FG_GREEN}{HL2 * right_fill}{TR2}{RESET}"
    _print(header)
    content = f"  {FG_GREEN}{text}{RESET}"
    _print(_border_row(content, FG_GREEN, thin=True))
    _print(f"{FG_GREEN}{BL2}{HL2 * (W - 2)}{BR2}{RESET}")
    _print()


def reminder_box(text: str):
    """
    Distinct orange alert panel for due reminders.
    """
    _print()
    label = f" {BOLD}{FG_ORANGE}⏰ REMINDER ALERT{RESET} "
    import re
    ansi_escape = re.compile(r'\033\[[0-9;]*m')
    label_vis = len(ansi_escape.sub('', label))
    right_fill = W - 2 - label_vis
    header = f"{FG_ORANGE}{TL}{RESET}{label}{FG_ORANGE}{HL * right_fill}{TR}{RESET}"
    _print(header)
    content = f"  {BOLD}{FG_YELLOW}{text}{RESET}"
    _print(_border_row(content, FG_ORANGE))
    _print(f"{FG_ORANGE}{BL}{HL * (W - 2)}{BR}{RESET}")
    _print()


def status(msg: str, kind: str = "info"):
    """
    Inline status line.  kind = "ok" | "wait" | "info" | "warn" | "err"
    """
    _icons = {
        "ok":   (FG_GREEN,   "  OK  "),
        "wait": (FG_CYAN,    " WAIT "),
        "info": (FG_GREY,    " INFO "),
        "warn": (FG_YELLOW,  " WARN "),
        "err":  (FG_RED,     "  ERR "),
    }
    color, tag = _icons.get(kind, (FG_GREY, " INFO "))
    now = datetime.datetime.now().strftime("%H:%M:%S")
    _print(f"  {FG_GREY}{now}{RESET}  {BOLD}{color}[{tag}]{RESET}  {FG_WHITE}{msg}{RESET}")


def divider(color: str = FG_GREY):
    """Thin horizontal rule."""
    _print(f"{color}  {HL2 * (W - 4)}{RESET}")


def prompt_wake() -> str:
    """
    Styled wake-word prompt for typed mode.
    Returns the user's input string.
    """
    _print()
    _write(f"  {FG_CYAN}◈{RESET}  {DIM}{FG_GREY}say or type{RESET} {BOLD}{FG_CYAN}jarvis{RESET}  {FG_GREY}›{RESET}  ")
    sys.stdout.flush()
    return input()


def prompt_command() -> str:
    """
    Styled command-input prompt.
    Returns the user's input string.
    """
    _print()
    _write(f"  {FG_GREEN}▸{RESET}  {FG_WHITE}Command{RESET}  {FG_GREY}›{RESET}  ")
    sys.stdout.flush()
    return input()


def startup_menu():
    """
    Full redesigned command reference menu.
    Printed before entering the main loop in typed mode.
    """
    _print()
    # ── Header ──
    _print(f"{FG_CYAN}{TL}{HL * (W - 2)}{TR}{RESET}")
    _print(_border_row(f"  {BOLD}{FG_WHITE}◈  COMMAND REFERENCE{RESET}", FG_CYAN))
    _print(_border_mid(FG_CYAN))

    def section(icon: str, title: str, items: list[tuple[str, str]]):
        _print(_border_row(f"  {BOLD}{FG_CYAN}{icon}  {title}{RESET}", FG_CYAN))
        _print(_border_row(f"  {FG_GREY}{HL2 * (W - 6)}{RESET}", FG_CYAN))
        for cmd, desc in items:
            row = f"    {FG_GREEN}{cmd:<32}{RESET}{FG_GREY}→{RESET}  {FG_WHITE}{desc}{RESET}"
            _print(_border_row(row, FG_CYAN))
        _print(_border_row("", FG_CYAN))

    section("🎤", "VOICE / TYPED COMMANDS", [
        ('"who are you"',        "Meet JARVIS"),
        ('"what time is it"',    "Get current time"),
        ('"today\'s date"',      "Get today\'s date"),
        ('"play music"',         "Spotify playback"),
        ('"search [query]"',     "Web search via DuckDuckGo"),
        ('"take a note [text]"', "Save quick note"),
        ('"remind me [task]"',   "Set reminder with time"),
        ('"help"',               "List all features"),
    ])

    _print(_border_mid(FG_CYAN))

    section("⚡", "SHORTCUTS", [
        ("jarvis",               "Wake word (typed or spoken)"),
        ("exit / goodbye",       "Shutdown JARVIS"),
        ("clear memory",         "Reset conversation brain"),
    ])

    _print(_border_mid(FG_CYAN))

    section("📚", "SKILL CATEGORIES", [
        ("🌤  weather / forecast",  "Live weather & forecast"),
        ("📰  news / headlines",    "Top news stories"),
        ("🎵  play / pause / next", "Music playback control"),
        ("🔍  search / look up",    "Web search"),
        ("🖥  volume / open app",   "System control"),
        ("📝  note / save",         "Quick notes"),
        ("🎓  quiz / explain",      "Study assistant"),
        ("⏰  reminder / task",     "Reminders & schedule"),
    ])

    _print(f"{FG_CYAN}{BL}{HL * (W - 2)}{BR}{RESET}")
    _print()
    _write(f"  {FG_GREY}Ready?{RESET}  {FG_CYAN}Press Enter to start JARVIS  ›{RESET}  ")
    sys.stdout.flush()
    input()


def shutdown_banner(user_name: str = "Praneeth"):
    """Styled goodbye screen shown on exit."""
    _print()
    _print(f"{FG_CYAN}{TL}{HL * (W - 2)}{TR}{RESET}")
    _print(_border_row("", FG_CYAN))
    msg = f"{BOLD}{FG_WHITE}Goodbye, {user_name}.  JARVIS going offline.{RESET}"
    import re
    ansi_escape = re.compile(r'\033\[[0-9;]*m')
    inner = W - 2
    vis = len(ansi_escape.sub('', msg))
    lpad = (inner - vis) // 2
    rpad = inner - vis - lpad
    _print(f"{FG_CYAN}{VL}{RESET}{' ' * lpad}{msg}{' ' * rpad}{FG_CYAN}{VL}{RESET}")
    _print(_border_row("", FG_CYAN))
    tag = f"{FG_GREY}Session ended · {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}"
    vis2 = len(ansi_escape.sub('', tag))
    lpad2 = (inner - vis2) // 2
    rpad2 = inner - vis2 - lpad2
    _print(f"{FG_CYAN}{VL}{RESET}{' ' * lpad2}{tag}{' ' * rpad2}{FG_CYAN}{VL}{RESET}")
    _print(_border_row("", FG_CYAN))
    _print(f"{FG_CYAN}{BL}{HL * (W - 2)}{BR}{RESET}")
    _print()
