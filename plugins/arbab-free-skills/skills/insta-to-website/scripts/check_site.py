"""Self-check for a generated one-page site.

Usage: python check_site.py path/to/index.html
Exit code 0 = all checks passed, 1 = problems found (listed).
Standard library only.
"""
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

PLACEHOLDERS = re.compile(r"lorem|ipsum|your text|placeholder|coming soon|xxx|TODO", re.I)
WA = re.compile(r"^https://wa\.me/9\d{7,14}(\?text=.*)?$")
MAPS = re.compile(r"^https://(www\.)?google\.[a-z.]+/maps|^https://maps\.app\.goo\.gl/|^https://goo\.gl/maps")
IG = re.compile(r"^https://(www\.)?instagram\.com/[A-Za-z0-9._]+/?$|^https://ig\.me/m/[A-Za-z0-9._]+$")
MIN_CONTRAST = 4.5


class Scan(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.html_attrs: dict = {}
        self.links: list[str] = []
        self.imgs: list[str] = []
        self.meta_desc = False
        self.icon = False
        self.title = ""
        self._in_title = False
        self.lang_count = {"ar": 0, "en": 0}
        self.sections: list[list[str]] = []
        self.toggle = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.html_attrs = a
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
        if tag == "img" and a.get("src"):
            self.imgs.append(a["src"])
            if self.sections:
                self.sections[-1].append("[image]")
        if tag == "meta" and a.get("name") == "description" and a.get("content"):
            self.meta_desc = True
        if tag == "link" and "icon" in (a.get("rel") or ""):
            self.icon = True
        if tag == "title":
            self._in_title = True
        if a.get("lang") in self.lang_count and tag != "html":
            self.lang_count[a["lang"]] += 1
        if tag == "section":
            self.sections.append([])
        if tag == "button" and a.get("id") == "lang":
            self.toggle = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self.sections and data.strip():
            self.sections[-1].append(data.strip())


def luminance(hex_colour: str) -> float:
    h = hex_colour.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def main() -> int:
    path = Path(sys.argv[1])
    src = path.read_text(encoding="utf-8")
    s = Scan()
    s.feed(src)
    problems: list[str] = []
    if s.html_attrs.get("lang") != "ar" or s.html_attrs.get("dir") != "rtl":
        problems.append('<html> must start lang="ar" dir="rtl"')
    if not s.toggle:
        problems.append('language toggle <button id="lang"> missing')
    if min(s.lang_count.values()) == 0:
        problems.append(f"one language missing: {s.lang_count}")
    elif abs(s.lang_count["ar"] - s.lang_count["en"]) > 2:
        problems.append(f"Arabic/English blocks out of balance: {s.lang_count}")
    text_only = re.sub(r"<[^>]+>", " ", re.sub(r"<(style|script)[\s\S]*?</\1>", " ", src))
    if PLACEHOLDERS.search(text_only):
        problems.append(f"placeholder text found: {PLACEHOLDERS.search(text_only).group(0)!r}")
    for i, sec in enumerate(s.sections, 1):
        if len(" ".join(sec)) < 10:
            problems.append(f"section #{i} looks empty")
    if not s.title.strip():
        problems.append("<title> missing")
    if not s.meta_desc:
        problems.append("meta description missing")
    if not s.icon:
        problems.append("favicon link missing")
    wa = [l for l in s.links if "wa.me" in l]
    ig = [l for l in s.links if "instagram.com" in l or "ig.me" in l]
    maps = [l for l in s.links if "maps" in l]
    if not wa and not ig:
        problems.append("no WhatsApp or Instagram DM button")
    problems += [f"bad wa.me link: {l}" for l in wa if not WA.match(l)]
    problems += [f"bad Instagram link: {l}" for l in ig if not IG.match(l)]
    problems += [f"bad maps link: {l}" for l in maps if not MAPS.match(l)]
    for img in s.imgs:
        if not img.startswith(("data:", "http")) and not (path.parent / img).exists():
            problems.append(f"image not found: {img}")
    tokens = dict(re.findall(r"--(bg|ink|accent|on-accent)\s*:\s*(#[0-9a-fA-F]{3,6})\b", src))
    for fg, bg in (("ink", "bg"), ("on-accent", "accent")):
        if fg in tokens and bg in tokens:
            c = contrast(tokens[fg], tokens[bg])
            if c < MIN_CONTRAST:
                problems.append(f"contrast --{fg} on --{bg} is {c:.2f}:1 (< {MIN_CONTRAST})")
        else:
            problems.append(f"colour token --{fg} or --{bg} missing on :root")
    print(f"checked {path}: {len(s.sections)} sections, {len(s.imgs)} images, langs {s.lang_count}")
    if problems:
        print("PROBLEMS:\n- " + "\n- ".join(problems))
        return 1
    print("OK: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
