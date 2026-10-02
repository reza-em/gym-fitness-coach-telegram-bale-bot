"""Personalised program: phases, weekly sessions (injury substitutions + session-length fit), warm-up, double progression, PRs."""
import json, math, datetime as dt
import config, db, util, exdata as X

# ---------------------------------------------------------------- phases
def phase_of(week):
    """week (1-based) -> dict(key, name, sets_c, sets_i, reps_c, reps_i, rir, rir_n, factor_hint, note)"""
    if week == 1:
        return dict(key="ramp", name="سازگاری (هفتهٔ 1)", sets_c=2, sets_i=2, reps_c=(10, 12), reps_i=(10, 15), rir="3–4", rir_n=4, load=0.8,
                    note="هفتهٔ اول فقط برای آماده‌شدن مفصل‌ها و تاندون‌ها بعد از 6 ماه استراحته: وزنه سبک، تکنیک تمیز، هیچ‌وقت تا ناتوانی نرو.")
    if week == 2:
        return dict(key="ramp", name="سازگاری (هفتهٔ 2)", sets_c=3, sets_i=2, reps_c=(10, 12), reps_i=(10, 15), rir="3–4", rir_n=3, load=0.9,
                    note="هفتهٔ دوم هم هنوز سازگاری است؛ یک ست بیشتر، ولی همچنان 3–4 تکرار در سنگینی نگه‌دار.")
    if 3 <= week <= 4:
        return dict(key="build", name=f"ساخت حجم (هفتهٔ {week})", sets_c=3, sets_i=3, reps_c=(8, 12), reps_i=(10, 15), rir="2–3", rir_n=2, load=1.0,
                    note="از اینجا اضافه‌بار تدریجی شروع می‌شود: وقتی همهٔ ست‌ها به سقف تکرار رسید، وزنه را بالا ببر.")
    if 5 <= week <= 6:
        return dict(key="build", name=f"ساخت حجم (هفتهٔ {week})", sets_c=4, sets_i=3, reps_c=(8, 12), reps_i=(10, 15), rir="1–2", rir_n=2, load=1.0,
                    note="حجم بالاتر و کمی نزدیک‌تر به ناتوانی؛ غذا و خواب را جدی بگیر.")
    if 7 <= week <= 8:
        return dict(key="intensify", name=f"تشدید (هفتهٔ {week})", sets_c=4, sets_i=3, reps_c=(6, 10), reps_i=(8, 12), rir="1–2", rir_n=1, load=1.0,
                    note="وزنه‌ها سنگین‌تر و تکرارها کمتر. اگر خستگی یا درد مفصل داری، سبک‌ترش کن.")
    if week == 9:
        return dict(key="deload", name="هفتهٔ سبک (دیلود)", sets_c=2, sets_i=2, reps_c=(8, 10), reps_i=(10, 12), rir="4", rir_n=4, load=0.9,
                    note="یک هفتهٔ سبک برای ریکاوری؛ بعدش دور تازه با وزنه‌های بالاتر شروع می‌شود.")
    k = (week - 10) % 7            # next cycle: 4 build, 2 intensify, 1 deload
    if k < 4:
        p = phase_of(5 if k >= 2 else 3); p = dict(p); p["name"] = f"ساخت حجم (هفتهٔ {week})"; return p
    if k < 6:
        p = dict(phase_of(7)); p["name"] = f"تشدید (هفتهٔ {week})"; return p
    p = dict(phase_of(9)); p["name"] = f"هفتهٔ سبک (هفتهٔ {week})"; return p

def deload_phase():
    p = dict(phase_of(9)); p["name"] = "هفتهٔ سبک (دیلود)"; return p

def phase_for_user(u, week):
    if u.get("deload_week") and u["deload_week"] == week: return deload_phase()
    return phase_of(week)

# ---------------------------------------------------------------- calendar
def start_date(u):
    return util.parse_day(u["start_date"]) if u.get("start_date") else util.today(u["tz"])

