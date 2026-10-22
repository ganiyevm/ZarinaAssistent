from datetime import date, timedelta

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from .. import db, scheduler
from ..greeting import age_on, make_greeting, next_birthday, parse_date, birth_date
from ..keyboards import (
    BTN_ADD, BTN_LIST, BTN_SEARCH, BTN_UPCOMING, MENU_BUTTONS, cancel_menu, ikb, main_menu,
)
from .common import IsAdmin, esc

router = Router(name="employees")
router.message.filter(F.chat.type == "private", IsAdmin())
router.callback_query.filter(IsAdmin())

PER_PAGE = 10
WEEKDAYS = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]


class AddEmp(StatesGroup):
    name = State()
    birth = State()
    gender = State()


class EditEmp(StatesGroup):
    value = State()


class Search(StatesGroup):
    query = State()


def gender_icon(g: str) -> str:
    return "👨" if g == "M" else "👩"


def emp_button(e) -> tuple[str, str]:
    return f"{gender_icon(e['gender'])} {e['full_name']} — {birth_date(e):%d.%m}", f"emp:v:{e['id']}"


# ---------- ro‘yxat ----------

def list_view(page: int):
    total = db.count_employees()
    pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = max(0, min(page, pages - 1))
    rows = [[emp_button(e)] for e in db.list_employees(page * PER_PAGE, PER_PAGE)]
    nav = []
    if page > 0:
        nav.append(("◀️", f"emp:p:{page - 1}"))
    nav.append((f"{page + 1} / {pages}", "noop"))
    if page < pages - 1:
        nav.append(("▶️", f"emp:p:{page + 1}"))
    rows.append(nav)
    text = f"👥 <b>Xodimlar ro‘yxati</b> — jami {total} ta\n\nXodimni tanlang yoki ismini yozib qidiring."
    return text, ikb(*rows)


@router.message(F.text == BTN_LIST)
async def show_list(message: Message, state: FSMContext) -> None:
    await state.clear()
    text, kb = list_view(0)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("emp:p:"))
async def list_page(cb: CallbackQuery) -> None:
    text, kb = list_view(int(cb.data.split(":")[2]))
    await cb.message.edit_text(text, reply_markup=kb)
    await cb.answer()


# ---------- qidiruv ----------

@router.message(F.text == BTN_SEARCH)
async def ask_search(message: Message, state: FSMContext) -> None:
    await state.set_state(Search.query)
    await message.answer(
        "🔍 Xodimning ismi yoki familiyasini yozing (lotin yoki kirillda):", reply_markup=cancel_menu
    )


async def do_search(message: Message, query: str) -> None:
    found = db.search_employees(query)
    if not found:
        await message.answer(f"«{esc(query)}» bo‘yicha hech kim topilmadi.", reply_markup=main_menu)
        return
    await message.answer(f"🔍 Topildi: {len(found)} ta", reply_markup=main_menu)
    await message.answer("Tanlang:", reply_markup=ikb(*[[emp_button(e)] for e in found]))


@router.message(Search.query, F.text, ~F.text.in_(MENU_BUTTONS))
async def search_state(message: Message, state: FSMContext) -> None:
    await state.clear()
    await do_search(message, message.text)


# ---------- yaqin tug‘ilgan kunlar ----------

@router.message(F.text == BTN_UPCOMING)
async def upcoming(message: Message, state: FSMContext) -> None:
    await state.clear()
    today = scheduler.today()
    items = []
    for e in db.list_employees():
        nb = next_birthday(e, today)
        if (nb - today).days <= 30:
            items.append((nb, e))
    items.sort(key=lambda x: (x[0], x[1]["full_name"]))
    if not items:
        await message.answer("Keyingi 30 kunda tug‘ilgan kun yo‘q.")
        return
    lines = ["🎂 <b>Keyingi 30 kun ichida:</b>\n"]
    current = None
    for nb, e in items:
        if nb != current:
            current = nb
            label = "Bugun" if nb == today else "Ertaga" if nb == today + timedelta(days=1) else WEEKDAYS[nb.weekday()]
            lines.append(f"\n<b>{nb:%d.%m} — {label}</b>")
        mark = " ✅" if nb == today and db.was_sent(e["id"], today) else ""
        lines.append(f"{gender_icon(e['gender'])} {esc(e['full_name'])} ({age_on(e, nb)} yosh){mark}")
    await message.answer("\n".join(lines)[:4000])


# ---------- xodim kartochkasi ----------

