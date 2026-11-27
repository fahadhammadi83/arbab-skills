# Style library (8 directions)

Each style = structure + fonts + shapes + motion. Colours always come from the business: map their 3 brand colours to `--bg`, `--ink`, `--accent` (plus derived `--surface`, `--muted`). Sample colours below are only for when a brand has a single colour.

Type scale is given as clamp() for the hero title / h2 / body. Spacing = vertical padding of sections.

---

## 1. Luxury dark
- Fits: fine dining, perfume, jewellery, high-end salons, cars, premium real estate. Dark photo mood.
- Layout: full-bleed photo hero with a dark gradient, centred name; narrow text column (max 620px); generous space; thin 1px hairlines between sections.
- Fonts: Arabic **El Messiri** (500/700); Latin **Bodoni Moda** (display, italic for accents) + **Jost** 300/400 for body and small caps eyebrows.
- Scale: hero clamp(2.6rem, 8vw, 6rem) / h2 clamp(1.8rem, 4vw, 3rem) / body 1rem, line-height 1.8.
- Spacing: 120px desktop, 80px mobile.
- Radius: 0. Buttons are thin outlined rectangles; WhatsApp button filled with the light brand colour.
- Section shapes: full-width image bands, numbered menu list with dotted leaders, masonry gallery with 2px gaps.
- Motion: slow fade + 12px rise on scroll (600ms), hero image slow zoom (scale 1.06 over 12s). Nothing bouncy.
- Sample colours: deep ink #0E1424, ivory #EDE6DC, muted brass is FORBIDDEN (no gold); use the brand's own light tone.

## 2. Clean clinic
- Fits: dental, skin, medical, physio, labs, pharmacies. Bright mood, blue/teal/white brands.
- Layout: split hero (text + photo card), booking card visible on first screen, trust chips row, service cards grid, team cards, location block with map button.
- Fonts: Arabic **IBM Plex Sans Arabic** (400/600/700); Latin **Plus Jakarta Sans** (400/600/800).
- Scale: hero clamp(2.2rem, 6vw, 4rem) / h2 clamp(1.6rem, 3.4vw, 2.4rem) / body 1.02rem, line-height 1.7.
- Spacing: 96px / 64px.
- Radius: 20px cards, 999px buttons and chips.
- Section shapes: white cards on a very light tint of the brand colour, soft shadow (0 10px 30px rgba(brand,.10)), icon circles (inline SVG line icons), one solid brand-colour band for the booking CTA.
- Motion: cards lift 4px on hover, fade-in 400ms. Calm.
- Sample colours: brand blue #0B57A4, white, tint #EEF4FB.

## 3. Bold street
- Fits: creators, consultants with a loud brand, streetwear, gyms, burger/food trucks, barbers, tech startups. High-contrast, neon or saturated accent.
- Layout: text-led hero with a huge headline (2-3 words per line), a cut-out or tightly cropped photo overlapping the edge, a marquee strip, sticker-style tags, alternating dark / accent / light blocks.
- Fonts: Arabic **Changa** (600/800); Latin **Archivo** (800 for headings with font-stretch 112% where supported, 400 body).
- Scale: hero clamp(3rem, 12vw, 8.5rem), line-height 0.95 / h2 clamp(2rem, 6vw, 4rem) / body 1.05rem.
- Spacing: 100px / 70px.
- Radius: 0 for blocks; 999px pill stickers rotated -3deg to 4deg.
- Section shapes: hard offset shadows (6px 6px 0 var(--ink)), thick 3px borders, numbered service rows that invert colours on hover, horizontal scroll strip of their post covers.
- Motion: marquee scroll (30s linear), quick 200ms hovers, stickers wobble once on load.
- Sample colours: night #0A0A0A, accent neon, off-white.

## 4. Warm café
- Fits: cafés, bakeries, dessert shops, home kitchens, flower shops. Warm mood, browns, creams, terracotta.
- Layout: split hero with a rounded photo and a handwritten-feel tagline; menu first (cards with item names, prices only if visible); scroll-strip gallery; opening hours if visible; cosy map block.
- Fonts: Arabic **Almarai** (400/700/800); Latin **Fraunces** (soft serif, 600 italic accents) + Almarai Latin for body.
- Scale: hero clamp(2.4rem, 7vw, 5rem) / h2 clamp(1.7rem, 4vw, 2.8rem) / body 1.02rem.
- Spacing: 90px / 64px.
- Radius: 28px; photos with organic blob masks (border-radius 60% 40% 55% 45% / 50% 55% 45% 50%).
- Section shapes: paper-tone background, wavy SVG dividers, menu cards like a printed card, small doodle stars (inline SVG).
- Motion: gentle float on decorative shapes (6s ease-in-out), fade-ups.
- Sample colours: cream #F6EFE6, espresso #3B2A20, terracotta #C8643B.

