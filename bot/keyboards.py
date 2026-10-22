from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

BTN_UPCOMING = "🎂 Yaqin tug‘ilgan kunlar"
BTN_SEARCH = "🔍 Qidirish"
BTN_LIST = "👥 Xodimlar"
BTN_ADD = "➕ Xodim qo‘shish"
BTN_TEMPLATES = "📝 Shablonlar"
BTN_SETTINGS = "⚙️ Sozlamalar"
BTN_EXCEL = "📁 Excel import / export"
BTN_CANCEL = "❌ Bekor qilish"

MENU_BUTTONS = {
    BTN_UPCOMING, BTN_SEARCH, BTN_LIST, BTN_ADD, BTN_TEMPLATES, BTN_SETTINGS, BTN_EXCEL, BTN_CANCEL,
}

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BTN_UPCOMING), KeyboardButton(text=BTN_SEARCH)],
        [KeyboardButton(text=BTN_LIST), KeyboardButton(text=BTN_ADD)],
        [KeyboardButton(text=BTN_TEMPLATES), KeyboardButton(text=BTN_SETTINGS)],
        [KeyboardButton(text=BTN_EXCEL)],
    ],
    resize_keyboard=True,
    input_field_placeholder="Xodim ismini yozing — qidiraman",
)

cancel_menu = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=BTN_CANCEL)]], resize_keyboard=True
)


def ikb(*rows: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    """ikb([("Matn", "callback"), ...], [...])"""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t, callback_data=d) for t, d in row] for row in rows if row]
    )
