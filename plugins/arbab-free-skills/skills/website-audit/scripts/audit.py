"""Website audit: seven proof checks on one business, scored /70, as a clean report (HTML, plus PDF when Chrome or
Edge is installed) and a short message to send with it. English or Arabic.

    python audit.py init  --url https://business.example --name "Business" [--lang en|ar] [--name-ar "..."]
                          [--by "Your Company"] [--contact "https://wa.me/971500000000"] [--out audits] [--no-speed]
        -> audits/<date>-<slug>-<lang>/checks.json with the automatic checks done (homepage signals, phone speed via
           Lighthouse when Node.js is installed) and the manual checks marked "not tested". Fill those, then:
    python audit.py build audits/<date>-<slug>-<lang>
        -> report-<lang>.html, report-<lang>.pdf (when Chrome/Edge is found), message.txt

Seven rules, each 0-10, total /70 (rubric in RUBRIC below). Never invent a number: a check that didn't run says
"not tested" and takes 3 points. Part of arbab-skills (github.com/fahadhammadi83/arbab-skills), CC BY-NC 4.0.
"""
import datetime
import html
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

RULES = ["gbp", "speed", "local_search", "whatsapp", "proof", "cadence", "lead_capture"]
NOT_TESTED_POINTS = 3
RUBRIC = {
    "gbp": "Google Business Profile: 0 none · 3 exists, 0 reviews or unverified · 6 under 10 reviews or under 4.5 stars "
           "· 8 10-50 reviews at 4.5+ · 10 over 50 reviews at 4.5+",
    "speed": "Lighthouse mobile performance: 90+ = 10 · 70-89 = 7 · 50-69 = 4 · under 50 = 2",
    "local_search": "Best Google position on three buyer searches in the customers' language (UAE: Arabic): "
                    "#1-3 = 10 · page 1 = 7 · page 2 = 4 · absent but has pages in that language = 1 · none = 0",
    "whatsapp": "Never message the business to test. WhatsApp link on the site = 5 (not tested) · none = 0",
    "proof": "Named real clients with numbers on the first screen = 10 · numbers without names = 5 · "
             "testimonials without numbers = 4 · none = 2",
    "cadence": "Instagram posting days in the last 30: 20+ = 10 · 12-19 = 7 · 4-11 = 4 · 1-3 = 1 · no account = 0",
    "lead_capture": "Form + WhatsApp + booking = 10 · form or prefilled WhatsApp = 7 · WhatsApp link only = 5 · "
                    "phone link only = 3 · nothing = 0",
}
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/124.0 Safari/537.36")
BOOKING = (r"calendly\.com", r"acuityscheduling", r"fresha\.com", r"booksy\.com", r"vagaro\.com", r"setmore",
           r"simplybook", r"bookings\.zoho", r"book(ing)?[-_ ]?now", r"book[-_ ]an?[-_ ]appointment", r"احجز")

