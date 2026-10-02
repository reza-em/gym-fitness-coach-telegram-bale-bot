#!/usr/bin/env python3
"""One-off: download the two start/end images of each exercise from free-exercise-db (https://github.com/yuhonas/free-exercise-db, The Unlicense = public domain)
into assets/ex/<id>_0.jpg / _1.jpg and build a looping 2-frame GIF assets/ex/<id>.gif. The bot only reads these local files (no runtime downloads)."""
import os, io, sys, requests
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exdata as X
RAW = "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/exercises/"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "ex"); os.makedirs(OUT, exist_ok=True)
for eid, fed in X.FED.items():
    frames = []
    for i in (0, 1):
        p = os.path.join(OUT, f"{eid}_{i}.jpg")
        if not os.path.exists(p):
            r = requests.get(f"{RAW}{fed}/{i}.jpg", timeout=30)
            if r.status_code != 200: print("MISSING", eid, fed, i, r.status_code); break
            open(p, "wb").write(r.content)
        frames.append(Image.open(p).convert("P", palette=Image.ADAPTIVE) if False else Image.open(p).convert("RGB"))
    if len(frames) == 2:
        w = 480; frames = [f.resize((w, int(f.height * w / f.width))) for f in frames]
        h = min(f.height for f in frames); frames = [f.crop((0, 0, w, h)) for f in frames]
        frames[0].save(os.path.join(OUT, f"{eid}.gif"), save_all=True, append_images=frames[1:], duration=1000, loop=0, optimize=True)
        print("ok", eid)
