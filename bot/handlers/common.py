import html

from aiogram import F, Router
from aiogram.filters import BaseFilter, Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, TelegramObject

from .. import config, db
from ..keyboards import BTN_CANCEL, main_menu


class IsAdmin(BaseFilter):
    async def __call__(self, event: TelegramObject) -> bool:
        user = getattr(event, "from_user", None)
        return bool(user and db.is_admin(user.id))


class IsSuperAdmin(BaseFilter):
    async def __call__(self, event: TelegramObject) -> bool:
        user = getattr(event, "from_user", None)
        return bool(user and user.id in config.SUPER_ADMINS)


# ---------- guruhdagi buyruqlar ----------
group_router = Router(name="group")
group_router.message.filter(F.chat.type.in_({"group", "supergroup"}))


@group_router.message(Command("setgroup"), IsAdmin())
async def set_group(message: Message) -> None:
    db.set_setting("group_id", str(message.chat.id))
    db.set_setting("group_title", message.chat.title or "")
    db.set_setting("thread_id", str(message.message_thread_id) if message.is_topic_message else "")
    await message.reply("✅ Shu guruh tabriklar uchun ulandi. Tug‘ilgan kun tabriklari shu yerga yoziladi.")


@group_router.message(F.migrate_to_chat_id)
async def group_migrated(message: Message) -> None:
    # Oddiy guruh superguruhga aylansa ID o‘zgaradi
    if db.get_setting("group_id") == str(message.chat.id):
        db.set_setting("group_id", str(message.migrate_to_chat_id))


# ---------- admin: umumiy ----------
router = Router(name="common")
router.message.filter(F.chat.type == "private", IsAdmin())
router.callback_query.filter(IsAdmin())

HELP = (
    "🤖 <b>ZarinaAssistent</b> — xodimlarni tug‘ilgan kuni bilan guruhda tabriklaydi.\n\n"
    "<b>Boshlash:</b>\n"
    "1. Botni ishxona guruhiga qo‘shing (yozish huquqi bilan).\n"
    "2. Guruhda <code>/setgroup</code> deb yozing.\n"
    "3. ⚙️ Sozlamalardan tabrik tili va vaqtini tanlang.\n"
    "4. 📝 Shablonlarda tabrik matnlarini tahrirlang.\n\n"
    "🔍 Qidirish uchun shunchaki xodim ismini yozing — lotin yoki kirillda, masalan "
    "<i>Azamat</i> yoki <i>Азамат</i>."
)


@router.message(CommandStart())
@router.message(Command("help"))
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(HELP, reply_markup=main_menu)


@router.message(Command("cancel"))
@router.message(F.text == BTN_CANCEL)
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=main_menu)


@router.callback_query(F.data == "noop")
async def noop(cb: CallbackQuery) -> None:
    await cb.answer()


# ---------- admin bo‘lmaganlar ----------
fallback_router = Router(name="fallback")


@fallback_router.message(F.chat.type == "private")
async def not_admin(message: Message) -> None:
    await message.answer(
        "Kechirasiz, bu bot faqat adminlar uchun.\n"
        f"Sizning Telegram ID: <code>{message.from_user.id}</code>\n"
        "Admin bo‘lish uchun shu raqamni bosh adminga yuboring."
    )


@fallback_router.callback_query()
async def not_admin_cb(cb: CallbackQuery) -> None:
    await cb.answer("Ruxsat yo‘q", show_alert=True)


def esc(s: str) -> str:
    return html.escape(s or "")
