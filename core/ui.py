"""
core/ui.py  ─  NEXUS Terminal Interface v4.0
─────────────────────────────────────────────
Cinematic high-tech terminal UI featuring:
  ◈ Matrix rain intro                ◈ Glitch typewriter banner
  ◈ Animated waveform listener       ◈ Typewriter TTS output
  ◈ Live CPU / RAM / clock badge     ◈ Neon gradient borders
  ◈ Brainwave spinner                ◈ Holographic shutdown
"""

import sys, os, time, random, threading, datetime, itertools, shutil
from contextlib import contextmanager

# ── True-colour helpers ───────────────────────────────────────────────────────
def _rgb(r,g,b):  return f"\033[38;2;{r};{g};{b}m"
def _bg(r,g,b):   return f"\033[48;2;{r};{g};{b}m"
def _c(*c):       return f"\033[{';'.join(map(str,c))}m"

R=_c(0); B=_c(1); DM=_c(2); IT=_c(3)

# Neon palette
NC  = _rgb(0,255,255)    # neon cyan
NB  = _rgb(30,120,255)   # electric blue
NM  = _rgb(220,0,255)    # hot magenta
NG  = _rgb(57,255,20)    # matrix green
NY  = _rgb(255,230,0)    # electric amber
NO  = _rgb(255,110,0)    # plasma orange
NR  = _rgb(255,30,60)    # red alert
NW  = _rgb(210,235,255)  # cold white
DG  = _rgb(50,65,85)     # deep space grey
MG  = _rgb(95,115,140)   # mid grey
SC  = _rgb(0,190,220)    # soft cyan
NP  = _rgb(160,0,255)    # ultraviolet

# Gradient for logo lines
_GR = [_rgb(0,230,255),_rgb(0,200,255),_rgb(0,165,255),
       _rgb(40,130,255),_rgb(90,95,255),_rgb(140,65,255)]

# Box chars
TL,TR,BL,BR,HL,VL,ML,MR = "╔","╗","╚","╝","═","║","╠","╣"
tl,tr,bl,br,hl,vl        = "┌","┐","└","┘","─","│"

W = min(shutil.get_terminal_size((80,24)).columns, 90)

# ── I/O primitives ────────────────────────────────────────────────────────────
def _p(t=""): sys.stdout.write(t+"\n"); sys.stdout.flush()
def _w(t):    sys.stdout.write(t);     sys.stdout.flush()
def _clr():   sys.stdout.write("\r\033[K"); sys.stdout.flush()

import re as _re
_strip = _re.compile(r'\033\[[0-9;]*m|\033\[3[48];2;[0-9;]*m')
def _vl(t): return len(_strip.sub("",t))
def _pad(t,n): return t+" "*max(0,n-_vl(t))
def _cen(t,n,f=" "): v=_vl(t); l=(n-v)//2; r=n-v-l; return f*l+t+f*r

def _row(content, bc, w=None, thin=False):
    w = w or W
    v = _vl(content)
    p = max(0, w-2-v)
    c = vl if thin else VL
    return f"{bc}{c}{R}{content}{' '*p}{bc}{c}{R}"

def _top(bc,w=None,thin=False):
    w=w or W; a,b,h=(tl,tr,hl)if thin else(TL,TR,HL)
    return f"{bc}{a}{h*(w-2)}{b}{R}"
def _bot(bc,w=None,thin=False):
    w=w or W; a,b,h=(bl,br,hl)if thin else(BL,BR,HL)
    return f"{bc}{a}{h*(w-2)}{b}{R}"
def _mid(bc,w=None,thin=False):
    w=w or W; a,b,h=("├","┤",hl)if thin else(ML,MR,HL)
    return f"{bc}{a}{h*(w-2)}{b}{R}"


# ── Logo ──────────────────────────────────────────────────────────────────────
_LOGO = [
    r"  ███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗",
    r"  ████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝",
    r"  ██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗",
    r"  ██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║",
    r"  ██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║",
    r"  ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝",
]
_GLITCH = "!@#$%^&*<>?/|\\~±§"


# ── Matrix rain intro ─────────────────────────────────────────────────────────
def matrix_intro(duration: float = 1.8):
    """Short matrix rain splash before banner."""
    cols  = W
    rows  = 7
    chars = "アイウエオカキクケコNEXUSABCDEF0123456789#@!><"
    stop  = time.time() + duration
    while time.time() < stop:
        line = ""
        for _ in range(cols):
            intensity = random.random()
            if intensity > 0.85:
                line += f"{B}{NG}{random.choice(chars)}{R}"
            elif intensity > 0.6:
                line += f"{SC}{random.choice(chars)}{R}"
            elif intensity > 0.3:
                line += f"{DG}{random.choice('01')}{R}"
            else:
                line += " "
        _p(line)
        time.sleep(0.045)
    sys.stdout.write(f"\033[{rows}A\033[J")
    sys.stdout.flush()


