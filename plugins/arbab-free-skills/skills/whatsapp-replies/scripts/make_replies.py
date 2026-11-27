"""Build ready WhatsApp Business replies as a phone page (one Copy button per message) and a .txt file.

Usage: python make_replies.py replies.json OUT_DIR
Needs: Python 3.8+ only (standard library).
Writes: OUT_DIR/replies.html and OUT_DIR/replies.txt
"""
import html
import json
import os
import re
import sys

SAFE_CHARS = 700          # greeting / away: keep well inside the app's limit
QUICK_CHARS = 600         # a quick reply should still read like one WhatsApp message
SHORTCUT_MAX = 12         # one short word, no spaces
GAP_RE = re.compile(r"\[[^\[\]\n]{2,40}\]")

TEXT = {
    "ar": {
        "title": "ردود الواتساب", "greeting": "رسالة الترحيب", "away": "رسالة خارج الدوام",
        "quick": "الردود السريعة", "booking": "رسالة الحجز والطلب", "faq": "أسئلة يكررها الزباين",
        "gaps": "عبّها مرة وحدة", "where": "وين تحط كل وحدة", "copy": "انسخ", "copied": "تم النسخ",
        "shortcut": "الاختصار", "chars": "حرف",
        "gaps_note": "هذي معلومات ما لقيتها في الصورة. عدّلها في الرد قبل لا تحفظه.",
        "where_steps": [
            "رسالة الترحيب: الإعدادات، أدوات الأعمال، رسالة الترحيب. شغّلها والصق النص.",
            "رسالة خارج الدوام: الإعدادات، أدوات الأعمال، رسالة الغياب. اختار «خارج ساعات العمل» (تمشي على الساعات اللي في ملفك التجاري).",
            "الردود السريعة: الإعدادات، أدوات الأعمال، الردود السريعة، زر الإضافة. الصق الرد واكتب الاختصار بدون /.",
            "رسالة الحجز والأجوبة: احفظها ردود سريعة بعد، أو انسخها وقت ما تحتاجها.",
        ],
        "where_note": "أسماء القوائم تختلف شوي حسب التلفون ونسخة التطبيق. دوّر على نفس الكلمات.",
    },
    "en": {
        "title": "WhatsApp replies", "greeting": "Greeting message", "away": "Away message",
        "quick": "Quick replies", "booking": "Booking / order message", "faq": "Questions customers repeat",
        "gaps": "Fill these once", "where": "Where each one goes", "copy": "Copy", "copied": "Copied",
        "shortcut": "Shortcut", "chars": "characters",
        "gaps_note": "These were not in your photo. Edit them in the reply before you save it.",
        "where_steps": [
            "Greeting message: Settings, Business tools, Greeting message. Turn it on and paste the text.",
            "Away message: Settings, Business tools, Away message. Choose \"Outside of business hours\" (it uses the hours in your business profile).",
            "Quick replies: Settings, Business tools, Quick replies, then the add button. Paste the reply and type the shortcut without the /.",
            "Booking message and answers: save them as quick replies too, or copy them when you need them.",
        ],
        "where_note": "Menu names differ a little by phone and app version. Look for the same words.",
    },
}


