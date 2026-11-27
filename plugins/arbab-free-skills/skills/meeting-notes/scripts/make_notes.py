"""Build meeting minutes (Word + HTML copy) and a running task tracker (Excel) from a JSON outline.

Usage: python make_notes.py notes.json OUT_DIR [last_meeting_tasks.xlsx]
Needs: pip install python-docx openpyxl
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
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

HEADINGS = {
    "ar": {"summary": "الخلاصة", "attendees": "الحضور", "decisions": "القرارات", "tasks": "المهام",
           "carried": "مهام الاجتماع السابق", "numbers": "الأرقام", "open_questions": "أسئلة مفتوحة",
           "next_meeting": "الاجتماع الجاي", "date": "التاريخ",
           "owner": "المسؤول", "task": "المهمة", "due": "الموعد", "status": "الحالة",
           "done": "تم ✓", "open": "مفتوحة", "dropped": "ملغاة"},
    "en": {"summary": "Summary", "attendees": "Attendees", "decisions": "Decisions", "tasks": "Tasks",
           "carried": "From last meeting", "numbers": "Numbers", "open_questions": "Open questions",
           "next_meeting": "Next meeting", "date": "Date",
           "owner": "Owner", "task": "Task", "due": "Due", "status": "Status",
           "done": "Done ✓", "open": "Open", "dropped": "Dropped"},
}
TRACKER_HEAD = {"ar": ["تاريخ الاجتماع", "الاجتماع", "المسؤول", "المهمة", "الموعد", "الحالة"],
                "en": ["Meeting date", "Meeting", "Owner", "Task", "Due", "Status"]}
ACCENT = RGBColor(0x1F, 0x3A, 0x5F)
MUTED = RGBColor(0x55, 0x5F, 0x6D)
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def labels(d: dict) -> dict:
    base = HEADINGS["ar" if d.get("lang", "ar") == "ar" else "en"]
    return {**base, **(d.get("headings") or {})}


def set_rtl(paragraph, rtl: bool) -> None:
    """Mark a paragraph right to left (bidi alone starts the text on the right)."""
    if rtl:
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
        if rtl:
            rpr = run._r.get_or_add_rPr()
            el = OxmlElement("w:rtl")
            el.set(qn("w:val"), "1")
            rpr.append(el)
            run.font.cs_bold = run.bold
            fonts = rpr.find(qn("w:rFonts"))
            if fonts is None:
                fonts = OxmlElement("w:rFonts")
                rpr.append(fonts)
            fonts.set(qn("w:cs"), "Arial")
            szcs = OxmlElement("w:szCs")
            szcs.set(qn("w:val"), str(size * 2))
            rpr.append(szcs)


def para(doc, text: str, rtl: bool, **kw) -> None:
    p = doc.add_paragraph()
    set_rtl(p, rtl)
    add_runs(p, text, rtl, **kw)


def heading(doc, text: str, rtl: bool) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(4)
    set_rtl(p, rtl)
    add_runs(p, text, rtl, size=13, color=ACCENT, bold_all=True)


def bullets(doc, items: list, rtl: bool) -> None:
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        set_rtl(p, rtl)
        add_runs(p, item, rtl)


def table(doc, rows: list, rtl: bool) -> None:
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    if rtl:
        t._tbl.tblPr.append(OxmlElement("w:bidiVisual"))
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            p = t.cell(r, c).paragraphs[0]
            set_rtl(p, rtl)
            add_runs(p, str(val), rtl, size=10, bold_all=(r == 0))


def task_rows(d: dict, h: dict) -> list:
    rows = [[h["owner"], h["task"], h["due"]]]
    rows += [[t.get("owner", ""), t.get("task", ""), t.get("due_label") or t.get("due", "")] for t in d.get("tasks", [])]
    return rows


def carried_rows(d: dict, h: dict) -> list:
    rows = [[h["owner"], h["task"], h["status"]]]
    rows += [[c.get("owner", ""), c.get("task", ""), h.get(c.get("status", "open"), c.get("status", ""))]
             for c in d.get("carried", [])]
    return rows


def build_docx(d: dict, path: str) -> None:
    rtl = d.get("lang", "ar") == "ar"
    h = labels(d)
    doc = Document()
    doc.styles["Normal"].font.name = "Arial"
    doc.styles["Normal"].font.size = Pt(11)
    para(doc, d.get("title", ""), rtl, size=20, color=ACCENT, bold_all=True)
    if d.get("date_label") or d.get("date"):
        para(doc, f"{h['date']}: {d.get('date_label') or d['date']}", rtl, size=10, color=MUTED)
    if d.get("attendees"):
        para(doc, f"{h['attendees']}: " + "، ".join(d["attendees"]) if rtl else f"{h['attendees']}: " + ", ".join(d["attendees"]),
             rtl, size=10, color=MUTED)
    if d.get("summary"):
        heading(doc, h["summary"], rtl)
        para(doc, d["summary"], rtl, size=12, bold_all=True)
    if d.get("decisions"):
        heading(doc, h["decisions"], rtl)
        bullets(doc, d["decisions"], rtl)
    if d.get("tasks"):
        heading(doc, h["tasks"], rtl)
        table(doc, task_rows(d, h), rtl)
    if d.get("carried"):
        heading(doc, h["carried"], rtl)
        table(doc, carried_rows(d, h), rtl)
    if len(d.get("numbers") or []) > 1:
        heading(doc, h["numbers"], rtl)
        table(doc, d["numbers"], rtl)
    if d.get("open_questions"):
        heading(doc, h["open_questions"], rtl)
        bullets(doc, d["open_questions"], rtl)
    if d.get("next_meeting"):
        heading(doc, h["next_meeting"], rtl)
        para(doc, d["next_meeting"], rtl)
    doc.save(path)


def md(text: str) -> str:
    return BOLD_RE.sub(r"<b>\1</b>", html.escape(str(text)))


def html_table(rows: list) -> str:
    head = "".join(f"<th>{md(x)}</th>" for x in rows[0])
    body = "".join("<tr>" + "".join(f"<td>{md(x)}</td>" for x in r) + "</tr>" for r in rows[1:])
    return f"<table><tr>{head}</tr>{body}</table>"


def build_html(d: dict, path: str) -> None:
    rtl = d.get("lang", "ar") == "ar"
    h = labels(d)
    out = [f"<h1>{md(d.get('title', ''))}</h1>"]
    if d.get("date_label") or d.get("date"):
        out.append(f"<p class='meta'>{h['date']}: {md(d.get('date_label') or d['date'])}</p>")
    if d.get("attendees"):
        out.append(f"<p class='meta'>{h['attendees']}: {md(('، ' if rtl else ', ').join(d['attendees']))}</p>")
    if d.get("summary"):
        out.append(f"<h2>{h['summary']}</h2><p class='head'>{md(d['summary'])}</p>")
    if d.get("decisions"):
        out.append(f"<h2>{h['decisions']}</h2><ul>" + "".join(f"<li>{md(x)}</li>" for x in d["decisions"]) + "</ul>")
    if d.get("tasks"):
        out.append(f"<h2>{h['tasks']}</h2>" + html_table(task_rows(d, h)))
    if d.get("carried"):
        out.append(f"<h2>{h['carried']}</h2>" + html_table(carried_rows(d, h)))
    if len(d.get("numbers") or []) > 1:
        out.append(f"<h2>{h['numbers']}</h2>" + html_table(d["numbers"]))
    if d.get("open_questions"):
        out.append(f"<h2>{h['open_questions']}</h2><ul>" + "".join(f"<li>{md(x)}</li>" for x in d["open_questions"]) + "</ul>")
    if d.get("next_meeting"):
        out.append(f"<h2>{h['next_meeting']}</h2><p>{md(d['next_meeting'])}</p>")
    page = f"""<!doctype html><html lang="{'ar' if rtl else 'en'}" dir="{'rtl' if rtl else 'ltr'}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(d.get('title', 'Meeting notes'))}</title>
