"""
core/ui.py
──────────
NEXUS High-Tech Terminal Interface v3.0

Cinematic dark terminal UI with:
  ◈ Neon cyan / electric blue / deep magenta colour system
  ◈ Animated ASCII boot with typewriter effect
  ◈ Gradient-style bordered message panels
  ◈ Glitch-pulse status indicators
  ◈ Brainwave spinner frames
  ◈ Matrix-style boot sequence
  ◈ Holographic shutdown screen
"""

import sys
import time
import random
import threading
import datetime
import itertools
from contextlib import contextmanager

# ── ANSI True-Colour Palette ──────────────────────────────────────────────────

ESC = "\033["

def _c(*codes) -> str:
    return f"{ESC}{';'.join(str(c) for c in codes)}m"

def _rgb(r, g, b) -> str:
    """True-colour foreground."""
    return f"\033[38;2;{r};{g};{b}m"

def _rgb_bg(r, g, b) -> str:
    """True-colour background."""
    return f"\033[48;2;{r};{g};{b}m"

RESET   = _c(0)
BOLD    = _c(1)
DIM     = _c(2)
ITALIC  = _c(3)
BLINK   = _c(5)
UNDERLINE = _c(4)

# ── Neon Palette ──────────────────────────────────────────────────────────────
NEON_CYAN     = _rgb(0,   255, 255)   # electric cyan
NEON_BLUE     = _rgb(30,  100, 255)   # deep electric blue
NEON_MAGENTA  = _rgb(255, 0,   200)   # hot magenta
NEON_GREEN    = _rgb(57,  255, 20)    # matrix green
NEON_YELLOW   = _rgb(255, 230, 0)     # electric amber
NEON_ORANGE   = _rgb(255, 120, 0)     # plasma orange
NEON_RED      = _rgb(255, 30,  60)    # red alert
NEON_PURPLE   = _rgb(180, 0,   255)   # ultraviolet
NEON_WHITE    = _rgb(220, 240, 255)   # cold white
DEEP_GREY     = _rgb(60,  70,  90)    # deep space grey
MID_GREY      = _rgb(100, 115, 135)   # mid-tone grey
SOFT_CYAN     = _rgb(0,   180, 210)   # softer cyan for text

# ── Legacy aliases (kept for fallback compatibility) ──────────────────────────
FG_CYAN    = NEON_CYAN
FG_GREEN   = NEON_GREEN
FG_YELLOW  = NEON_YELLOW
FG_ORANGE  = NEON_ORANGE
FG_RED     = NEON_RED
FG_WHITE   = NEON_WHITE
FG_GREY    = DEEP_GREY
FG_MAGENTA = NEON_MAGENTA
FG_BLUE    = NEON_BLUE

W = 78  # terminal width

# ── Box-drawing sets ──────────────────────────────────────────────────────────
# Heavy double-line (NEXUS panels)
TL, TR, BL, BR = "╔", "╗", "╚", "╝"
HL, VL         = "═", "║"
ML, MR         = "╠", "╣"
# Light single-line (user panels)
TL2, TR2, BL2, BR2 = "┌", "┐", "└", "┘"
HL2, VL2            = "─", "│"
# Accent chars
DOT  = "·"
DIAM = "◈"
TRI  = "▸"
WAVE = "≋"


# ── Core I/O helpers ──────────────────────────────────────────────────────────

def _print(text: str = ""):
    sys.stdout.write(text + "\n")
    sys.stdout.flush()

def _write(text: str):
    sys.stdout.write(text)
    sys.stdout.flush()

def _clear_line():
    sys.stdout.write("\r\033[K")
    sys.stdout.flush()

def _ansi_strip(text: str) -> str:
    import re
    return re.compile(r'\033\[[0-9;]*m|\033\[38;2;[0-9;]*m|\033\[48;2;[0-9;]*m').sub('', text)

def _vis_len(text: str) -> int:
    return len(_ansi_strip(text))

