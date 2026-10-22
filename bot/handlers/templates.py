import html

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from .. import config, db, scheduler
from ..greeting import PLACEHOLDERS_HELP, render
from ..keyboards import BTN_TEMPLATES, MENU_BUTTONS, cancel_menu, ikb, main_menu
from .common import IsAdmin

router = Router(name="templates")
router.message.filter(F.chat.type == "private", IsAdmin())
router.callback_query.filter(IsAdmin())

SAMPLE = {
    "M": {"full_name": "Karimov Jasur Anvarovich", "birth_date": "1990-05-15", "gender": "M", "telegram": "@jasur"},
    "F": {"full_name": "Karimova Nilufar Anvarovna", "birth_date": "1992-03-08", "gender": "F", "telegram": "@nilufar"},
}
GENDER_TITLE = {"M": "👨 Erkaklar uchun", "F": "👩 Ayollar uchun"}


class TplEdit(StatesGroup):
    text = State()


def sample_render(text: str, lang: str, gender: str) -> str:
    return render(text, SAMPLE[gender], lang, scheduler.today())


def menu_view():
    current = db.get_setting("lang")
    rows = [
        [(f"{name}{' ✅' if code == current else ''}", f"tpl:l:{code}")]
        for code, name in config.LANGS.items()
    ]
    text = (
        "📝 <b>Tabrik shablonlari</b>\n\n"
        f"Guruhga hozir <b>{config.LANGS[current]}</b> tilida yoziladi (✅). "
        "Tilni ⚙️ Sozlamalardan o‘zgartirasiz.\n\n"
        "Har bir til va jins uchun bir nechta shablon bo‘lishi mumkin — bot har safar "
        "tasodifiy birini tanlaydi, shunda tabriklar takrorlanmaydi."
    )
    return text, ikb(*rows)


@router.message(F.text == BTN_TEMPLATES)
async def templates_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    text, kb = menu_view()
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "tpl:menu")
async def templates_menu_cb(cb: CallbackQuery) -> None:
    text, kb = menu_view()
    await cb.message.edit_text(text, reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.startswith("tpl:l:"))
async def lang_menu(cb: CallbackQuery) -> None:
    lang = cb.data.split(":")[2]
    rows = [
        [(f"{GENDER_TITLE[g]} ({db.count_templates(lang, g)})", f"tpl:list:{lang}:{g}:0")] for g in ("M", "F")
    ]
    rows.append([("⬅️ Orqaga", "tpl:menu")])
    await cb.message.edit_text(f"📝 <b>{config.LANGS[lang]}</b> shablonlari:", reply_markup=ikb(*rows))
    await cb.answer()


@router.callback_query(F.data.startswith("tpl:list:"))
async def tpl_list(cb: CallbackQuery) -> None:
    _, _, lang, g, idx = cb.data.split(":")
    await show_template(cb.message, lang, g, int(idx), edit=True)
    await cb.answer()


async def show_template(msg: Message, lang: str, g: str, idx: int, edit: bool = False) -> None:
    items = db.list_templates(lang, g)
    header = f"📝 {config.LANGS[lang]} · {GENDER_TITLE[g]}"
    add_btn = [("➕ Yangi shablon", f"tpl:add:{lang}:{g}")]
    back_btn = [("⬅️ Orqaga", f"tpl:l:{lang}")]
    if not items:
        text, kb = f"{header}\n\nShablon yo‘q.", ikb(add_btn, back_btn)
    else:
        idx = max(0, min(idx, len(items) - 1))
        t = items[idx]
        nav = []
        if idx > 0:
            nav.append(("◀️", f"tpl:list:{lang}:{g}:{idx - 1}"))
        nav.append((f"{idx + 1} / {len(items)}", "noop"))
        if idx < len(items) - 1:
            nav.append(("▶️", f"tpl:list:{lang}:{g}:{idx + 1}"))
        text = f"{header} — №{idx + 1}\n\n{t['text']}"
        kb = ikb(
            nav,
            [("👁 Namuna", f"tpl:pv:{t['id']}"), ("✏️ Tahrirlash", f"tpl:ed:{t['id']}"), ("🗑", f"tpl:del:{t['id']}")],
            add_btn,
            back_btn,
        )
    if edit:
        await msg.edit_text(text, reply_markup=kb)
    else:
        await msg.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("tpl:pv:"))
