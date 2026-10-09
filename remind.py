"""Reminders (workout day, creatine, gainer, water, sleep, weekly weigh-in/check-in): settings UI + background scheduler.
Reminders are sent at most once per (kind, time, local day), never more than 3 h late, and skipped when already done."""
import time, logging, threading
import config, db, util, program as P, nutrition as N
import core as C, ui
from core import btn, kb, send, show
from util import fnum

log = logging.getLogger("sched")
KINDS = {
 "workout": ("🏋️ تمرین (روزهای تمرین)", "17:00", ["07:00", "16:00", "17:00", "18:30", "20:00"]),
 "creatine": ("🧪 کراتین", "10:00", ["08:00", "10:00", "13:00", "21:00"]),
 "gainer": ("🥤 گینر", "17:30", ["15:30", "17:30", "19:00", "21:00"]),
 "water": ("💧 آب", "10:00,13:00,16:00,19:00", None),
 "sleep": ("😴 خواب", "23:00", ["22:00", "22:30", "23:00", "23:30"]),
 "weighin": ("⚖️ وزن‌کشی و بررسی هفتگی", "08:00", ["07:00", "08:00", "09:00", "20:00"]),
}

def defaults(uid, enable=True):
    u = ui.U(uid)
    for k, (_lbl, t, _p) in KINDS.items():
        on = 1 if enable else 0
        if k == "creatine" and not (u["creatine_on"] and N.creatine_ok(u)): on = 0
        if k == "gainer" and not u["gainer_on"]: on = 0
        db.ex("INSERT INTO reminders(user_id,kind,times,enabled) VALUES(?,?,?,?) ON CONFLICT(user_id,kind) DO UPDATE SET enabled=excluded.enabled", (uid, k, t, on))

def get(uid):
    rows = {r["kind"]: r for r in db.q("SELECT * FROM reminders WHERE user_id=?", (uid,))}
    return {k: rows.get(k) or dict(user_id=uid, kind=k, times=KINDS[k][1], enabled=0) for k in KINDS}

def menu(uid, mid=None):
    rm = get(uid); u = ui.U(uid)
    lines = ["⏰ <b>یادآورها</b> (به وقت " + ("تهران" if u["tz"] == "Asia/Tehran" else u["tz"]) + ")", ""]
    rows = []
    for k, (lbl, _d, _p) in KINDS.items():
        r = rm[k]; lines.append(f"{'🟢' if r['enabled'] else '⚪️'} {lbl}: {r['times'].replace(',', '، ')}")
        rows.append([btn(("خاموش: " if r["enabled"] else "روشن: ") + lbl.split(' ', 1)[1].split(' (')[0], f"r:t:{k}"), btn("🕒 زمان", f"r:e:{k}")])
    lines.append("\nیادآورها فقط وقتی می‌آیند که کار آن روز انجام نشده باشد؛ هر یادآور حداکثر یک بار در روز.")
    rows.append(ui.menu_row())
    return show(uid, mid, "\n".join(lines), kb(rows))

def edit(uid, mid, kind):
    lbl, _d, presets = KINDS[kind]
    db.set_await(uid, "rtime", {"kind": kind})
    rows = [[btn(t, f"r:s:{kind}:{t}") for t in presets]] if presets else []
    rows.append([btn("◀️ بازگشت", "r:menu")])
    hint = "ساعت‌ها را با کاما بنویس، مثلاً 10:00,13:00,16:00" if kind == "water" else "ساعت را بنویس (مثلاً 18:30) یا یکی از دکمه‌ها"
    return show(uid, mid, f"{lbl}\n{hint}", kb(rows))

def set_times(uid, kind, times):
    db.ex("INSERT INTO reminders(user_id,kind,times,enabled) VALUES(?,?,?,1) ON CONFLICT(user_id,kind) DO UPDATE SET times=excluded.times, enabled=1", (uid, kind, times))
    db.ex("DELETE FROM rem_sent WHERE user_id=? AND key LIKE ?", (uid, kind + "@%"))

def on_text(uid, aw, d, text):
    kind = d["kind"]; parts = [x for x in util.norm(text).replace("،", ",").replace(" ", ",").split(",") if x]
    ts = [util.parse_hhmm(x) for x in parts]
    if not ts or any(t is None for t in ts) or (kind != "water" and len(ts) != 1):
        return send(uid, "ساعت معتبر نیست؛ مثل 18:30 بنویس" + (" (برای آب چند ساعت با کاما)" if kind == "water" else "") + ".")
    set_times(uid, kind, ",".join(sorted(set(ts)))); db.set_await(uid, None)
    return menu(uid)

def cb(uid, mid, p):
    k = p[1]
    if k == "menu": db.set_await(uid, None); return menu(uid, mid)
    if k == "t":
        r = get(uid)[p[2]]
        if p[2] == "creatine" and not r["enabled"] and not (ui.U(uid)["creatine_on"] and N.creatine_ok(ui.U(uid))):
            return send(uid, "کراتین در تنظیمات مکمل‌ها غیرفعال است.")
        db.ex("INSERT INTO reminders(user_id,kind,times,enabled) VALUES(?,?,?,?) ON CONFLICT(user_id,kind) DO UPDATE SET enabled=excluded.enabled", (uid, p[2], r["times"], 0 if r["enabled"] else 1))
        return menu(uid, mid)
    if k == "e": return edit(uid, mid, p[2])
    if k == "s": set_times(uid, p[2], ":".join(p[3:])); db.set_await(uid, None); return menu(uid, mid)