def _center_in(text: str, width: int, fill: str = " ") -> str:
    vis = _vis_len(text)
    lp = max(0, (width - vis) // 2)
    rp = max(0, width - vis - lp)
    return fill * lp + text + fill * rp

def _pad_right(text: str, width: int) -> str:
    vis = _vis_len(text)
    return text + " " * max(0, width - vis)


# ── Border builders ───────────────────────────────────────────────────────────

def _top(color: str, w: int = W, thin: bool = False) -> str:
    tl, tr, h = (TL2, TR2, HL2) if thin else (TL, TR, HL)
    return f"{color}{tl}{h * (w - 2)}{tr}{RESET}"

def _bot(color: str, w: int = W, thin: bool = False) -> str:
    bl, br, h = (BL2, BR2, HL2) if thin else (BL, BR, HL)
    return f"{color}{bl}{h * (w - 2)}{br}{RESET}"

def _mid(color: str, w: int = W, thin: bool = False) -> str:
    ml, mr, h = ("├", "┤", HL2) if thin else (ML, MR, HL)
    return f"{color}{ml}{h * (w - 2)}{mr}{RESET}"

def _row(content: str, border_color: str, w: int = W, thin: bool = False) -> str:
    vl = VL2 if thin else VL
    vis = _vis_len(content)
    pad = max(0, w - 2 - vis)
    return f"{border_color}{vl}{RESET}{content}{' ' * pad}{border_color}{vl}{RESET}"


# ── ASCII Logo ────────────────────────────────────────────────────────────────

_LOGO_LINES = [
    r"  ███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗",
    r"  ████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝",
    r"  ██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗",
    r"  ██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║",
    r"  ██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║",
    r"  ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝",
]

# Neon gradient colours for logo lines (top → bottom)
_LOGO_COLOURS = [
    _rgb(0,   220, 255),
    _rgb(0,   200, 255),
    _rgb(0,   170, 255),
    _rgb(30,  140, 255),
    _rgb(80,  110, 255),
    _rgb(130, 80,  255),
]


# ── Public API ────────────────────────────────────────────────────────────────

def banner(animate: bool = True):
    """
    Full NEXUS boot banner with neon gradient logo and animated typewriter.
    """
    _print()

    # ── Outer frame top ──────────────────────────────────────────────────────
    _print(f"{NEON_CYAN}{TL}{HL * (W - 2)}{TR}{RESET}")
    _print(_row("", NEON_CYAN))

    # ── Logo lines with gradient colour ──────────────────────────────────────
    inner = W - 2
    for i, line in enumerate(_LOGO_LINES):
        col = _LOGO_COLOURS[i]
        vis = len(_ansi_strip(line))
        lp  = (inner - vis) // 2
        rp  = inner - vis - lp
        content = f"{' ' * lp}{BOLD}{col}{line}{RESET}{' ' * rp}"
        _print(f"{NEON_CYAN}{VL}{RESET}{content}{NEON_CYAN}{VL}{RESET}")
        if animate:
            time.sleep(0.06)

    _print(_row("", NEON_CYAN))

    # ── Tagline separator ─────────────────────────────────────────────────────
    sep = f"  {DEEP_GREY}{DOT * ((W - 6) // 2)}{RESET}"
    _print(_row(sep, NEON_CYAN))

    # ── Info lines ────────────────────────────────────────────────────────────
    def _info_row(icon, label, value):
        return (f"  {DEEP_GREY}{icon}{RESET}  "
                f"{MID_GREY}{label}:{RESET}  "
                f"{BOLD}{NEON_WHITE}{value}{RESET}")

    _print(_row(
        f"  {BOLD}{NEON_CYAN}{DIAM}{RESET}  "
        f"{BOLD}{NEON_WHITE}Neural EXecution & Unified System Automation{RESET}"
        f"  {DEEP_GREY}v3.0{RESET}",
        NEON_CYAN
    ))
    _print(_row("", NEON_CYAN))
    _print(_row(_info_row("◉", "User   ", "Praneeth          "), NEON_CYAN))
    _print(_row(_info_row("◉", "City   ", "Coimbatore        "), NEON_CYAN))
    _print(_row(_info_row("◉", "Engine ", "DeepSeek-R1 via OpenRouter"), NEON_CYAN))
    _print(_row(_info_row("◉", "Voice  ", "Deep Male · 175WPM"), NEON_CYAN))
    _print(_row("", NEON_CYAN))

    # ── Bottom frame ──────────────────────────────────────────────────────────
    _print(f"{NEON_CYAN}{BL}{HL * (W - 2)}{BR}{RESET}")
    _print()


def boot_sequence(steps: list | None = None):
    """
    Animated matrix-style system initialisation sequence.
    """
    if steps is None:
        steps = [
            ("Voice Engine        ", 0.20),
            ("Reasoning Core      ", 0.35),
            ("Wake Word Detector  ", 0.20),
            ("Face Auth Module    ", 0.15),
            ("Skills Registry     ", 0.25),
            ("OpenRouter AI       ", 0.30),
            ("Command Router      ", 0.15),
            ("Stock Market Module ", 0.20),
        ]

    _print()
    _print(f"  {NEON_CYAN}{DIAM}{RESET}  {BOLD}{NEON_WHITE}SYSTEM INITIALISATION{RESET}  "
           f"{DEEP_GREY}{HL2 * 30}{RESET}")
    _print()

    for label, delay in steps:
        # Simulate scanning flicker
        for _ in range(2):
            _write(f"\r  {DEEP_GREY}▸{RESET}  {MID_GREY}{label}{RESET}  "
                   f"{DEEP_GREY}{'.' * random.randint(3,8)}{RESET}  ")
            time.sleep(delay * 0.3)

        _write(f"\r  {NEON_CYAN}▸{RESET}  {NEON_WHITE}{label}{RESET}  ")
        time.sleep(delay * 0.5)
        _print(f"{BOLD}{NEON_GREEN}[  OK  ]{RESET}")

    _print()
    _print(f"  {DEEP_GREY}{HL2 * (W - 4)}{RESET}")
    _print(f"  {NEON_GREEN}{BOLD}◈  ALL SYSTEMS ONLINE{RESET}  "
           f"{DEEP_GREY}{DOT}  NEXUS READY{RESET}")
    _print(f"  {DEEP_GREY}{HL2 * (W - 4)}{RESET}")
    _print()
    time.sleep(0.25)


@contextmanager
def spinner(label: str = "Processing", color: str = None):
    """
    Animated brainwave spinner shown during Ollama inference.
    """
    if color is None:
        color = NEON_CYAN

    # Brainwave-style frames
    frames = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
    pulse   = [NEON_CYAN, SOFT_CYAN, NEON_BLUE, NEON_MAGENTA,
               NEON_BLUE, SOFT_CYAN, NEON_CYAN]
    stop_ev = threading.Event()
    tick    = itertools.count()

    def _spin():
        for frame, col in zip(itertools.cycle(frames), itertools.cycle(pulse)):
            if stop_ev.is_set():
                break
            n = next(tick)
            dots = DOT * ((n // 3) % 4 + 1)
            _write(
                f"\r  {col}{frame}{RESET}  "
                f"{NEON_CYAN}{label}{RESET}"
                f"{DEEP_GREY}{dots:<4}{RESET}  "
            )
            time.sleep(0.09)

    t = threading.Thread(target=_spin, daemon=True)
    t.start()
    try:
        yield
    finally:
        stop_ev.set()
        t.join()
        _clear_line()


def speak_box(text: str):
    """
    Premium NEXUS response panel.
    Neon cyan double-border with glowing header chip.
    """
    _print()
    now = datetime.datetime.now().strftime("%H:%M:%S")

    # ── Header ────────────────────────────────────────────────────────────────
    chip   = (f" {BOLD}{NEON_CYAN}{DIAM} NEXUS{RESET} "
              f"{DEEP_GREY}{DOT}{RESET} "
              f"{DIM}{MID_GREY}{now}{RESET} ")
    chip_v = _vis_len(chip)
    rfill  = W - 2 - chip_v
    _print(f"{NEON_CYAN}{TL}{RESET}{chip}"
           f"{SOFT_CYAN}{HL * rfill}{TR}{RESET}")

    # ── Word-wrapped text ─────────────────────────────────────────────────────
    words  = text.split()
    lines, cur = [], ""
    for word in words:
        test = (cur + " " + word).strip()
        if len(test) <= W - 6:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)

    for i, line in enumerate(lines):
        # Subtle colour shift on first line
        tc = NEON_WHITE if i == 0 else _rgb(200, 225, 240)
        content = f"  {BOLD}{tc}{line}{RESET}"
        _print(_row(content, NEON_CYAN))

    # ── Footer ────────────────────────────────────────────────────────────────
    _print(f"{SOFT_CYAN}{BL}{HL * (W - 2)}{BR}{RESET}")
    _print()


def user_box(text: str):
    """
    User command echo panel.
    Electric green thin-border with mic icon.
    """
    _print()
    now = datetime.datetime.now().strftime("%H:%M:%S")
    chip   = (f" {BOLD}{NEON_GREEN}{TRI} YOU{RESET} "
              f"{DEEP_GREY}{DOT}{RESET} "
              f"{DIM}{MID_GREY}{now}{RESET} ")
    chip_v = _vis_len(chip)
    rfill  = W - 2 - chip_v
    _print(f"{NEON_GREEN}{TL2}{RESET}{chip}"
           f"{DEEP_GREY}{HL2 * rfill}{TR2}{RESET}")

    content = f"  {NEON_GREEN}🎙  {BOLD}{NEON_WHITE}{text}{RESET}"
    _print(_row(content, NEON_GREEN, thin=True))
    _print(f"{DEEP_GREY}{BL2}{HL2 * (W - 2)}{BR2}{RESET}")
    _print()


def reminder_box(text: str):
    """
    Urgent plasma-orange reminder alert panel.
    """
    _print()
    chip   = f" {BOLD}{NEON_ORANGE}⏰  REMINDER{RESET} "
    chip_v = _vis_len(chip)
    rfill  = W - 2 - chip_v
    _print(f"{NEON_ORANGE}{TL}{RESET}{chip}"
           f"{NEON_ORANGE}{HL * rfill}{TR}{RESET}")
    content = f"  {BOLD}{NEON_YELLOW}{text}{RESET}"
    _print(_row(content, NEON_ORANGE))
    _print(f"{NEON_ORANGE}{BL}{HL * (W - 2)}{BR}{RESET}")
    _print()


def status(msg: str, kind: str = "info"):
    """
    Inline glowing status badge.
    kind: "ok" | "wait" | "info" | "warn" | "err"
    """
    _badges = {
        "ok":   (NEON_GREEN,    f"  {BOLD}{_rgb(0,0,0)}{_rgb_bg(57,255,20)}  OK  {RESET}"),
        "wait": (NEON_CYAN,     f"  {BOLD}{_rgb(0,0,0)}{_rgb_bg(0,200,255)} WAIT {RESET}"),
        "info": (MID_GREY,      f"  {BOLD}{_rgb(0,0,0)}{_rgb_bg(100,115,135)} INFO {RESET}"),
        "warn": (NEON_YELLOW,   f"  {BOLD}{_rgb(0,0,0)}{_rgb_bg(255,230,0)} WARN {RESET}"),
        "err":  (NEON_RED,      f"  {BOLD}{_rgb(255,255,255)}{_rgb_bg(255,30,60)}  ERR {RESET}"),
    }
    col, badge = _badges.get(kind, _badges["info"])
    now = datetime.datetime.now().strftime("%H:%M:%S")
    _print(f"  {DEEP_GREY}{now}{RESET} {badge}  {col}{msg}{RESET}")


def divider(color: str = None):
    """Thin neon horizontal rule."""
    c = color or DEEP_GREY
    _print(f"{c}  {HL2 * (W - 4)}{RESET}")


def prompt_wake() -> str:
    """Styled wake prompt for typed mode."""
    _print()
    _write(f"  {NEON_CYAN}{DIAM}{RESET}  {DIM}{DEEP_GREY}say or type{RESET} "
           f"{BOLD}{NEON_CYAN}nexus{RESET}  {DEEP_GREY}›{RESET}  ")
    sys.stdout.flush()
    return input()


def prompt_command() -> str:
    """Styled command input prompt."""
    _print()
    _write(f"  {NEON_GREEN}{TRI}{RESET}  {NEON_WHITE}Command{RESET}  "
           f"{DEEP_GREY}›{RESET}  ")
    sys.stdout.flush()
    return input()


def startup_menu():
    """
    High-tech animated command reference panel shown at startup.
    """
    _print()
    _print(f"{NEON_CYAN}{TL}{HL * (W - 2)}{TR}{RESET}")

    # Title bar
    title = (f"  {NEON_CYAN}{DIAM}{RESET}  "
             f"{BOLD}{NEON_WHITE}NEXUS  COMMAND  MATRIX{RESET}  "
             f"{DEEP_GREY}{DOT}  v3.0{RESET}")
    _print(_row(title, NEON_CYAN))
    _print(_mid(NEON_CYAN))

    def section(icon, title_text, items, col=NEON_CYAN):
        heading = (f"  {col}{icon}{RESET}  "
                   f"{BOLD}{NEON_WHITE}{title_text}{RESET}")
        _print(_row(heading, col))
        sep = f"  {DEEP_GREY}{HL2 * (W - 6)}{RESET}"
        _print(_row(sep, col))
        for cmd, desc in items:
            cmd_s  = f"{BOLD}{NEON_CYAN}{cmd:<32}{RESET}"
            desc_s = f"{MID_GREY}{desc}{RESET}"
            _print(_row(f"    {cmd_s} {DEEP_GREY}›{RESET}  {desc_s}", col))
        _print(_row("", col))

    section("🎤", "VOICE COMMANDS", [
        ('"who are you"',         "Identity check"),
        ('"what time is it"',     "Current time"),
        ('"today\'s date"',       "Current date"),
        ('"what is [topic]"',     "LLM-powered answer"),
        ('"explain [topic]"',     "Dynamic study explanation"),
        ('"search [query]"',      "Web search"),
        ('"play [song]"',         "Spotify playback"),
        ('"take a note [text]"',  "Save note"),
        ('"remind me [task]"',    "Set reminder"),
    ])

    _print(_mid(NEON_CYAN))

    section("⚡", "SYSTEM COMMANDS", [
        ("nexus",                 "Wake word (voice or typed)"),
        ('"nexus sleep"',         "Sleep mode — pauses all listening"),
        ('"nexus wake up"',       "Resume from sleep"),
        ('"clear memory"',        "Reset LLM conversation context"),
        ('"switch model to X"',   "Hot-swap OpenRouter model at runtime"),
        ('"shutdown nexus"',      "Graceful shutdown"),
    ], col=NEON_BLUE)

    _print(_mid(NEON_CYAN))

    section("🧠", "LLM CAPABILITIES (DeepSeek-R1 via OpenRouter)", [
        ("Any question",          "Open-ended reasoning via OpenRouter"),
        ("Follow-up questions",   "3-exchange context memory"),
        ("Code concepts",         "Explain any programming topic"),
        ("Writing / drafting",    "Emails, summaries, decisions"),
        ("Logic / math",          "Calculations and reasoning"),
    ], col=NEON_MAGENTA)

    _print(f"{NEON_CYAN}{BL}{HL * (W - 2)}{BR}{RESET}")
    _print()
    _write(f"  {DEEP_GREY}Ready?{RESET}  "
           f"{NEON_CYAN}{BOLD}Press Enter to engage NEXUS{RESET}  "
           f"{DEEP_GREY}›{RESET}  ")
    sys.stdout.flush()
    input()


def shutdown_banner(user_name: str = "Praneeth"):
    """
    Holographic shutdown screen.
    """
    _print()
    now = datetime.datetime.now().strftime("%Y-%m-%d  %H:%M:%S")

    _print(f"{NEON_MAGENTA}{TL}{HL * (W - 2)}{TR}{RESET}")
    _print(_row("", NEON_MAGENTA))

    # Animated power-down line
    msg  = f"{BOLD}{NEON_WHITE}Goodbye, {user_name}.{RESET}  {NEON_MAGENTA}NEXUS going offline.{RESET}"
    _print(f"{NEON_MAGENTA}{VL}{RESET}{_center_in(msg, W - 2)}{NEON_MAGENTA}{VL}{RESET}")

    _print(_row("", NEON_MAGENTA))

    sub  = f"{DEEP_GREY}{WAVE}  Session ended  {DOT}  {now}  {WAVE}{RESET}"
    _print(f"{NEON_MAGENTA}{VL}{RESET}{_center_in(sub, W - 2)}{NEON_MAGENTA}{VL}{RESET}")

    _print(_row("", NEON_MAGENTA))
    _print(f"{NEON_MAGENTA}{BL}{HL * (W - 2)}{BR}{RESET}")
    _print()


# ═══════════════════════════════════════════════════════════════════════════════
# ██ STOCK MARKET INTELLIGENCE PANELS ██████████████████████████████████████████
# ═══════════════════════════════════════════════════════════════════════════════


def _pnl_color(value: float | None) -> str:
    """Return neon green for positive, neon red for negative, grey for zero/None."""
    if value is None:
        return MID_GREY
    return NEON_GREEN if value >= 0 else NEON_RED


def _sentiment_badge(sentiment: str) -> str:
    """Colored inline sentiment tag."""
    s = sentiment.upper()
    if s == "BULLISH":
        return f"{BOLD}{_rgb(0,0,0)}{_rgb_bg(0,255,136)}  BULL {RESET}"
    if s == "BEARISH":
        return f"{BOLD}{_rgb(255,255,255)}{_rgb_bg(255,30,60)}  BEAR {RESET}"
    return f"{DIM}{_rgb(0,0,0)}{_rgb_bg(100,115,135)}  NEUT {RESET}"


def stock_quote_card(quote: dict):
    """
    Bloomberg-style single stock quote tile.
    Shows: ticker, name, price, day change, high/low, volume, data source.
    """
    _print()
    ticker   = quote.get("ticker", "???")
    name     = quote.get("name", ticker)[:22]
    price    = quote.get("price")
    change   = quote.get("change", 0) or 0
    chg_pct  = quote.get("change_pct", 0) or 0
    high     = quote.get("high")
    low      = quote.get("low")
    volume   = quote.get("volume", 0) or 0
    currency = quote.get("currency", "")
    source   = quote.get("source", "cached" if quote.get("cached") else "live")
    cached   = quote.get("cached", False)
    error    = quote.get("error")

    # ── Price direction arrows ─────────────────────────────────────────────────
    arrow       = "▲" if change >= 0 else "▼"
    price_col   = _pnl_color(change)
    cached_tag  = f"  {DIM}{MID_GREY}[cached]{RESET}" if cached else ""
    now         = datetime.datetime.now().strftime("%H:%M:%S")

    # ── Header ────────────────────────────────────────────────────────────────
    chip = (
        f" {BOLD}{NEON_CYAN}📈 {ticker}{RESET}  "
        f"{DIM}{DEEP_GREY}{name}{RESET}  "
        f"{DEEP_GREY}{DOT}{RESET}  "
        f"{DIM}{MID_GREY}{now}{RESET} "
    )
    chip_v = _vis_len(chip)
    rfill  = W - 2 - chip_v
    _print(f"{NEON_CYAN}{TL}{RESET}{chip}{SOFT_CYAN}{HL * max(0, rfill)}{TR}{RESET}")

    if error and price is None:
        _print(_row(f"  {NEON_RED}⚠  {error}{RESET}", NEON_CYAN))
        _print(f"{SOFT_CYAN}{BL}{HL * (W - 2)}{BR}{RESET}")
        _print()
        return

    # ── Price row ─────────────────────────────────────────────────────────────
    price_str  = f"{price:,.2f} {currency}" if price is not None else "N/A"
    change_str = f"{arrow} {change:+.2f} ({chg_pct:+.2f}%)"
    price_line = (
        f"  {BOLD}{_rgb(220,240,255)}{price_str:<20}{RESET}"
        f"  {BOLD}{price_col}{change_str}{RESET}{cached_tag}"
    )
    _print(_row(price_line, NEON_CYAN))

    # ── High/Low/Volume row ───────────────────────────────────────────────────
    hl_line = (
        f"  {DEEP_GREY}H{RESET} {NEON_GREEN}{high or 'N/A':<10}{RESET}  "
        f"{DEEP_GREY}L{RESET} {NEON_RED}{low or 'N/A':<10}{RESET}  "
        f"{DEEP_GREY}Vol{RESET} {MID_GREY}{volume:,}{RESET}  "
        f"{DEEP_GREY}src:{RESET} {DIM}{MID_GREY}{source}{RESET}"
    )
    _print(_row(hl_line, NEON_CYAN))
    _print(f"{SOFT_CYAN}{BL}{HL * (W - 2)}{BR}{RESET}")
    _print()


def stock_portfolio_panel(summary: dict):
    """
    Full portfolio panel — Bloomberg terminal style.
    Shows each holding with buy price, current price, P&L columns.
    """
    _print()
    now = datetime.datetime.now().strftime("%H:%M:%S")

    # ── Header ────────────────────────────────────────────────────────────────
    chip = (
        f" {BOLD}{NEON_CYAN}💼 PORTFOLIO{RESET}  "
        f"{DEEP_GREY}{DOT}{RESET}  {DIM}{MID_GREY}{now}{RESET} "
    )
    chip_v = _vis_len(chip)
    rfill  = W - 2 - chip_v
    _print(f"{NEON_CYAN}{TL}{RESET}{chip}{SOFT_CYAN}{HL * max(0, rfill)}{TR}{RESET}")
    _print(_row("", NEON_CYAN))

    # ── Column headers ────────────────────────────────────────────────────────
    hdr = (
        f"  {BOLD}{NEON_WHITE}"
        f"{'TICKER':<12}{'QTY':>6}  {'BUY':>10}  {'NOW':>10}  "
        f"{'CHG%':>7}  {'P&L':>10}  {'VALUE':>12}{RESET}"
    )
    _print(_row(hdr, NEON_CYAN))
    _print(_row(f"  {DEEP_GREY}{HL2 * (W - 6)}{RESET}", NEON_CYAN))

    # ── Holdings rows ─────────────────────────────────────────────────────────
    for h in summary["holdings"]:
        pnl_col   = _pnl_color(h.get("pnl"))
        arrow     = "▲" if (h.get("pnl") or 0) >= 0 else "▼"
        cached    = f"{DIM}~{RESET}" if h.get("cached") else " "

        ticker_s   = f"{BOLD}{NEON_WHITE}{h['ticker']:<11}{RESET}{cached}"
        qty_s      = f"{MID_GREY}{h['qty']:>6.0f}{RESET}"
        buy_s      = f"{DEEP_GREY}{h['buy_price']:>10.2f}{RESET}"
        now_s      = (
            f"{BOLD}{_rgb(220,240,255)}{h['current_price']:>10.2f}{RESET}"
            if h.get("current_price") else f"{MID_GREY}{'N/A':>10}{RESET}"
        )
        chg_s      = (
            f"{pnl_col}{h['change_pct']:>6.2f}%{RESET}"
            if h.get("change_pct") is not None else f"{MID_GREY}{'N/A':>7}{RESET}"
        )
        pnl_s      = (
            f"{BOLD}{pnl_col}{arrow}{h['pnl']:>9.0f}{RESET}"
            if h.get("pnl") is not None else f"{MID_GREY}{'N/A':>10}{RESET}"
        )
        val_s      = (
            f"{BOLD}{_rgb(220,240,255)}{h['value']:>12.0f}{RESET}"
            if h.get("value") else f"{MID_GREY}{'N/A':>12}{RESET}"
        )

        row_content = f"  {ticker_s}  {qty_s}  {buy_s}  {now_s}  {chg_s}  {pnl_s}  {val_s}"
        _print(_row(row_content, NEON_CYAN))

    # ── Totals footer ─────────────────────────────────────────────────────────
    _print(_row(f"  {NEON_CYAN}{HL2 * (W - 6)}{RESET}", NEON_CYAN))
    tot_pnl     = summary["total_pnl"]
    tot_col     = _pnl_color(tot_pnl)
    tot_arrow   = "▲" if tot_pnl >= 0 else "▼"
    totals = (
        f"  {BOLD}{NEON_WHITE}{'TOTAL':<11}{RESET}  "
        f"{'':>6}  {'':>10}  "
        f"{BOLD}{_rgb(220,240,255)}{summary['total_current']:>10.0f}{RESET}  "
        f"{'':>7}  "
        f"{BOLD}{tot_col}{tot_arrow}{summary['total_pnl']:>9.0f}{RESET}  "
        f"{BOLD}{_rgb(220,240,255)}{summary['total_current']:>12.0f}{RESET}"
    )
    _print(_row(totals, NEON_CYAN))
    _print(_row("", NEON_CYAN))

    # ── P&L summary line ──────────────────────────────────────────────────────
    pnl_pct = summary.get("total_pnl_pct", 0)
    pnl_summary = (
        f"  {DEEP_GREY}Invested:{RESET} {_rgb(220,240,255)}{summary['total_invested']:.0f}{RESET}  "
        f"{DEEP_GREY}Current:{RESET} {_rgb(220,240,255)}{summary['total_current']:.0f}{RESET}  "
        f"{DEEP_GREY}Total P&L:{RESET} {BOLD}{tot_col}{tot_arrow} "
        f"{abs(tot_pnl):.0f} ({abs(pnl_pct):.2f}%){RESET}"
    )
    _print(_row(pnl_summary, NEON_CYAN))
    _print(f"{SOFT_CYAN}{BL}{HL * (W - 2)}{BR}{RESET}")
    _print()


def news_feed_panel(articles: list):
    """
    Market news card feed with sentiment badges.
    Each card: headline, source, time, sentiment (Bullish/Bearish/Neutral).
    """
    _print()
    now = datetime.datetime.now().strftime("%H:%M:%S")
    chip = (
        f" {BOLD}{NEON_CYAN}📰 MARKET NEWS{RESET}  "
        f"{DEEP_GREY}{DOT}{RESET}  {DIM}{MID_GREY}{now}{RESET} "
    )
    chip_v = _vis_len(chip)
    rfill  = W - 2 - chip_v
    _print(f"{NEON_CYAN}{TL}{RESET}{chip}{SOFT_CYAN}{HL * max(0, rfill)}{TR}{RESET}")

    for i, article in enumerate(articles):
        headline  = article.get("headline", "No headline")
        source    = article.get("source", "")
        ts        = article.get("time", "")
        sentiment = article.get("sentiment", "Neutral")
        badge     = _sentiment_badge(sentiment)

        # ── Headline (word-wrapped to panel width) ────────────────────────────
        max_width   = W - 6
        words       = headline.split()
        lines, cur  = [], ""
        for word in words:
            test = (cur + " " + word).strip()
            if len(test) <= max_width:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)

        # Separator before each article
        _print(_row(f"  {DEEP_GREY}{HL2 * (W - 6)}{RESET}", NEON_CYAN))

        for j, line in enumerate(lines):
            col = NEON_WHITE if j == 0 else _rgb(180, 200, 225)
            _print(_row(f"  {BOLD}{col}{line}{RESET}", NEON_CYAN))

        meta = (
            f"  {badge}  "
            f"{DEEP_GREY}{source}{RESET}  "
            f"{DIM}{MID_GREY}{ts}{RESET}"
        )
        _print(_row(meta, NEON_CYAN))

    _print(f"{SOFT_CYAN}{BL}{HL * (W - 2)}{BR}{RESET}")
    _print()


def watchlist_panel(items: list):
    """
    Watchlist panel with ticker, current price, change, and alert status.
    """
    _print()
    now = datetime.datetime.now().strftime("%H:%M:%S")
    chip = (
        f" {BOLD}{NEON_CYAN}🔔 WATCHLIST{RESET}  "
        f"{DEEP_GREY}{DOT}{RESET}  {DIM}{MID_GREY}{now}{RESET} "
    )
    chip_v = _vis_len(chip)
    rfill  = W - 2 - chip_v
    _print(f"{NEON_CYAN}{TL}{RESET}{chip}{SOFT_CYAN}{HL * max(0, rfill)}{TR}{RESET}")
    _print(_row("", NEON_CYAN))

    hdr = (
        f"  {BOLD}{NEON_WHITE}"
        f"{'TICKER':<14}{'PRICE':>12}  {'CHG%':>8}  {'ALERT':>10}  STATUS{RESET}"
    )
    _print(_row(hdr, NEON_CYAN))
    _print(_row(f"  {DEEP_GREY}{HL2 * (W - 6)}{RESET}", NEON_CYAN))

    for item in items:
        chg_col   = _pnl_color(item.get("change_pct"))
        arrow     = "▲" if (item.get("change_pct") or 0) >= 0 else "▼"
        triggered = "⚡" if item.get("triggered") else " "

        ticker_s  = f"{BOLD}{NEON_WHITE}{triggered}{item['ticker']:<13}{RESET}"
        price_s   = (
            f"{_rgb(220,240,255)}{item['price']:>12.2f}{RESET}"
            if item.get("price") else f"{MID_GREY}{'N/A':>12}{RESET}"
        )
        chg_s     = (
            f"{chg_col}{arrow}{item['change_pct']:>7.2f}%{RESET}"
            if item.get("change_pct") is not None else f"{MID_GREY}{'N/A':>8}{RESET}"
        )
        alert_s   = (
            f"{NEON_YELLOW}{item['alert_price']:>10.2f}{RESET}"
            if item.get("alert_price") else f"{MID_GREY}{'–':>10}{RESET}"
        )
        status_s  = f"{DIM}{MID_GREY}{item.get('status','')[:20]}{RESET}"

        row_content = f"  {ticker_s}  {price_s}  {chg_s}  {alert_s}  {status_s}"
        _print(_row(row_content, NEON_CYAN))

    _print(f"{SOFT_CYAN}{BL}{HL * (W - 2)}{BR}{RESET}")
    _print()


def market_alert(ticker: str, message: str):
    """
    Urgent neon-yellow market alert box — for price threshold breaches.
    Wraps the existing reminder_box style but with a stock-specific icon.
    """
    _print()
    chip   = f" {BOLD}{NEON_YELLOW}⚡  MARKET ALERT  —  {ticker}{RESET} "
    chip_v = _vis_len(chip)
    rfill  = W - 2 - chip_v
    _print(f"{NEON_YELLOW}{TL}{RESET}{chip}{NEON_YELLOW}{HL * max(0, rfill)}{TR}{RESET}")
    content = f"  {BOLD}{NEON_WHITE}{message}{RESET}"
    _print(_row(content, NEON_YELLOW))
    _print(f"{NEON_YELLOW}{BL}{HL * (W - 2)}{BR}{RESET}")
    _print()