T = {
    "en": {
        "dir": "ltr", "title": "Website audit: {name}", "sub": "Seven proof checks on {url} · {date}{by}",
        "by": " · by {by}", "score": "Score", "of": "/ 70", "cols": ["#", "Check", "Score", "What we found"],
        "rules": {"gbp": "Google Business Profile and reviews", "speed": "Website speed on a phone",
                  "local_search": "Search visibility in the customers' language", "whatsapp": "WhatsApp path",
                  "proof": "Proof on the site", "cadence": "Instagram activity (30 days)",
                  "lead_capture": "Lead capture"},
        "fixes_h": "The three fixes that matter most", "fix_cols": ["Fix", "Why it matters", "Effort"],
        "next_h": "Next step", "method_h": "How we checked",
        "method": "Google searches from the UAE, a Lighthouse mobile test ({lh}), the public homepage, the Google "
                  "Business Profile as shown in search, and the Instagram account linked from the site.",
        "nt_list": "Not tested in this audit: {items}.", "all_ran": "Every check ran.", "nt": "not tested",
        "message": "Hi {name} team, here's a free audit of your website: {total}/70 on seven proof checks. "
                   "The biggest quick win is {fix1}. Report attached. Happy to walk you through it in 15 minutes.",
    },
    "ar": {
        "dir": "rtl", "title": "تدقيق الموقع: {name}", "sub": "سبع فحوصات على {url} · {date}{by}",
        "by": " · من {by}", "score": "النتيجة", "of": "من 70", "cols": ["#", "الفحص", "الدرجة", "شو لقينا"],
        "rules": {"gbp": "ملف قوقل للأعمال والتقييمات", "speed": "سرعة الموقع على التلفون",
                  "local_search": "الظهور في البحث بلغة الزبائن", "whatsapp": "طريق الواتساب",
                  "proof": "الإثبات في الموقع", "cadence": "نشاط إنستقرام (30 يوم)", "lead_capture": "استقبال العملاء"},
        "fixes_h": "ثلاث إصلاحات تفرق أكثر شي", "fix_cols": ["الإصلاح", "ليش يفرق", "الجهد"],
        "next_h": "الخطوة الجاية", "method_h": "كيف فحصنا",
        "method": "بحث قوقل من الإمارات، فحص سرعة على التلفون ({lh})، الصفحة الرئيسية، ملف قوقل للأعمال كما "
                  "يظهر في البحث، وحساب إنستقرام المربوط بالموقع.",
        "nt_list": "ما تم فحصه في هذا التدقيق: {items}.", "all_ran": "كل الفحوصات تمت.", "nt": "ما تم فحصه",
        "message": "هلا فريق {name}، هذا تدقيق مجاني لموقعكم: {total} من 70 في سبع فحوصات. أسرع فرصة عندكم: {fix1}. "
                   "التقرير مرفق، ونقدر نشرحه لكم في 15 دقيقة.",
    },
}


# ---------- automatic checks ----------

def fetch(url, timeout=30):
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": BROWSER_UA}), timeout=timeout)
        return r.read(3_000_000).decode("utf-8", "ignore"), ""
    except Exception as e:
        return "", str(e)[:200]


def site_signals(html_text, url):
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<script.*?</script>|<style.*?</style>", "",
                                                             html_text)))
    host = urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")
    numbers = [n for n in re.findall(r"\b\d{2,}(?:[.,]\d+)?%?", text) if not re.fullmatch(r"(19|20)\d\d|\d{7,}", n)]
    return {"ran": True, "wa_links": len(re.findall(r"wa\.me|api\.whatsapp\.com", html_text)),
            "wa_prefilled": bool(re.search(r"(wa\.me/\d+|api\.whatsapp\.com/send)\?[^\"'\s>]*text=", html_text)),
            "tel_links": html_text.count('href="tel:'), "forms": html_text.count("<form"),
            "booking": any(re.search(p, html_text, re.I) for p in BOOKING),
            "local_language_pages": 'hreflang="ar' in html_text or "/ar/" in html_text or 'lang="ar' in html_text,
            "numbers_on_page": numbers[:10], "review_words": len(re.findall(r"review|testimonial|Google rating|"
                                                                            r"آراء|تقييم", text, re.I)),
            "instagram": sorted({h.lower() for h in re.findall(r"instagram\.com/([A-Za-z0-9_.]{2,30})", html_text)
                                 if h.lower() not in {"p", "reel", "explore", "accounts"}})[:3],
            "words": len(text.split()), "host": host}


