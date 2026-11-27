"""Suggest brand colours from Instagram screenshots / photos.

Usage:  python extract_palette.py <image-or-folder> [more ...]
Prints the dominant colours (hex, share, lightness, saturation) across all
images, plus a short "mood" line (bright/dark, warm/cool). Claude still picks
the final 3 brand colours by looking at the logo and the post grid; this script
only gives exact hex values so nobody guesses.
Needs Pillow (pip install pillow).
"""
import colorsys
import sys
from pathlib import Path

from PIL import Image

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
SAMPLE_SIZE = 160
BUCKETS = 20


def collect(paths):
    files = []
    for p in map(Path, paths):
        if p.is_dir():
            files += [f for f in sorted(p.iterdir()) if f.suffix.lower() in IMAGE_EXT]
        elif p.suffix.lower() in IMAGE_EXT:
            files.append(p)
    return files


def pixels(path):
    im = Image.open(path).convert("RGB")
    im.thumbnail((SAMPLE_SIZE, SAMPLE_SIZE))
    return list(im.getdata())


def main():
    files = collect(sys.argv[1:])
    if not files:
        sys.exit("No images found.")
    allpx = []
    for f in files:
        allpx += pixels(f)
    img = Image.new("RGB", (len(allpx), 1))
    img.putdata(allpx)
    pal = img.quantize(colors=BUCKETS, method=Image.Quantize.MEDIANCUT)
    counts = sorted(pal.getcolors(), reverse=True)
    palette = pal.getpalette()
    total = len(allpx)
    light_sum = warm = 0
    print(f"{len(files)} images, {total} sampled pixels\n")
    print("hex      share  light  sat   note")
    for count, idx in counts:
        r, g, b = palette[idx * 3: idx * 3 + 3]
        h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        share = count / total
        light_sum += l * share
        if s > 0.15:
            warm += share if (h < 0.17 or h > 0.92) else -share
        note = "neutral" if s < 0.12 else ("accent?" if s > 0.45 and share < 0.12 else "")
        print(f"#{r:02X}{g:02X}{b:02X}  {share:5.1%}  {l:4.2f}  {s:4.2f}  {note}")
    mood = "bright" if light_sum > 0.55 else ("dark" if light_sum < 0.35 else "mid")
    tone = "warm" if warm > 0.05 else ("cool" if warm < -0.05 else "neutral")
    print(f"\nmood: {mood} (avg lightness {light_sum:.2f}), {tone}")


if __name__ == "__main__":
    main()
