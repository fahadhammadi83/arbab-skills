"""Prospect emails: hand-written one-to-one outreach with approval, caps and a log. This tool never sends.

It picks companies, checks the emails Claude drafts, records YOUR approval, hands out ONE email at a time
for sending through your own connected mailbox, keeps the log, and lists follow-ups that are due.

    python outreach.py pick     --list scanned.csv [--date D]    companies to write to on day D
    python outreach.py check    [--date D]                       validate batch.json, write batch.md to review
    python outreach.py approve  [--date D] [--skip 2,5]          only on the user's own word
    python outreach.py next     [--date D] [--now HH:MM]         the next approved email to send, or WAIT/DONE
    python outreach.py mark     <id> sent|failed|bounced|replied|not-interested [--date D] [--note TEXT]
    python outreach.py due      [--date D]                       follow-ups due (touch 2 on day 5, touch 3 on day 14)
    python outreach.py halt     <reason>                         stops all sending
    python outreach.py status   [--date D]

Working folder: ./outreach (change with --dir). Settings: outreach/config.json (written on first run).
Kill switch: an empty file named STOP in the working folder. HALT is written on a warning; only you clear either.

Part of arbab-skills (github.com/fahadhammadi83/arbab-skills), CC BY-NC 4.0.
"""
from __future__ import annotations

import argparse
import csv
import difflib
import json
import re
import shutil
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_CONFIG = {
    "daily_cap": 20,              # outreach emails a day; keep it low on a new or warned mailbox
    "utc_offset_hours": 4,        # your time zone (4 = UAE)
    "window_start": "09:30",
    "window_end": "16:30",
    "min_gap_minutes": 15,        # spacing between two sends
    "send_days": [0, 1, 2, 3, 4], # Monday=0 ... Sunday=6
    "spares": 4,                  # extra candidates picked in case some fail the eye check
    "max_bounce_rate": 0.02,
    "min_sends_for_bounce_rule": 50,
    "max_bounces_per_day": 2,
    "similarity_limit": 0.6,      # two bodies more alike than this count as repeated text
    "banned_words": [],           # words that must never appear (competitors, sensitive topics)
    "followup_days": [5, 14],     # touch 2 and touch 3, counted from the first email
}
GENERIC_LOCAL_PARTS = frozenset({
    "info", "contact", "contactus", "hello", "hi", "inquiry", "inquiries", "enquiry", "enquiries", "sales",
    "admin", "office", "mail", "support", "team", "business", "marketing", "reception", "general", "connect",
    "care", "customercare", "service", "services", "clients", "booking", "bookings", "reservations",
})
LOG_FIELDS = ("date", "time", "id", "touch", "company", "to", "domain", "subject", "status", "note")
CLOSED = ("bounced", "replied", "not-interested")


class Desk:
    """One working folder: config, log, kill switches and a folder per sending day."""

    def __init__(self, folder: str | Path):
        self.dir = Path(folder)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.cfg_path, self.log_path = self.dir / "config.json", self.dir / "log.csv"
        if not self.cfg_path.exists():
            write_json(self.cfg_path, DEFAULT_CONFIG)
        self.cfg = dict(DEFAULT_CONFIG, **read_json(self.cfg_path, {}))
        self.tz = timezone(timedelta(hours=self.cfg["utc_offset_hours"]))

    def now(self) -> datetime:
        return datetime.now(self.tz)

    def day(self, d: str) -> Path:
        return self.dir / d

    def log(self) -> list[dict]:
        if not self.log_path.exists():
            return []
        with self.log_path.open(encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))

    def write_log(self, rows: list[dict]) -> None:
        with self.log_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=LOG_FIELDS)
            w.writeheader()
            w.writerows({k: r.get(k, "") for k in LOG_FIELDS} for r in rows)

    def append(self, row: dict) -> None:
        self.write_log(self.log() + [row])

    def contacted(self) -> set[str]:
        return {r["domain"] for r in self.log() if r["status"] in ("sent",) + CLOSED and r["domain"]}

    def stop_reason(self) -> str:
        if (self.dir / "STOP").exists():
            return "STOP file (kill switch)"
        if (self.dir / "HALT").exists():
            return "HALT: " + (self.dir / "HALT").read_text(encoding="utf-8").strip()
        return ""

    def bounce_reason(self) -> str:
        rows = [r for r in self.log() if r["status"] in ("sent", "bounced", "replied", "not-interested")]
        bounced = sum(1 for r in rows if r["status"] == "bounced")
        if len(rows) >= self.cfg["min_sends_for_bounce_rule"] and bounced / len(rows) > self.cfg["max_bounce_rate"]:
            return f"bounce rate {bounced}/{len(rows)} is over {self.cfg['max_bounce_rate']:.0%}"
        today = self.now().strftime("%Y-%m-%d")
        today_b = sum(1 for r in rows if r["status"] == "bounced" and r["date"] == today)
        if today_b >= self.cfg["max_bounces_per_day"]:
            return f"{today_b} bounces from today's sends (limit {self.cfg['max_bounces_per_day']})"
        return ""