# ── Banner ────────────────────────────────────────────────────────────────────
def banner(animate: bool = True):
    matrix_intro(1.6 if animate else 0)
    _p()
    _p(f"{NC}{TL}{HL*(W-2)}{TR}{R}")
    _p(_row("", NC))

    inner = W - 2
    for i, line in enumerate(_LOGO):
        col  = _GR[i]
        vis  = len(line)
        lp   = (inner - vis) // 2
        rp   = inner - vis - lp
        if animate:
            # Glitch typewriter reveal
            _w(f"{NC}{VL}{R}{' '*lp}{B}{col}")
            for ch in line:
                if random.random() < 0.12:
                    _w(random.choice(_GLITCH))
                    time.sleep(0.007)
                    _w("\b \b")
                _w(ch)
                time.sleep(0.005)
            _w(f"{R}{' '*rp}{NC}{VL}{R}\n")
        else:
            content = f"{' '*lp}{B}{col}{line}{R}{' '*rp}"
            _p(f"{NC}{VL}{R}{content}{NC}{VL}{R}")

    _p(_row("", NC))
    sep = f"  {DG}{'·'*((W-6)//2)}{R}"
    _p(_row(sep, NC))

    def _ir(icon, label, val):
        return f"  {DG}{icon}{R}  {MG}{label}:{R}  {B}{NW}{val}{R}"

    _p(_row(f"  {B}{NC}◈{R}  {B}{NW}Neural EXecution & Unified System Automation{R}  {DG}v4.0{R}", NC))
    _p(_row("", NC))
    _p(_row(_ir("◉", "User   ", "Praneeth           "), NC))
    _p(_row(_ir("◉", "City   ", "Coimbatore, India  "), NC))
    _p(_row(_ir("◉", "Engine ", "Mistral  ·  Ollama "), NC))
    _p(_row(_ir("◉", "Voice  ", "Deep Male · 175 WPM"), NC))
    _p(_row(_ir("◉", "Mode   ", "Voice + LLM Active "), NC))
    _p(_row("", NC))
    _p(f"{NC}{BL}{HL*(W-2)}{BR}{R}")
    _p()


# ── Boot sequence ─────────────────────────────────────────────────────────────
def _progress_bar(pct: float, width: int = 20) -> str:
    filled = int(width * pct)
    empty  = width - filled
    bar    = f"{B}{NG}{'█'*filled}{R}{DG}{'░'*empty}{R}"
    return f"[{bar}]"

def boot_sequence(steps=None):
    if steps is None:
        steps = [
            ("Voice Engine        ", 0.18),
            ("Reasoning Core      ", 0.30),
            ("Wake Word Detector  ", 0.18),
            ("Face Auth Module    ", 0.14),
            ("Skills Registry     ", 0.22),
            ("Ollama LLM Bridge   ", 0.28),
            ("Command Router      ", 0.14),
        ]
    total = len(steps)
    _p()
    _p(f"  {NC}◈{R}  {B}{NW}SYSTEM INITIALISATION{R}  {DG}{hl*32}{R}")
    _p()

    for idx, (label, delay) in enumerate(steps):
        pct = idx / total
        bar = _progress_bar(pct)
        # scan flicker
        for _ in range(3):
            glitch = random.choice(_GLITCH) if random.random() < 0.25 else "▸"
            _w(f"\r  {DG}{glitch}{R}  {MG}{label}{R}  {bar}  {DG}scanning…{R}   ")
            time.sleep(delay * 0.25)
        _w(f"\r  {NC}▸{R}  {NW}{label}{R}  ")
        time.sleep(delay * 0.4)
        bar2 = _progress_bar(1.0)
        _p(f"{bar2}  {B}{NG}[  OK  ]{R}")

    _p()
    # Full progress bar
    _w(f"  {DG}Loading  [{R}")
    for i in range(W - 14):
        col = _rgb(0, int(100 + 155*(i/(W-14))), int(255 - 100*(i/(W-14))))
        _w(f"{col}█{R}")
        time.sleep(0.012)
    _p(f"]{R}")
    _p()
    _p(f"  {DG}{hl*(W-4)}{R}")
    _p(f"  {B}{NG}◈  ALL SYSTEMS ONLINE{R}  {DG}·  NEXUS READY{R}")
    _p(f"  {DG}{hl*(W-4)}{R}")
    _p()
    time.sleep(0.2)