## 5. Editorial minimal
- Fits: architects, interior designers, photographers, fashion labels, galleries, boutique hotels. Neutral photos, lots of white.
- Layout: text-led hero with an oversized serif line and a small caption; numbered sections (01, 02...); asymmetric two-column grid; masonry gallery; footer like a magazine colophon.
- Fonts: Arabic **Alexandria** (300/500); Latin **Instrument Serif** (display) + **Inter Tight** 400 (body).
- Scale: hero clamp(2.8rem, 9vw, 7rem), line-height 1 / h2 clamp(1.8rem, 4vw, 3.2rem) / body 1rem.
- Spacing: 140px / 90px.
- Radius: 0. Hairline rules, lots of empty space, captions in small caps.
- Motion: image reveal with clip-path (left to right in EN, right to left in AR), 800ms.
- Sample colours: paper #F4F2EE, ink #161616, one brand accent used sparingly.

## 6. Soft pastel
- Fits: kids, nurseries, beauty/nails, lash studios, gift shops, cake studios, women's wellness. Pastel or pink/lilac/mint brands.
- Layout: centred hero with a big rounded photo and floating blobs; services as pill cards; grid gallery with rounded tiles; friendly FAQ only if they posted the answers.
- Fonts: Arabic **Rubik** (400/600/700); Latin **Nunito** (400/800).
- Scale: hero clamp(2.3rem, 7vw, 4.6rem) / h2 clamp(1.6rem, 3.6vw, 2.5rem) / body 1.05rem.
- Spacing: 88px / 60px.
- Radius: 32px cards, 999px buttons.
- Section shapes: blob backgrounds, wavy dividers, pastel cards on white, emoji-free.
- Motion: soft bounce on buttons (cubic-bezier(.34,1.56,.64,1)), floating blobs.
- Sample colours: blush #F7D6DF, lilac #DCD3F5, plum ink #3D2645.

## 7. Corporate trust
- Fits: law firms, accountants, consultancies (B2B), logistics, insurance, training centres, government suppliers.
- Layout: split hero with headline + 2 buttons; numbers row only if numbers are visible; services in a structured 3-column grid; process steps; client logos only if shown on their account.
- Fonts: Arabic **Cairo** (400/600/700); Latin **Manrope** (400/700/800).
- Scale: hero clamp(2.2rem, 5.5vw, 3.8rem) / h2 clamp(1.6rem, 3vw, 2.4rem) / body 1rem.
- Spacing: 96px / 64px.
- Radius: 8px.
- Section shapes: thin borders, a deep brand-colour band, a 12-column feel, icon + heading + 2-line text tiles.
- Motion: minimal: counters do NOT animate fake numbers; only fade-in.
- Sample colours: navy #10233F, white, signal accent.

## 8. Modern Gulf
- Fits: abayas, oud and perfume (local), majlis furniture, Emirati food, events, national brands, Arabic calligraphy, dates. Brands that lean into heritage but want modern.
- Layout: centred hero inside an arch-shaped photo frame; subtle 8-point star geometric pattern (inline SVG, 4-6% opacity) behind sections; arches for gallery tiles; Arabic headline large, English smaller under it.
- Fonts: Arabic **Tajawal** (400/700/800); Latin **Sora** (300/600).
- Scale: hero clamp(2.6rem, 8vw, 5.5rem) / h2 clamp(1.8rem, 4vw, 2.8rem) / body 1.05rem.
- Spacing: 100px / 70px.
- Radius: arches (border-radius: 999px 999px 0 0) for photos, 14px cards.
- Section shapes: arch frames, pattern bands, thin double borders.
- Motion: pattern drifts slowly (60s), arches rise in on scroll.
- Sample colours: sand #EFE6D8, deep teal #0F3B3A, date brown #6B3E26 (never gold).

---

## Choosing quickly

| Business | First pick | Second |
|---|---|---|
| Clinic (dental, skin, medical) | Clean clinic | Corporate trust / Soft pastel (kids, women) |
| Fine dining, dark photos | Luxury dark | Editorial minimal |
| Café, bakery, casual food | Warm café | Bold street (burgers, trucks) |
| Creator, consultant, coach | Bold street | Editorial minimal / Corporate trust |
| Beauty, nails, kids | Soft pastel | Luxury dark (high-end) |
| Abaya, oud, heritage | Modern Gulf | Luxury dark |
| B2B, law, finance | Corporate trust | Editorial minimal |
| Design, fashion, photo | Editorial minimal | Luxury dark |

Tie-breakers: photo mood (dark photos never go in a pastel style), type feel of their posts (heavy condensed posts → Bold street), and their colours (neon → Bold street; navy + cream → Luxury dark or Corporate).