<style>body{{font-family:Arial,Tahoma,sans-serif;max-width:760px;margin:32px auto;padding:0 24px;color:#1b2430;line-height:1.6;background:#fff}}
h1{{color:#1F3A5F;margin:0 0 4px;font-size:26px}}h2{{color:#1F3A5F;font-size:17px;margin:22px 0 6px;border-bottom:2px solid #e6ebf2;padding-bottom:4px}}
.meta{{color:#555F6D;font-size:13px;margin:0}}.head{{font-weight:bold;font-size:16px}}table{{border-collapse:collapse;width:100%;font-size:14px}}
th,td{{border:1px solid #d5dde8;padding:6px 8px;text-align:start}}th{{background:#eef3f9}}li{{margin:3px 0}}</style></head><body>
{''.join(out)}</body></html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)


def build_tracker(d: dict, path: str, previous: str | None) -> None:
    """Running task list: last meeting's rows (status updated from 'carried') + this meeting's tasks."""
    lang = "ar" if d.get("lang", "ar") == "ar" else "en"
    h = labels(d)
    rows = []
    if previous and os.path.exists(previous):
        ws_old = load_workbook(previous).active
        rows = [list(r) for r in ws_old.iter_rows(min_row=2, values_only=True) if any(r)]
    status_of = {c.get("task", "").strip(): h.get(c.get("status", "open"), c.get("status", ""))
                 for c in d.get("carried", [])}
    rows = [r[:5] + [status_of.get(str(r[3]).strip(), r[5])] for r in rows]
    for t in d.get("tasks", []):
        rows.append([d.get("date", ""), d.get("title", ""), t.get("owner", ""), t.get("task", ""),
                     t.get("due") or t.get("due_label", ""), h["open"]])
    wb = Workbook()
    ws = wb.active
    ws.title = "Tasks" if lang == "en" else "المهام"
    ws.sheet_view.rightToLeft = lang == "ar"
    ws.append(TRACKER_HEAD[lang])
    for r in rows:
        ws.append(r)
    fill = PatternFill("solid", fgColor="1F3A5F")
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = fill
    for col, width in zip("ABCDEF", (14, 34, 16, 48, 14, 12)):
        ws.column_dimensions[col].width = width
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    wb.save(path)


def main() -> None:
    if len(sys.argv) not in (3, 4):
        print("Usage: python make_notes.py notes.json OUT_DIR [last_meeting_tasks.xlsx]")
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    build_docx(data, os.path.join(out, "meeting-notes.docx"))
    build_html(data, os.path.join(out, "meeting-notes.html"))
    build_tracker(data, os.path.join(out, "meeting-tasks.xlsx"), sys.argv[3] if len(sys.argv) == 4 else None)
    print("written:", os.path.join(out, "meeting-notes.docx"), "+ meeting-tasks.xlsx")


if __name__ == "__main__":
    main()
