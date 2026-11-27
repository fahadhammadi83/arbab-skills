"""One PowerPoint slide for the weekly meeting: headline, three numbers, a trend chart.

Usage: python make_slide.py report.json OUT_DIR [weekly-tracker.xlsx]
Needs: pip install python-pptx openpyxl
"""
import json
import os
import sys

from openpyxl import load_workbook
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

NAVY = RGBColor(0x1F, 0x3A, 0x5F)
MUTED = RGBColor(0x55, 0x5F, 0x6D)
TILE = RGBColor(0xEE, 0xF3, 0xF9)


def text_box(slide, left, top, width, height, text, size, bold=False, color=NAVY, rtl=False):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    for i, line in enumerate(str(text).replace("**", "").splitlines() or [""]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.RIGHT if rtl else PP_ALIGN.LEFT
        if rtl:
            p._p.get_or_add_pPr().set("rtl", "1")
        run = p.add_run()
        run.text = line
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = color
        if rtl:
            rpr = run._r.get_or_add_rPr()
            rpr.set("lang", "ar-AE")
            rpr.set("altLang", "en-US")
            cs = rpr.makeelement(qn("a:cs"), {"typeface": "Arial"})
            rpr.append(cs)
    return box


def three_numbers(report: dict) -> list[tuple[str, str]]:
    rows = (report.get("numbers") or [])[1:]
    return [(str(r[0]), str(r[1])) for r in rows[:3] if len(r) >= 2]


def trend(tracker_path: str | None) -> tuple[list[str], str, list[float]] | None:
    """Weeks and the first metric's values from the tracker, if it has 2+ weeks."""
    if not tracker_path or not os.path.exists(tracker_path):
        return None
    ws = load_workbook(tracker_path, data_only=True)["Weeks"]
    if ws.max_row < 3 or ws.max_column < 5:
        return None
    name = str(ws.cell(1, 5).value)
    weeks, vals = [], []
    for r in range(2, ws.max_row + 1):
        v = ws.cell(r, 5).value
        if isinstance(v, (int, float)):
            weeks.append(str(ws.cell(r, 1).value))
            vals.append(float(v))
    return (weeks, name, vals) if len(vals) >= 2 else None


def main() -> None:
    if len(sys.argv) not in (3, 4):
        print("Usage: python make_slide.py report.json OUT_DIR [weekly-tracker.xlsx]")
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as f:
        report = json.load(f)
    rtl = report.get("lang", "ar") == "ar"
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    text_box(slide, Inches(0.6), Inches(0.4), Inches(12.1), Inches(0.5),
             " · ".join(x for x in [report.get("person", ""), report.get("week", "")] if x), 14, color=MUTED, rtl=rtl)
    text_box(slide, Inches(0.6), Inches(0.9), Inches(12.1), Inches(1.4), report.get("headline", ""), 28, bold=True, rtl=rtl)

    nums = three_numbers(report)
    tile_w = Inches(3.8)
    for i, (label, value) in enumerate(nums):
        idx = (len(nums) - 1 - i) if rtl else i
        left = Inches(0.6) + idx * (tile_w + Inches(0.35))
        tile = slide.shapes.add_shape(1, left, Inches(2.6), tile_w, Inches(1.9))
        tile.fill.solid()
        tile.fill.fore_color.rgb = TILE
        tile.line.fill.background()
        text_box(slide, left + Inches(0.2), Inches(2.75), tile_w - Inches(0.4), Inches(1.0), value, 40, bold=True, rtl=rtl)
        text_box(slide, left + Inches(0.2), Inches(3.75), tile_w - Inches(0.4), Inches(0.6), label, 16, color=MUTED, rtl=rtl)

    t = trend(sys.argv[3] if len(sys.argv) == 4 else None)
    if t:
        weeks, name, vals = t
        data = CategoryChartData()
        data.categories = weeks
        data.add_series(name, vals)
        gf = slide.shapes.add_chart(XL_CHART_TYPE.LINE_MARKERS, Inches(0.6), Inches(4.8), Inches(12.1), Inches(2.4), data)
        gf.chart.has_legend = False
        gf.chart.has_title = True
        gf.chart.chart_title.text_frame.text = name
    else:
        blockers = (report.get("blockers") or [])[1:]
        nxt = report.get("next_week") or []
        lines = [f"• {b[0]}" for b in blockers[:2]] + [f"• {n}" for n in nxt[:3]]  # bullet then a space
        if lines:
            text_box(slide, Inches(0.6), Inches(4.9), Inches(12.1), Inches(2.3), "\n".join(lines), 18, color=NAVY, rtl=rtl)

    os.makedirs(sys.argv[2], exist_ok=True)
    path = os.path.join(sys.argv[2], "weekly-slide.pptx")
    prs.save(path)
    print("written:", path)


if __name__ == "__main__":
    main()