def run_lighthouse(url, out):
    npx = shutil.which("npx.cmd") or shutil.which("npx")
    if not npx:
        return {"ran": False, "error": "Node.js (npx) not installed"}
    cmd = [npx, "--yes", "lighthouse", url, "--output", "json", "--output-path", str(out), "--form-factor=mobile",
           "--screenEmulation.mobile", "--throttling-method=simulate", "--only-categories=performance",
           "--chrome-flags=--headless=new --no-sandbox", "--quiet"]
    try:
        subprocess.run(cmd, check=True, timeout=600, capture_output=True, cwd=out.parent)
        d = json.loads(out.read_text(encoding="utf-8"))
        return {"ran": True, "date": d["fetchTime"][:10], "perf": round(d["categories"]["performance"]["score"] * 100),
                "lcp": d["audits"]["largest-contentful-paint"]["displayValue"]}
    except Exception as e:  # the report must say the check didn't run, never guess
        return {"ran": False, "error": str(e)[:200]}


def rule(score, not_tested=False, en="", ar=""):
    return {"score": score, "not_tested": not_tested, "evidence_en": en, "evidence_ar": ar}


def auto_rules(sig, lh):
    """First-pass scores from what a script can see. Claude confirms or corrects every one by eye."""
    nt = rule(NOT_TESTED_POINTS, True)
    rules = {"gbp": dict(nt), "local_search": dict(nt), "cadence": dict(nt), "proof": dict(nt), "speed": dict(nt),
             "whatsapp": dict(nt), "lead_capture": dict(nt)}
    if lh.get("ran"):
        p = lh["perf"]
        rules["speed"] = rule(10 if p >= 90 else 7 if p >= 70 else 4 if p >= 50 else 2, False,
                              f"Mobile performance {p}/100, largest content shows in {lh['lcp']}.",
                              f"أداء التلفون {p} من 100، وأكبر محتوى يظهر خلال {lh['lcp']}.")
    if sig.get("ran"):
        wa = sig["wa_links"] > 0
        rules["whatsapp"] = rule(5 if wa else 0, wa,
                                 "A WhatsApp link is on the site. We did not message it." if wa else
                                 "No WhatsApp link on the site.",
                                 "رابط الواتساب موجود في الموقع، وما راسلناه." if wa else "ما في رابط واتساب في الموقع.")
        has_form, booking = sig["forms"] > 0, sig["booking"]
        cap = (10 if has_form and wa and booking else 7 if has_form or sig["wa_prefilled"] else 5 if wa
               else 3 if sig["tel_links"] else 0)
        rules["lead_capture"] = rule(cap, False, f"Form: {'yes' if has_form else 'no'} · WhatsApp: "
                                     f"{'yes' if wa else 'no'} · Booking: {'yes' if booking else 'no'}.",
                                     f"نموذج: {'نعم' if has_form else 'لا'} · واتساب: {'نعم' if wa else 'لا'} · "
                                     f"حجز: {'نعم' if booking else 'لا'}.")
        # Proof needs a human look (are the clients and numbers real and named?), so it stays "not tested" here.
    return rules


def slugify(s):
    s = re.sub(r"^https?://(www\.)?", "", s.strip().lower())
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:40] or "business"


