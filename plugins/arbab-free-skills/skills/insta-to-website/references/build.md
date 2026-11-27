# Build rules for the one page

## Files
```
site/
  index.html      one file: HTML + <style> + small <script>
  img/            their photos, cropped and resized (max 1400px, JPG q80; logo/favicon PNG)
```
Crop with Pillow (or any tool you have): remove Instagram UI, captions and burned-in text; centre the subject; export 2-3 sizes only if needed. No stock, no AI images.

## Skeleton (structure only; the look comes from the style)
```html
<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Name | what they do, city</title>
<meta name="description" content="one real sentence, Arabic or English">
<link rel="icon" href="img/favicon.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=<Arabic>&family=<Latin>&display=swap" rel="stylesheet">
<style>
:root{ --bg:#..; --ink:#..; --accent:#..; --on-accent:#..; --surface:#..; --muted:#.. }
html[lang=ar] [lang=en], html[lang=en] [lang=ar]{display:none !important}
...
</style>
</head>
<body>
  <header> logo · nav anchors · <button id="lang">English / عربي</button> </header>
  <section id="hero">...</section>
  ...
  <a class="wa-float" href="https://wa.me/9715XXXXXXXX?text=...">WhatsApp</a>
<script>
const b=document.getElementById('lang');
b.onclick=()=>{const h=document.documentElement,ar=h.lang==='ar';h.lang=ar?'en':'ar';h.dir=ar?'ltr':'rtl';};
</script>
</body></html>
```
Bilingual text: write every text twice as sibling elements, `<span lang="ar">…</span><span lang="en">…</span>` (or `<p lang="ar">` + `<p lang="en">`). The CSS rule above shows one language at a time. Use logical CSS (margin-inline-start, inset-inline-end, text-align:start) so RTL and LTR both work.

## Must-haves
- Mobile-first CSS; test widths 390 and 1440. Tap targets ≥ 44px. Body text ≥ 16px.
- Big WhatsApp button in the hero AND a floating one bottom corner (inline-end) on mobile.
- Maps link, Instagram link, footer with handle and year.
- `loading="lazy"` on all images below the hero; width/height attributes set AND `img{height:auto}` in CSS (otherwise the height attribute overrides aspect-ratio and photos get cropped tall).
- `prefers-reduced-motion`: switch animations off.
- Colour tokens on `:root` named --bg, --ink, --accent, --on-accent (check_site.py reads them). Text on --bg must reach 4.5:1; button text on --accent 4.5:1. If a brand colour fails, keep it for shapes and use a darker/lighter shade for text.
- No lorem, no "coming soon", no empty section, no fake numbers, no testimonials you did not see.

## Self-check
`python scripts/check_site.py site/index.html` then a 390px screenshot. Fix and repeat until clean.