def load(path: str) -> dict:
    """Read the JSON and check the parts the page needs."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("replies.json must hold one JSON object")
    lang = data.get("lang", "ar")
    if lang not in TEXT:
        raise ValueError('"lang" must be "ar" or "en"')
    quick = [q for q in (data.get("quick") or []) if isinstance(q, dict) and q.get("text")]
    faq = [x for x in (data.get("faq") or []) if isinstance(x, dict) and x.get("a")]
    gaps = [g for g in (data.get("gaps") or []) if isinstance(g, dict) and g.get("gap")]
    return {**data, "lang": lang, "quick": quick, "faq": faq, "gaps": gaps}


def warnings(d: dict) -> list:
    """Soft checks: print them, never stop the build."""
    out = []
    for key in ("greeting", "away"):
        n = len(d.get(key) or "")
        if n > SAFE_CHARS:
            out.append(f"{key} is {n} characters; keep it under {SAFE_CHARS}")
    for q in d["quick"]:
        sc = str(q.get("shortcut", "")).lstrip("/")
        if not sc or " " in sc or len(sc) > SHORTCUT_MAX:
            out.append(f"shortcut '{sc}' should be one short word with no space")
        if len(q["text"]) > QUICK_CHARS:
            out.append(f"quick reply /{sc} is {len(q['text'])} characters; shorten it")
    listed = {g["gap"].strip() for g in d["gaps"]}
    for text in all_texts(d):
        for gap in GAP_RE.findall(text):
            if gap not in listed:
                out.append(f"gap {gap} is used but not listed in \"gaps\"")
                listed.add(gap)
    return out


def all_texts(d: dict) -> list:
    texts = [d.get("greeting") or "", d.get("away") or "", d.get("booking") or ""]
    texts += [q["text"] for q in d["quick"]]
    texts += [x["a"] for x in d["faq"]]
    return texts


def mark_gaps(escaped: str) -> str:
    """Highlight [gaps] in already-escaped text."""
    return GAP_RE.sub(lambda m: f"<mark>{m.group(0)}</mark>", escaped)


def msg_card(label: str, text: str, t: dict) -> str:
    body = mark_gaps(html.escape(text))
    count = f"{len(text)} {t['chars']}"
    return (
        "<div class='card'><div class='top'>"
        f"<span class='lbl'>{label}</span><button type='button' class='cp'>{t['copy']}</button></div>"
        f"<div class='msg'>{body}</div><div class='n'>{html.escape(count)}</div></div>"
    )


def section(title: str, inner: str) -> str:
    return f"<h2>{html.escape(title)}</h2>{inner}" if inner else ""


SCRIPT = """
function done(b){var o=b.textContent;b.textContent=b.dataset.ok;b.classList.add('ok');
setTimeout(function(){b.textContent=o;b.classList.remove('ok')},1500)}
function fallback(t,b){var a=document.createElement('textarea');a.value=t;a.setAttribute('readonly','');
a.style.position='fixed';a.style.opacity='0';document.body.appendChild(a);a.select();
try{document.execCommand('copy');done(b)}catch(e){}document.body.removeChild(a)}
document.querySelectorAll('.cp').forEach(function(b){b.dataset.ok=document.body.dataset.ok;
b.addEventListener('click',function(){var t=b.closest('.card').querySelector('.msg').textContent;
if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(t).then(function(){done(b)},
function(){fallback(t,b)})}else{fallback(t,b)}})});
"""

CSS = """body{font-family:Arial,Tahoma,sans-serif;max-width:640px;margin:0 auto;padding:18px 16px 40px;
color:#1b2430;background:#f3f5f2;line-height:1.6}h1{margin:0;font-size:25px;color:#0b5d3b}
.sub{color:#5a6570;font-size:13px;margin:2px 0 8px}h2{font-size:17px;color:#0b5d3b;margin:22px 0 8px}
.card{background:#fff;border:1px solid #dfe5dc;border-radius:12px;padding:10px 12px;margin:8px 0}
.top{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:6px}
.lbl{font-weight:bold;font-size:14px;color:#33404c}.msg{white-space:pre-wrap;background:#e7f7dc;
border-radius:10px;padding:9px 11px;font-size:15px;-webkit-user-select:text;user-select:text}
.n{color:#8a949e;font-size:11px;margin-top:4px}.cp{background:#0b5d3b;color:#fff;border:0;border-radius:18px;
padding:7px 16px;font-size:14px;cursor:pointer;min-width:74px}.cp.ok{background:#4f8a2b}
.sc{display:inline-block;background:#0b5d3b;color:#fff;border-radius:6px;padding:0 7px;font-size:13px;
direction:ltr;unicode-bidi:isolate}mark{background:#ffe08a;border-radius:4px;padding:0 2px}
.gaps{background:#fff8e1;border:1px solid #f1d98a;border-radius:12px;padding:10px 14px}
.gaps p{margin:0 0 6px;font-size:13px;color:#6b5a1e}ul,ol{margin:4px 0;padding-inline-start:22px}
li{margin:4px 0;font-size:14px}.note{color:#5a6570;font-size:12px}"""


def build_html(d: dict, path: str) -> None:
    t = TEXT[d["lang"]]
    rtl = d["lang"] == "ar"
    business = d.get("business") or ""
    parts = [f"<h1>{html.escape(t['title'])}</h1>"]
    if business:
        parts.append(f"<p class='sub'>{html.escape(business)}</p>")
    if d.get("greeting"):
        parts.append(section(t["greeting"], msg_card(t["greeting"], d["greeting"], t)))
    if d.get("away"):
        parts.append(section(t["away"], msg_card(t["away"], d["away"], t)))
    quick = "".join(
        msg_card(f"{t['shortcut']} <span class='sc'>/{html.escape(str(q.get('shortcut', '')).lstrip('/'))}</span>",
                 q["text"], t)
        for q in d["quick"]
    )
    parts.append(section(t["quick"], quick))
    if d.get("booking"):
        parts.append(section(t["booking"], msg_card(t["booking"], d["booking"], t)))
    faq = "".join(msg_card(html.escape(x.get("q", "")), x["a"], t) for x in d["faq"])
    parts.append(section(t["faq"], faq))
    if d["gaps"]:
        items = "".join(
            f"<li><mark>{html.escape(g['gap'])}</mark> {html.escape(g.get('why', ''))}</li>" for g in d["gaps"]
        )
        parts.append(section(t["gaps"], f"<div class='gaps'><p>{html.escape(t['gaps_note'])}</p><ul>{items}</ul></div>"))
    steps = "".join(f"<li>{html.escape(s)}</li>" for s in t["where_steps"])
    parts.append(section(t["where"], f"<ol>{steps}</ol><p class='note'>{html.escape(t['where_note'])}</p>"))
    page = (
        f"<!doctype html><html lang=\"{d['lang']}\" dir=\"{'rtl' if rtl else 'ltr'}\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        f"<title>{html.escape(t['title'])}</title><style>{CSS}</style></head>"
        f"<body data-ok=\"{html.escape(t['copied'])}\">{''.join(parts)}<script>{SCRIPT}</script></body></html>"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)


def build_txt(d: dict, path: str) -> None:
    t = TEXT[d["lang"]]
    rule = "-" * 24
    out = [t["title"] + (f" · {d['business']}" if d.get("business") else ""), ""]
    for key in ("greeting", "away"):
        if d.get(key):
            out += [f"== {t[key]} ==", d[key], ""]
    if d["quick"]:
        out.append(f"== {t['quick']} ==")
        for q in d["quick"]:
            out += [f"/{str(q.get('shortcut', '')).lstrip('/')}", q["text"], rule]
        out.append("")
    if d.get("booking"):
        out += [f"== {t['booking']} ==", d["booking"], ""]
    if d["faq"]:
        out.append(f"== {t['faq']} ==")
        for x in d["faq"]:
            out += [f"? {x.get('q', '')}", x["a"], rule]
        out.append("")
    if d["gaps"]:
        out += [f"== {t['gaps']} ==", t["gaps_note"]]
        out += [f"{g['gap']} {g.get('why', '')}".strip() for g in d["gaps"]]
        out.append("")
    out += [f"== {t['where']} =="] + t["where_steps"] + [t["where_note"]]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit("Usage: python make_replies.py replies.json OUT_DIR")
    try:
        data = load(sys.argv[1])
    except (OSError, ValueError) as err:
        sys.exit(f"Could not read the replies: {err}")
    os.makedirs(sys.argv[2], exist_ok=True)
    for w in warnings(data):
        sys.stdout.write(f"warning: {w}\n")
    build_html(data, os.path.join(sys.argv[2], "replies.html"))
    build_txt(data, os.path.join(sys.argv[2], "replies.txt"))
    sys.stdout.write(f"written: {os.path.join(sys.argv[2], 'replies.html')} and replies.txt\n")


if __name__ == "__main__":
    main()
