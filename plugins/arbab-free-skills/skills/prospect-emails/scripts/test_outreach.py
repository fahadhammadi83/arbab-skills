"""Offline tests for outreach.py. Run: python -m pytest test_outreach.py -q"""
import csv
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import outreach as o  # noqa: E402

MON, TUE, SAT = "2026-11-30", "2026-12-01", "2026-12-05"
ROWS = [
    {"name": "Lina Beauty", "website": "https://linabeauty.example", "email": "info@linabeauty.example",
     "site_status": "ok", "lead_signal": "No Arabic version of the site"},
    {"name": "Sara Person", "website": "https://sarafirm.example", "email": "sara@sarafirm.example",
     "site_status": "ok", "lead_signal": "No WhatsApp"},
    {"name": "Gmail Shop", "website": "https://gshop.example", "email": "gshop@gmail.com",
     "site_status": "ok", "lead_signal": "No booking"},
    {"name": "No Gap Co", "website": "https://nogap.example", "email": "info@nogap.example",
     "site_status": "ok", "lead_signal": ""},
    {"name": "Fast Freight", "website": "https://fastfreight.example", "email": "sales@fastfreight.example",
     "site_status": "ok", "lead_signal": "Running Meta ads, no online booking"},
]


def make_list(tmp):
    path = tmp / "scanned.csv"
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(ROWS[0]))
        w.writeheader()
        w.writerows(ROWS)
    return str(path)


def email(i, to, company, body, **extra):
    return dict({"id": i, "company": company, "to": to, "subject": f"Quick note for {company}", "body": body,
                 "gap_note": "seen", "verified_on_site": True, "gap_checked": True}, **extra)


BODY_A = "Hello Lina Beauty team, I noticed your site is English only while many of your clients book in Arabic."
BODY_B = "Hi Fast Freight, your Meta ads send people to a page with no way to request a quote or book a pickup."


def ready_day(tmp, d=MON):
    desk = o.Desk(tmp / "out")
    picked = o.pick(desk, [make_list(tmp)], d, mx=lambda dom: True)
    o.write_json(desk.day(d) / "batch.json", [
        email(1, "info@linabeauty.example", "Lina Beauty", BODY_A),
        email(2, "sales@fastfreight.example", "Fast Freight", BODY_B)])
    return desk, picked


def test_pick_keeps_company_inboxes_with_a_gap_only(tmp_path):
    desk, picked = ready_day(tmp_path)
    assert [p["to"] for p in picked] == ["info@linabeauty.example", "sales@fastfreight.example"]


def test_pick_skips_weekend_and_kill_switch(tmp_path):
    desk = o.Desk(tmp_path / "out")
    assert o.pick(desk, [make_list(tmp_path)], SAT, mx=lambda d: True) == []
    (desk.dir / "STOP").touch()
    assert o.pick(desk, [make_list(tmp_path)], MON, mx=lambda d: True) == []


def test_check_catches_links_repeats_and_unverified(tmp_path):
    desk, _ = ready_day(tmp_path)
    bad = [email(1, "info@linabeauty.example", "Lina Beauty", BODY_A + " See https://x.example"),
           email(2, "sales@fastfreight.example", "Fast Freight", BODY_A + " See https://x.example",
                 verified_on_site=False)]
    problems = o.validate(desk, bad, o.read_json(desk.day(MON) / "candidates.json", []), MON)
    text = " ".join(problems)
    assert "no links" in text and "alike" in text and "verified_on_site" in text


def test_nothing_sends_before_approval_then_one_at_a_time(tmp_path):
    desk, _ = ready_day(tmp_path)
    desk.now = lambda: o.datetime(2026, 11, 30, 10, 0, tzinfo=desk.tz)  # the send is logged at 10:00
    assert o.next_email(desk, MON, "10:00") is None          # not approved
    assert o.check(desk, MON) and o.approve(desk, MON, set())
    first = o.next_email(desk, MON, "10:00")
    assert first["id"] == 1
    o.mark(desk, MON, 1, "sent")
    assert o.next_email(desk, MON, "10:05") is None           # 15-minute gap
    assert o.next_email(desk, MON, "08:00") is None           # outside the window
    assert o.next_email(desk, MON, "10:30")["id"] == 2


def test_approve_with_skip(tmp_path):
    desk, _ = ready_day(tmp_path)
    o.approve(desk, MON, {1})
    assert o.next_email(desk, MON, "10:00")["id"] == 2


def test_never_contacts_a_company_twice(tmp_path):
    desk, _ = ready_day(tmp_path)
    o.approve(desk, MON, set())
    o.mark(desk, MON, 1, "sent")
    picked_again = o.pick(desk, [make_list(tmp_path)], TUE, mx=lambda d: True)
    assert "info@linabeauty.example" not in [p["to"] for p in picked_again]


def test_followups_due_on_day_5_and_stop_on_reply(tmp_path):
    desk, _ = ready_day(tmp_path)
    o.approve(desk, MON, set())
    o.mark(desk, MON, 1, "sent")
    o.mark(desk, MON, 2, "sent")
    assert o.followups_due(desk, "2026-12-03") == []          # day 3: too early
    due = o.followups_due(desk, "2026-12-05")                 # day 5
    assert {x["to"] for x in due} == {"info@linabeauty.example", "sales@fastfreight.example"}
    o.mark(desk, MON, 2, "replied", "asked for a call")
    assert [x["to"] for x in o.followups_due(desk, "2026-12-05")] == ["info@linabeauty.example"]


def test_followup_email_passes_only_when_due(tmp_path):
    desk, _ = ready_day(tmp_path)
    o.approve(desk, MON, set())
    o.mark(desk, MON, 1, "sent")
    fu = [email(1, "info@linabeauty.example", "Lina Beauty", "One more thing since my last note.", touch=2,
                verified_on_site=False, gap_checked=False)]
    assert o.validate(desk, fu, [], "2026-12-02")             # day 2: not due
    assert o.validate(desk, fu, [], "2026-12-07") == []       # day 7: due


def test_two_bounces_in_a_day_halt_everything(tmp_path):
    desk, _ = ready_day(tmp_path)
    o.approve(desk, MON, set())
    today = desk.now().date().isoformat()
    o.write_json(desk.day(today) / "batch.json", o.read_json(desk.day(MON) / "batch.json", []))
    o.mark(desk, today, 1, "sent")
    o.mark(desk, today, 2, "sent")
    o.mark(desk, today, 1, "bounced")
    o.mark(desk, today, 2, "bounced")
    assert (desk.dir / "HALT").exists()
    assert o.next_email(desk, MON, "11:00") is None


def test_config_written_on_first_run(tmp_path):
    desk = o.Desk(tmp_path / "out")
    cfg = json.loads((desk.dir / "config.json").read_text(encoding="utf-8"))
    assert cfg["daily_cap"] == 20 and cfg["followup_days"] == [5, 14]
