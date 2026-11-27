"""Prospect scan: a list of businesses in, the gaps on their websites out, best prospects first.

    python scan.py run --list businesses.csv [--list more.csv] [--out prospect-scan] [--batch 50] [--minutes 40]
        -> <out>/scanned.csv      every business ever scanned (the running total, so nothing is scanned twice)
           <out>/<date>.json      this run's batch, best reason-to-message first
    python scan.py status --list businesses.csv [--out prospect-scan]
        -> how many are scanned, how many are left, and whether the kill switch is on.

Input: a CSV with a "website" column (other columns used when present: name, category, phone, rating, reviews,
address, maps_url), an Apify Google Maps export (.json), or a .txt file with one URL per line.
Listings with no website are kept: "no website" is the strongest gap for a web build.

How it reads a site: plain HTTP and regex over the homepage, robots.txt, the sitemap and a careers page.
No browser, no AI model, no paid tool, no sign-in. Nothing is ever sent to anyone.
Kill switch: an empty file named STOP in the output folder. Caps: --batch (max 50) and --minutes (max 60).

Part of arbab-skills (github.com/fahadhammadi83/arbab-skills), CC BY-NC 4.0.
Buying-signal ideas adapted from Harvey's profiler (github.com/ethanplusai/harvey, MIT).
"""
import concurrent.futures
import csv
import datetime
import json
import os
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/124.0 Safari/537.36")
DEFAULT_BATCH, MAX_BATCH = 50, 50
DEFAULT_MINUTES, MAX_MINUTES = 40, 60
WORKERS = 8
STALE_DAYS = 180
FAIL_SCORE = 50
MOBILE = re.compile(r"^(\+?971|0)5\d{8}$")  # UAE mobile = WhatsApp-able; change for another country

# A "website" that is only a social page, link list or booking page is no website for a site build.
SOCIAL_HOSTS = ("instagram.com", "facebook.com", "fb.com", "linktr.ee", "tiktok.com", "wa.me", "whatsapp.com",
                "linkedin.com", "beacons.ai", "bio.link", "x.com", "twitter.com", "youtube.com", "snapchat.com",
                "linko.page", "fresha.com", "booksy.com", "tablecheck.com", "setmore.com", "calendly.com")
# Down for good. A 403 or bot check is "blocked", which says nothing about the business.
DEAD = re.compile(r"getaddrinfo|Name or service not known|No address|refused|HTTP Error (404|410|5\d\d)|timed out|"
                  r"CERTIFICATE_VERIFY_FAILED|certificate has expired|10060|did not properly respond", re.I)
# Pixels loaded through Google Tag Manager are not in the HTML: empty means "not seen", never "no ads".
ADS = {"google": (r"googleadservices\.com", r"google_conversion", r"['\"=]AW-\d+"),
       "meta": (r"connect\.facebook\.net/[^\"']*fbevents\.js", r"fbq\s*\(\s*['\"]init"),
       "snap": (r"sc-static\.net/scevent", r"snaptr\s*\("), "tiktok": (r"analytics\.tiktok\.com", r"ttq\.load")}
TECH = {"WordPress": (r"wp-content/", r"wp-includes/"), "Shopify": (r"cdn\.shopify\.com",),
        "Wix": (r"static\.parastorage\.com",), "Squarespace": (r"static1\.squarespace\.com",),
        "Webflow": (r"assets\.website-files\.com", r"data-wf-domain"), "Framer": (r"framerusercontent\.com",),
        "Next.js": (r"/_next/static/",), "WooCommerce": (r"woocommerce",), "Salla": (r"salla\.(sa|network)",),
        "Zid": (r"zid\.store",), "HubSpot": (r"js\.hs-scripts\.com", r"js\.hsforms\.net"),
        "Google Analytics": (r"googletagmanager\.com/gtag", r"google-analytics\.com")}
BOOKING = (r"calendly\.com", r"acuityscheduling", r"fresha\.com", r"booksy\.com", r"vagaro\.com", r"setmore",
           r"simplybook", r"bookings\.zoho", r"book(ing)?[-_ ]?now", r"book[-_ ]an?[-_ ]appointment", r"احجز")