def card(emp) -> tuple[str, object]:
    today = scheduler.today()
    nb = next_birthday(emp, today)
    days = (nb - today).days
    when = "🎉 <b>bugun!</b>" if days == 0 else f"{nb:%d.%m.%Y} ({days} kundan keyin)"
    text = (
        f"{gender_icon(emp['gender'])} <b>{esc(emp['full_name'])}</b>\n\n"
        f"🎂 Tug‘ilgan sana: {birth_date(emp):%d.%m.%Y} ({age_on(emp, today)} yosh)\n"
        f"⚧ Jins: {'Erkak' if emp['gender'] == 'M' else 'Ayol'}\n"
        f"💬 Telegram: {esc(emp['telegram']) or '—'}\n"
        f"📅 Keyingi tug‘ilgan kun: {when}"
    )
    i = emp["id"]
    kb = ikb(
        [("✏️ F.I.Sh", f"emp:e:{i}:full_name"), ("✏️ Sana", f"emp:e:{i}:birth_date")],
        [("✏️ Jins", f"emp:gs:{i}"), ("✏️ Telegram", f"emp:e:{i}:telegram")],
        [("👁 Tabrik namunasi", f"emp:prev:{i}"), ("📨 Guruhga yuborish", f"emp:send:{i}")],
        [("🗑 O‘chirish", f"emp:del:{i}")],
        [("⬅️ Ro‘yxatga", "emp:p:0")],
    )
    return text, kb


async def show_card(target: Message, emp_id: int, edit: bool = False) -> None:
    emp = db.get_employee(emp_id)
    if not emp:
        await target.answer("Xodim topilmadi (o‘chirilgan bo‘lishi mumkin).")
        return
    text, kb = card(emp)
    if edit:
        await target.edit_text(text, reply_markup=kb)
    else:
        await target.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("emp:v:"))
async def view(cb: CallbackQuery) -> None:
    await show_card(cb.message, int(cb.data.split(":")[2]), edit=True)
    await cb.answer()


@router.callback_query(F.data.startswith("emp:prev:"))
async def preview(cb: CallbackQuery) -> None:
    emp = db.get_employee(int(cb.data.split(":")[2]))
    if emp:
        day = next_birthday(emp, scheduler.today())
        await cb.message.answer("👁 <i>Guruhda shunday ko‘rinadi (shablon tasodifiy tanlanadi):</i>")
        await scheduler.deliver(cb.bot, cb.message.chat.id, make_greeting(emp, day), emp["gender"])
    await cb.answer()


@router.callback_query(F.data.startswith("emp:send:"))
async def send_confirm(cb: CallbackQuery) -> None:
    i = cb.data.split(":")[2]
    await cb.message.edit_reply_markup(
        reply_markup=ikb([("✅ Ha, hozir yuborish", f"emp:sendok:{i}"), ("⬅️ Yo‘q", f"emp:v:{i}")])
    )
    await cb.answer("Tabrik hozir guruhga yuborilsinmi?")


@router.callback_query(F.data.startswith("emp:sendok:"))
async def send_now(cb: CallbackQuery) -> None:
    emp = db.get_employee(int(cb.data.split(":")[2]))
    if not emp:
        return await cb.answer("Topilmadi")
    try:
        await scheduler.send_greeting(cb.bot, emp, scheduler.today())
        await cb.answer("✅ Guruhga yuborildi", show_alert=True)
    except Exception as e:
        await cb.answer(f"❌ Yuborilmadi: {e}"[:190], show_alert=True)
    await show_card(cb.message, emp["id"], edit=True)


# ---------- o‘chirish ----------

@router.callback_query(F.data.startswith("emp:del:"))
async def delete_confirm(cb: CallbackQuery) -> None:
    i = cb.data.split(":")[2]
    await cb.message.edit_reply_markup(
        reply_markup=ikb([("🗑 Ha, o‘chirish", f"emp:delok:{i}"), ("⬅️ Yo‘q", f"emp:v:{i}")])
    )
    await cb.answer("Rostdan o‘chirilsinmi?")


@router.callback_query(F.data.startswith("emp:delok:"))
async def delete(cb: CallbackQuery) -> None:
    emp = db.get_employee(int(cb.data.split(":")[2]))
    if emp:
        db.delete_employee(emp["id"])
        await cb.message.edit_text(f"🗑 <b>{esc(emp['full_name'])}</b> ro‘yxatdan o‘chirildi.")
    await cb.answer()


