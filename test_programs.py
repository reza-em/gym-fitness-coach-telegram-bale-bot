#!/usr/bin/env python3
"""Unit tests for the 📂 body-type program bank (programs_db.py): ./venv/bin/python test_programs.py"""
import os, sys, tempfile
os.environ.setdefault("FITNESS_DB_PATH", os.path.join(tempfile.mkdtemp(prefix="fit-pdb-"), "t.db"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exdata as X, programs_db as PDB, program as P

FAIL = 0; N = 0
def ok(c, name):
    global FAIL, N
    N += 1
    if not c: FAIL += 1; print("FAIL:", name)

# --- classification: BMI cut-offs + goal inside the normal range
ac = PDB.auto_category
ok(ac(185, 61)[0] == "lean", "BMI 17.8 -> لاغری")
ok(ac(180, 59.9)[0] == "lean", "BMI 18.49 -> لاغری")
ok(ac(180, 60)[0] == "fit", "BMI 18.5 -> تناسب")
ok(ac(180, 80.6)[0] == "fit", "BMI 24.9 -> تناسب")
ok(ac(180, 81)[0] == "fat", "BMI 25.0 -> چاقی")
ok(ac(175, 89, 100)[0] == "fat", "BMI >= 25 stays چاقی even with a gain goal (override button exists)")
ok(ac(175, 70, 64)[0] == "fat", "normal BMI + goal 6 kg lower -> چاقی (fat loss)")
ok(ac(175, 70, 76)[0] == "lean", "normal BMI + goal 6 kg higher -> لاغری (lean gain)")
ok(ac(175, 70, 71.5)[0] == "fit", "normal BMI + goal close to current -> تناسب")
ok(ac(None, 70)[0] is None and ac(175, None)[0] is None, "no height/weight -> unknown")
ok(abs(PDB.bmi(81, 180) - 25.0) < 0.01, "BMI formula")
u = dict(height=180, weight=90, goal_w=80, sex="m")
ok(PDB.category(u) == "fat" and not PDB.info(u)["manual"], "auto category from the saved profile")
ok(PDB.category(dict(u, body_cat="fit")) == "fit" and PDB.info(dict(u, body_cat="fit"))["manual"], "manual override wins")
ok(PDB.category(dict(u, body_cat="junk")) == "fat", "invalid override ignored")
ok(PDB.category(dict(u, goal_w=None, target_w=95)) == "fat", "target_w used when goal_w missing")

# --- the bank: every referenced exercise exists (tutorial buttons keep working), every combination present
ids = PDB.all_exercise_ids()
ok(ids and ids <= set(X.EX), "every bank exercise id exists in exdata.EX: missing=%s" % sorted(ids - set(X.EX)))
ok(all(X.aparat_url(e) and X.yt_url(e) and e in X.TIPS for e in ids), "every bank exercise has tutorial links + tips")
for c in PDB.CATS:
    for s in "mf":
        for d in PDB.DAYS:
            t = PDB.template(c, d, s)
            ok(len(t) == d, f"{c}/{s}/{d}: one session per training day")
            ok(all(len({e for e, _ in items}) == len(items) and len(items) >= 4 and any(p == 1 for _, p in items) for _ti, items in t),
               f"{c}/{s}/{d}: sessions have >=4 unique exercises with essentials")
            ok(PDB.plan_name(c, d, s), f"{c}/{s}/{d}: plan name")
        ok(PDB.CARDIO[c] and PDB.NUTRITION[c] and len(PDB.SAMPLE_DAY[c]) >= 4 and PDB.SAFETY[c] and PDB.supplements(c), f"{c}: guidance texts")
ok(PDB.template("lean", 4, "m") is X.TEMPLATES["ul"] and PDB.template("lean", 3, "f") is X.TEMPLATES_F["fb"], "lean 3/4 days = the original programmes")
lower = lambda t: sum(1 for _ti, it in t for e, _ in it if X.EX[e]["grp"] in X.LOWER_GROUPS)
ok(all(lower(PDB.template(c, 4, "f")) > lower(PDB.template(c, 4, "m")) for c in PDB.CATS), "female templates keep the lower-body emphasis")
ok("گینر برای کاهش چربی مناسب نیست." in "\n".join(PDB.supplements("fat")) and any("پزشک" in x for x in PDB.supplements("lean", kidney=True)), "supplement notes: no gainer for fat loss; kidney -> no creatine")

# --- program.py uses the bank
base = dict(injuries="", sess_min=90, deload_week=0, sex="m", age=30, activity=1.55, surplus=450, protein_gk=2.0)
ok(P.template_for(dict(base, plan_type="ul")) is X.TEMPLATES["ul"], "no height/weight -> classic template (unchanged behaviour)")
fat5 = dict(base, plan_type="d5", days_pw=5, height=175, weight=95, goal_w=80)
ok(P.n_sessions(fat5) == 5 and P.template_for(fat5) is PDB.template("fat", 5, "m"), "fat-loss 5-day user gets the bank template")
s = P.build_session(fat5, 3, 2)
ok(s["title"] == PDB.template("fat", 5, "m")[2][0] and all(i["ex"] in X.EX for i in s["items"]), "build_session from the bank")
ok(P.template_for(dict(fat5, body_cat="lean", plan_type="ul", days_pw=4)) is X.TEMPLATES["ul"], "override to lean (4 days) -> original upper/lower")
ok(X.plan_type_for_days(4) == "ul" and X.plan_type_for_days(3) == "fb" and X.plan_type_for_days(6) == "d6" and PDB.days_of(dict(plan_type="d2")) == 2, "plan types for 2-6 days")
ok(all(len(X.DAY_PRESETS[d][0][1]) == d for d in PDB.DAYS), "weekday presets for 2-6 days")
inj = P.build_session(dict(fat5, injuries="knee"), 3, 1)
ok(all("knee" not in X.EX[i["ex"]]["avoid"] for i in inj["items"]), "injury substitution still works on bank templates")

# --- personal numbers
n = PDB.numbers(dict(base, height=175, weight=95), "fat")
ok(n and -600 <= n["delta"] <= -300 and n["kcal"] >= 1500 and n["ref_w"] < 95, "fat loss: 300-600 kcal deficit, floor, protein from reference weight")
nl = PDB.numbers(dict(base, height=185, weight=61), "lean")
ok(nl["delta"] == 450 and nl["protein"] == 122, "lean gain: the bot's own surplus, 2 g/kg")
ok(PDB.numbers(dict(base, height=180, weight=75), "fit")["delta"] == 0, "fit: maintenance")
ok(PDB.numbers(dict(sex="m"), "fit") is None, "incomplete profile -> no numbers")

print(f"test_programs: {N - FAIL} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
