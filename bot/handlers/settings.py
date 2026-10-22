import json
import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from .. import config, db, scheduler
from ..keyboards import BTN_SETTINGS, MENU_BUTTONS, cancel_menu, ikb, main_menu
from .common import IsAdmin, esc

router = Router(name="settings")
router.message.filter(F.chat.type == "private", IsAdmin())
router.callback_query.filter(IsAdmin())


class SetTime(StatesGroup):
    value = State()


class AddAdmin(StatesGroup):
    value = State()


class AnimUpload(StatesGroup):
    file = State()


def settings_view(user_id: int):
    lang = db.get_setting("lang")
    group = db.get_setting("group_id")
    group_line = f"{esc(db.get_setting('group_title'))} (<code>{group}</code>)" if group else "❗ ulanmagan"
    notify = db.get_setting("notify_admins") == "1"
    pin = db.get_setting("pin") == "1"
    text = (
        "⚙️ <b>Sozlamalar</b>\n\n"
        f"🌐 Tabrik tili: <b>{config.LANGS[lang]}</b>\n"
        f"⏰ Yuborish vaqti: <b>{db.get_setting('send_time')}</b> ({config.TIMEZONE})\n"
        f"👥 Guruh: {group_line}\n"
        f"📌 Tabrikni guruh tepasiga mahkamlash (pin): <b>{'yoqilgan' if pin else 'o‘chirilgan'}</b>\n"
        f"🔔 Adminlarga kunlik hisobot va ertangi ro‘yxat: <b>{'yoqilgan' if notify else 'o‘chirilgan'}</b>"
    )
    rows = [
        [("🌐 Tabrik tili", "set:lang"), ("⏰ Vaqt", "set:time")],
        [("👥 Guruhni ulash", "set:group"), ("🧪 Test xabar", "set:test")],
        [(f"📌 Pin: {'o‘chirish' if pin else 'yoqish'}", "set:pin"),
         (f"🔔 Hisobot: {'o‘chirish' if notify else 'yoqish'}", "set:notify")],
    ]
    rows.append([("🎆 Salyut animatsiyasi", "anim:menu")])
    rows.append([("👮 Adminlar", "adm:list")])
    return text, ikb(*rows)


@router.message(F.text == BTN_SETTINGS)
async def settings_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    text, kb = settings_view(message.from_user.id)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "set:menu")
async def settings_menu_cb(cb: CallbackQuery) -> None:
    text, kb = settings_view(cb.from_user.id)
    await cb.message.edit_text(text, reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data == "set:lang")
async def choose_lang(cb: CallbackQuery) -> None:
    current = db.get_setting("lang")
    rows = [[(f"{n}{' ✅' if c == current else ''}", f"set:lang:{c}")] for c, n in config.LANGS.items()]
    rows.append([("⬅️ Orqaga", "set:menu")])
    await cb.message.edit_text("🌐 Guruhga tabrik qaysi tilda yozilsin?", reply_markup=ikb(*rows))
    await cb.answer()


@router.callback_query(F.data.startswith("set:lang:"))
async def set_lang(cb: CallbackQuery) -> None:
    db.set_setting("lang", cb.data.split(":")[2])
    await settings_menu_cb(cb)


@router.callback_query(F.data == "set:notify")
async def toggle_notify(cb: CallbackQuery) -> None:
    db.set_setting("notify_admins", "0" if db.get_setting("notify_admins") == "1" else "1")
    await settings_menu_cb(cb)


@router.callback_query(F.data == "set:pin")
async def toggle_pin(cb: CallbackQuery) -> None:
    db.set_setting("pin", "0" if db.get_setting("pin") == "1" else "1")
    await settings_menu_cb(cb)


@router.callback_query(F.data == "set:group")
async def group_help(cb: CallbackQuery) -> None:
    me = await cb.bot.get_me()
    await cb.message.answer(
        "👥 <b>Guruhni ulash:</b>\n\n"
        f"1. @{me.username} ni ishxona guruhiga qo‘shing.\n"
        "2. Botni guruhda admin qiling: «Xabar yozish» va «Xabarlarni mahkamlash (pin)» huquqlari bilan.\n"
        "3. Guruhda <code>/setgroup</code> deb yozing.\n\n"
        "Agar guruhda «Mavzular» (topics) bo‘lsa, buyruqni kerakli mavzu ichida yozing — tabriklar o‘sha yerga tushadi."
    )
    await cb.answer()