# ── Spinner ───────────────────────────────────────────────────────────────────
@contextmanager
def spinner(label="Processing", color=None):
    color = color or NC
    frames = ["⣾","⣽","⣻","⢿","⡿","⣟","⣯","⣷"]
    pulse  = [NC, SC, NB, NM, NB, SC, NC]
    dots   = ["·","··","···","····","···","··","·",""]
    stop   = threading.Event()
    n      = itertools.count()

    def _spin():
        for fr, col, dt in zip(itertools.cycle(frames),
                               itertools.cycle(pulse),
                               itertools.cycle(dots)):
            if stop.is_set(): break
            _w(f"\r  {col}{fr}{R}  {NC}{label}{R}  {DG}{dt:<5}{R}  ")
            time.sleep(0.09)

    t = threading.Thread(target=_spin, daemon=True)
    t.start()
    try:    yield
    finally:
        stop.set(); t.join(); _clr()


# ── Typewriter speak box ──────────────────────────────────────────────────────
def speak_box(text: str, typewriter: bool = True):
    """NEXUS response panel with optional typewriter effect."""
    _p()
    now   = datetime.datetime.now().strftime("%H:%M:%S")
    chip  = f" {B}{NC}◈ NEXUS{R} {DG}·{R} {DM}{MG}{now}{R} "
    cv    = _vl(chip)
    rf    = W - 2 - cv
    _p(f"{NC}{TL}{R}{chip}{SC}{HL*rf}{TR}{R}")

    words = text.split()
    lines, cur = [], ""
    for w in words:
        t = (cur+" "+w).strip()
        if len(t) <= W-6: cur = t
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)

    for i, line in enumerate(lines):
        tc = NW if i == 0 else _rgb(185,215,240)
        if typewriter and i == 0:
            _w(f"{NC}{VL}{R}  {B}{tc}")
            for ch in line:
                _w(ch)
                time.sleep(0.018)
            vis = 2 + len(line)
            _p(f"{R}{' '*max(0,W-2-vis)}{NC}{VL}{R}")
        else:
            content = f"  {B}{tc}{line}{R}"
            _p(_row(content, NC))

    _p(f"{SC}{BL}{HL*(W-2)}{BR}{R}")
    _p()


# ── Waveform listening indicator ──────────────────────────────────────────────
_WAVE_BARS = "▁▂▃▄▅▆▇█"

@contextmanager
def waveform_listen(label="Listening"):
    """Animated waveform shown while STT is active."""
    stop = threading.Event()
    W2   = 24   # waveform width

    def _wave():
        levels = [random.randint(0,7) for _ in range(W2)]
        while not stop.is_set():
            # shift + randomise
            levels = levels[1:] + [random.randint(0,7)]
            wave   = ""
            for lvl in levels:
                col = [DG,MG,SC,NC,NB,NB,NM,NM][lvl]
                wave += f"{col}{_WAVE_BARS[lvl]}{R}"
            _w(f"\r  {B}{NG}◈{R}  {NW}{label}{R}  {wave}  ")
            time.sleep(0.07)

    t = threading.Thread(target=_wave, daemon=True)
    t.start()
    try:    yield
    finally:
        stop.set(); t.join(); _clr()


# ── User box ──────────────────────────────────────────────────────────────────
def user_box(text: str):
    _p()
    now  = datetime.datetime.now().strftime("%H:%M:%S")
    chip = f" {B}{NG}▸ YOU{R} {DG}·{R} {DM}{MG}{now}{R} "
    cv   = _vl(chip)
    rf   = W - 2 - cv
    _p(f"{NG}{tl}{R}{chip}{DG}{hl*rf}{tr}{R}")
    _p(_row(f"  {NG}🎙  {B}{NW}{text}{R}", NG, thin=True))
    _p(f"{DG}{bl}{hl*(W-2)}{br}{R}")
    _p()


# ── Reminder box ──────────────────────────────────────────────────────────────
def reminder_box(text: str):
    _p()
    chip = f" {B}{NO}⏰  REMINDER{R} "
    cv   = _vl(chip)
    rf   = W - 2 - cv
    _p(f"{NO}{TL}{R}{chip}{NO}{HL*rf}{TR}{R}")
    _p(_row(f"  {B}{NY}{text}{R}", NO))
    _p(f"{NO}{BL}{HL*(W-2)}{BR}{R}")
    _p()


# ── Status badges ─────────────────────────────────────────────────────────────
def _sysinfo() -> str:
    """Live CPU + RAM mini-badge."""
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        return f"{DG} CPU {_rgb(57,255,20) if cpu<60 else _rgb(255,110,0)}{cpu:.0f}%{R}{DG} ▸ RAM {_rgb(57,255,20) if ram<70 else _rgb(255,110,0)}{ram:.0f}%{R}"
    except Exception:
        return ""

