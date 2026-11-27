# Report format

## JSON shape for scripts/make_report.py

```json
{
  "lang": "ar",
  "style": "relaxed or formal (government); Arabic only",
  "title": "التقرير الأسبوعي",
  "person": "Name · Role · Team (only what is known)",
  "week": "9 to 13 Nov 2026",
  "to": "Manager name, or empty",
  "headline": "One sentence: the most important outcome of the week.",
  "done": ["Verb first, **numbers in bold**.", "..."],
  "numbers": [["What", "This week", "Note"], ["...", "...", "..."]],
  "in_progress": [["Item", "Where it stands", "Expected"], ["...", "...", "..."]],
  "blockers": [["What is blocked", "Who can unblock it", "Since"]],
  "next_week": ["...", "..."],
  "decisions": ["Approve X? (yes / no)"]
}
```

- `lang`: "ar" (right to left) or "en".
- `numbers`, `in_progress`, `blockers`: first row is the header. Leave a list empty (`[]`) to drop the section.
- `**bold**` works inside any text.
- `headings` (optional): the company's own section names, e.g. `{"done": "Highlights", "in_progress": "Pipeline", "blockers": "Issues", "next_week": "Plan"}`. Use it whenever the user's old report or template has its own headings; set the section order in the JSON the same way theirs runs.

## Section headings

| Section | Arabic | English |
|---|---|---|
| headline | <div dir="rtl" align="right">‏خلاصة الأسبوع</div> | This week in one line |
| done | <div dir="rtl" align="right">‏اللي خلص هالأسبوع</div> | Done this week |
| numbers | <div dir="rtl" align="right">‏الأرقام</div> | Numbers |
| in_progress | <div dir="rtl" align="right">‏قيد التنفيذ</div> | In progress |
| blockers | <div dir="rtl" align="right">‏اللي واقف وشو أحتاج</div> | Blockers and what I need |
| next_week | <div dir="rtl" align="right">‏الأسبوع الجاي</div> | Next week |
| decisions | <div dir="rtl" align="right">‏قرارات أحتاجها منك</div> | Decisions needed from you |

For a formal government team, use these Arabic headings instead: ملخص الأسبوع · الإنجازات · المؤشرات · الأعمال الجارية · المعوقات والاحتياجات · خطة الأسبوع القادم · قرارات مطلوبة.

## Tone examples (style only, never copy the content)

Arabic, relaxed corporate:

<div dir="rtl" align="right">

‏سلّمنا عرض شركة النخبة يوم الثلاثاء، والرد المتوقع الأسبوع الجاي.

‏ردّينا على **٤٢** استفسار، والوقت المتوسط للرد نزل من يوم لساعتين.

</div>

Arabic, formal government:

<div dir="rtl" align="right">

‏تم إصدار **٣** بيانات صحفية ونشرها عبر المنصات الرسمية.

‏تم التنسيق مع إدارة الفعاليات لترتيبات منتدى الأسبوع القادم.

</div>

English:
- Closed **3** renewals worth **AED 18,400**; the Al Noor account moves to next week.
- Waiting on IT for the CRM login since Tuesday; nothing can be logged until then.

## What a manager wants (keep it in mind)

1. What got done, with numbers. 2. What's stuck and what you need from them. 3. What's next. Two minutes to read, no surprises.