def init(url, name, lang="en", name_ar="", by="", contact="", out="audits", speed=True, today=None,
         fetcher=fetch, lighthouse=run_lighthouse, force=False):
    if url and not url.startswith("http"):
        url = "https://" + url
    date = (today or datetime.date.today()).isoformat()
    folder = pathlib.Path(out) / f"{date}-{slugify(url or name)}-{lang}"
    if (folder / "checks.json").exists() and not force:
        print(f"EXISTS: {folder / 'checks.json'} is already there (maybe already filled). Use --force to start over.")
        return folder
    folder.mkdir(parents=True, exist_ok=True)
    page, err = fetcher(url) if url else ("", "no website given")
    sig = site_signals(page, url) if page else {"ran": False, "error": err}
    lh = lighthouse(url, folder.resolve() / "lighthouse.json") if (url and speed and page) else \
        {"ran": False, "error": "skipped"}
    checks = {"_rubric": RUBRIC,
              "business": {"name": name, "name_ar": name_ar, "url": url, "lang": lang, "date": date},
              "by": by, "contact": contact, "auto": {"site": sig, "lighthouse": lh},
              "rules": auto_rules(sig, lh),
              "top_fixes": {lang: [{"fix": "", "why": "", "effort": ""} for _ in range(3)]},
              "next_step": {lang: ""}}
    (folder / "checks.json").write_text(json.dumps(checks, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"site: {'read' if sig.get('ran') else 'NOT read (' + sig.get('error', '') + ')'} · "
          f"speed: {lh.get('perf', 'not run')}")
    print("wrote", folder / "checks.json")
    return folder


# ---------- report ----------

def problems_in(checks, lang):
    out = []
    for r in RULES:
        x = checks["rules"].get(r, {})
        score = x.get("score")
        if not isinstance(score, int) or not 0 <= score <= 10:
            out.append(f"{r}: score must be a whole number 0-10")
        if not str(x.get(f"evidence_{lang}", "")).strip():
            out.append(f"{r}: evidence_{lang} is empty (write what you saw, or 'not tested')")
        if x.get("not_tested") and score != NOT_TESTED_POINTS and r != "whatsapp":
            out.append(f"{r}: a not-tested check scores {NOT_TESTED_POINTS}")
    fixes = checks.get("top_fixes", {}).get(lang, [])
    if len(fixes) != 3 or any(not f.get("fix", "").strip() or not f.get("why", "").strip() for f in fixes):
        out.append(f"top_fixes.{lang}: needs exactly 3 fixes, each with fix and why")
    text = json.dumps(checks, ensure_ascii=False)
    if re.search(r"\b(None|TODO|TBD|lorem)\b", text):
        out.append("placeholder text (None/TODO/TBD/lorem) left in checks.json")
    return out


def render_html(checks, lang):
    t, b, rules = T[lang], checks["business"], checks["rules"]
    e = html.escape
    name = (b.get("name_ar") or b["name"]) if lang == "ar" else b["name"]
    total = sum(rules[r]["score"] for r in RULES)
    nt = [t["rules"][r] for r in RULES if rules[r].get("not_tested")]
    lh = checks["auto"].get("lighthouse", {})
    rows = "".join(
        f"<tr><td>{i}</td><td>{e(t['rules'][r])}</td><td class='s'>{rules[r]['score']}/10"
        f"{'<br><small>' + t['nt'] + '</small>' if rules[r].get('not_tested') else ''}</td>"
        f"<td>{e(rules[r]['evidence_' + lang])}</td></tr>" for i, r in enumerate(RULES, 1))
    fixes = "".join(f"<tr><td>{e(f['fix'])}</td><td>{e(f['why'])}</td><td>{e(f.get('effort', ''))}</td></tr>"
                    for f in checks["top_fixes"][lang])
    nxt = checks.get("next_step", {}).get(lang, "").strip()
    contact = checks.get("contact", "").strip()
    by = t["by"].format(by=e(checks["by"])) if checks.get("by") else ""
    font = "'Noto Sans Arabic','Segoe UI',Tahoma,sans-serif" if lang == "ar" else "'Segoe UI',Helvetica,Arial,sans-serif"
    return f"""<!doctype html><html lang="{lang}" dir="{t['dir']}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(t['title'].format(name=name))}</title>
<style>
@page{{size:A4;margin:16mm}} body{{font-family:{font};color:#1d1d1f;max-width:820px;margin:24px auto;padding:0 16px;
line-height:1.55}} h1{{font-size:26px;margin:0 0 4px}} .sub{{color:#666;margin:0 0 18px}}
.score{{display:inline-block;background:#111;color:#fff;border-radius:12px;padding:10px 18px;font-size:22px;
margin-bottom:18px}} table{{width:100%;border-collapse:collapse;margin:8px 0 22px;font-size:14px}}
th,td{{border-bottom:1px solid #e5e5e5;padding:8px 6px;text-align:start;vertical-align:top}}
th{{background:#f5f5f7}} td.s{{white-space:nowrap;font-weight:600}} small{{color:#888;font-weight:400}}
h2{{font-size:18px;margin:22px 0 6px}} .foot{{color:#666;font-size:13px}} .pb{{break-before:page}}
</style></head><body>
<h1>{e(t['title'].format(name=name))}</h1>
<p class="sub">{e(t['sub'].format(url=b['url'] or b['name'], date=b['date'], by=''))}{by}</p>
<div class="score">{t['score']}: <b>{total}</b> {t['of']}</div>
<table><tr>{''.join(f'<th>{c}</th>' for c in t['cols'])}</tr>{rows}</table>
<h2 class="pb">{t['fixes_h']}</h2>
<table><tr>{''.join(f'<th>{c}</th>' for c in t['fix_cols'])}</tr>{fixes}</table>
{f'<h2>{t["next_h"]}</h2><p>{e(nxt)}</p>' if nxt else ''}
{f'<p><b>{e(contact)}</b></p>' if contact else ''}
<h2>{t['method_h']}</h2>
<p class="foot">{e(t['method'].format(lh=lh.get('date', t['nt'])))}<br>
{e(t['nt_list'].format(items=('، ' if lang == 'ar' else ', ').join(nt))) if nt else t['all_ran']}</p>
</body></html>""", total


def find_browser():
    names = ["msedge", "chrome", "google-chrome", "chromium", "chromium-browser"]
    paths = [shutil.which(n) for n in names] + [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"]
    return next((p for p in paths if p and os.path.exists(p)), None)


def to_pdf(html_path, pdf_path):
    browser = find_browser()
    if not browser:
        return "no Chrome or Edge found: open the .html file and print it to PDF"
    try:
        subprocess.run([browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={pdf_path.resolve()}", html_path.resolve().as_uri()],
                       check=True, timeout=120, capture_output=True)
        return "" if pdf_path.exists() and pdf_path.stat().st_size > 0 else "PDF was not written"
    except Exception as e:
        return f"PDF failed ({str(e)[:120]}): open the .html and print it to PDF"


def build(folder, pdf=True):
    folder = pathlib.Path(folder)
    checks = json.loads((folder / "checks.json").read_text(encoding="utf-8"))
    lang = checks["business"]["lang"]
    if problems := problems_in(checks, lang):
        print("PROBLEMS:\n" + "\n".join("  - " + p for p in problems))
        return None
    page, total = render_html(checks, lang)
    html_path = folder / f"report-{lang}.html"
    html_path.write_text(page, encoding="utf-8")
    fix1 = checks["top_fixes"][lang][0]["fix"]
    if lang == "en" and fix1[:1].isupper() and not fix1[:2].isupper():
        fix1 = fix1[0].lower() + fix1[1:]
    name = (checks["business"].get("name_ar") or checks["business"]["name"]) if lang == "ar" else \
        checks["business"]["name"]
    (folder / "message.txt").write_text(T[lang]["message"].format(name=name, total=total, fix1=fix1) + "\n",
                                        encoding="utf-8")
    note = to_pdf(html_path, folder / f"report-{lang}.pdf") if pdf else "PDF skipped"
    print(f"OK: {total}/70 · {html_path}" + (f" · {folder / f'report-{lang}.pdf'}" if not note else f" · {note}"))
    print("message:", folder / "message.txt")
    return total


if __name__ == "__main__":
    a = sys.argv[1:]
    kv = {a[i]: a[i + 1] for i in range(len(a) - 1) if a[i].startswith("--") and not a[i + 1].startswith("--")}
    if a[:1] == ["init"] and ("--url" in kv or "--name" in kv):
        init(kv.get("--url", ""), kv.get("--name") or kv.get("--url", ""), kv.get("--lang", "en"),
             kv.get("--name-ar", ""), kv.get("--by", ""), kv.get("--contact", ""), kv.get("--out", "audits"),
             speed="--no-speed" not in a, force="--force" in a)
    elif a[:1] == ["build"] and len(a) > 1:
        sys.exit(0 if build(a[1], pdf="--no-pdf" not in a) is not None else 1)
    else:
        print(__doc__)