AI_BOTS = ("gptbot", "oai-searchbot", "chatgpt-user", "google-extended", "claudebot", "anthropic-ai",
           "perplexitybot", "ccbot")
CAREERS = ("/careers", "/jobs", "/join-us")
OPEN_ROLES = re.compile(r"apply now|apply for this|open (positions|roles|vacanc)|current (openings|vacancies)|"
                        r"we'?re hiring|job description|full[- ]time|part[- ]time|وظائف شاغرة|الوظائف المتاحة|نوظف", re.I)
# Only wording that says who built the site counts: a wrong agency name in a pitch is worse than none.
CREDIT = re.compile(r"(powered|website|site|web\s*design|designed|developed|built|created|marketing)\s+(by|&)|"
                    r"تصميم|تطوير|برمجة", re.I)
NOT_AGENCY = ("facebook.", "instagram.", "twitter.", "x.com", "linkedin.", "youtube.", "tiktok.", "snapchat.",
              "wa.me", "whatsapp.", "google.", "goo.gl", "apple.com", "wordpress.org", "wix.com", "squarespace.com",
              "shopify.com", "webflow.com", "salla.", "zid.", "trustpilot", "cloudflare")
FIELDS = ["scan_date", "source", "name", "category", "phone", "channel", "rating", "reviews", "address", "maps_url",
          "website", "site_status", "score", "lead_signal", "ads", "tech", "booking", "whatsapp", "arabic",
          "built_by", "ai_blocked", "days_since_update", "careers_page", "error"]


# ---------- reading a site ----------

def fetch(url, timeout=15):
    """(text, final url), or ("", "") when it fails: a missing page is a finding, not a crash."""
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": BROWSER_UA}), timeout=timeout)
        return r.read(2_000_000).decode("utf-8", "ignore"), r.geturl()
    except Exception:
        return "", ""


def matches(html, patterns):
    return any(re.search(p, html, re.I) for p in patterns)


def built_by(html, host):
    """The agency the footer credits ("Website by X", «تصميم وتطوير»), or ""."""
    html = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", "", html)
    m = re.search(r"(?is)<footer\b.*?</footer>", html)
    region = m.group(0) if m else html[-12000:]
    for a in re.finditer(r'(?is)<a\b[^>]*href=["\'](https?://[^"\']+)["\'][^>]*>(.*?)</a>', region):
        link_host = urllib.parse.urlparse(a.group(1)).netloc.lower().removeprefix("www.")
        anchor = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", a.group(2))).strip()
        if not anchor or len(anchor) > 80 or not link_host or host in link_host or link_host in host:
            continue
        if any(b in link_host for b in NOT_AGENCY):
            continue
        before = re.sub(r"<[^>]+>", " ", region[max(0, a.start() - 80):a.start()])
        if CREDIT.search(f"{before} {anchor}"):
            return anchor
    return ""


def ai_bots_blocked(robots):
    """AI search bots told "Disallow: /" (the site can't appear in ChatGPT or Perplexity answers)."""
    groups, agents, in_rules = {}, [], False
    for line in robots.lower().splitlines():
        key, _, val = line.split("#")[0].partition(":")
        key, val = key.strip(), val.strip()
        if key == "user-agent":
            if in_rules:
                agents, in_rules = [], False
            agents.append(val)
            groups.setdefault(val, False)
        elif key in ("allow", "disallow"):
            in_rules = True
            if key == "disallow" and val == "/":
                groups.update({a: True for a in agents})
    return [b for b in AI_BOTS if groups.get(b, groups.get("*", False))]


def days_since(dates, today=None):
    valid = []
    for d in dates:
        try:
            valid.append(datetime.date.fromisoformat(d))
        except ValueError:
            pass
    return ((today or datetime.date.today()) - max(valid)).days if valid else None


def careers_page(root):
    """A careers page that shows open roles, or "": a careers page alone doesn't prove they're hiring now."""
    for path in CAREERS:
        page, final = fetch(root + path)
        if page and path.strip("/") in final:
            text = re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<script.*?</script>|<style.*?</style>", "", page))
            return final if OPEN_ROLES.search(text) else ""
    return ""


def site_signals(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA})
        html = urllib.request.urlopen(req, timeout=60).read(3_000_000).decode("utf-8", "ignore")
    except Exception as e:
        return {"ran": False, "error": str(e)[:200]}
    return signals_from(html, url, *robots_and_sitemap(url))


