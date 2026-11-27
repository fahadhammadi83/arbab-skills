# Replies format

## JSON shape for scripts/make_replies.py

```json
{
  "lang": "ar",
  "business": "Name exactly as on the photo",
  "kind": "مقهى",
  "greeting": "Hello message for a new customer. Short.",
  "away": "Message for when you're closed. Gaps as [ساعات الدوام].",
  "quick": [
    {"shortcut": "سعر", "text": "The price list in a few lines, real prices only."},
    {"shortcut": "دوام", "text": "..."},
    {"shortcut": "لاتيه", "text": "One item or category with its real price."}
  ],
  "booking": "How to book or order, from the photo. Gaps where unknown.",
  "faq": [
    {"q": "عندكم توصيل؟", "a": "The answer, built only from the photo."}
  ],
  "gaps": [
    {"gap": "[موقع المحل]", "why": "مب مكتوب في الصورة. حط رابط اللوكيشن."}
  ]
}
```

- `lang`: "ar" (right to left) or "en".
- `business`: printed under the title. Leave empty if the photo shows no name.
- `greeting`, `away`: under 700 characters each (aim for under 350). The script warns above 700.
- `quick`: `shortcut` is one short word with no space and no `/` (the script adds it). Only shortcuts the input supports.
- `booking`: one message. Leave it out (`""`) only if the business takes no bookings or orders at all.
- `faq`: 8 to 12 items. `q` is how a customer would type it; `a` is ready to send.
- `gaps`: every `[...]` used anywhere must be listed here once, with what to put in it. The script warns if one is missing.
- Line breaks: use `\n` inside any text.

## Outputs

- `replies.html`: phone page, one Copy button per message, gaps highlighted in yellow, plus the "where each one goes" steps.
- `replies.txt`: the same messages as plain text, one block each.

## Shortcut menu (Arabic default, English in brackets)

Use only the ones the input supports.

| Shortcut | When |
|---|---|
| `سعر` (price) | always, if the input has prices |
| `دوام` (hours) | always; a gap if the input has no hours |
| `موقع` (location) | always; a gap if the input has no address |
| `حجز` (book) | the input mentions booking, appointments or a phone for orders |
| `طلب` (order) | the business sells things to order (bakery, kitchen, shop) |
| `توصيل` (delivery) | the input mentions delivery |
| `دفع` (payment) | the input mentions payment methods |
| one per main item or category | with its real price from the input |

## Tone examples (style only, never copy the content)

<div dir="rtl" align="right">

‏هلا والله، حياك في محلنا. شو تحب نخدمك فيه؟

‏مرحبا، احنا مسكرين الحين. نرد عليك أول ما نفتح إن شاء الله.

‏الكرك بـ 3 درهم، والشاي الأحمر بـ 2 درهم.

</div>

English:
- Hi, welcome to [business]. How can we help?
- We're closed right now. We'll reply as soon as we open.