# ---------- tahrirlash ----------

PROMPTS = {
    "full_name": "Yangi F.I.Sh ni yozing (Familiya Ism Otasining ismi):",
    "birth_date": "Yangi tug‘ilgan sanani yozing (kk.oo.yyyy, masalan 17.12.1976):",
    "telegram": "Telegram username yozing (masalan @azamat). O‘chirish uchun «-» yuboring:",
}


@router.callback_query(F.data.startswith("emp:e:"))
async def edit_start(cb: CallbackQuery, state: FSMContext) -> None:
    _, _, emp_id, field = cb.data.split(":")
    await state.set_state(EditEmp.value)
    await state.update_data(emp_id=int(emp_id), field=field)
    await cb.message.answer(PROMPTS[field], reply_markup=cancel_menu)
    await cb.answer()


@router.message(EditEmp.value, F.text, ~F.text.in_(MENU_BUTTONS))
async def edit_value(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    field, value = data["field"], message.text.strip()
    if field == "birth_date":
        value = parse_date(value)
        if not value:
            return await message.answer("❗ Sana noto‘g‘ri. Masalan: 17.12.1976")
    elif field == "telegram":
        value = "" if value == "-" else "@" + value.lstrip("@").split("/")[-1]
    elif len(value.split()) < 2:
        return await message.answer("❗ Kamida familiya va ism kerak.")
    db.update_employee(data["emp_id"], **{field: value})
    await state.clear()
    await message.answer("✅ Saqlandi", reply_markup=main_menu)
    await show_card(message, data["emp_id"])


@router.callback_query(F.data.startswith("emp:gs:"))
async def gender_choose(cb: CallbackQuery) -> None:
    i = cb.data.split(":")[2]
    await cb.message.edit_reply_markup(
        reply_markup=ikb([("👨 Erkak", f"emp:g:{i}:M"), ("👩 Ayol", f"emp:g:{i}:F")], [("⬅️ Orqaga", f"emp:v:{i}")])
    )
    await cb.answer()


@router.callback_query(F.data.startswith("emp:g:"))
async def gender_set(cb: CallbackQuery) -> None:
    _, _, emp_id, g = cb.data.split(":")
    db.update_employee(int(emp_id), gender=g)
    await show_card(cb.message, int(emp_id), edit=True)
    await cb.answer("✅ Saqlandi")


# ---------- yangi xodim ----------

@router.message(F.text == BTN_ADD)
async def add_start(message: Message, state: FSMContext) -> None:
    await state.set_state(AddEmp.name)
    await message.answer(
        "➕ <b>Yangi xodim</b>\n\nF.I.Sh ni yozing (Familiya Ism Otasining ismi):\n"
        "<i>Masalan: Karimov Jasur Anvarovich</i>",
        reply_markup=cancel_menu,
    )


@router.message(AddEmp.name, F.text, ~F.text.in_(MENU_BUTTONS))
async def add_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if len(name.split()) < 2:
        return await message.answer("❗ Kamida familiya va ism kerak.")
    await state.update_data(name=name)
    await state.set_state(AddEmp.birth)
    await message.answer("🎂 Tug‘ilgan sanasi (kk.oo.yyyy, masalan 17.12.1976):")


@router.message(AddEmp.birth, F.text, ~F.text.in_(MENU_BUTTONS))
async def add_birth(message: Message, state: FSMContext) -> None:
    d = parse_date(message.text)
    if not d:
        return await message.answer("❗ Sana noto‘g‘ri. Masalan: 17.12.1976")
    await state.update_data(birth=d.isoformat())
    await state.set_state(AddEmp.gender)
    await message.answer("⚧ Jinsi:", reply_markup=ikb([("👨 Erkak", "add:g:M"), ("👩 Ayol", "add:g:F")]))


@router.callback_query(AddEmp.gender, F.data.startswith("add:g:"))
async def add_gender(cb: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()
    emp_id = db.add_employee(data["name"], date.fromisoformat(data["birth"]), cb.data.split(":")[2])
    await cb.message.edit_text("✅ Xodim qo‘shildi")
    await cb.message.answer("Asosiy menyu", reply_markup=main_menu)
    await show_card(cb.message, emp_id)
    await cb.answer()


# ---------- erkin matn = qidiruv ----------

@router.message(StateFilter(None), F.text, ~F.text.startswith("/"), ~F.text.in_(MENU_BUTTONS))
async def free_text_search(message: Message) -> None:
    await do_search(message, message.text)
