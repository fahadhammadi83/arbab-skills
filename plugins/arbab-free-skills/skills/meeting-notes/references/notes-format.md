# Minutes JSON (input to scripts/make_notes.py)

```json
{
  "lang": "ar",
  "title": "محضر اجتماع: إطلاق فرع الخوانيج",
  "date": "2026-11-12",
  "date_label": "الخميس 12 نوفمبر 2026",
  "attendees": ["سالم (المدير)", "نورة (التسويق)", "خالد (المشتريات)"],
  "summary": "اتفقنا نفتح الفرع يوم 1 ديسمبر والميزانية 40 ألف للإعلانات.",
  "decisions": ["الافتتاح 1 ديسمبر", "ميزانية الإعلانات 40,000 درهم"],
  "tasks": [
    {"owner": "نورة", "task": "خطة إعلانات الافتتاح", "due": "2026-11-19", "due_label": "الخميس 19 نوفمبر (الخميس الجاي)"},
    {"owner": "غير محدد", "task": "حجز الكاتيرنغ", "due": "", "due_label": "غير محدد"}
  ],
  "carried": [
    {"owner": "خالد", "task": "عرض سعر المكيفات", "status": "done"}
  ],
  "open_questions": ["من يتابع حجز الكاتيرنغ؟"],
  "numbers": [["البند", "الرقم"], ["ميزانية الإعلانات", "40,000 درهم"]],
  "next_meeting": "الخميس 19 نوفمبر، 10 الصبح"
}
```

- `lang`: `ar` or `en` (the language most of the meeting used). Arabic gets right-to-left everywhere.
- `date`: ISO date of the meeting (goes in the tracker). `due`: ISO date or empty; `due_label`: how it reads in the minutes.
- `carried`: last meeting's tasks with `status` = `done`, `open` or `dropped`. Leave out if there was no earlier tracker.
- `numbers`: a table, first row = headers. Leave out if no numbers were said.
- Leave out any section with nothing in it. Use `**bold**` for a word that must stand out.
- Optional `headings`: the company's own section names, e.g. `{"tasks": "Action items"}`.
