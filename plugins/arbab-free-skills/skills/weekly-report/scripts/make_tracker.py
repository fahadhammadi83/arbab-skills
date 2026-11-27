"""Add this week's report to a running Excel tracker (creates it on week 1).

Usage: python make_tracker.py report.json OUT_DIR [last_week_tracker.xlsx]
Needs: pip install openpyxl
Writes OUT_DIR/weekly-tracker.xlsx with three sheets:
  Weeks       one row per week: headline, counts, and every numeric metric
  Items       every in-progress / blocked item with its status history
  Chart       a line chart of up to three metrics across the weeks
"""
import json
import os
import re
import sys

from openpyxl import Workbook, load_workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.styles import Alignment, Font, PatternFill

NUM_RE = re.compile(r"-?\d[\d,]*\.?\d*")
HEAD_FILL = PatternFill("solid", fgColor="EEF3F9")
BOLD = Font(bold=True, color="1F3A5F")


def to_number(text: str) -> float | None:
    """First number in a cell ("AED 7,200/month" -> 7200). None if there is none."""
    m = NUM_RE.search(str(text).replace("٬", ","))
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def metrics(report: dict) -> dict[str, float]:
    """Metric name -> number, from the report's numbers table (header row skipped)."""
    out: dict[str, float] = {}
    for row in (report.get("numbers") or [])[1:]:
        if len(row) >= 2:
            val = to_number(row[1])
            if val is not None:
                out[str(row[0]).strip()] = val
    return out


def write_header(ws, names: list[str]) -> None:
    """Put the header in row 1 of a new sheet (an empty sheet already has row 1)."""
    if ws.cell(1, 1).value is None:
        for c, name in enumerate(names, start=1):
            ws.cell(1, c, name)


def style_header(ws, rtl: bool) -> None:
    for cell in ws[1]:
        cell.font = BOLD
        cell.fill = HEAD_FILL
        cell.alignment = Alignment(horizontal="right" if rtl else "left", wrap_text=True)
    ws.sheet_view.rightToLeft = rtl


def update_weeks(wb, report: dict, rtl: bool) -> None:
    ws = wb["Weeks"] if "Weeks" in wb.sheetnames else wb.create_sheet("Weeks")
    write_header(ws, ["Week", "Headline", "Done", "Blockers"])
    header = [c.value for c in ws[1]]
    m = metrics(report)
    for name in m:
        if name not in header:
            header.append(name)
            ws.cell(1, len(header), name)
    week = report.get("week", "")
    row_vals = {
        "Week": week,
        "Headline": BOLD_STRIP(report.get("headline", "")),
        "Done": len(report.get("done") or []),
        "Blockers": max(len(report.get("blockers") or []) - 1, 0),
        **m,
    }
    target = None
    for r in range(2, ws.max_row + 1):
        if ws.cell(r, 1).value == week:
            target = r
            break
    target = target or ws.max_row + 1
    for c, name in enumerate(header, start=1):
        if name in row_vals:
            ws.cell(target, c, row_vals[name])
    style_header(ws, rtl)
    ws.column_dimensions["B"].width = 60


def update_items(wb, report: dict, rtl: bool) -> None:
    ws = wb["Items"] if "Items" in wb.sheetnames else wb.create_sheet("Items")
    write_header(ws, ["Item", "Status", "First seen", "Last update"])
    week = report.get("week", "")
    current: dict[str, str] = {}
    for row in (report.get("in_progress") or [])[1:]:
        current[str(row[0])] = str(row[1]) if len(row) > 1 else ""
    for row in (report.get("blockers") or [])[1:]:
        current[str(row[0])] = "blocked: " + (str(row[1]) if len(row) > 1 else "")
    existing = {ws.cell(r, 1).value: r for r in range(2, ws.max_row + 1)}
    for item, status in current.items():
        if item in existing:
            r = existing[item]
            ws.cell(r, 2, status)
            ws.cell(r, 4, week)
        else:
            ws.append([item, status, week, week])
    for item, r in existing.items():
        if item not in current and not str(ws.cell(r, 2).value).startswith("closed"):
            ws.cell(r, 2, f"closed or dropped by {week}")
    style_header(ws, rtl)
    ws.column_dimensions["A"].width = 45
    ws.column_dimensions["B"].width = 40


def update_chart(wb, rtl: bool) -> None:
    if "Chart" in wb.sheetnames:
        del wb["Chart"]
    ws_w = wb["Weeks"]
    if ws_w.max_row < 2 or ws_w.max_column < 5:
        return
    chart_ws = wb.create_sheet("Chart")
    chart_ws.sheet_view.rightToLeft = rtl
    chart = LineChart()
    chart.title = "Week by week"
    chart.height, chart.width = 9, 18
    last_col = min(ws_w.max_column, 7)
    data = Reference(ws_w, min_col=5, max_col=last_col, min_row=1, max_row=ws_w.max_row)
    cats = Reference(ws_w, min_col=1, min_row=2, max_row=ws_w.max_row)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    chart_ws.add_chart(chart, "B2")


def BOLD_STRIP(text: str) -> str:  # noqa: N802 - tiny helper, reads as a constant op
    return str(text).replace("**", "")


def main() -> None:
    if len(sys.argv) not in (3, 4):
        print("Usage: python make_tracker.py report.json OUT_DIR [last_week_tracker.xlsx]")
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as f:
        report = json.load(f)
    rtl = report.get("lang", "ar") == "ar"
    if len(sys.argv) == 4 and os.path.exists(sys.argv[3]):
        wb = load_workbook(sys.argv[3])
    else:
        wb = Workbook()
        wb.active.title = "Weeks"
    update_weeks(wb, report, rtl)
    update_items(wb, report, rtl)
    update_chart(wb, rtl)
    os.makedirs(sys.argv[2], exist_ok=True)
    path = os.path.join(sys.argv[2], "weekly-tracker.xlsx")
    wb.save(path)
    print("written:", path)


if __name__ == "__main__":
    main()
