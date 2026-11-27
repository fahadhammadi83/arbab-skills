"""Offline tests for audit.py. Run: python -m pytest test_audit.py -q"""
import datetime
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import audit as a  # noqa: E402

DAY = datetime.date(2026, 11, 30)
PAGE = ('<html lang="en"><body><form></form><a href="https://wa.me/971500000000?text=Hi">WhatsApp</a> '
        'Book now · 120 happy clients · Google rating reviews <a href="https://instagram.com/lina.beauty">IG</a>'
        '</body></html>')


def fake_lh(perf):
    return lambda url, out: {"ran": True, "date": "2026-11-30", "perf": perf, "lcp": "2.1 s"}


def start(tmp, page=PAGE, perf=82, lang="en"):
    return a.init("lina.example", "Lina Beauty", lang=lang, out=str(tmp), today=DAY,
                  fetcher=lambda u: (page, ""), lighthouse=fake_lh(perf))


def load(folder):
    return json.loads((folder / "checks.json").read_text(encoding="utf-8"))


def test_init_scores_what_a_script_can_see(tmp_path):
    c = load(start(tmp_path))
    r = c["rules"]
    assert r["speed"]["score"] == 7 and not r["speed"]["not_tested"]
    assert r["whatsapp"]["score"] == 5 and r["whatsapp"]["not_tested"]  # never messaged
    assert r["lead_capture"]["score"] == 10  # form + WhatsApp + booking
    assert r["gbp"]["not_tested"] and r["gbp"]["score"] == a.NOT_TESTED_POINTS
    assert c["auto"]["site"]["instagram"] == ["lina.beauty"]


def test_unreadable_site_never_gets_guessed_scores(tmp_path):
    folder = a.init("down.example", "Down Co", out=str(tmp_path), today=DAY,
                    fetcher=lambda u: ("", "HTTP Error 404"), lighthouse=fake_lh(99))
    r = load(folder)["rules"]
    assert all(r[k]["not_tested"] for k in a.RULES)
    assert r["speed"]["score"] == a.NOT_TESTED_POINTS  # Lighthouse isn't run on a site we couldn't read


def test_build_refuses_empty_evidence_and_missing_fixes(tmp_path):
    folder = start(tmp_path)
    assert a.build(folder, pdf=False) is None
    assert not (folder / "report-en.html").exists()


def fill(folder, lang="en"):
    c = load(folder)
    for k in a.RULES:
        if not c["rules"][k][f"evidence_{lang}"]:
            c["rules"][k][f"evidence_{lang}"] = "not tested" if c["rules"][k]["not_tested"] else "seen"
    c["top_fixes"][lang] = [{"fix": "Claim the Google profile", "why": "Most buyers start on Maps", "effort": "1 hour"},
                            {"fix": "Add an Arabic page", "why": "Half the searches are Arabic", "effort": "2 days"},
                            {"fix": "Show named results", "why": "Proof builds trust", "effort": "1 day"}]
    (folder / "checks.json").write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    return c


def test_build_writes_report_and_message_with_the_right_total(tmp_path):
    folder = start(tmp_path)
    c = fill(folder)
    total = a.build(folder, pdf=False)
    assert total == sum(c["rules"][k]["score"] for k in a.RULES)
    page = (folder / "report-en.html").read_text(encoding="utf-8")
    assert f"<b>{total}</b>" in page and "Lina Beauty" in page and "not tested" in page
    msg = (folder / "message.txt").read_text(encoding="utf-8")
    assert f"{total}/70" in msg and "claim the Google profile" in msg


def test_arabic_report_is_right_to_left(tmp_path):
    folder = a.init("lina.example", "Lina Beauty", lang="ar", name_ar="لينا بيوتي", out=str(tmp_path), today=DAY,
                    fetcher=lambda u: (PAGE, ""), lighthouse=fake_lh(95))
    fill(folder, "ar")
    a.build(folder, pdf=False)
    page = (folder / "report-ar.html").read_text(encoding="utf-8")
    assert 'dir="rtl"' in page and "لينا بيوتي" in page


def test_placeholder_text_is_caught(tmp_path):
    folder = start(tmp_path)
    c = fill(folder)
    c["rules"]["gbp"]["evidence_en"] = "TODO"
    (folder / "checks.json").write_text(json.dumps(c), encoding="utf-8")
    assert a.build(folder, pdf=False) is None


def test_speed_bands():
    sig = {"ran": False}
    assert a.auto_rules(sig, {"ran": True, "perf": 91, "lcp": "1 s"})["speed"]["score"] == 10
    assert a.auto_rules(sig, {"ran": True, "perf": 49, "lcp": "9 s"})["speed"]["score"] == 2


def test_init_never_overwrites_a_filled_audit(tmp_path):
    folder = start(tmp_path)
    fill(folder)
    again = start(tmp_path)
    assert again == folder and load(folder)["top_fixes"]["en"][0]["fix"] == "Claim the Google profile"
