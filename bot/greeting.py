import html
import random
import re
from datetime import date

from . import db
from .translit import has_latin, lat2cyr

FALLBACK = {
    "uz_latn": "🎉 <b>{full_name}</b>, tug‘ilgan kuningiz muborak! {mention}",
    "uz_cyrl": "🎉 <b>{full_name}</b>, туғилган кунингиз муборак! {mention}",
    "ru": "🎉 <b>{full_name}</b>, с днём рождения! {mention}",
}

PLACEHOLDERS_HELP = (
    "<code>{full_name}</code> — familiya, ism, otasining ismi\n"
    "<code>{name}</code> — ism va otasining ismi (Azamat Naimovich)\n"
    "<code>{first_name}</code> — faqat ism\n"
    "<code>{last_name}</code> — familiya\n"
    "<code>{patronymic}</code> — otasining ismi\n"
    "<code>{age}</code> — necha yoshga to‘lgani\n"
    "<code>{mention}</code> — @telegram (kiritilgan bo‘lsa)"
)


def parse_date(text: str) -> date | None:
    text = text.strip()
    m = re.fullmatch(r"(\d{1,2})[./\- ](\d{1,2})[./\- ](\d{4})", text)
    if m:
        d, mth, y = map(int, m.groups())
    else:
        m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
        if not m:
            return None
        y, mth, d = map(int, m.groups())
    try:
        result = date(y, mth, d)
    except ValueError:
        return None
    return result if 1900 <= y <= date.today().year else None


def birth_date(emp) -> date:
    return date.fromisoformat(emp["birth_date"])


def age_on(emp, day: date) -> int:
    b = birth_date(emp)
    return day.year - b.year - ((day.month, day.day) < (b.month, b.day))


def next_birthday(emp, today: date) -> date:
    b = birth_date(emp)
    for year in (today.year, today.year + 1):
        try:
            nb = date(year, b.month, b.day)
        except ValueError:  # 29-fevral
            nb = date(year, 2, 28)
        if nb >= today:
            return nb
    raise AssertionError


def name_parts(full_name: str) -> dict[str, str]:
    words = full_name.split()
    return {
        "full_name": full_name,
        "last_name": words[0] if words else "",
        "first_name": words[1] if len(words) > 1 else (words[0] if words else ""),
        "patronymic": " ".join(words[2:]),
    }


def render(template: str, emp, lang: str, day: date) -> str:
    full = emp["full_name"]
    if lang in ("uz_cyrl", "ru") and has_latin(full):
        full = lat2cyr(full)
    parts = name_parts(full)
    parts["name"] = " ".join(x for x in (parts["first_name"], parts["patronymic"]) if x)
    tg = (emp["telegram"] or "").strip()
    values = {k: html.escape(v) for k, v in parts.items()}
    values["age"] = str(age_on(emp, day))
    values["mention"] = html.escape(tg) if tg else ""
    text = template
    for k, v in values.items():
        text = text.replace("{" + k + "}", v)
    # {mention} bo‘sh qolsa ortiqcha bo‘shliqlarni olib tashlaymiz
    return re.sub(r"[ \t]+\n", "\n", text).strip()


def pick_template(lang: str, gender: str) -> str:
    rows = db.list_templates(lang, gender) or db.list_templates(lang, "M" if gender == "F" else "F")
    return random.choice(rows)["text"] if rows else FALLBACK[lang]


def make_greeting(emp, day: date, lang: str | None = None) -> str:
    lang = lang or db.get_setting("lang")
    return render(pick_template(lang, emp["gender"]), emp, lang, day)
