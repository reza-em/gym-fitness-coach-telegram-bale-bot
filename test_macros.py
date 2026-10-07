#!/usr/bin/env python3
"""Pure unit test for the 🧮 target-weight calculator (macros.py): ./venv/bin/python test_macros.py"""
import os, sys, tempfile
os.environ.setdefault("FITNESS_DB_PATH", os.path.join(tempfile.mkdtemp(prefix="fit-mc-"), "t.db"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import macros as MC

m = MC.calc(90)
assert (m["kcal"], m["protein"], m["fat"], m["fiber"], m["carbs"], m["water_l"]) == (2160, 198, 72, 30, 180, 3.0), m
txt = MC.card_text(90)
assert "روش محاسبه بر اساس آموزش سامان خوارزمی" in txt and "2160 − 1440 = 720" in txt
assert MC.suggestions(178, "m") == dict(lo=59, hi=78, bmi22=70, devine=73)
print("test_macros: OK (90 kg -> 2160 kcal / 198 P / 72 F / 30 fiber / 180 C / 3.0 L)")