def robots_and_sitemap(url):
    p = urllib.parse.urlparse(url)
    root = f"{p.scheme}://{p.netloc}"
    robots, _ = fetch(root + "/robots.txt")
    sitemap, _ = fetch((re.findall(r"(?im)^\s*sitemap:\s*(\S+)", robots) or [root + "/sitemap.xml"])[0])
    return robots, sitemap, careers_page(root)


def signals_from(html, url, robots="", sitemap="", careers=""):
    """Every signal from already-fetched pages (split out so tests run with no network)."""
    text = re.sub(r"<script.*?</script>|<style.*?</style>", "", html, flags=re.S)
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text))
    host = urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")
    return {"ran": True, "wa_links": len(re.findall(r"wa\.me|api\.whatsapp\.com", html)),
            "tel_links": html.count('href="tel:'),
            "wa_prefilled": bool(re.search(r"(wa\.me/\d+|api\.whatsapp\.com/send)\?[^\"'\s>]*text=", html)),
            "forms": html.count("<form"),
            "arabic_pages": 'hreflang="ar' in html or "/ar/" in html or 'lang="ar' in html,
            "numbers": re.findall(r"\b\d{2,}(?:[.,]\d+)?%?", text)[:20],
            "review_words": len(re.findall(r"review|Clutch|Google rating", text, re.I)),
            "ads_running": [k for k, pats in ADS.items() if matches(html, pats)],
            "tech": [k for k, pats in TECH.items() if matches(html, pats)],
            "booking_hint": matches(html, BOOKING), "built_by": built_by(html, host),
            "ai_bots_blocked": ai_bots_blocked(robots),
            "days_since_update": days_since(re.findall(r"<lastmod>\s*(\d{4}-\d{2}-\d{2})", sitemap)),
            "careers_page": careers}


# ---------- judging a business ----------

def gbp_points(rating, reviews):
    """Google profile: 3 no reviews · 6 under 10 or under 4.5 stars · 8 at 10-50 · 10 over 50."""
    rating, reviews = num(rating, 0, float), num(reviews)
    if not reviews:
        return 3
    if reviews < 10 or rating < 4.5:
        return 6
    return 10 if reviews > 50 else 8


def score(row, s):
    """Four script-checkable rules, scaled to /100 (lower = weaker site = better prospect).
    Google profile 0-10, WhatsApp 0-5, proof 0-5, lead capture 0-7."""
    numbers = [n for n in s["numbers"] if not re.fullmatch(r"(19|20)\d\d|\d{7,}", n)]  # years, phone digits
    proof = 5 if numbers and s["review_words"] else 4 if s["review_words"] else 2
    capture = 7 if s["forms"] or s["wa_prefilled"] else 5 if s["wa_links"] else 3 if s["tel_links"] else 0
    total = gbp_points(row["rating"], row["reviews"]) + (5 if s["wa_links"] else 0) + proof + capture
    return round(total * 100 / 27)


def lead_signal(r):
    """The one reason to message this business today, or "" when there is none."""
    status = r["site_status"]
    if status == "none":
        return "No website on the listing"
    if status == "social":
        return f"The only website is a social or booking page ({r['website']})"
    if status == "dead":
        return "The website on the listing is down"
    if status != "ok":
        return ""
    if r["careers_page"]:
        return f"Hiring: open roles on {r['careers_page']}"
    gaps = [g for g, missing in (("online booking", r["booking"] != "yes"),
                                 ("WhatsApp on the site", r["whatsapp"] != "yes")) if missing]
    if r["ads"] and gaps:
        return f"Running {' + '.join(a.capitalize() for a in r['ads'].split(', '))} ads, no {' or '.join(gaps)}"
    if r["built_by"]:
        return f"Site credits {r['built_by']}"
    if r["arabic"] != "yes":
        return "No Arabic version of the site"
    if r["ai_blocked"]:
        return "Site blocks ChatGPT/Perplexity from reading it"
    if str(r["days_since_update"]).isdigit() and int(r["days_since_update"]) > STALE_DAYS:
        return f"Site not updated in {r['days_since_update']} days"
    return ""