def status(msg: str, kind: str = "info"):
    _map = {
        "ok":   (NG,  f"{B}{_bg(30,30,30)} {B}{NG} ✓ OK  {R}"),
        "wait": (NC,  f"{B}{_bg(30,30,30)} {B}{NC} ◈ WAIT{R}"),
        "info": (MG,  f"{B}{_bg(30,30,30)} {B}{MG} ℹ INFO{R}"),
        "warn": (NY,  f"{B}{_bg(30,30,30)} {B}{NY} ⚠ WARN{R}"),
        "err":  (NR,  f"{B}{_bg(50,0,10)} {B}{NR} ✗ ERR {R}"),
    }
    col, badge = _map.get(kind, _map["info"])
    now   = datetime.datetime.now().strftime("%H:%M:%S")
    sys_  = _sysinfo()
    _p(f"  {DG}{now}{R} {badge}  {col}{msg}{R}  {sys_}")


# ── Divider ───────────────────────────────────────────────────────────────────
def divider(color=None):
    c = color or DG
    _p(f"{c}  {hl*(W-4)}{R}")


# ── Prompts ───────────────────────────────────────────────────────────────────
def prompt_wake() -> str:
    _p()
    _w(f"  {NC}◈{R}  {DM}{DG}say or type{R} {B}{NC}nexus{R}  {DG}›{R}  ")
    sys.stdout.flush()
    return input()

def prompt_command() -> str:
    _p()
    _w(f"  {NG}▸{R}  {NW}Command{R}  {DG}›{R}  ")
    sys.stdout.flush()
    return input()


# ── Startup menu ──────────────────────────────────────────────────────────────
def startup_menu():
    _p()
    _p(f"{NC}{TL}{HL*(W-2)}{TR}{R}")
    title = f"  {NC}◈{R}  {B}{NW}NEXUS  COMMAND  MATRIX{R}  {DG}·  v4.0{R}"
    _p(_row(title, NC))
    _p(_mid(NC))

    def section(icon, title_text, items, col=NC):
        _p(_row(f"  {col}{icon}{R}  {B}{NW}{title_text}{R}", col))
        _p(_row(f"  {DG}{hl*(W-6)}{R}", col))
        for cmd, desc in items:
            cs = f"{B}{NC}{cmd:<32}{R}"
            ds = f"{MG}{desc}{R}"
            _p(_row(f"    {cs} {DG}›{R}  {ds}", col))
        _p(_row("", col))

    section("🎤", "VOICE COMMANDS", [
        ('"what is [anything]"',   "LLM open-ended answer"),
        ('"explain [topic]"',      "Dynamic study explanation"),
        ('"search [query]"',       "DuckDuckGo web search"),
        ('"play [song]"',          "Spotify playback"),
        ('"take a note [text]"',   "Save note"),
        ('"remind me [task]"',     "Set reminder"),
        ('"what time / date"',     "Time & date"),
        ('"weather / forecast"',   "Live weather"),
    ])
    _p(_mid(NC))
    section("⚡", "SYSTEM", [
        ('"nexus sleep / wake up"', "Suspend & resume"),
        ('"clear memory"',          "Reset LLM context"),
        ('"switch model to X"',     "Hot-swap Ollama model"),
        ('"shutdown nexus"',        "Graceful exit"),
    ], col=NB)
    _p(_mid(NC))
    section("🧠", "LLM  (Mistral · offline)", [
        ("Any question",            "Reasoning via Ollama"),
        ("Follow-up questions",     "3-exchange memory context"),
        ("Code, math, writing",     "General intelligence"),
    ], col=NM)
    _p(f"{NC}{BL}{HL*(W-2)}{BR}{R}")
    _p()
    _w(f"  {DG}Ready?{R}  {B}{NC}Press Enter to engage NEXUS{R}  {DG}›{R}  ")
    sys.stdout.flush(); input()


# ── Shutdown banner ───────────────────────────────────────────────────────────
def shutdown_banner(user_name: str = "Praneeth"):
    _p()
    now = datetime.datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
    _p(f"{NM}{TL}{HL*(W-2)}{TR}{R}")
    _p(_row("", NM))

    # Fade-out animation
    msg = f"Goodbye, {user_name}.  NEXUS going offline."
    colours = [NW, SC, NC, NB, NM, NP, DG, MG]
    for col in colours:
        _w(f"\r{NM}{VL}{R}{_cen(f'{B}{col}{msg}{R}', W-2)}{NM}{VL}{R}")
        time.sleep(0.07)
    _p()

    _p(_row("", NM))
    sub = f"{DG}≋  Session ended  ·  {now}  ≋{R}"
    _p(f"{NM}{VL}{R}{_cen(sub, W-2)}{NM}{VL}{R}")
    _p(_row("", NM))
    _p(f"{NM}{BL}{HL*(W-2)}{BR}{R}")
    _p()
