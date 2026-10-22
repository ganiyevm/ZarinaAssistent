import html
from datetime import date

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from .. import db, excel, scheduler
from ..keyboards import BTN_EXCEL, cancel_menu, ikb, main_menu
from .common import IsAdmin

router = Router(name="excel")
router.message.filter(F.chat.type == "private", IsAdmin())
router.callback_query.filter(IsAdmin())


class Import(StatesGroup):
    file = State()
    confirm = State()


@router.message(F.text == BTN_EXCEL)
async def excel_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "📁 <b>Excel</b>\n\n"
        "📥 <b>Qo‘shish</b> — fayldagi yangi xodimlar qo‘shiladi, mavjudlari o‘zgarmaydi.\n"
        "🔄 <b>To‘liq yangilash</b> — baza fayl bilan tenglashtiriladi: faylda yo‘q xodimlar "
        "(ishdan ketganlar) o‘chiriladi. Kadrlar bo‘limidan yangi ro‘yxat kelganda qulay.\n"
        "📤 <b>Export</b> — joriy ro‘yxatni Excel qilib yuklab olish.",
        reply_markup=ikb(
            [("📥 Qo‘shish", "xl:imp:add"), ("🔄 To‘liq yangilash", "xl:imp:sync")],
            [("📤 Export", "xl:exp")],
        ),
    )


@router.callback_query(F.data == "xl:exp")
async def export(cb: CallbackQuery) -> None:
    data = excel.export()
    name = f"xodimlar_{scheduler.today():%d.%m.%Y}.xlsx"
    await cb.message.answer_document(BufferedInputFile(data, name), caption=f"Jami: {db.count_employees()} ta")
    await cb.answer()


@router.callback_query(F.data.startswith("xl:imp:"))
async def import_start(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Import.file)
    await state.update_data(sync=cb.data.endswith("sync"))
    await cb.message.answer(
        "Excel faylni yuboring (.xls yoki .xlsx).\n"
        "Ustunlar: <b>F.I.Sh</b> (Сотрудник), <b>Tug‘ilgan sana</b> (Дата рождения), <b>Jins</b> (Пол).",
        reply_markup=cancel_menu,
    )
    await cb.answer()


@router.message(Import.file, F.document)
async def import_file(message: Message, state: FSMContext) -> None:
    doc = message.document
    if not (doc.file_name or "").lower().endswith((".xls", ".xlsx")):
        return await message.answer("❗ Faqat .xls yoki .xlsx fayl.")
    buf = await message.bot.download(doc)
    try:
        parsed = excel.parse(buf.read(), doc.file_name)
    except Exception as e:
        return await message.answer(f"❗ Faylni o‘qib bo‘lmadi: <code>{html.escape(str(e))}</code>")
    if not parsed.rows:
        return await message.answer("❗ Faylda xodim topilmadi.\n" + "\n".join(parsed.errors[:10]))

    sync = (await state.get_data())["sync"]
    p = excel.plan(parsed.rows, sync)
    await state.update_data(rows=[(r.full_name, r.birth_date.isoformat(), r.gender) for r in parsed.rows])
    await state.set_state(Import.confirm)

    lines = [
        f"📄 Faylda: <b>{len(parsed.rows)}</b> ta xodim",
        f"➕ Qo‘shiladi: <b>{len(p['add'])}</b>",
        f"✏️ Jinsi yangilanadi: <b>{len(p['update'])}</b>",
    ]
    if sync:
        lines.append(f"🗑 O‘chiriladi (faylda yo‘q): <b>{len(p['delete'])}</b>")
        lines += [f"   • {html.escape(e['full_name'])}" for e in p["delete"][:15]]
        if len(p["delete"]) > 15:
            lines.append(f"   … va yana {len(p['delete']) - 15} ta")
    if parsed.errors:
        lines.append(f"\n⚠️ O‘qilmagan qatorlar: {len(parsed.errors)}")
        lines += [f"   • {html.escape(e)}" for e in parsed.errors[:10]]
    await message.answer(
        "\n".join(lines)[:4000],
        reply_markup=ikb([("✅ Tasdiqlash", "xl:ok"), ("❌ Bekor qilish", "xl:no")]),
    )


@router.callback_query(Import.confirm, F.data == "xl:ok")
async def import_confirm(cb: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()
    rows = [excel.ParsedRow(n, date.fromisoformat(d), g) for n, d, g in data["rows"]]
    p = excel.plan(rows, data["sync"])  # tasdiqlash orasida baza o‘zgargan bo‘lishi mumkin
    excel.apply(p)
    await cb.message.edit_text(
        f"✅ Import tugadi.\n➕ {len(p['add'])} · ✏️ {len(p['update'])} · 🗑 {len(p['delete'])}\n"
        f"Jami xodimlar: {db.count_employees()}"
    )
    await cb.message.answer("Asosiy menyu", reply_markup=main_menu)
    await cb.answer()


@router.callback_query(F.data == "xl:no")
async def import_cancel(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await cb.message.edit_text("Import bekor qilindi.")
    await cb.message.answer("Asosiy menyu", reply_markup=main_menu)
    await cb.answer()
