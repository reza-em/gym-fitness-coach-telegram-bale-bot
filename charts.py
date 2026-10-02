"""matplotlib charts (PNG bytes) with Persian labels (arabic-reshaper + python-bidi + bundled Vazirmatn). Falls back to English labels if the
Persian libraries/fonts are missing. Charts are plain PNG photos, so they work identically on Telegram and Bale."""
import io, datetime as dt
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
import config, exdata as X

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    _FA = True
except Exception:                       # pragma: no cover
    _FA = False
try:
    fm.fontManager.addfont(config.FONT_REG); fm.fontManager.addfont(config.FONT_BOLD)
    _FONT = "Vazirmatn"
except Exception:                       # pragma: no cover
    _FONT = "DejaVu Sans"; _FA = False

def fa(s):
    """Prepare a Persian string for matplotlib."""
    if not _FA: return s
    return get_display(arabic_reshaper.reshape(s))

def L(fa_text, en_text): return fa(fa_text) if _FA else en_text

def _style():
    plt.rcParams.update({"font.family": _FONT, "axes.unicode_minus": False, "axes.spines.top": False, "axes.spines.right": False})

def _png(fig):
    buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor="white"); plt.close(fig); return buf.getvalue()

def _dates(pts): return [p[0] for p in pts]

def weight_chart(points, start_date, start_w, target_w, goal_w, target_days, rate_lo=None, rate_hi=None):
    """points [(date, kg)]; shows the 73 kg wish line, realistic band (0.5-1 kg/week), and the long-term goal."""
    _style(); fig, ax = plt.subplots(figsize=(8, 4.6))
    end = start_date + dt.timedelta(days=max(target_days, 56) + 14)
    if points:
        ax.plot(_dates(points), [p[1] for p in points], "-o", color="#1565c0", lw=2, ms=5, label=L("وزن ثبت‌شده", "Weight"), zorder=5)
    x0 = start_date; xs = [x0 + dt.timedelta(days=i) for i in (0, end.toordinal() - x0.toordinal())]
    n = (xs[1] - xs[0]).days / 7.0
    rate_lo = config.REAL_RATE_LO if rate_lo is None else rate_lo; rate_hi = config.REAL_RATE_HI if rate_hi is None else rate_hi
    lo = [start_w, start_w + rate_lo * n]; hi = [start_w, start_w + rate_hi * n]
    ax.fill_between(xs, lo, hi, color="#43a047", alpha=0.18, label=L(f"محدودهٔ واقع‌بینانه ({rate_lo:g}–{rate_hi:g} کیلو در هفته)".translate(str.maketrans("0123456789.", "۰۱۲۳۴۵۶۷۸۹٫")), f"Realistic {rate_lo:g}-{rate_hi:g} kg/wk"))
    if target_w:
        ax.axhline(target_w, color="#ef6c00", ls="--", lw=1.4, label=L(f"هدف {target_w:g} کیلو", f"Target {target_w:g} kg"))
        ax.axvline(start_date + dt.timedelta(days=target_days), color="#ef6c00", ls=":", lw=1)
    if goal_w and goal_w != target_w:
        ax.axhline(goal_w, color="#c62828", ls="--", lw=1.4, label=L(f"هدف بلندمدت {goal_w:g} کیلو", f"Long-term {goal_w:g} kg"))
    ax.set_title(L("پیشرفت وزن", "Weight progress")); ax.set_ylabel(L("کیلوگرم", "kg"))
    ax.grid(alpha=0.25); ax.legend(loc="lower right", fontsize=8, frameon=False); fig.autofmt_xdate()
    top = max([goal_w or 0, target_w or 0] + [p[1] for p in points]); bot = min([start_w] + [p[1] for p in points])
    ax.set_ylim(bot - 2, top + 2)
    return _png(fig)

MEAS_FA = {"arm": "بازو", "chest": "سینه", "waist": "کمر", "thigh": "ران"}
MEAS_EN = {"arm": "Arm", "chest": "Chest", "waist": "Waist", "thigh": "Thigh"}
def measures_chart(series):
    """series: {kind: [(date, cm)]}"""
    _style(); kinds = [k for k in MEAS_FA if series.get(k)]
    fig, axes = plt.subplots(1, max(1, len(kinds)), figsize=(max(4, 3.2 * len(kinds)), 3.6), squeeze=False)
    for ax, k in zip(axes[0], kinds):
        pts = series[k]; ax.plot([p[0] for p in pts], [p[1] for p in pts], "-o", color="#6a1b9a", lw=2, ms=4)
        ax.set_title(L(MEAS_FA[k] + " (سانتی‌متر)", MEAS_EN[k] + " (cm)")); ax.grid(alpha=0.25)
        for lab in ax.get_xticklabels(): lab.set_rotation(35); lab.set_fontsize(7)
    return _png(fig)

def strength_chart(eid, rows):
    """rows: [(date, top_weight, e1rm)]"""
    _style(); fig, ax = plt.subplots(figsize=(8, 4.2))
    d = [r[0] for r in rows]
    ax.plot(d, [r[1] for r in rows], "-o", color="#1565c0", lw=2, label=L("بیشترین وزنه", "Top weight"))
    ax.plot(d, [r[2] for r in rows], "--s", color="#ef6c00", lw=1.5, ms=4, label=L("۱RM تخمینی", "Est. 1RM"))
    ax.set_title(fa(X.ex_name(eid)) if _FA else X.EX[eid]["en"]); ax.set_ylabel(L("کیلوگرم", "kg")); ax.grid(alpha=0.25)
    ax.legend(frameon=False, fontsize=8); fig.autofmt_xdate(); return _png(fig)

def volume_chart(rows):
    """rows: [(week_no, volume_kg)]"""
    _style(); fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar([str(r[0]) for r in rows], [r[1] for r in rows], color="#00897b")
    ax.set_title(L("حجم تمرین هفتگی (کیلوگرم × تکرار)", "Weekly training volume")); ax.set_xlabel(L("هفته", "Week")); ax.grid(axis="y", alpha=0.25)
    return _png(fig)