# ---------------------------------------------------------------- scheduler
def due(tz, hhmm, key, uid, ts=None):
    """-> 'send' | 'skip' (past the window, mark done silently) | None (not yet / already done today)"""
    now = util.local_now(tz, ts); day = now.date().isoformat()
    if db.val("SELECT 1 FROM rem_sent WHERE user_id=? AND key=? AND day=?", (uid, key, day)): return None
    late = now.hour * 60 + now.minute - util.minutes(hhmm)
    if late < 0: return None
    return "send" if late <= config.REMIND_MAX_LATE_MIN else "skip"

def compose(u, kind, ts=None):
    """-> (text, markup) or None when the reminder is pointless right now."""
    import diet, workout
    d = util.local_now(u["tz"], ts).date(); sup = diet.today_supp(u)
    if kind == "workout":
        if not P.is_train_day(u, d): return None
        wk = P.week_of(u, d)
        if db.val("SELECT COUNT(*) FROM workouts WHERE user_id=? AND day=? AND finished=1", (u["id"], d.isoformat()), 0): return None
        nx = workout.next_session_idx(u, wk)
        if nx is None: return None
        title = P.build_session(u, wk, nx)["title"]
        return (f"🏋️ امروز روز تمرینه! جلسهٔ «{title}». حتی یک جلسهٔ کوتاه بهتر از هیچه 💪", kb([[btn("▶️ تمرین امروز", "w:today")]]))
    if kind == "creatine":
        if not (u["creatine_on"] and N.creatine_ok(u)) or sup.get("creatine"): return None
        return (f"🧪 کراتین {fnum(u['creatine_g'])} گرم با یک لیوان آب (هر روز، حتی روز استراحت).", kb([[btn("✅ خوردم", "s:log:creatine")]]))
    if kind == "gainer":
        if not (u["gainer_on"] and u["gainer_kcal"]) or sup.get("gainer", (0, 0))[0] >= u["gainer_n"]: return None
        train = P.is_train_day(u, d)
        return ("🥤 وقت گینره" + (" (بعد از تمرین بخور)" if train else " (بین وعده‌ها)") + f" — {fnum(u['gainer_kcal'])} kcal کمک به کالری هدف.", kb([[btn("✅ خوردم", "s:log:gainer")]]))
    if kind == "water":
        tgt = N.targets(u)["water_ml"]; w = diet.water_today(u)
        if w >= tgt: return None
        return (f"💧 آب بنوش! تا الان {w} از {tgt} ml.", kb([[btn("+250", "wt:250"), btn("+500", "wt:500")]]))
    if kind == "sleep":
        return ("😴 وقت آماده‌شدن برای خوابه. عضله موقع خواب ساخته می‌شود؛ هدف ۷–۹ ساعت. گوشی را کنار بگذار 🌙", None)
    if kind == "weighin":
        off = (d - P.start_date(u)).days
        if off <= 0 or off % 7 != 0 or u["last_checkin_week"] >= P.week_of(u, d): return None
        return ("⚖️ وقت وزن‌کشی و بررسی هفتگیه (صبح، ناشتا). بعد از وزن، چند سؤال کوتاه می‌پرسم و کالری را تنظیم می‌کنم.", kb([[btn("✅ بررسی هفتگی", "ci:start")]]))
    return None

def _claim(uid, key, day):
    """Atomically mark (user, reminder key) done for `day`; False if another tick (overlapping cron call) already did."""
    cur = db.ex("INSERT INTO rem_sent(user_id,key,day) VALUES(?,?,?) ON CONFLICT(user_id,key) DO UPDATE SET day=excluded.day WHERE rem_sent.day <> excluded.day",
                (uid, key, day))
    return (cur.rowcount or 0) > 0

def tick(ts=None, deadline=None):
    """Send due reminders once. `deadline` (time.time() value) stops early in serverless mode; the next tick continues
    (everything not yet claimed is still due, up to REMIND_MAX_LATE_MIN late)."""
    sent = 0
    for u in db.q("SELECT * FROM users WHERE onboarded=1 AND banned=0 AND can_dm=1"):
        if deadline and time.time() > deadline: break
        for r in db.q("SELECT * FROM reminders WHERE user_id=? AND enabled=1", (u["id"],)):
            for t in r["times"].split(","):
                if not util.hhmm_ok(t): continue
                key = f"{r['kind']}@{t}"; st = due(u["tz"], t, key, u["id"], ts)
                if st is None: continue
                if not _claim(u["id"], key, util.local_now(u["tz"], ts).date().isoformat()): continue
                if st != "send": continue
                try: msg = compose(u, r["kind"], ts)
                except Exception as e: log.warning("reminder %s: %s", r["kind"], type(e).__name__); continue
                if not msg: continue
                res = send(u["id"], msg[0], msg[1])
                if res: sent += 1
                else: db.update_user(u["id"], can_dm=0)
                time.sleep(0.03)
    return sent

def loop(interval=30):
    while True:
        try: tick()
        except Exception as e: log.exception("scheduler: %s", C.safe(e))
        time.sleep(interval)

def start():
    """Polling mode only: background scheduler thread. Serverless mode calls tick() from /api/cron/tick instead."""
    t = threading.Thread(target=loop, daemon=True, name="scheduler"); t.start(); return t
