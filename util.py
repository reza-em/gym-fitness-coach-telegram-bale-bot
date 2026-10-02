"""Small helpers: clock/time zones, Jalali dates, number parsing/formatting, RTL, text grids."""
import re, time, datetime as dt

try:
    from zoneinfo import ZoneInfo
except Exception:                                   # pragma: no cover
    ZoneInfo = None

_clock = time.time
def set_clock(fn):
    """Tests replace the clock."""
    global _clock; _clock = fn
def now(): return int(_clock())

def tzinfo(tz):
    if ZoneInfo:
        try: return ZoneInfo(tz)
        except Exception: pass
    return dt.timezone(dt.timedelta(hours=3, minutes=30)) if tz == "Asia/Tehran" else dt.timezone.utc

def local_now(tz, ts=None):
    return dt.datetime.fromtimestamp(_clock() if ts is None else ts, tzinfo(tz))

def today(tz, ts=None): return local_now(tz, ts).date()
def day_str(d): return d.isoformat()
def parse_day(s): return dt.date.fromisoformat(s)

# ---- Jalali (Solar Hijri) conversion, standard arithmetic algorithm ----
def g2j(gy, gm, gd):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if gm > 2 else gy
    days = 355666 + 365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400 + gd + g_d_m[gm - 1]
    jy = -1595 + 33 * (days // 12053); days %= 12053
    jy += 4 * (days // 1461); days %= 1461
    if days > 365:
        jy += (days - 1) // 365; days = (days - 1) % 365
    if days < 186: jm = 1 + days // 31; jd = 1 + days % 31
    else: jm = 7 + (days - 186) // 30; jd = 1 + (days - 186) % 30
    return jy, jm, jd

JMONTHS = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
WEEKDAYS = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]       # python weekday(): 0=Monday
WEEK_ORDER = [5, 6, 0, 1, 2, 3, 4]       # Persian week: Saturday first

def jdate(d, with_year=False):
    jy, jm, jd = g2j(d.year, d.month, d.day)
    s = f"{jd} {JMONTHS[jm - 1]}"
    return f"{s} {jy}" if with_year else s

def dlabel(d):
    """e.g. «شنبه ۱۱ مهر»"""
    return f"{WEEKDAYS[d.weekday()]} {jdate(d)}"

# ---- numbers ----
_DIG = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩٫٬،", "01234567890123456789.,,")
def norm(s): return (s or "").translate(_DIG).strip()

def parse_num(s, lo=None, hi=None):
    s = norm(s).replace(",", ".")
    if not re.fullmatch(r"\d{1,4}(\.\d{1,2})?", s): return None
    v = float(s)
    if lo is not None and v < lo: return None
    if hi is not None and v > hi: return None
    return v

def parse_int(s, lo=0, hi=10**9):
    s = norm(s)
    if not re.fullmatch(r"\d{1,9}", s): return None
    n = int(s); return n if lo <= n <= hi else None

def fnum(v, nd=1):
    """12.0 -> '12', 12.5 -> '12.5'"""
    if v is None: return "-"
    r = round(float(v), nd)
    return str(int(r)) if r == int(r) else f"{r:.{nd}f}".rstrip("0").rstrip(".")

def sgn(v, nd=1):
    r = round(float(v), nd)
    return ("+" if r > 0 else "") + fnum(r, nd) if r != 0 else "0"

def hhmm_ok(s): return bool(re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", s or ""))
def parse_hhmm(s):
    m = re.fullmatch(r"(\d{1,2})(?:[:.](\d{2}))?", norm(s))
    if not m: return None
    h, mi = int(m.group(1)), int(m.group(2) or 0)
    return f"{h:02d}:{mi:02d}" if h <= 23 and mi <= 59 else None

def minutes(hhmm): h, m = hhmm.split(":"); return int(h) * 60 + int(m)

# ---- text ----
RLM = "\u200f"
def rtl(text):
    """A right-to-left mark at the start of every non-empty line keeps lines that begin with Latin/digits/emoji right-aligned."""
    return "\n".join((RLM + ln) if ln.strip() and not ln.startswith(RLM) else ln for ln in text.split("\n"))

def esc(t): return str(t if t is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
def grid(buttons, per=2): return [buttons[i:i + per] for i in range(0, len(buttons), per)]
def bar(frac, n=10):
    f = max(0.0, min(1.0, frac)); k = int(round(f * n)); return "█" * k + "░" * (n - k)
