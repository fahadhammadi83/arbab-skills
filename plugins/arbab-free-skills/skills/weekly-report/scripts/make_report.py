"""Build a weekly report as a Word file (+ an HTML copy) from a JSON outline.

Usage: python make_report.py report.json OUT_DIR
Needs: pip install python-docx
"""
import html
import json
import os
import re
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

HEADINGS = {
    "ar": {"headline": "خلاصة الأسبوع", "done": "اللي خلص هالأسبوع", "numbers": "الأرقام",
           "in_progress": "قيد التنفيذ", "blockers": "اللي واقف وشو أحتاج",
           "next_week": "الأسبوع الجاي", "decisions": "قرارات أحتاجها منك", "to": "إلى"},
    "ar_formal": {"headline": "ملخص الأسبوع", "done": "الإنجازات", "numbers": "المؤشرات",
                  "in_progress": "الأعمال الجارية", "blockers": "المعوقات والاحتياجات",
                  "next_week": "خطة الأسبوع القادم", "decisions": "قرارات مطلوبة", "to": "إلى"},
    "en": {"headline": "This week in one line", "done": "Done this week", "numbers": "Numbers",
           "in_progress": "In progress", "blockers": "Blockers and what I need",
           "next_week": "Next week", "decisions": "Decisions needed from you", "to": "To"},
}
ACCENT = RGBColor(0x1F, 0x3A, 0x5F)
MUTED = RGBColor(0x55, 0x5F, 0x6D)
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def set_rtl(paragraph, rtl):
    """Mark a paragraph right to left (Word needs w:bidi on the paragraph)."""
    if not rtl:
        return
    ppr = paragraph._p.get_or_add_pPr()
    bidi = OxmlElement("w:bidi")
    bidi.set(qn("w:val"), "1")
    ppr.append(bidi)
    # In a bidi paragraph Word reads jc="right" as the far (left) side, so no explicit
    # alignment: bidi alone starts the text on the right.


def add_runs(paragraph, text, rtl, size=11, color=None, bold_all=False):
    """Add text with **bold** spans; each run marked RTL when needed."""
    parts = BOLD_RE.split(text)
    for i, part in enumerate(parts):
        if not part:
            continue
        run = paragraph.add_run(part)
        run.bold = bold_all or (i % 2 == 1)
        run.font.size = Pt(size)
        if color is not None:
            run.font.color.rgb = color
        if rtl:
            rpr = run._r.get_or_add_rPr()
            rtl_el = OxmlElement("w:rtl")
            rtl_el.set(qn("w:val"), "1")
            rpr.append(rtl_el)
            run.font.cs_bold = run.bold
            rpr_fonts = rpr.find(qn("w:rFonts"))
            if rpr_fonts is None:
                rpr_fonts = OxmlElement("w:rFonts")
                rpr.append(rpr_fonts)
            rpr_fonts.set(qn("w:cs"), "Arial")
            szcs = OxmlElement("w:szCs")
            szcs.set(qn("w:val"), str(size * 2))
            rpr.append(szcs)


def heading(doc, text, rtl):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(4)
    set_rtl(p, rtl)
    add_runs(p, text, rtl, size=13, color=ACCENT, bold_all=True)


def bullets(doc, items, rtl):
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        set_rtl(p, rtl)
        add_runs(p, item, rtl)


def table(doc, rows, rtl):
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    if rtl:
        tblpr = t._tbl.tblPr
        bidi = OxmlElement("w:bidiVisual")
        tblpr.append(bidi)
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            cell = t.cell(r, c)
            cell.text = ""
            p = cell.paragraphs[0]
            set_rtl(p, rtl)
            add_runs(p, str(val), rtl, size=10, bold_all=(r == 0))