@router.callback_query(F.data == "set:test")
async def test_message(cb: CallbackQuery) -> None:
    group = db.get_setting("group_id")
    if not group:
        return await cb.answer("Avval guruhni ulang", show_alert=True)
    thread = db.get_setting("thread_id")
    try:
        await cb.bot.send_message(
            int(group), "🤖 ZarinaAssistent ulandi. Bu test xabar.",
            message_thread_id=int(thread) if thread else None,
        )
        await cb.answer("✅ Guruhga yuborildi", show_alert=True)
    except Exception as e:
        await cb.answer(f"❌ Xato: {e}"[:190], show_alert=True)


@router.callback_query(F.data == "set:time")
async def ask_time(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SetTime.value)
    await cb.message.answer("⏰ Tabrik soat nechada yuborilsin? (SS:MM, masalan 09:00)", reply_markup=cancel_menu)
    await cb.answer()


@router.message(SetTime.value, F.text, ~F.text.in_(MENU_BUTTONS))
async def set_time(message: Message, state: FSMContext) -> None:
    m = re.fullmatch(r"(\d{1,2})[:.](\d{2})", message.text.strip())
    if not m or int(m[1]) > 23 or int(m[2]) > 59:
        return await message.answer("❗ Format noto‘g‘ri. Masalan: 09:00")
    db.set_setting("send_time", f"{int(m[1]):02d}:{m[2]}")
    await state.clear()
    note = ""
    if scheduler.now().time() >= scheduler.send_time():
        note = "\n<i>Bugungi vaqt o‘tib ketgan — bugungi hali yuborilmagan tabriklar hozir yuboriladi.</i>"
    await message.answer(f"✅ Vaqt saqlandi: {db.get_setting('send_time')}{note}", reply_markup=main_menu)


# ---------- adminlar (har qanday admin boshqara oladi) ----------

def admins_view():
    rows = [[(f"🗑 {a['name'] or a['user_id']}", f"adm:rm:{a['user_id']}")] for a in db.list_admins()]
    rows.append([("➕ Admin qo‘shish", "adm:add")])
    rows.append([("⬅️ Orqaga", "set:menu")])
    supers = ", ".join(f"<code>{i}</code>" for i in sorted(config.SUPER_ADMINS))
    text = (
        "👮 <b>Adminlar</b>\n\n"
        f"Bosh adminlar (.env faylda): {supers}\n\n"
        "Qo‘shimcha adminlar pastda. O‘chirish uchun ustiga bosing.\n"
        "<i>Har bir admin yangi admin qo‘sha va olib tashlay oladi. Bosh adminlarni faqat .env orqali o‘zgartirish mumkin.</i>"
    )
    return text, ikb(*rows)


@router.callback_query(F.data == "adm:list")
async def admins_list(cb: CallbackQuery) -> None:
    text, kb = admins_view()
    await cb.message.edit_text(text, reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.startswith("adm:rm:"))
async def admin_remove(cb: CallbackQuery) -> None:
    user_id = int(cb.data.split(":")[2])
    if user_id == cb.from_user.id:
        return await cb.answer("O‘zingizni o‘chira olmaysiz", show_alert=True)
    db.remove_admin(user_id)
    await admins_list(cb)


@router.callback_query(F.data == "adm:add")
async def admin_add_start(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddAdmin.value)
    await cb.message.answer(
        "Yangi adminning Telegram ID raqamini yuboring.\n"
        "<i>U botga /start yozsa, bot unga ID sini ko‘rsatadi.</i>\n\n"
        "Ism ham qo‘shish mumkin: <code>123456789 Zarina</code>",
        reply_markup=cancel_menu,
    )
    await cb.answer()