def week_of(u, day=None):
    day = day or util.today(u["tz"])
    return max(1, (day - start_date(u)).days // 7 + 1)

def week_range(u, week):
    s = start_date(u) + dt.timedelta(days=7 * (week - 1)); return s, s + dt.timedelta(days=6)

def train_days(u):
    return [int(x) for x in (u.get("train_days") or "").split(",") if x != ""]

def n_sessions(u): return len(X.template(u["plan_type"], u.get("sex") or "m"))

def is_train_day(u, day=None):
    day = day or util.today(u["tz"]); return day.weekday() in train_days(u)

# ---------------------------------------------------------------- building sessions
def ex_minutes(eid, sets):
    return sets * (X.EX[eid]["rest"] + 45) / 60.0 + 1.0

def item_scheme(u, ph, eid):
    """-> (sets, lo, hi) for an exercise in a phase. Women: rep ranges +2/+3 (a bit higher reps), upper body one set less once the ramp-up is over
    (maintain / tone), lower body keeps full volume."""
    kind = X.EX[eid]["kind"]
    lo, hi = ph["reps_c"] if kind == "c" else ph["reps_i"]
    sets = ph["sets_c"] if kind == "c" else ph["sets_i"]
    if (u.get("sex") or "m") == "f":
        lo, hi = lo + 2, min(20, hi + 3)
        if X.EX[eid]["grp"] not in X.LOWER_GROUPS and ph["key"] != "ramp" and ph["key"] != "deload": sets = max(2, sets - 1)
    return sets, lo, hi

def build_session(u, week, sidx):
    """-> dict(title, items=[{ex,sets,lo,hi,rir,note}], dropped=[...], notes=[...]). Injury-aware and fitted to the session length."""
    sex = u.get("sex") or "m"; tmpl = X.template(u["plan_type"], sex)
    title, base = tmpl[sidx % len(tmpl)]
    ph = phase_for_user(u, week)
    injuries = {x for x in (u.get("injuries") or "").split(",") if x}
    items, dropped, subs = [], [], []
    for eid, pr in base:
        use = eid
        if X.EX[eid]["avoid"] & injuries:
            use = None
            for a in X.EX[eid]["alts"]:
                if not (X.EX[a]["avoid"] & injuries) and a not in [i["ex"] for i in items] + [b for b, _ in base]:
                    use = a; break
            if use is None: dropped.append(eid); continue
            subs.append((eid, use))
        sets, lo, hi = item_scheme(u, ph, use)
        items.append(dict(ex=use, orig=eid, pr=pr, sets=sets, lo=lo, hi=hi, rir=ph["rir"]))
    budget = max(20, int(u["sess_min"]) - 8)          # 8 min general warm-up
    def total(): return sum(ex_minutes(i["ex"], i["sets"]) for i in items)
    while total() > budget and len(items) > 3:
        worst = max(items, key=lambda i: (i["pr"], items.index(i)))
        items.remove(worst); dropped.append(worst["orig"])
    notes = []
    if subs: notes.append("به‌خاطر محدودیت (آسیب) جایگزین شد: " + "، ".join(f"{X.ex_name(a)} ← {X.ex_name(b)}" for a, b in subs))
    return dict(title=title, items=items, dropped=dropped, notes=notes, minutes=int(total() + 8), phase=ph["name"], rir=ph["rir"])

# ---------------------------------------------------------------- loads
def round_to(w, inc):
    return max(inc, round(w / inc) * inc) if w > 0 else 0

def ref_weight(uid, eid):
    r = db.q1("SELECT w FROM ref_weights WHERE user_id=? AND ex=?", (uid, eid))
    return r["w"] if r else None

def set_ref(uid, eid, w):
    db.ex("INSERT INTO ref_weights(user_id,ex,w) VALUES(?,?,?) ON CONFLICT(user_id,ex) DO UPDATE SET w=excluded.w", (uid, eid, w))

def last_session_sets(uid, eid, before_workout=None):
    """Working sets of the most recent workout containing the exercise (before the given workout id)."""
    r = db.q1("SELECT workout_id FROM sets WHERE user_id=? AND ex=? AND (? IS NULL OR workout_id<?) ORDER BY id DESC LIMIT 1",
              (uid, eid, before_workout, before_workout))
    if not r: return []
    return db.q("SELECT * FROM sets WHERE user_id=? AND ex=? AND workout_id=? ORDER BY setno", (uid, eid, r["workout_id"]))

def suggest(u, eid, item, week, before_workout=None):
    """Double progression. -> dict(w, reps (target text), why, last (text or None)). w may be None when nothing is known."""
    inc = X.EX[eid]["inc"]; ph = phase_for_user(u, week); lo, hi = item["lo"], item["hi"]
    last = last_session_sets(u["id"], eid, before_workout)
    out = dict(w=None, why="", last=None)
    if not last:
        ref = ref_weight(u["id"], eid)
        if ref is None and item.get("orig") and item["orig"] != eid: ref = ref_weight(u["id"], item["orig"])
        if ref is None:
            out["why"] = "وزنهٔ شروع را خودت انتخاب کن (سبک شروع کن، 3–4 تکرار در سنگینی نگه‌دار)."; return out
        w = round_to(ref * ph["load"], inc)
        out.update(w=w, why=f"از وزنهٔ مرجع {util.fnum(ref)} کیلو با ضریب سازگاری {int(ph['load']*100)}٪ شروع می‌کنیم."); return out
    top = max(s["w"] for s in last)
    at = [s for s in last if s["w"] == top]
    desc = " | ".join(f"{util.fnum(s['w'])}×{s['reps']}" for s in last)
    out["last"] = desc
    planned = item["sets"]
    reps = [s["reps"] for s in at]
    if ph["key"] == "deload":
        out.update(w=round_to(top * 0.9, inc), why="هفتهٔ سبک: 10٪ سبک‌تر از آخرین بار."); return out
    if len(at) >= min(planned, 2) and min(reps) >= hi:
        out.update(w=top + inc, why=f"همهٔ ست‌ها به سقف {hi} تکرار رسید ← +{util.fnum(inc)} کیلو و تکرار از {lo} شروع."); return out
    if sum(reps) / len(reps) < lo - 0.01:
        out.update(w=max(inc, top - inc), why=f"میانگین تکرار زیر {lo} بود ← {util.fnum(inc)} کیلو سبک‌تر تا تکرارها به بازه برگردد."); return out
    out.update(w=top, why=f"همین وزنه؛ هدف: هر ست یک تکرار بیشتر (تا {hi}).")
    return out

def warmup_sets(w, inc, heavy=True):
    """Warm-up ramp for a working weight: -> list of (weight, reps)."""
    if not w: return []
    steps = [(0.5, 8), (0.7, 5)] + ([(0.85, 3)] if heavy and w >= 12 else [])
    out = []
    for f, r in steps:
        ww = round_to(w * f, inc) if w * f >= inc else 0
        if ww and ww < w and (not out or ww > out[-1][0]): out.append((ww, r))
    return out

# ---------------------------------------------------------------- PRs
def e1rm(w, reps):
    reps = max(1, min(int(reps), 12))
    return w * (1 + reps / 30.0) if reps > 1 else float(w)

def record_set(u, workout_id, eid, setno, w, reps):
    """Insert a set; -> list of PR messages (empty when none). First ever set of an exercise is a baseline, not a PR."""
    today = util.today(u["tz"]).isoformat()
    had = db.val("SELECT COUNT(*) FROM sets WHERE user_id=? AND ex=?", (u["id"], eid), 0) > 0
    db.ex("INSERT INTO sets(user_id,workout_id,ex,setno,w,reps,ts,day) VALUES(?,?,?,?,?,?,?,?)", (u["id"], workout_id, eid, setno, w, reps, util.now(), today))
    msgs = []
    est = e1rm(w, reps)
    for kind, v in (("e1rm", est), ("max_w", float(w) if reps >= 3 else 0.0)):
        if v <= 0: continue
        cur = db.q1("SELECT val FROM prs WHERE user_id=? AND ex=? AND kind=?", (u["id"], eid, kind))
        if cur is None or v > cur["val"] + 1e-9:
            db.ex("INSERT INTO prs(user_id,ex,kind,val,w,reps,day) VALUES(?,?,?,?,?,?,?) ON CONFLICT(user_id,ex,kind) DO UPDATE SET val=excluded.val,w=excluded.w,reps=excluded.reps,day=excluded.day",
                  (u["id"], eid, kind, v, w, reps, today))
            if cur is not None and had:
                msgs.append((kind, f"🏆 رکورد جدید در {X.ex_name(eid)}: " + (f"1RM تخمینی {util.fnum(est)} کیلو" if kind == "e1rm" else f"سنگین‌ترین وزنهٔ {util.fnum(w)} کیلو (حداقل 3 تکرار)")))
    # one message is enough: prefer the heaviest-weight PR text, else e1rm
    if len(msgs) > 1: msgs = [next((m for m in msgs if m[0] == "max_w"), msgs[0])]
    return [m for _k, m in msgs]

def recompute_prs(uid, eid):
    """After an undo: rebuild PRs of one exercise from the logged sets."""
    db.ex("DELETE FROM prs WHERE user_id=? AND ex=?", (uid, eid))
    best_e = best_w = None
    for s in db.q("SELECT * FROM sets WHERE user_id=? AND ex=? ORDER BY id", (uid, eid)):
        est = e1rm(s["w"], s["reps"])
        if best_e is None or est > best_e[0]: best_e = (est, s)
        if s["reps"] >= 3 and (best_w is None or s["w"] > best_w[0]): best_w = (s["w"], s)
    for kind, b in (("e1rm", best_e), ("max_w", best_w)):
        if b: db.ex("INSERT INTO prs(user_id,ex,kind,val,w,reps,day) VALUES(?,?,?,?,?,?,?)", (uid, eid, kind, b[0], b[1]["w"], b[1]["reps"], b[1]["day"]))

def parse_set_text(text, default_w=None):
    """'20x10', '20 10', '20*10', '20×10', '10' (reps at the current weight) -> (w, reps) or None."""
    import re
    s = util.norm(text).lower().replace("×", "x").replace("*", "x").replace("*", "x")
    m = re.fullmatch(r"(\d{1,3}(?:\.\d{1,2})?)\s*(?:x|\s|/|-)\s*(\d{1,3})", s)
    if m:
        w, r = float(m.group(1)), int(m.group(2))
    elif re.fullmatch(r"\d{1,3}", s) and default_w:
        w, r = float(default_w), int(s)
    else:
        return None
    if not (0 < w <= 500 and 1 <= r <= 100): return None
    return w, r

# ---------------------------------------------------------------- volume / stats
def workout_volume(uid, wid):
    return db.val("SELECT SUM(w*reps) FROM sets WHERE user_id=? AND workout_id=?", (uid, wid), 0) or 0

def week_workouts_done(u, week):
    return db.q("SELECT * FROM workouts WHERE user_id=? AND week=? AND finished=1 ORDER BY id", (u["id"], week))