def build_docx(d, path):
    rtl = d.get("lang", "ar") == "ar"
    h = pick_headings(d)
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Arial"
    style.font.size = Pt(11)

    p = doc.add_paragraph()
    set_rtl(p, rtl)
    add_runs(p, d.get("title", ""), rtl, size=20, color=ACCENT, bold_all=True)
    meta = " · ".join(x for x in [d.get("person", ""), d.get("week", "")] if x)
    if meta:
        p = doc.add_paragraph()
        set_rtl(p, rtl)
        add_runs(p, meta, rtl, size=10, color=MUTED)
    if d.get("to"):
        p = doc.add_paragraph()
        set_rtl(p, rtl)
        add_runs(p, f"{h['to']}: {d['to']}", rtl, size=10, color=MUTED)

    if d.get("headline"):
        heading(doc, h["headline"], rtl)
        p = doc.add_paragraph()
        set_rtl(p, rtl)
        add_runs(p, d["headline"], rtl, size=12, bold_all=True)
    if d.get("done"):
        heading(doc, h["done"], rtl)
        bullets(doc, d["done"], rtl)
    for key in ("numbers", "in_progress", "blockers"):
        rows = d.get(key) or []
        if len(rows) > 1:
            heading(doc, h[key], rtl)
            table(doc, rows, rtl)
    if d.get("next_week"):
        heading(doc, h["next_week"], rtl)
        bullets(doc, d["next_week"], rtl)
    if d.get("decisions"):
        heading(doc, h["decisions"], rtl)
        bullets(doc, d["decisions"], rtl)
    doc.save(path)


def pick_headings(d: dict) -> dict:
    """Default headings by language/style, overridden by the company's own ("headings")."""
    if d.get("lang", "ar") != "ar":
        base = HEADINGS["en"]
    else:
        base = HEADINGS["ar_formal"] if d.get("style") == "formal" else HEADINGS["ar"]
    return {**base, **(d.get("headings") or {})}


def md_inline(text):
    return BOLD_RE.sub(r"<b>\1</b>", html.escape(text))


def build_html(d, path):
    rtl = d.get("lang", "ar") == "ar"
    h = pick_headings(d)
    out = []
    out.append(f"<h1>{html.escape(d.get('title', ''))}</h1>")
    meta = " · ".join(x for x in [d.get("person", ""), d.get("week", "")] if x)
    if meta:
        out.append(f"<p class='meta'>{html.escape(meta)}</p>")
    if d.get("to"):
        out.append(f"<p class='meta'>{h['to']}: {html.escape(d['to'])}</p>")
    if d.get("headline"):
        out.append(f"<h2>{h['headline']}</h2><p class='head'>{md_inline(d['headline'])}</p>")

    def ul(key):
        if d.get(key):
            out.append(f"<h2>{h[key]}</h2><ul>" + "".join(f"<li>{md_inline(x)}</li>" for x in d[key]) + "</ul>")

    def tb(key):
        rows = d.get(key) or []
        if len(rows) > 1:
            head = "".join(f"<th>{md_inline(str(x))}</th>" for x in rows[0])
            body = "".join("<tr>" + "".join(f"<td>{md_inline(str(x))}</td>" for x in r) + "</tr>" for r in rows[1:])
            out.append(f"<h2>{h[key]}</h2><table><tr>{head}</tr>{body}</table>")

    ul("done")
    for k in ("numbers", "in_progress", "blockers"):
        tb(k)
    ul("next_week")
    ul("decisions")
    page = f"""<!doctype html><html lang="{'ar' if rtl else 'en'}" dir="{'rtl' if rtl else 'ltr'}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(d.get('title', 'Weekly report'))}</title>
<style>body{{font-family:Arial,Tahoma,sans-serif;max-width:760px;margin:32px auto;padding:0 24px;color:#1b2430;line-height:1.6;background:#fff}}
h1{{color:#1F3A5F;margin:0 0 4px;font-size:28px}}h2{{color:#1F3A5F;font-size:17px;margin:22px 0 6px;border-bottom:2px solid #e6ebf2;padding-bottom:4px}}
.meta{{color:#555F6D;font-size:13px;margin:0}}.head{{font-weight:bold;font-size:16px}}table{{border-collapse:collapse;width:100%;font-size:14px}}
th,td{{border:1px solid #d5dde8;padding:6px 8px;text-align:start}}th{{background:#eef3f9}}li{{margin:3px 0}}</style></head><body>
{''.join(out)}</body></html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)


def main():
    if len(sys.argv) != 3:
        print("Usage: python make_report.py report.json OUT_DIR")
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)
    os.makedirs(sys.argv[2], exist_ok=True)
    build_docx(data, os.path.join(sys.argv[2], "weekly-report.docx"))
    build_html(data, os.path.join(sys.argv[2], "weekly-report.html"))
    print("written:", os.path.join(sys.argv[2], "weekly-report.docx"))


if __name__ == "__main__":
    main()
