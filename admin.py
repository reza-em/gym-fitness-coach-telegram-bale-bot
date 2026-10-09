"""🛠 Admin panel (/admin or the main-menu button, admins only): stats, users (list, detail, message, block, reset onboarding),
search, broadcast, admins management, CSV export.
Owner (super-admin, can never be removed): Telegram = OWNER_ID env; Bale = whoever redeems the one-time /claim code, which is
written to an owner-only file next to the database (never to the log). Other admins live in the `admins` table (owner adds them).
Broadcasts are resumable: a row in `broadcasts` with a cursor (last user id sent). Each step sends until a deadline, so the work
is spread over the confirm click, the panel's refresh button and every cron tick / polling scheduler pass (serverless-safe)."""
import os, io, csv, re, time, secrets, logging, datetime as dt
import config, db, util
import core as C, ui
from core import btn, kb, send, show
from util import esc, fnum
from plat import PLAT

log = logging.getLogger("bot")
TZ = "Asia/Tehran"
PAGE = 8
BC_STEP_S = 8.0                 # seconds of broadcasting inside an interactive request (webhook must answer quickly)
BLOCKED_TEXT = "🙏 متأسفیم، دسترسی شما به این ربات توسط مدیر محدود شده است. اگر فکر می‌کنید اشتباهی رخ داده، با پشتیبانی تماس بگیرید."
NOT_ADMIN_TEXT = "این بخش فقط برای ادمین‌ها و مالک ربات است."
BACK_PANEL = "◀️ پنل ادمین"

# ---------------------------------------------------------------- owner claim (Bale)
def claim_file():
    return os.path.join(os.path.dirname(os.path.abspath(PLAT.db_path)), "owner_claim_code%s.txt" % PLAT.suffix)

def ensure_claim_code():
    """Bale without an owner: make a one-time claim code and store it in an owner-only file (0600). Never logged."""
    if not PLAT.claim: return None
    if db.owner_id(): return None
    code = db.meta_get("claim_code")
    if not code:
        code = "-".join(secrets.token_hex(2).upper() for _ in range(3)); db.meta_set("claim_code", code)
    path = claim_file()
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f: f.write("send this to the %s bot once to become its owner:\n/claim %s\n" % (PLAT.name, code))
        os.chmod(path, 0o600)
        log.info("no owner yet: the one-time owner claim code is in %s (owner-only file; send '/claim <code>' to the bot)", path)
    except OSError as e:
        log.warning("could not write the claim code file (%s); the code is in the database meta table (claim_code)", type(e).__name__)
    return code

def try_claim(uid, code):
    if not C.rate_ok(("claim", uid), 5, 3600): return "throttled"
    real = db.meta_get("claim_code")
    if not real or db.owner_id() or (code or "").strip().upper() != real: return "bad"
    db.update_user(uid, is_admin=1); db.meta_set("owner_id", uid); db.meta_set("claim_code", None)
    try: os.remove(claim_file())
    except OSError: pass
    return "ok"

def sync_owner(uid):
    """Telegram: the numeric owner id is admin automatically."""
    if not PLAT.claim and config.OWNER_ID and uid == config.OWNER_ID:
        u = db.get_user(uid)
        if u and not u["is_admin"]: db.update_user(uid, is_admin=1)

# ---------------------------------------------------------------- helpers
def _ts_day_start(days_ago=0):
    d = util.local_now(TZ).replace(hour=0, minute=0, second=0, microsecond=0) - dt.timedelta(days=days_ago)
    return int(d.timestamp())

def _date(ts):
    if not ts: return "—"
    l = util.local_now(TZ, ts); return f"{util.jdate(l.date(), True)} {l:%H:%M}"

def _ago(ts):
    if not ts: return "—"
    s = max(0, util.now() - int(ts))
    if s < 60: return "همین حالا"
    if s < 3600: return f"{s // 60} دقیقه پیش"
    if s < 86400: return f"{s // 3600} ساعت پیش"
    return f"{s // 86400} روز پیش"

def _who(u, link=True):
    name = esc(u.get("name") or "بی‌نام")
    un = f" @{esc(u['username'])}" if u.get("username") else ""
    return f"{name}{un}"

