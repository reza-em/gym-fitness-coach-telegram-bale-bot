#!/usr/bin/env python3
"""Generate Persian PDF of all exercises with Aparat + YouTube tutorial links."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT, TA_CENTER

import config, exdata as X

OUT = os.path.join(config.ASSETS, "exercises_tutorials.pdf")
OUT2 = os.environ.get("FITNESS_PDF_COPY", "")     # optional extra copy path

def fa(t):
    if not t: return ""
    return get_display(arabic_reshaper.reshape(str(t)))

def main():
    pdfmetrics.registerFont(TTFont("Vazir", config.FONT_REG))
    pdfmetrics.registerFont(TTFont("VazirBold", config.FONT_BOLD))
    doc = SimpleDocTemplate(OUT, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    title_s = ParagraphStyle("T", fontName="VazirBold", fontSize=16, alignment=TA_CENTER, leading=24, spaceAfter=12)
    h_s = ParagraphStyle("H", fontName="VazirBold", fontSize=12, alignment=TA_RIGHT, leading=18, spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#1a5f2a"))
    b_s = ParagraphStyle("B", fontName="Vazir", fontSize=9, alignment=TA_RIGHT, leading=14, spaceAfter=2)
    link_s = ParagraphStyle("L", fontName="Vazir", fontSize=8, alignment=TA_RIGHT, leading=12, textColor=colors.HexColor("#0b57d0"))
    story = []
    story.append(Paragraph(fa("کتابچهٔ آموزش حرکات — مربی بدنسازی"), title_s))
    story.append(Paragraph(fa("همهٔ حرکت‌ها با لینک آپارات (فارسی) و یوتیوب. برای مبتدی / خانه و سالن."), b_s))
    story.append(Spacer(1, 8))

    # group by muscle
    groups = {}
    for eid, ex in X.EX.items():
        groups.setdefault(ex["grp"], []).append((eid, ex))

    n = 0
    for grp in groups:
        story.append(Paragraph(fa(f"▸ {grp}"), h_s))
        for eid, ex in groups[grp]:
            n += 1
            aparat = X.aparat_url(eid)
            yt = X.yt_url(eid)
            yt_m = X.yt_url(eid, "mistakes")
            head = f"{n}. {ex['fa']} — {ex['en']} | {ex['eq']}"
            story.append(Paragraph(fa(head), ParagraphStyle("E", fontName="VazirBold", fontSize=10, alignment=TA_RIGHT, leading=15, spaceBefore=6)))
            story.append(Paragraph(fa(ex["how"]), b_s))
            # clickable links
            story.append(Paragraph(f'<link href="{aparat}">{fa("آپارات (جستجوی آموزش فارسی)")}</link>', link_s))
            story.append(Paragraph(f'<link href="{yt}">{fa("یوتیوب — آموزش فرم")}</link>', link_s))
            story.append(Paragraph(f'<link href="{yt_m}">{fa("یوتیوب — اشتباهات رایج")}</link>', link_s))
    story.append(Spacer(1, 16))
    story.append(Paragraph(fa("هشدار: این راهنما آموزشی است و جایگزین پزشک نیست. در صورت درد تیز متوقف شوید."), b_s))
    doc.build(story)
    print(OUT, "exercises=", n)
    if OUT2:
        import shutil
        shutil.copy2(OUT, OUT2); print(OUT2)

if __name__ == "__main__":
    main()
