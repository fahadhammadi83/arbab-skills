# Brief format

## JSON shape for scripts/make_brief.py

```json
{
  "lang": "ar",
  "title": "موجز اليوم",
  "person": "Name (only if known)",
  "date": "الأربعاء 18 نوفمبر 2026",
  "headline": "One sentence: what today is really about.",
  "first": ["Verb first, **the when in bold**.", "...", "..."],
  "meetings": [["Time", "With", "Prepare"], ["10:00 to 10:45", "...", "..."]],
  "reply": [
    {"who": "Name · organisation", "about": "What they asked", "since": "Tuesday",
     "draft": "The reply, ready to send.\nSecond line. Gaps as [ ]."}
  ],
  "waiting": [["Who", "What they owe you", "Since"]],
  "later": ["Item that can wait, with the day if stated."],
  "clashes": ["13:00 lunch overlaps the 12:30 call."]
}
```

- `lang`: "ar" (right to left) or "en".
- `first`: three items at most.
- `meetings`, `waiting`: first row is the header. Leave a list empty (`[]`) to drop the section.
- `reply`: five at most. `draft` may hold line breaks (`\n`).
- `**bold**` works inside any text.

## Section headings

| Section | Arabic | English |
|---|---|---|
| headline | <div dir="rtl" align="right">‏يومك في سطر</div> | Today in one line |
| first | <div dir="rtl" align="right">‏ابدا بهذي</div> | Do first |
| clashes | <div dir="rtl" align="right">‏انتبه</div> | Watch out |
| meetings | <div dir="rtl" align="right">‏اجتماعات اليوم</div> | Today's meetings |
| reply | <div dir="rtl" align="right">‏ناس ينتظرون ردك</div> | Waiting for your reply |
| waiting | <div dir="rtl" align="right">‏إنت تنتظر منهم</div> | You are waiting on |
| later | <div dir="rtl" align="right">‏يتأجل عادي</div> | Can wait |

## Tone examples (style only, never copy the content)

Arabic:

<div dir="rtl" align="right">

‏أرسل عرض السعر لشركة النخبة **قبل اجتماع الساعة ١١**.

‏رد على مديرك: يبي أرقام الأسبوع **اليوم قبل ٣**.

</div>

English:
- Send Delta Build the pickup price **before the 11:00 call**.
- Reply to your manager: she wants the weekly numbers **by 3 pm today**.

## What a good brief does

One page, two minutes. The reader knows what to open first, walks into every meeting prepared, and clears the replies in one sitting because the drafts are already written.