def _parse_id(s):
    s = util.norm(s)
    return int(s) if re.fullmatch(r"\d{3,15}", s) else None

def _goal(u):
    g, w = u.get("goal_w") or u.get("target_w"), u.get("weight")
    if not g or not w: return "unknown"
    return "gain" if g - w >= 0.5 else ("lose" if g - w <= -0.5 else "keep")

GOAL_FA = {"gain": "📈 افزایش وزن", "lose": "📉 کاهش وزن", "keep": "⚖️ حفظ وزن", "unknown": "❔ نامشخص"}

def _back(rows=None, data="ad:menu", label=BACK_PANEL): return kb(ui.with_back(rows or [], data, label))

def _bc_running(): return db.q1("SELECT * FROM broadcasts WHERE status='run' ORDER BY id LIMIT 1")

def _recipients_sql(): return "FROM users WHERE onboarded=1 AND banned=0 AND can_dm=1"

# ---------------------------------------------------------------- screens
def panel(uid, mid=None):
    if not db.is_admin(uid): return send(uid, NOT_ADMIN_TEXT)
    n = db.val("SELECT COUNT(*) FROM users", (), 0); ob = db.val("SELECT COUNT(*) FROM users WHERE onboarded=1", (), 0)
    new1 = db.val("SELECT COUNT(*) FROM users WHERE created>=?", (_ts_day_start(),), 0)
    role = "👑 مالک" if db.is_owner(uid) else "👮 ادمین"
    txt = (f"🛠 <b>پنل ادمین</b> ({PLAT.label}) — {role}\n"
           f"👥 کاربران: {n} (ثبت‌نام کامل: {ob}) | 🆕 امروز: {new1}")
    rows = [[btn("📊 آمار", "ad:st"), btn("👥 کاربران", "ad:ul:0")],
            [btn("🔎 جستجوی کاربر", "ad:sr"), btn("📢 پیام همگانی", "ad:bc")]]
    bc = _bc_running()
    if bc: txt += f"\n📢 ارسال همگانی در جریان: {bc['sent'] + bc['failed']} از {bc['total']}"; rows.append([btn("📢 وضعیت ارسال همگانی", "ad:bcs")])
    rows.append(([btn("👮 مدیریت ادمین‌ها", "ad:am")] if db.is_owner(uid) else []) + [btn("📥 خروجی CSV کاربران", "ad:csv")])
    rows.append(ui.menu_row())
    return show(uid, mid, txt, kb(rows))

def stats_text():
    import programs_db as PDB
    n = db.val("SELECT COUNT(*) FROM users", (), 0)
    ob = db.val("SELECT COUNT(*) FROM users WHERE onboarded=1", (), 0)
    new1 = db.val("SELECT COUNT(*) FROM users WHERE created>=?", (_ts_day_start(),), 0)
    new7 = db.val("SELECT COUNT(*) FROM users WHERE created>=?", (_ts_day_start(6),), 0)
    d7 = (util.today(TZ) - dt.timedelta(days=6)).isoformat()
    act1 = db.val("SELECT COUNT(*) FROM activity WHERE day=?", (util.today(TZ).isoformat(),), 0)
    act7 = db.val("SELECT COUNT(DISTINCT user_id) FROM activity WHERE day>=?", (d7,), 0)
    banned = db.val("SELECT COUNT(*) FROM users WHERE banned=1", (), 0)
    nodm = db.val("SELECT COUNT(*) FROM users WHERE can_dm=0", (), 0)
    admins = len(admin_ids())
    wo = db.val("SELECT COUNT(*) FROM workouts WHERE finished=1", (), 0); st = db.val("SELECT COUNT(*) FROM sets", (), 0)
    sex = {"m": 0, "f": 0}; goals = {k: 0 for k in GOAL_FA}; cats = {c: 0 for c in PDB.CATS}; cats[None] = 0
    for u in db.q("SELECT * FROM users WHERE onboarded=1"):
        sex["f" if u["sex"] == "f" else "m"] += 1; goals[_goal(u)] += 1
        try: c = PDB.category(u)
        except Exception: c = None
        cats[c if c in cats else None] += 1
    pct = lambda a, b: f"{round(100.0 * a / b)}٪" if b else "—"
    L = [f"📊 <b>آمار ربات</b> ({PLAT.label})", "",
         f"👥 کل کاربران: <b>{n}</b>", f"🆕 جدید امروز: {new1} | ۷ روز اخیر: {new7}",
         f"🔥 فعال امروز: {act1} | ۷ روز اخیر: {act7}",
         f"✅ ثبت‌نام کامل: {ob} از {n} ({pct(ob, n)})", "",
         "<b>جنسیت</b> (ثبت‌نام کامل):", f"👨 مرد: {sex['m']} | 👩 زن: {sex['f']}", "",
         "<b>هدف</b>:", " | ".join(f"{GOAL_FA[k]}: {v}" for k, v in goals.items() if v or k != "unknown"), "",
         "<b>وضعیت بدنی</b>:", " | ".join(f"{PDB.CAT_EMOJI[c]} {PDB.CAT_FA[c]}: {cats[c]}" for c in PDB.CATS) + (f" | ❔ نامشخص: {cats[None]}" if cats[None] else ""), "",
         f"🏋️ جلسه‌های تمام‌شده: {wo} | ست‌ها: {st}",
         f"🚫 مسدود: {banned} | 📵 پیام نمی‌گیرند: {nodm} | 👮 ادمین‌ها: {admins}"]
    return "\n".join(L)

