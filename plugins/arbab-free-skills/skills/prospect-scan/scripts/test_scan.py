"""Offline tests for scan.py (no network). Run: python -m pytest test_scan.py -q"""
import csv
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import scan  # noqa: E402

PLACE = {"source": "t.csv", "name": "Test Salon", "category": "Salon", "phone": "+971 50 123 4567",
         "rating": "4.8", "reviews": "120", "address": "Dubai", "maps_url": "", "website": "https://salon.example"}


def page(body, lang="en"):
    return f'<html lang="{lang}"><body>{body}<footer>© 2026</footer></body></html>'


def reader_for(html, robots="", sitemap=""):
    return lambda url: scan.signals_from(html, url, robots, sitemap, "")


def test_no_website_is_the_top_gap():
    row = scan.check(dict(PLACE, website=""))
    assert row["site_status"] == "none"
    assert row["lead_signal"] == "No website on the listing"


def test_instagram_only_counts_as_social():
    row = scan.check(dict(PLACE, website="https://instagram.com/salon"))
    assert row["site_status"] == "social"
    assert "social or booking page" in row["lead_signal"]


def test_dead_site_vs_blocked_site():
    dead = scan.check(PLACE, lambda u: {"ran": False, "error": "HTTP Error 404: Not Found"})
    blocked = scan.check(PLACE, lambda u: {"ran": False, "error": "HTTP Error 403: Forbidden"})
    assert dead["site_status"] == "dead" and dead["lead_signal"]
    assert blocked["site_status"] == "blocked" and blocked["lead_signal"] == ""


def test_ads_without_booking_or_whatsapp():
    html = page('<script src="https://connect.facebook.net/en_US/fbevents.js"></script>')
    row = scan.check(PLACE, reader_for(html))
    assert row["lead_signal"] == "Running Meta ads, no online booking or WhatsApp on the site"


def test_missing_arabic_is_a_gap_and_arabic_site_is_not():
    full = '<a href="https://wa.me/971501234567">WhatsApp</a> Book now'
    assert scan.check(PLACE, reader_for(page(full)))["lead_signal"] == "No Arabic version of the site"
    assert scan.check(PLACE, reader_for(page(full, "ar")))["lead_signal"] == ""


def test_footer_credit_names_the_agency():
    html = '<html><body><footer>Website by <a href="https://agency.example">Pixel Agency</a></footer></body></html>'
    assert scan.built_by(html, "salon.example") == "Pixel Agency"


def test_ai_bots_blocked_from_robots():
    assert scan.ai_bots_blocked("User-agent: GPTBot\nDisallow: /\n") == ["gptbot"]
    assert scan.ai_bots_blocked("User-agent: *\nDisallow: /admin\n") == []


def test_channel_from_phone():
    assert scan.channel("+971 50 123 4567") == "whatsapp"
    assert scan.channel("04 123 4567") == "call"
    assert scan.channel("") == "instagram or linkedin"


def test_rank_puts_reasons_first_and_blocked_last():
    rows = [dict(site_status="blocked", lead_signal="", score="", reviews="500"),
            dict(site_status="ok", lead_signal="", score="40", reviews="10"),
            dict(site_status="ok", lead_signal="No Arabic version of the site", score="70", reviews="10")]
    ranked = scan.rank(rows)
    assert ranked[0]["lead_signal"] and ranked[-1]["site_status"] == "blocked"


def write_list(path, sites):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["name", "website", "phone"])
        w.writeheader()
        for i, s in enumerate(sites):
            w.writerow({"name": f"Biz {i}", "website": s, "phone": ""})


def test_run_never_scans_a_business_twice(tmp_path):
    lst = tmp_path / "list.csv"
    write_list(lst, ["a.example", "www.a.example/about", "b.example", ""])
    out = tmp_path / "out"
    reader = reader_for(page("hello"))
    scan.run([str(lst)], out, 50, 1, reader)
    first = scan.read_csv(out / "scanned.csv")
    assert len(first) == 3  # a.example once, b.example, and the listing with no website
    assert scan.run([str(lst)], out, 50, 1, reader) is None  # queue empty, nothing rescanned
    assert len(scan.read_csv(out / "scanned.csv")) == 3


def test_batch_cap_and_kill_switch(tmp_path):
    lst = tmp_path / "list.csv"
    write_list(lst, [f"site{i}.example" for i in range(80)])
    out = tmp_path / "out"
    scan.run([str(lst)], out, 500, 1, reader_for(page("x")))
    assert len(scan.read_csv(out / "scanned.csv")) == scan.MAX_BATCH
    (out / "STOP").touch()
    assert scan.run([str(lst)], out, 50, 1, reader_for(page("x"))) is None
    assert len(scan.read_csv(out / "scanned.csv")) == scan.MAX_BATCH
