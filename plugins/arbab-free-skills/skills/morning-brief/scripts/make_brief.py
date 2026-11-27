"""Build a one-page morning brief as an HTML page and a Word file from a JSON outline.

Usage: python make_brief.py brief.json OUT_DIR
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
    "ar": {"headline": "يومك في سطر", "first": "ابدا بهذي", "clashes": "انتبه",
           "meetings": "اجتماعات اليوم", "reply": "ناس ينتظرون ردك",
           "waiting": "إنت تنتظر منهم", "later": "يتأجل عادي",
           "about": "الموضوع", "since": "من", "draft": "الرد جاهز"},
    "en": {"headline": "Today in one line", "first": "Do first", "clashes": "Watch out",
           "meetings": "Today's meetings", "reply": "Waiting for your reply",
           "waiting": "You are waiting on", "later": "Can wait",
           "about": "About", "since": "Since", "draft": "Ready reply"},
}
MAX_FIRST = 3
MAX_REPLY = 5
ACCENT = RGBColor(0x1F, 0x3A, 0x5F)
MUTED = RGBColor(0x55, 0x5F, 0x6D)
WARN = RGBColor(0xA1, 0x3B, 0x1E)
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def load_brief(path: str) -> dict:
    """Read the outline and keep the page inside its limits."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("brief.json must hold one JSON object")
    lang = data.get("lang", "ar")
    if lang not in HEADINGS:
        raise ValueError('"lang" must be "ar" or "en"')
    return {
        **data,
        "lang": lang,
        "first": list(data.get("first") or [])[:MAX_FIRST],
        "reply": list(data.get("reply") or [])[:MAX_REPLY],
    }


def set_rtl(paragraph, rtl: bool) -> None:
    """Mark a paragraph right to left (Word needs w:bidi on the paragraph)."""
    if not rtl:
        return
    bidi = OxmlElement("w:bidi")
    bidi.set(qn("w:val"), "1")
    paragraph._p.get_or_add_pPr().append(bidi)


def add_runs(paragraph, text: str, rtl: bool, size: int = 11, color=None, bold_all: bool = False) -> None:
    """Add text with **bold** spans; each run marked RTL when needed."""
    for i, part in enumerate(BOLD_RE.split(text)):
        if not part:
            continue
        run = paragraph.add_run(part)
        run.bold = bold_all or (i % 2 == 1)
        run.font.size = Pt(size)
        if color is not None:
            run.font.color.rgb = color
        if not rtl:
            continue
        rpr = run._r.get_or_add_rPr()
        rtl_el = OxmlElement("w:rtl")
        rtl_el.set(qn("w:val"), "1")
        rpr.append(rtl_el)
        run.font.cs_bold = run.bold
        fonts = rpr.find(qn("w:rFonts"))
        if fonts is None:
            fonts = OxmlElement("w:rFonts")
            rpr.append(fonts)
        fonts.set(qn("w:cs"), "Arial")
        szcs = OxmlElement("w:szCs")
        szcs.set(qn("w:val"), str(size * 2))
        rpr.append(szcs)


def para(doc, text: str, rtl: bool, style: str | None = None, **kw) -> None:
    p = doc.add_paragraph(style=style) if style else doc.add_paragraph()
    set_rtl(p, rtl)
    add_runs(p, text, rtl, **kw)


def heading(doc, text: str, rtl: bool, color=ACCENT) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(3)
    set_rtl(p, rtl)
    add_runs(p, text, rtl, size=13, color=color, bold_all=True)


def table(doc, rows: list, rtl: bool) -> None:
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    if rtl:
        t._tbl.tblPr.append(OxmlElement("w:bidiVisual"))
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            cell = t.cell(r, c)
            cell.text = ""
            p = cell.paragraphs[0]
            set_rtl(p, rtl)
            add_runs(p, str(val), rtl, size=10, bold_all=(r == 0))


def build_docx(d: dict, path: str) -> None:
    rtl = d["lang"] == "ar"
    h = HEADINGS[d["lang"]]
    doc = Document()
    doc.styles["Normal"].font.name = "Arial"
    doc.styles["Normal"].font.size = Pt(11)

    para(doc, d.get("title", ""), rtl, size=20, color=ACCENT, bold_all=True)
    meta = " · ".join(x for x in [d.get("person", ""), d.get("date", "")] if x)
    if meta:
        para(doc, meta, rtl, size=10, color=MUTED)
    if d.get("headline"):
        heading(doc, h["headline"], rtl)
        para(doc, d["headline"], rtl, size=12, bold_all=True)
    if d["first"]:
        heading(doc, h["first"], rtl)
        for item in d["first"]:
            para(doc, item, rtl, style="List Number")
    if d.get("clashes"):
        heading(doc, h["clashes"], rtl, color=WARN)
        for item in d["clashes"]:
            para(doc, item, rtl, style="List Bullet")
    if len(d.get("meetings") or []) > 1:
        heading(doc, h["meetings"], rtl)
        table(doc, d["meetings"], rtl)
    if d["reply"]:
        heading(doc, h["reply"], rtl)
        for item in d["reply"]:
            para(doc, item.get("who", ""), rtl, bold_all=True)
            line = " · ".join(x for x in [
                f"{h['about']}: {item['about']}" if item.get("about") else "",
                f"{h['since']}: {item['since']}" if item.get("since") else "",
            ] if x)
            if line:
                para(doc, line, rtl, size=10, color=MUTED)
            if item.get("draft"):
                para(doc, h["draft"], rtl, size=10, color=ACCENT, bold_all=True)
                for row in item["draft"].split("\n"):
                    para(doc, row, rtl, size=10)
    if len(d.get("waiting") or []) > 1:
        heading(doc, h["waiting"], rtl)
        table(doc, d["waiting"], rtl)
    if d.get("later"):
        heading(doc, h["later"], rtl)
        for item in d["later"]:
            para(doc, item, rtl, style="List Bullet")
    doc.save(path)