# ---------- helpers ----------

def read_json(p: Path, default):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def write_json(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def domain_of_url(url: str) -> str:
    host = urlparse(url if "//" in url else "//" + url).hostname or ""
    return host.lower().removeprefix("www.")


def domain_of_email(addr: str) -> str:
    return addr.rsplit("@", 1)[-1].strip().lower() if "@" in addr else ""


def same_org(mail_dom: str, site_dom: str) -> bool:
    return bool(mail_dom and site_dom) and (mail_dom == site_dom or mail_dom.endswith("." + site_dom)
                                            or site_dom.endswith("." + mail_dom))


def is_generic_inbox(addr: str) -> bool:
    """Company inboxes only (info@, contact@ ...). A named person's address is personal data."""
    return addr.split("@", 1)[0].lower() in GENERIC_LOCAL_PARTS


def has_mx(domain: str) -> bool | None:
    """True/False from a DNS lookup, or None when this computer has no nslookup (then skip the check)."""
    if not shutil.which("nslookup"):
        return None
    try:
        out = subprocess.run(["nslookup", "-type=mx", domain], capture_output=True, text=True, timeout=15).stdout
    except (OSError, subprocess.TimeoutExpired):
        return False
    return "mail exchanger" in out.lower() or "mx preference" in out.lower()


def first_email(cell: str) -> str:
    m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", cell or "")
    return m.group(0).lower() if m else ""


# ---------- commands ----------

def pick(desk: Desk, lists: list[str], d: str, mx=has_mx) -> list[dict]:
    if date.fromisoformat(d).weekday() not in desk.cfg["send_days"]:
        print(f"NO SEND DAY: {d} is not a sending day.")
        return []
    if reason := desk.stop_reason():
        print(f"STOPPED: {reason}")
        return []
    rows = []
    for path in lists:
        with open(path, encoding="utf-8-sig", newline="") as f:
            rows += list(csv.DictReader(f))
    done, want = desk.contacted(), desk.cfg["daily_cap"] + desk.cfg["spares"]
    picked, skipped = [], dict.fromkeys(("no gap", "site not readable", "no email", "not own domain",
                                         "already contacted", "named person", "no mail server"), 0)
    mx_skipped = False
    for r in rows:
        if len(picked) >= want:
            break
        email = first_email(r.get("email", ""))
        site_dom, mail_dom = domain_of_url(r.get("website", "")), domain_of_email(email)
        gap = (r.get("lead_signal") or r.get("gap") or "").strip()
        status = r.get("site_status", "ok")
        reason = ("site not readable" if status not in ("ok", "") else "no gap" if not gap
                  else "no email" if not email else "not own domain" if not same_org(mail_dom, site_dom)
                  else "already contacted" if mail_dom in done or any(p["domain"] == mail_dom for p in picked)
                  else "named person" if not is_generic_inbox(email) else "")
        if not reason:
            ok = mx(mail_dom)
            mx_skipped = mx_skipped or ok is None
            reason = "no mail server" if ok is False else ""
        if reason:
            skipped[reason] += 1
            continue
        picked.append({"id": len(picked) + 1, "company": r.get("name") or r.get("company") or site_dom,
                       "website": r.get("website", ""), "to": email, "domain": mail_dom, "gap": gap,
                       "category": r.get("category", ""), "arabic_site": r.get("arabic", ""),
                       "whatsapp": r.get("whatsapp", ""), "booking": r.get("booking", "")})
    write_json(desk.day(d) / "candidates.json", picked)
    print(f"PICKED {len(picked)} of {want} wanted for {d} -> {desk.day(d) / 'candidates.json'}")
    print("skipped: " + ", ".join(f"{k} {v}" for k, v in skipped.items()))
    if mx_skipped:
        print("note: no nslookup on this computer, so the mail-server check was skipped")
    if len(picked) < desk.cfg["daily_cap"]:
        print(f"SHORT: only {len(picked)} qualify. Send fewer; never loosen the rules.")
    return picked


def validate(desk: Desk, batch: list[dict], candidates: list[dict], d: str) -> list[str]:
    problems, cand = [], {c["to"]: c for c in candidates}
    done, cfg = desk.contacted(), desk.cfg
    due_now = {x["to"]: x["touch"] for x in followups_due(desk, d)}
    if len(batch) > cfg["daily_cap"]:
        problems.append(f"{len(batch)} emails, the daily cap is {cfg['daily_cap']}")
    seen_to, seen_subj = set(), set()
    for e in batch:
        tag = f"#{e.get('id')} {e.get('company', '?')}"
        for k in ("id", "company", "to", "subject", "body"):
            if not str(e.get(k, "")).strip():
                problems.append(f"{tag}: missing {k}")
        to = str(e.get("to", "")).lower()
        touch = int(e.get("touch", 1))
        if touch > 1:  # a follow-up: allowed only when that company's next touch is due
            if due_now.get(to) != touch:
                problems.append(f"{tag}: touch {touch} to {to} is not due (run `due`)")
        else:
            if to not in cand:
                problems.append(f"{tag}: {to} is not in candidates.json")
            if domain_of_email(to) in done:
                problems.append(f"{tag}: {to} was already contacted")
        if to in seen_to:
            problems.append(f"{tag}: duplicate address")
        seen_to.add(to)
        subj = str(e.get("subject", "")).strip().lower()
        if subj in seen_subj:
            problems.append(f"{tag}: subject repeats another email")
        seen_subj.add(subj)
        if e.get("cc") or e.get("bcc"):
            problems.append(f"{tag}: no CC or BCC")
        if touch == 1 and re.search(r"https?://|www\.", str(e.get("body", ""))):
            problems.append(f"{tag}: no links in a first email")
        text = f"{e.get('subject', '')} {e.get('body', '')}".lower()
        problems += [f'{tag}: contains banned word "{w}"' for w in cfg["banned_words"] if w.lower() in text]
        if touch == 1 and not e.get("verified_on_site"):
            problems.append(f"{tag}: address not confirmed on the company's own site (verified_on_site)")
        if touch == 1 and not e.get("gap_checked"):
            problems.append(f"{tag}: gap not confirmed by eye (gap_checked)")
    bodies = [(e.get("id"), str(e.get("body", ""))) for e in batch]
    for i in range(len(bodies)):
        for j in range(i + 1, len(bodies)):
            ratio = difflib.SequenceMatcher(None, bodies[i][1], bodies[j][1]).ratio()
            if ratio > cfg["similarity_limit"]:
                problems.append(f"#{bodies[i][0]} and #{bodies[j][0]} are {ratio:.0%} alike: rewrite one")
    return problems


def check(desk: Desk, d: str) -> bool:
    batch = read_json(desk.day(d) / "batch.json", None)
    if batch is None:
        print(f"ERROR: no batch.json in {desk.day(d)}")
        return False
    problems = validate(desk, batch, read_json(desk.day(d) / "candidates.json", []), d)
    if problems:
        print("PROBLEMS:\n" + "\n".join("  - " + p for p in problems))
        return False
    lines = [f"# Outreach emails for {d} · {len(batch)} to approve", "",
             'Nothing is sent until you say "send them" (or "send them, skip 3 and 7").', ""]
    for e in batch:
        lines += [f"## {e['id']} · {e['company']}", "", f"To: {e['to']}  ", f"Gap: {e.get('gap_note', '')}  ",
                  f"Subject: {e['subject']}", "", e["body"], "", "---", ""]
    (desk.day(d) / "batch.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"OK: {len(batch)} emails pass. Review file: {desk.day(d) / 'batch.md'}")
    return True


def approve(desk: Desk, d: str, skip: set[int]) -> bool:
    batch = read_json(desk.day(d) / "batch.json", None)
    if batch is None:
        print(f"ERROR: no batch.json for {d}")
        return False
    problems = validate(desk, batch, read_json(desk.day(d) / "candidates.json", []), d)
    if problems:
        print("NOT APPROVED, the batch fails its checks: " + "; ".join(problems))
        return False
    ids = [e["id"] for e in batch if e["id"] not in skip]
    write_json(desk.day(d) / "approved.json", {"approved_at": desk.now().isoformat(timespec="minutes"),
                                               "ids": ids, "skipped": sorted(skip)})
    print(f"APPROVED {len(ids)} for {d} (skipped {sorted(skip) or 'none'}).")
    return True


def next_email(desk: Desk, d: str, now: str | None = None) -> dict | None:
    cfg = desk.cfg
    if reason := desk.stop_reason():
        print(f"WAIT: {reason}. Send nothing.")
        return None
    if reason := desk.bounce_reason():
        (desk.dir / "HALT").write_text(reason, encoding="utf-8")
        print(f"WAIT: HALT written, {reason}. Send nothing; tell the user.")
        return None
    if date.fromisoformat(d).weekday() not in cfg["send_days"]:
        print("WAIT: not a sending day.")
        return None
    appr = read_json(desk.day(d) / "approved.json", None)
    if appr is None:
        print("WAIT: today's batch is not approved yet.")
        return None
    now = now or desk.now().strftime("%H:%M")
    if not cfg["window_start"] <= now <= cfg["window_end"]:
        print(f"WAIT: {now} is outside {cfg['window_start']}-{cfg['window_end']}.")
        return None
    today = [r for r in desk.log() if r["date"] == d and r["status"] in ("sent",) + CLOSED]
    if len(today) >= cfg["daily_cap"]:
        print(f"DONE: {len(today)} sent today, cap {cfg['daily_cap']}.")
        return None
    if today:
        last = max(r["time"] for r in today)
        gap = int((datetime.strptime(now, "%H:%M") - datetime.strptime(last, "%H:%M")).total_seconds() // 60)
        if gap < cfg["min_gap_minutes"]:
            print(f"WAIT: last send {last}, only {gap} min ago.")
            return None
    handled = {r["id"] for r in desk.log() if r["date"] == d}
    batch, contacted = {e["id"]: e for e in read_json(desk.day(d) / "batch.json", [])}, desk.contacted()
    due_map = {x["to"]: x["touch"] for x in followups_due(desk, d)}
    for i in appr["ids"]:
        e = batch.get(i)
        if not e or str(i) in handled:
            continue
        follow_up_ok = int(e.get("touch", 1)) > 1 and due_map.get(e["to"]) == int(e.get("touch", 1))
        if domain_of_email(e["to"]) not in contacted or follow_up_ok:
            out = {k: e[k] for k in ("id", "company", "to", "subject", "body")}
            print("SEND " + json.dumps(out, ensure_ascii=False))
            return out
    print("DONE: every approved email for today is handled.")
    return None


def mark(desk: Desk, d: str, email_id: int, status: str, note: str = "") -> None:
    rows = desk.log()
    if status in ("bounced", "replied", "not-interested"):
        e = next((r for r in rows if r["id"] == str(email_id) and r["date"] == d), None)
        if e is None:
            print(f"ERROR: no logged email #{email_id} on {d}")
            return
        dom = e["domain"]
        for r in rows:  # closing a company closes every touch to it
            if r["domain"] == dom and r["status"] == "sent":
                r["status"], r["note"] = status, note or r["note"]
        desk.write_log(rows)
        print(f"MARKED {e['company']} {status}. No more follow-ups to {dom}.")
        if status == "bounced" and (reason := desk.bounce_reason()):
            (desk.dir / "HALT").write_text(reason, encoding="utf-8")
            print(f"HALT written: {reason}")
        return
    e = {x["id"]: x for x in read_json(desk.day(d) / "batch.json", [])}.get(email_id)
    if e is None:
        print(f"ERROR: no email #{email_id} in {d}")
        return
    desk.append({"date": d, "time": desk.now().strftime("%H:%M"), "id": e["id"], "touch": e.get("touch", 1),
                 "company": e["company"], "to": e["to"], "domain": domain_of_email(e["to"]),
                 "subject": e["subject"], "status": status, "note": note})
    print(f"MARKED #{email_id} {status}.")


def followups_due(desk: Desk, d: str) -> list[dict]:
    """Companies whose next touch is due: one first email, then touch 2 and touch 3 on the set days.
    A reply, a bounce or a no closes the company for good. Today's own sends don't count yet."""
    today, out = date.fromisoformat(d), []
    by_dom: dict[str, list[dict]] = {}
    for r in desk.log():
        by_dom.setdefault(r["domain"], []).append(r)
    for dom, rows in by_dom.items():
        if any(r["status"] in CLOSED for r in rows):
            continue
        sent = [r for r in rows if r["status"] == "sent" and r["date"] < d]
        if not sent or any(r["status"] == "sent" and r["date"] >= d for r in rows):
            continue
        first = min(date.fromisoformat(r["date"]) for r in sent)
        touches = len(sent)
        days = desk.cfg["followup_days"]
        if touches <= len(days) and (today - first).days >= days[touches - 1]:
            out.append({"company": sent[0]["company"], "to": sent[0]["to"], "touch": touches + 1,
                        "first_sent": first.isoformat(), "last_subject": sent[-1]["subject"]})
    return out


def due(desk: Desk, d: str) -> list[dict]:
    out = followups_due(desk, d)
    for x in out:
        print(f"DUE touch {x['touch']}: {x['company']} <{x['to']}> (first email {x['first_sent']})")
    if not out:
        print("No follow-ups due.")
    return out


def status(desk: Desk, d: str) -> None:
    rows = desk.log()
    dd = desk.day(d)
    print(f"stop: {desk.stop_reason() or 'none'}")
    print(f"{d}: batch {'yes' if (dd / 'batch.json').exists() else 'no'}, "
          f"approved {'yes' if (dd / 'approved.json').exists() else 'no'}, "
          f"sent today {sum(1 for r in rows if r['date'] == d and r['status'] != 'failed')}")
    counts = {s: sum(1 for r in rows if r["status"] == s) for s in ("sent",) + CLOSED}
    print("all time: " + ", ".join(f"{k} {v}" for k, v in counts.items()) + f", cap {desk.cfg['daily_cap']}/day")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default="outreach")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("pick", "check", "approve", "next", "mark", "due", "halt", "status"):
        p = sub.add_parser(name)
        p.add_argument("--date")
        if name == "pick":
            p.add_argument("--list", action="append", required=True)
        if name == "approve":
            p.add_argument("--skip", default="")
        if name == "next":
            p.add_argument("--now")
        if name == "mark":
            p.add_argument("id", type=int)
            p.add_argument("status", choices=("sent", "failed", "bounced", "replied", "not-interested"))
            p.add_argument("--note", default="")
        if name == "halt":
            p.add_argument("reason")
    a = ap.parse_args(argv)
    desk = Desk(a.dir)
    d = a.date or desk.now().date().isoformat()
    if a.cmd == "pick":
        pick(desk, a.list, d)
    elif a.cmd == "check":
        return 0 if check(desk, d) else 1
    elif a.cmd == "approve":
        return 0 if approve(desk, d, {int(x) for x in a.skip.split(",") if x.strip()}) else 1
    elif a.cmd == "next":
        next_email(desk, d, a.now)
    elif a.cmd == "mark":
        mark(desk, d, a.id, a.status, a.note)
    elif a.cmd == "due":
        due(desk, d)
    elif a.cmd == "halt":
        (desk.dir / "HALT").write_text(f"{desk.now():%Y-%m-%d %H:%M} {a.reason}", encoding="utf-8")
        print("HALT written. All sending stops until you delete the HALT file.")
    else:
        status(desk, d)
    return 0


if __name__ == "__main__":
    sys.exit(main())