def check(place, reader=site_signals):
    """One business: its site status, signals, score and reason to message."""
    row = dict(place, site_status="", score="", ads="", tech="", booking="", whatsapp="", arabic="", built_by="",
               ai_blocked="", days_since_update="", careers_page="", error="")
    host = re.sub(r"^https?://(www\.)?", "", place["website"].lower())
    if not place["website"]:
        row["site_status"] = "none"
    elif any(host.startswith(h) or ("." + h) in host.split("/")[0] for h in SOCIAL_HOSTS):
        row["site_status"] = "social"
    else:
        try:
            s = reader(place["website"])
        except Exception as e:  # one bad site must not cost the run
            s = {"ran": False, "error": f"scan error: {e}"}
        if not s["ran"]:
            row["error"] = s["error"][:120]
            row["site_status"] = "dead" if DEAD.search(s["error"]) else "blocked"
        else:
            row.update(site_status="ok", score=score(place, s), ads=", ".join(s["ads_running"]),
                       tech=", ".join(s["tech"]), booking="yes" if s["booking_hint"] else "no",
                       whatsapp="yes" if s["wa_links"] else "no", arabic="yes" if s["arabic_pages"] else "no",
                       built_by=s["built_by"], ai_blocked=", ".join(s["ai_bots_blocked"]),
                       days_since_update="" if s["days_since_update"] is None else s["days_since_update"],
                       careers_page=s["careers_page"])
    row["lead_signal"] = lead_signal(row)
    row["channel"] = channel(place["phone"])
    return row


def channel(phone):
    """How you can reach them by hand today: WhatsApp for a mobile number, a call for a landline."""
    digits = re.sub(r"[^\d+]", "", phone or "")
    if not digits:
        return "instagram or linkedin"
    return "whatsapp" if MOBILE.match(digits) else "call"


def rank(rows):
    """Readable sites with a reason to message first, then the weakest score, then the busiest listing."""
    return sorted(rows, key=lambda r: (r["site_status"] == "blocked", not r["lead_signal"],
                                       num(r["score"], 100), -num(r["reviews"])))


# ---------- the list and the running total ----------

def num(value, default=0, kind=int):
    """A number from a cell: "1,234" and "12.0" count; anything else is the default."""
    try:
        return kind(float(str(value).replace(",", "")))
    except ValueError:
        return default


def site_key(url):
    """One business per site: scheme, www and path don't make a new prospect."""
    return re.sub(r"^https?://(www\.)?", "", (url or "").strip().lower()).split("/")[0]


def load(path):
    """Businesses from a CSV, an Apify Google Maps JSON export, or a .txt of URLs. Company fields only."""
    p = pathlib.Path(path)
    raw = p.read_text(encoding="utf-8-sig")
    if p.suffix.lower() == ".json":
        items = json.loads(raw)
        items = items.get("items", items) if isinstance(items, dict) else items
    elif p.suffix.lower() == ".csv":
        items = list(csv.DictReader(raw.splitlines()))
    else:
        items = [{"website": ln.strip()} for ln in raw.splitlines() if ln.strip() and not ln.startswith("#")]
    places = []
    for it in items:
        if it.get("permanentlyClosed"):
            continue
        site = (it.get("website") or it.get("Website") or "").strip()
        if site and not site.startswith("http"):
            site = "https://" + site
        places.append({"source": p.name,
                       "name": it.get("title") or it.get("name") or it.get("organisation") or site_key(site),
                       "category": it.get("categoryName") or it.get("category") or "",
                       "phone": it.get("phone") or it.get("phoneUnformatted") or "",
                       "rating": it.get("totalScore") or it.get("rating") or "",
                       "reviews": it.get("reviewsCount") or it.get("reviews") or "",
                       "address": it.get("address") or "", "maps_url": it.get("url") or it.get("maps_url") or "",
                       "website": site})
    return places


def load_pool(paths):
    """Every business across the lists, first appearance wins. Listings with no website are kept by name."""
    seen, pool = set(), []
    for path in paths:
        if not pathlib.Path(path).exists():
            print(f"list missing, skipped: {path}")
            continue
        for place in load(path):
            key = site_key(place["website"]) or f"name:{place['name'].strip().lower()}"
            if key and key not in seen:
                seen.add(key)
                pool.append(place)
    return pool