def users_page(uid, mid, page):
    n = db.val("SELECT COUNT(*) FROM users", (), 0)
    pages = max(1, (n + PAGE - 1) // PAGE); page = max(0, min(page, pages - 1))
    rows_db = db.q("SELECT id,username,name,created,last_seen,onboarded,banned FROM users ORDER BY last_seen DESC, id DESC LIMIT ? OFFSET ?", (PAGE, page * PAGE))
    L = [f"👥 <b>کاربران</b> — {n} نفر (صفحهٔ {page + 1} از {pages}، مرتب بر اساس آخرین فعالیت)", ""]
    rows = []
    for i, u in enumerate(rows_db, page * PAGE + 1):
        flag = "🚫 " if u["banned"] else ("" if u["onboarded"] else "⏳ ")
        L.append(f"{i}. {flag}{_who(u)} · <code>{u['id']}</code>\n    📅 عضویت: {_date(u['created'])} | 🕒 {_ago(u['last_seen'])}")
        rows.append([btn(f"{i}. {flag}{(u['name'] or 'بی‌نام')[:24]}" + (f" @{u['username']}"[:20] if u["username"] else ""), f"ad:u:{u['id']}:{page}")])
    nav = []
    if page + 1 < pages: nav.append(btn("⬅️ بعدی", f"ad:ul:{page + 1}"))
    if page > 0: nav.append(btn("قبلی ➡️", f"ad:ul:{page - 1}"))
    if nav: rows.append(nav)
    if not rows_db: L.append("هنوز کاربری نیست.")
    L.append("\n⏳ = ثبت‌نام ناتمام | 🚫 = مسدود")
    return show(uid, mid, "\n".join(L), _back(rows))

def user_detail_text(t):
    import programs_db as PDB
    tid = t["id"]
    L = [f"👤 <b>{_who(t)}</b>", f"🆔 <code>{tid}</code>"]
    tags = []
    if db.is_owner(tid): tags.append("👑 مالک")
    elif db.is_admin(tid): tags.append("👮 ادمین")
    if t["banned"]: tags.append("🚫 مسدود")
    if not t["can_dm"]: tags.append("📵 ربات را بسته/پیام نمی‌گیرد")
    tags.append("✅ ثبت‌نام کامل" if t["onboarded"] else "⏳ ثبت‌نام ناتمام")
    L.append(" | ".join(tags))
    L.append(f"📅 عضویت: {_date(t['created'])}\n🕒 آخرین فعالیت: {_date(t['last_seen'])} ({_ago(t['last_seen'])})")
    if t["onboarded"]:
        cur = ui.current_weight(tid)
        try: cat = PDB.category(t, cur)
        except Exception: cat = None
        L += ["", "<b>پروفایل</b>",
              f"{config.sx(t['sex'])['label']} | سن {t['age'] or '—'} | قد {fnum(t['height']) if t['height'] else '—'} cm",
              f"⚖️ شروع {fnum(t['start_w']) if t['start_w'] else '—'} ← فعلی {fnum(cur) if cur else '—'} ← هدف {fnum(t['target_w']) if t['target_w'] else '—'} (بلندمدت {fnum(t['goal_w']) if t['goal_w'] else '—'})",
              f"🎯 {GOAL_FA[_goal(dict(t, weight=cur or t['weight']))]}" + (f" | {PDB.CAT_EMOJI[cat]} {PDB.CAT_FA[cat]}" if cat else ""),
              f"🏋️ {t['days_pw']} روز در هفته ({t['plan_type']})"]
    ws = db.q("SELECT day, kg FROM weights WHERE user_id=? ORDER BY day, id", (tid,))
    if ws:
        a, b = ws[0], ws[-1]; dlt = b["kg"] - a["kg"]
        L += ["", "<b>روند وزن</b>", f"{len(ws)} ثبت | {fnum(a['kg'])} ({util.jdate(util.parse_day(a['day']))}) ← {fnum(b['kg'])} ({util.jdate(util.parse_day(b['day']))}) = {'+' if dlt >= 0 else ''}{fnum(dlt)} کیلو"]
    nwo = db.val("SELECT COUNT(*) FROM workouts WHERE user_id=? AND finished=1", (tid,), 0)
    lwo = db.val("SELECT MAX(day) FROM workouts WHERE user_id=? AND finished=1", (tid,))
    nact = db.val("SELECT COUNT(*) FROM activity WHERE user_id=?", (tid,), 0)
    L += ["", "<b>فعالیت</b>", f"🏋️ جلسه‌های تمام‌شده: {nwo}" + (f" (آخرین: {util.jdate(util.parse_day(lwo))})" if lwo else ""),
          f"📆 روزهای فعال: {nact}"]
    return "\n".join(L)

def user_detail(uid, mid, tid, back="0"):
    t = db.get_user(tid)
    if not t: return show(uid, mid, "کاربر پیدا نشد.", _back())
    rows = [[btn("✉️ پیام خصوصی", f"ad:pm:{tid}:{back}")]]
    if not db.is_owner(tid) and tid != uid:
        rows[0].append(btn("✅ رفع مسدودی", f"ad:ub:{tid}:{back}") if t["banned"] else btn("🚫 مسدودکردن", f"ad:bl:{tid}:{back}"))
    rows.append([btn("🔄 ریست ثبت‌نام", f"ad:rs:{tid}:{back}")])
    if db.is_owner(uid) and not db.is_owner(tid):
        rows[-1].append(btn("❌ حذف از ادمین‌ها", f"ad:ar:{tid}:{back}") if db.is_admin(tid) else btn("👮 ادمین‌کردن", f"ad:aa2:{tid}:{back}"))
    back_data = f"ad:ul:{back}" if back.isdigit() else "ad:menu"
    return show(uid, mid, user_detail_text(t), _back(rows, back_data, "◀️ فهرست کاربران" if back.isdigit() else BACK_PANEL))

def search(uid, text):
    q = util.norm(text).strip()
    if not q: return send(uid, "عبارت جستجو خالی است.")
    i = _parse_id(q)
    if i: res = db.q("SELECT * FROM users WHERE id=?", (i,))
    elif q.startswith("@"): res = db.q("SELECT * FROM users WHERE lower(username) LIKE ? ORDER BY last_seen DESC LIMIT 10", (q[1:].lower() + "%",))
    else:
        like = "%" + q.lower() + "%"
        res = db.q("SELECT * FROM users WHERE lower(name) LIKE ? OR lower(username) LIKE ? ORDER BY last_seen DESC LIMIT 10", (like, like))
    db.set_await(uid, None)
    if not res:
        return send(uid, f"🔎 کاربری با «{esc(q)}» پیدا نشد.", _back([[btn("🔎 جستجوی دوباره", "ad:sr")]]))
    rows = [[btn(f"{'🚫 ' if u['banned'] else ''}{(u['name'] or 'بی‌نام')[:24]}" + (f" @{u['username']}"[:20] if u["username"] else "") + f" · {u['id']}", f"ad:u:{u['id']}:s")] for u in res]
    rows.append([btn("🔎 جستجوی دوباره", "ad:sr")])
    return send(uid, f"🔎 نتیجهٔ جستجو برای «{esc(q)}»: {len(res)} کاربر", _back(rows))

# ---------------------------------------------------------------- admins
def admin_ids():
    ids = {r["user_id"] for r in db.q("SELECT user_id FROM admins")} | {r["id"] for r in db.q("SELECT id FROM users WHERE is_admin=1")}
    o = db.owner_id()
    if o: ids.add(o)
    return ids

def admins_screen(uid, mid=None, note=""):
    o = db.owner_id()
    L = ["👮 <b>مدیریت ادمین‌ها</b>", ""]
    rows = []
    for aid in sorted(admin_ids(), key=lambda x: (x != o, x)):
        u = db.get_user(aid) or {"id": aid, "name": None, "username": None}
        if aid == o: L.append(f"👑 {_who(u)} · <code>{aid}</code> — مالک (قابل حذف نیست)")
        else:
            L.append(f"👮 {_who(u)} · <code>{aid}</code>"); rows.append([btn(f"❌ حذف {(u.get('name') or str(aid))[:24]}", f"ad:ar:{aid}:am")])
    rows.append([btn("➕ افزودن ادمین", "ad:aa")])
    if note: L += ["", note]
    return show(uid, mid, "\n".join(L), _back(rows))

def add_admin(uid, tid):
    if not db.is_owner(uid): return NOT_ADMIN_TEXT
    if db.is_admin(tid): return "این کاربر از قبل ادمین است."
    db.ex("INSERT OR IGNORE INTO admins(user_id, added_by, ts) VALUES(?,?,?)", (tid, uid, util.now()))
    if db.get_user(tid): send(tid, "👮 شما ادمین ربات شدید. برای ورود به پنل: /admin")
    return f"✅ کاربر <code>{tid}</code> ادمین شد."

def remove_admin(uid, tid):
    if not db.is_owner(uid): return NOT_ADMIN_TEXT
    if db.is_owner(tid): return "مالک ربات قابل حذف نیست."
    db.ex("DELETE FROM admins WHERE user_id=?", (tid,))
    if db.get_user(tid): db.update_user(tid, is_admin=0)
    return f"✅ کاربر <code>{tid}</code> از ادمین‌ها حذف شد."

def _forwarded_id(msg):
    for m in (msg, (msg or {}).get("reply_to_message") or {}):
        if not m: continue
        f = m.get("forward_from") or ((m.get("forward_origin") or {}).get("sender_user"))
        if f and f.get("id") and not f.get("is_bot"): return f["id"]
    return None

# ---------------------------------------------------------------- broadcast (resumable, chunked)
def bc_start(uid, text):
    total = db.val("SELECT COUNT(*) " + _recipients_sql(), (), 0)
    cur = db.ex("INSERT INTO broadcasts(admin_id,text,created,status,cursor,sent,failed,total) VALUES(?,?,?,'run',0,0,0,?)", (uid, text, util.now(), total))
    return cur.lastrowid or db.val("SELECT MAX(id) FROM broadcasts", (), 0)

def broadcast_step(deadline=None, max_msgs=None):
    """Send pending broadcast messages until `deadline` (time.time()) or `max_msgs`. Safe to run concurrently
    (cron tick + refresh click): each recipient is claimed by advancing the cursor with a compare-and-set first,
    so nobody gets a message twice. -> number of messages attempted."""
    done = 0
    while True:
        bc = _bc_running()
        if not bc: return done
        nxt = db.q("SELECT id " + _recipients_sql() + " AND id>? ORDER BY id LIMIT 25", (bc["cursor"],))
        if not nxt:
            if (db.ex("UPDATE broadcasts SET status='done', finished=? WHERE id=? AND status='run'", (util.now(), bc["id"])).rowcount or 0) > 0:
                bc = db.q1("SELECT * FROM broadcasts WHERE id=?", (bc["id"],))
                send(bc["admin_id"], f"📢 ارسال همگانی تمام شد.\n✅ موفق: {bc['sent']} | ❌ ناموفق: {bc['failed']} (از {bc['total']})", _back())
            continue
        cursor = bc["cursor"]
        for r in nxt:
            if (deadline and time.time() > deadline) or (max_msgs is not None and done >= max_msgs): return done
            if (db.ex("UPDATE broadcasts SET cursor=? WHERE id=? AND cursor=? AND status='run'", (r["id"], bc["id"], cursor)).rowcount or 0) == 0:
                break                       # another worker advanced it (or it was cancelled): reload
            cursor = r["id"]; done += 1
            res = send(r["id"], bc["text"], html=False)
            if res: db.ex("UPDATE broadcasts SET sent=sent+1 WHERE id=?", (bc["id"],))
            else:
                db.ex("UPDATE broadcasts SET failed=failed+1 WHERE id=?", (bc["id"],)); db.update_user(r["id"], can_dm=0)
            time.sleep(1.0 / config.BROADCAST_PER_SEC)

def bc_status(uid, mid=None):
    bc = _bc_running() or db.q1("SELECT * FROM broadcasts ORDER BY id DESC LIMIT 1")
    if not bc: return show(uid, mid, "هنوز پیام همگانی ارسال نشده است.", _back([[btn("📢 پیام همگانی جدید", "ad:bc")]]))
    st = {"run": "⏳ در حال ارسال", "done": "✅ تمام شد", "stop": "⏹ متوقف شد"}.get(bc["status"], bc["status"])
    n = bc["sent"] + bc["failed"]; pct = int(100 * n / bc["total"]) if bc["total"] else 100
    preview = bc["text"] if len(bc["text"]) <= 300 else bc["text"][:300] + "…"
    txt = (f"📢 <b>پیام همگانی #{bc['id']}</b> — {st}\n{'🟩' * (pct // 10)}{'⬜' * (10 - pct // 10)} {pct}٪\n"
           f"✅ موفق: {bc['sent']} | ❌ ناموفق: {bc['failed']} | کل: {bc['total']}\n🕒 شروع: {_date(bc['created'])}\n\n{esc(preview)}")
    if bc["status"] == "run":
        txt += "\n\nارسال در پس‌زمینه ادامه دارد (هر چند دقیقه یک بخش). «بروزرسانی» هم یک بخش دیگر می‌فرستد."
        rows = [[btn("🔄 بروزرسانی", "ad:bcs"), btn("⏹ توقف", "ad:bcx")]]
    else: rows = [[btn("📢 پیام همگانی جدید", "ad:bc")]]
    return show(uid, mid, txt, _back(rows))

# ---------------------------------------------------------------- CSV
CSV_COLS = ["id", "username", "name", "joined", "last_active", "onboarded", "sex", "age", "height_cm", "weight", "start_w", "target_w", "goal_w",
            "body_category", "days_per_week", "plan", "workouts_done", "banned", "can_dm", "admin"]

def users_csv():
    import programs_db as PDB
    wo = {r["user_id"]: r["n"] for r in db.q("SELECT user_id, COUNT(*) n FROM workouts WHERE finished=1 GROUP BY user_id")}
    adm = admin_ids()
    iso = lambda ts: util.local_now(TZ, ts).strftime("%Y-%m-%d %H:%M") if ts else ""
    buf = io.StringIO(); w = csv.writer(buf); w.writerow(CSV_COLS)
    for u in db.q("SELECT * FROM users ORDER BY id"):
        try: cat = PDB.category(u) if u["onboarded"] else None
        except Exception: cat = None
        w.writerow([u["id"], u["username"] or "", u["name"] or "", iso(u["created"]), iso(u["last_seen"]), u["onboarded"], u["sex"], u["age"] or "",
                    u["height"] or "", u["weight"] or "", u["start_w"] or "", u["target_w"] or "", u["goal_w"] or "", cat or "", u["days_pw"], u["plan_type"],
                    wo.get(u["id"], 0), u["banned"], u["can_dm"], int(u["id"] in adm)])
    return ("\ufeff" + buf.getvalue()).encode("utf-8")          # BOM: Excel opens Persian text correctly

# ---------------------------------------------------------------- text input
def on_text(uid, aw, d, text, msg=None):
    if not db.is_admin(uid): db.set_await(uid, None); return False
    t = (text or "").strip()
    if aw == "a_bc":
        if not t: return send(uid, "متن خالی است.")
        db.set_await(uid, "a_bc2", {"text": t})
        n = db.val("SELECT COUNT(*) " + _recipients_sql(), (), 0)
        return send(uid, f"📢 پیش‌نمایش پیام همگانی:\n\n{t}\n\nبه {n} کاربر ارسال شود؟", kb([[btn("✅ ارسال", "ad:bcgo"), btn("❌ لغو", "ad:menu")]]), html=False)
    if aw == "a_sr": return search(uid, t)
    if aw == "a_pm":
        tid = d.get("to")
        if not t: return send(uid, "متن خالی است.")
        db.set_await(uid, None)
        res = send(tid, "📩 <b>پیام از طرف ادمین ربات</b>\n\n" + esc(t))
        back = _back([[btn("👤 بازگشت به کاربر", f"ad:u:{tid}:{d.get('b', '0')}")]])
        return send(uid, "✅ پیام ارسال شد." if res else "❌ ارسال نشد (کاربر ربات را بسته یا هنوز استارت نکرده).", back)
    if aw == "a_add":
        if not db.is_owner(uid): db.set_await(uid, None); return send(uid, NOT_ADMIN_TEXT)
        tid = _forwarded_id(msg) or _parse_id(t)
        if not tid and t.startswith("@"):
            tid = db.val("SELECT id FROM users WHERE lower(username)=?", (t[1:].lower(),))
            if not tid: return send(uid, "کاربری با این نام‌کاربری ربات را استارت نکرده. شناسهٔ عددی را بفرست یا یک پیامش را فوروارد کن.")
        if not tid:
            hidden = msg and (msg.get("forward_sender_name") or (msg.get("forward_origin") or {}).get("type") == "hidden_user")
            return send(uid, "شناسهٔ این کاربر مخفی است (تنظیمات حریم خصوصی فوروارد). شناسهٔ عددی‌اش را بفرست." if hidden
                        else "شناسهٔ عددی، @نام‌کاربری یا یک پیام فورواردشده از آن کاربر را بفرست (لغو: /cancel).")
        db.set_await(uid, None)
        return admins_screen(uid, None, add_admin(uid, tid))
    return False

# ---------------------------------------------------------------- callbacks (every one requires admin)
def callback(uid, mid, p):
    if not db.is_admin(uid): return send(uid, NOT_ADMIN_TEXT)
    k = p[1] if len(p) > 1 else "menu"
    arg = lambda i, default=None: p[i] if len(p) > i else default
    if k == "menu": db.set_await(uid, None); return panel(uid, mid)
    if k == "st": return show(uid, mid, stats_text(), _back([[btn("🔄 بروزرسانی", "ad:st")]]))
    if k == "ul": return users_page(uid, mid, int(arg(2, "0")) if str(arg(2, "0")).isdigit() else 0)
    if k == "u":
        tid = _parse_id(arg(2, ""))
        return user_detail(uid, mid, tid, arg(3, "0")) if tid else panel(uid, mid)
    if k == "sr":
        db.set_await(uid, "a_sr")
        return show(uid, mid, "🔎 شناسهٔ عددی، @نام‌کاربری یا بخشی از نام کاربر را بفرست (لغو: /cancel):", _back())
    if k in ("pm", "bl", "ub", "rs", "rs2", "aa2"):
        tid = _parse_id(arg(2, "")); back = arg(3, "0")
        t = db.get_user(tid) if tid else None
        if not t: return show(uid, mid, "کاربر پیدا نشد.", _back())
        if k == "pm":
            db.set_await(uid, "a_pm", {"to": tid, "b": back})
            return show(uid, mid, f"✉️ متن پیام برای {_who(t)} را بفرست (لغو: /cancel):", _back([[btn("👤 بازگشت به کاربر", f"ad:u:{tid}:{back}")]]))
        if k in ("bl", "ub"):
            if db.is_owner(tid) or tid == uid or (db.is_admin(tid) and not db.is_owner(uid)):
                return show(uid, mid, "⛔️ این کاربر را نمی‌توانی مسدود کنی.", _back([[btn("👤 بازگشت به کاربر", f"ad:u:{tid}:{back}")]]))
            db.update_user(tid, banned=1 if k == "bl" else 0)
            log.info("admin %s %s user %s", uid, "blocked" if k == "bl" else "unblocked", tid)
            return user_detail(uid, mid, tid, back)
        if k == "rs":
            return show(uid, mid, f"🔄 ثبت‌نام {_who(t)} ریست شود؟ داده‌هایش (وزن، تمرین‌ها) پاک نمی‌شود؛ دفعهٔ بعد که پیام بدهد دوباره سؤال‌های ثبت‌نام را جواب می‌دهد.",
                        kb([[btn("✅ بله، ریست کن", f"ad:rs2:{tid}:{back}"), btn("❌ لغو", f"ad:u:{tid}:{back}")]]))
        if k == "rs2":
            db.update_user(tid, onboarded=0, ack=0, awaiting=None, adata=None)
            log.info("admin %s reset onboarding of %s", uid, tid)
            return user_detail(uid, mid, tid, back)
        if k == "aa2":
            note = add_admin(uid, tid)
            return user_detail(uid, mid, tid, back) if db.is_owner(uid) else show(uid, mid, note, _back())
    if k == "bc":
        if _bc_running(): return bc_status(uid, mid)
        db.set_await(uid, "a_bc")
        n = db.val("SELECT COUNT(*) " + _recipients_sql(), (), 0)
        return show(uid, mid, f"📢 متن پیام همگانی را بفرست (به {n} کاربر با ثبت‌نام کامل می‌رسد؛ لغو: /cancel):", _back())
    if k == "bcgo":
        aw, d = db.get_await(uid)
        if aw != "a_bc2" or not d.get("text"): return panel(uid, mid)
        if _bc_running(): return bc_status(uid, mid)
        db.set_await(uid, None); bc_start(uid, d["text"])
        broadcast_step(deadline=time.time() + BC_STEP_S)
        return bc_status(uid, mid)
    if k == "bcs":
        if _bc_running(): broadcast_step(deadline=time.time() + BC_STEP_S)
        return bc_status(uid, mid)
    if k == "bcx":
        db.ex("UPDATE broadcasts SET status='stop', finished=? WHERE status='run'", (util.now(),))
        return bc_status(uid, mid)
    if k == "csv":
        data = users_csv()
        C.send_document(uid, f"users_{PLAT.name}_{util.today(TZ).isoformat()}.csv", data, f"📥 خروجی کاربران ({PLAT.label}) — {db.val('SELECT COUNT(*) FROM users', (), 0)} نفر", mime="text/csv")
        return panel(uid, None)
    if not db.is_owner(uid) and k in ("am", "aa", "ar"): return show(uid, mid, "⛔️ مدیریت ادمین‌ها فقط برای مالک ربات است.", _back())
    if k == "am": db.set_await(uid, None); return admins_screen(uid, mid)
    if k == "aa":
        db.set_await(uid, "a_add")
        return show(uid, mid, "➕ شناسهٔ عددی یا @نام‌کاربری کاربر را بفرست، یا یک پیام از او را اینجا فوروارد کن (لغو: /cancel).\n"
                              "(کاربر باید ربات را استارت کرده باشد تا پیام‌ها و پنل را ببیند.)", _back([], "ad:am", "◀️ مدیریت ادمین‌ها"))
    if k == "ar":
        tid = _parse_id(arg(2, "")); back = arg(3, "am")
        note = remove_admin(uid, tid) if tid else "شناسه نامعتبر است."
        if back == "am": return admins_screen(uid, mid, note)
        return user_detail(uid, mid, tid, back)
    return panel(uid, mid)