def inline(text: str) -> str:
    return BOLD_RE.sub(r"<b>\1</b>", html.escape(str(text)))


def html_list(items: list, tag: str = "ul") -> str:
    return f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}>"


def html_table(rows: list) -> str:
    head = "".join(f"<th>{inline(x)}</th>" for x in rows[0])
    body = "".join("<tr>" + "".join(f"<td>{inline(x)}</td>" for x in r) + "</tr>" for r in rows[1:])
    return f"<table><tr>{head}</tr>{body}</table>"


def html_reply(item: dict, h: dict) -> str:
    meta = " · ".join(x for x in [
        f"{h['about']}: {inline(item['about'])}" if item.get("about") else "",
        f"{h['since']}: {inline(item['since'])}" if item.get("since") else "",
    ] if x)
    draft = ""
    if item.get("draft"):
        body = "<br>".join(inline(row) for row in item["draft"].split("\n"))
        draft = f"<div class='draft'><span>{h['draft']}</span>{body}</div>"
    return f"<div class='card'><b>{inline(item.get('who', ''))}</b><p class='meta'>{meta}</p>{draft}</div>"


CSS = """body{font-family:Arial,Tahoma,sans-serif;max-width:720px;margin:24px auto;padding:0 18px;color:#1b2430;
line-height:1.6;background:#fff}h1{color:#1F3A5F;margin:0 0 2px;font-size:27px}
h2{color:#1F3A5F;font-size:17px;margin:20px 0 6px;border-bottom:2px solid #e6ebf2;padding-bottom:4px}
h2.warn{color:#A13B1E;border-color:#f3ddd5}.meta{color:#555F6D;font-size:13px;margin:0}
.head{font-weight:bold;font-size:16px;margin:4px 0}ol,ul{margin:6px 0;padding-inline-start:22px}li{margin:4px 0}
ol li{font-size:16px}.tw{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px}
th,td{border:1px solid #d5dde8;padding:6px 8px;text-align:start;vertical-align:top}th{background:#eef3f9}
.card{border:1px solid #d5dde8;border-radius:8px;padding:10px 12px;margin:8px 0}
.draft{background:#f4f7fb;border-inline-start:3px solid #1F3A5F;padding:8px 10px;margin-top:8px;font-size:14px}
.draft span{display:block;color:#1F3A5F;font-weight:bold;font-size:12px;margin-bottom:4px}"""


def build_html(d: dict, path: str) -> None:
    rtl = d["lang"] == "ar"
    h = HEADINGS[d["lang"]]
    out = [f"<h1>{html.escape(d.get('title', ''))}</h1>"]
    meta = " · ".join(x for x in [d.get("person", ""), d.get("date", "")] if x)
    if meta:
        out.append(f"<p class='meta'>{html.escape(meta)}</p>")
    if d.get("headline"):
        out.append(f"<h2>{h['headline']}</h2><p class='head'>{inline(d['headline'])}</p>")
    if d["first"]:
        out.append(f"<h2>{h['first']}</h2>{html_list(d['first'], 'ol')}")
    if d.get("clashes"):
        out.append(f"<h2 class='warn'>{h['clashes']}</h2>{html_list(d['clashes'])}")
    if len(d.get("meetings") or []) > 1:
        out.append(f"<h2>{h['meetings']}</h2><div class='tw'>{html_table(d['meetings'])}</div>")
    if d["reply"]:
        out.append(f"<h2>{h['reply']}</h2>" + "".join(html_reply(x, h) for x in d["reply"]))
    if len(d.get("waiting") or []) > 1:
        out.append(f"<h2>{h['waiting']}</h2><div class='tw'>{html_table(d['waiting'])}</div>")
    if d.get("later"):
        out.append(f"<h2>{h['later']}</h2>{html_list(d['later'])}")
    page = (
        f"<!doctype html><html lang=\"{d['lang']}\" dir=\"{'rtl' if rtl else 'ltr'}\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        f"<title>{html.escape(d.get('title', 'Morning brief'))}</title><style>{CSS}</style></head><body>"
        f"{''.join(out)}</body></html>"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit("Usage: python make_brief.py brief.json OUT_DIR")
    try:
        data = load_brief(sys.argv[1])
    except (OSError, ValueError) as err:
        sys.exit(f"Could not read the brief: {err}")
    os.makedirs(sys.argv[2], exist_ok=True)
    build_docx(data, os.path.join(sys.argv[2], "morning-brief.docx"))
    build_html(data, os.path.join(sys.argv[2], "morning-brief.html"))
    sys.stdout.write(f"written: {os.path.join(sys.argv[2], 'morning-brief.html')}\n")


if __name__ == "__main__":
    main()