def key_of(row):
    return site_key(row["website"]) or f"name:{row['name'].strip().lower()}"


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def scanned_keys(out):
    path = out / "scanned.csv"
    return {key_of(r) for r in read_csv(path)} if path.exists() else set()


def next_batch(pool, done, size):
    return [p for p in pool if key_of(p) not in done][:size]


def append_scanned(out, rows):
    path = out / "scanned.csv"
    new_file = not path.exists() or path.stat().st_size == 0
    with open(path, "a", encoding="utf-8-sig" if new_file else "utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        if new_file:
            writer.writeheader()
        writer.writerows(rows)


def scan_batch(batch, minutes, today, reader=site_signals):
    """Read every site in parallel until the time limit. One not read in time stays in the queue for next run."""
    deadline = time.monotonic() + minutes * 60
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS)
    futures = [pool.submit(check, p, reader) for p in batch]
    rows = []
    try:
        for f in concurrent.futures.as_completed(futures, timeout=max(1, deadline - time.monotonic())):
            rows.append(dict(f.result(), scan_date=today))
    except concurrent.futures.TimeoutError:
        print(f"time limit reached: {len(rows)} of {len(batch)} read; the rest wait for the next run")
    pool.shutdown(wait=False, cancel_futures=True)
    return rank(rows)


def run(lists, out, batch_size, minutes, reader=site_signals):
    out.mkdir(parents=True, exist_ok=True)
    if (out / "STOP").exists():
        print(f"STOPPED: kill switch file present ({out / 'STOP'}). Nothing scanned.")
        return None
    pool, done = load_pool(lists), scanned_keys(out)
    batch = next_batch(pool, done, min(batch_size, MAX_BATCH))
    if not batch:
        print(f"QUEUE EMPTY: all {len(pool)} businesses are scanned. Add a new list.")
        return None
    today = datetime.date.today().isoformat()
    rows = scan_batch(batch, min(minutes, MAX_MINUTES), today, reader)
    tonight = out / f"{today}.json"
    earlier = json.loads(tonight.read_text(encoding="utf-8")) if tonight.exists() else []
    tonight.write_text(json.dumps(earlier + rows, indent=1, ensure_ascii=False), encoding="utf-8")
    append_scanned(out, rows)
    status = {k: sum(1 for r in rows if r["site_status"] == k) for k in ("ok", "none", "social", "dead", "blocked")}
    print(f"scanned {len(rows)} of {len(batch)}: " + ", ".join(f"{k} {v}" for k, v in status.items()))
    print(f"with a reason to message: {sum(1 for r in rows if r['lead_signal'])}")
    print(f"left in the queue: {len(pool) - len(done) - len(rows)} of {len(pool)}")
    print("wrote", tonight)
    return tonight


def status(lists, out):
    pool, done = load_pool(lists), scanned_keys(out)
    left = len(next_batch(pool, done, len(pool)))
    print(f"list {len(pool)}, scanned {len(pool) - left}, left {left}, "
          f"kill switch {'ON' if (out / 'STOP').exists() else 'off'}")


def parse(argv):
    opts = {"lists": [], "out": "prospect-scan", "batch": DEFAULT_BATCH, "minutes": DEFAULT_MINUTES}
    i = 1
    while i < len(argv):
        flag, val = argv[i], argv[i + 1] if i + 1 < len(argv) else ""
        if flag == "--list":
            opts["lists"].append(val)
        elif flag in ("--out", "--batch", "--minutes"):
            opts[flag[2:]] = val
        else:
            raise SystemExit(f"unknown option {flag}\n\n{__doc__}")
        i += 2
    if not opts["lists"]:
        raise SystemExit(f"give at least one --list\n\n{__doc__}")
    return opts


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["run"]:
        o = parse(args)
        run(o["lists"], pathlib.Path(o["out"]), int(o["batch"]), int(o["minutes"]))
        sys.stdout.flush()
        os._exit(0)  # everything is saved; don't wait for a slow site still sending bytes
    elif args[:1] == ["status"]:
        o = parse(args)
        status(o["lists"], pathlib.Path(o["out"]))
    else:
        print(__doc__)