async def tpl_preview(cb: CallbackQuery) -> None:
    t = db.get_template(int(cb.data.split(":")[2]))
    if t:
        await scheduler.deliver(cb.bot, cb.message.chat.id, sample_render(t["text"], t["lang"], t["gender"]), t["gender"])
    await cb.answer()


@router.callback_query(F.data.startswith("tpl:del:"))
async def tpl_delete_confirm(cb: CallbackQuery) -> None:
    i = cb.data.split(":")[2]
    t = db.get_template(int(i))
    if not t:
        return await cb.answer("Topilmadi")
    await cb.message.edit_reply_markup(
        reply_markup=ikb([("🗑 Ha, o‘chirish", f"tpl:delok:{i}"), ("⬅️ Yo‘q", f"tpl:list:{t['lang']}:{t['gender']}:0")])
    )
    await cb.answer("Shablon o‘chirilsinmi?")


@router.callback_query(F.data.startswith("tpl:delok:"))
async def tpl_delete(cb: CallbackQuery) -> None:
    t = db.get_template(int(cb.data.split(":")[2]))
    if t:
        db.delete_template(t["id"])
        await show_template(cb.message, t["lang"], t["gender"], 0, edit=True)
    await cb.answer("O‘chirildi")


ASK_TEXT = (
    "✍️ Shablon matnini yuboring. Telegramdagi <b>qalin</b>, <i>kursiv</i> formatlash va emojilar saqlanadi.\n\n"
    "Quyidagi so‘zlar xodim ma’lumotiga almashtiriladi:\n" + PLACEHOLDERS_HELP
)


@router.callback_query(F.data.startswith("tpl:add:"))
async def tpl_add(cb: CallbackQuery, state: FSMContext) -> None:
    _, _, lang, g = cb.data.split(":")
    await state.set_state(TplEdit.text)
    await state.update_data(lang=lang, gender=g, tpl_id=None)
    await cb.message.answer(ASK_TEXT, reply_markup=cancel_menu)
    await cb.answer()


@router.callback_query(F.data.startswith("tpl:ed:"))
async def tpl_edit(cb: CallbackQuery, state: FSMContext) -> None:
    t = db.get_template(int(cb.data.split(":")[2]))
    if not t:
        return await cb.answer("Topilmadi")
    await state.set_state(TplEdit.text)
    await state.update_data(lang=t["lang"], gender=t["gender"], tpl_id=t["id"])
    await cb.message.answer(ASK_TEXT + "\n\n<i>Hozirgi matnni nusxa olib, o‘zgartirib yuborishingiz mumkin.</i>",
                            reply_markup=cancel_menu)
    await cb.answer()


@router.message(TplEdit.text, F.text, ~F.text.in_(MENU_BUTTONS))
async def tpl_save(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    text = message.html_text.strip()
    try:
        await message.answer("👁 Namuna:\n\n" + sample_render(text, data["lang"], data["gender"]))
    except TelegramBadRequest as e:
        return await message.answer(f"❗ Matnda xato bor, qaytadan yuboring.\n<code>{html.escape(e.message)}</code>")
    if data["tpl_id"]:
        db.update_template(data["tpl_id"], text)
    else:
        db.add_template(data["lang"], data["gender"], text)
    await state.clear()
    await message.answer("✅ Shablon saqlandi", reply_markup=main_menu)
    items = db.list_templates(data["lang"], data["gender"])
    idx = next((i for i, t in enumerate(items) if t["text"] == text), 0)
    await show_template(message, data["lang"], data["gender"], idx)