@router.message(AddAdmin.value, F.text, ~F.text.in_(MENU_BUTTONS))
async def admin_add(message: Message, state: FSMContext) -> None:
    parts = message.text.strip().split(maxsplit=1)
    if not parts[0].isdigit():
        return await message.answer("❗ ID faqat raqamlardan iborat bo‘ladi.")
    db.add_admin(int(parts[0]), parts[1] if len(parts) > 1 else "")
    await state.clear()
    await message.answer("✅ Admin qo‘shildi", reply_markup=main_menu)
    text, kb = admins_view()
    await message.answer(text, reply_markup=kb)


# ---------- salyut animatsiyasi ----------

def anim_view():
    def status(g: str) -> str:
        return "✅ bor" if scheduler.get_animation(g) else "— yo‘q"

    text = (
        "🎆 <b>Salyut animatsiyasi</b>\n\n"
        "Animatsiya bo‘lsa, tabrik matni uning tagida bitta xabar bo‘lib chiqadi va "
        "guruhga kirgan har bir odamda o‘zi o‘ynaydi.\n\n"
        f"👨 Erkaklar uchun: {status('M')}\n"
        f"👩 Ayollar uchun: {status('F')}"
    )
    kb = ikb(
        [("⬆️ Hammaga yuklash", "anim:up:MF")],
        [("⬆️ Erkaklarga", "anim:up:M"), ("⬆️ Ayollarga", "anim:up:F")],
        [("👁 Erkaklar", "anim:pv:M"), ("👁 Ayollar", "anim:pv:F")],
        [("🗑 Erkaklar", "anim:rm:M"), ("🗑 Ayollar", "anim:rm:F")],
        [("⬅️ Orqaga", "set:menu")],
    )
    return text, kb


@router.callback_query(F.data == "anim:menu")
async def anim_menu(cb: CallbackQuery) -> None:
    text, kb = anim_view()
    await cb.message.edit_text(text, reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.startswith("anim:up:"))
async def anim_upload_start(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AnimUpload.file)
    await state.update_data(genders=cb.data.split(":")[2])
    await cb.message.answer(
        "🎆 Salyut GIF yoki videosini yuboring.\n\n"
        "<b>Eng oson yo‘li:</b> shu chatda <code>@gif salyut</code> yoki <code>@gif fireworks</code> deb yozing, "
        "chiqqan GIF lardan birini tanlang. Yoki o‘zingizdagi video/GIF ni yuboring.",
        reply_markup=cancel_menu,
    )
    await cb.answer()


@router.message(AnimUpload.file, F.animation | F.video)
async def anim_upload(message: Message, state: FSMContext) -> None:
    if message.animation:
        anim = {"type": "animation", "file_id": message.animation.file_id}
    else:
        anim = {"type": "video", "file_id": message.video.file_id}
    genders = (await state.get_data())["genders"]
    for g in genders:
        db.set_setting(f"anim_{g}", json.dumps(anim))
    await state.clear()
    await message.answer("✅ Salyut saqlandi. Endi tabriklar shu animatsiya bilan chiqadi.", reply_markup=main_menu)
    text, kb = anim_view()
    await message.answer(text, reply_markup=kb)


@router.message(AnimUpload.file, ~F.text.in_(MENU_BUTTONS))
async def anim_upload_wrong(message: Message) -> None:
    await message.answer("❗ GIF yoki video yuboring (rasm yoki stiker emas).")


@router.callback_query(F.data.startswith("anim:pv:"))
async def anim_preview(cb: CallbackQuery) -> None:
    from .templates import SAMPLE, sample_render

    g = cb.data.split(":")[2]
    if not scheduler.get_animation(g):
        return await cb.answer("Animatsiya yuklanmagan", show_alert=True)
    lang = db.get_setting("lang")
    text = sample_render(scheduler.pick_template_text(lang, g), lang, g)
    await scheduler.deliver(cb.bot, cb.message.chat.id, text, g)
    await cb.answer()


@router.callback_query(F.data.startswith("anim:rm:"))
async def anim_remove(cb: CallbackQuery) -> None:
    db.set_setting(f"anim_{cb.data.split(':')[2]}", "")
    await anim_menu(cb)
