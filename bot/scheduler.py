"""Har kuni belgilangan vaqtda guruhga tabrik yuboradi."""
import asyncio
import html
import json
import logging
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.types import Message

from . import config, db
from .greeting import age_on, make_greeting, pick_template as pick_template_text

log = logging.getLogger(__name__)
TZ = ZoneInfo(config.TIMEZONE)

_failures: dict[tuple[int, date], int] = defaultdict(int)
MAX_ATTEMPTS = 3


def now() -> datetime:
    return datetime.now(TZ)


def today() -> date:
    return now().date()


def send_time() -> time:
    hh, mm = db.get_setting("send_time").split(":")
    return time(int(hh), int(mm))


async def send_greeting(bot: Bot, emp, day: date) -> None:
    """Bitta xodimni guruhda tabriklaydi. Xato bo‘lsa exception chiqaradi."""
    group_id = db.get_setting("group_id")
    if not group_id:
        raise RuntimeError("Guruh ulanmagan")
    thread = db.get_setting("thread_id")
    msg = await deliver(bot, int(group_id), make_greeting(emp, day), emp["gender"], int(thread) if thread else None)
    db.mark_sent(emp["id"], day)
    if db.get_setting("pin") == "1":
        await pin(bot, int(group_id), msg.message_id, day)


def get_animation(gender: str) -> dict | None:
    raw = db.get_setting(f"anim_{gender}")
    return json.loads(raw) if raw else None


async def deliver(bot: Bot, chat_id: int, text: str, gender: str, thread: int | None = None) -> Message:
    """Tabrikni yuboradi: salyut animatsiyasi bo‘lsa, matn uning tagida (bitta xabar)."""
    anim = get_animation(gender)
    if not anim:
        return await bot.send_message(chat_id, text, message_thread_id=thread)
    send = bot.send_animation if anim["type"] == "animation" else bot.send_video
    if len(text) <= 1024:  # Telegram caption limiti
        return await send(chat_id, anim["file_id"], caption=text, message_thread_id=thread)
    await send(chat_id, anim["file_id"], message_thread_id=thread)
    return await bot.send_message(chat_id, text, message_thread_id=thread)


async def pin(bot: Bot, chat_id: int, message_id: int, day: date) -> None:
    """Tabrikni guruh tepasiga mahkamlaydi: kim kirsa ham birinchi bo‘lib ko‘radi."""
    try:
        # disable_notification=False — a’zolarga «xabar mahkamlandi» bildirishnomasi boradi
        await bot.pin_chat_message(chat_id, message_id, disable_notification=False)
    except Exception as e:
        log.warning("Pin qilib bo‘lmadi: %s", e)
        if db.get_setting("pin_error_day") != day.isoformat():
            db.set_setting("pin_error_day", day.isoformat())
            await notify_admins(
                bot,
                "⚠️ Tabrik yuborildi, lekin guruh tepasiga mahkamlanmadi (pin).\n"
                "Botni guruhda admin qiling va «Xabarlarni mahkamlash» huquqini bering.\n"
                f"<code>{html.escape(str(e))}</code>",
            )
        return
    pinned = json.loads(db.get_setting("pinned") or "[]")
    pinned.append([chat_id, message_id, day.isoformat()])
    db.set_setting("pinned", json.dumps(pinned))


async def unpin_old(bot: Bot, day: date) -> None:
    """Oldingi kunlarning tabriklarini pin dan olib tashlaydi."""
    pinned = json.loads(db.get_setting("pinned") or "[]")
    keep = []
    for chat_id, message_id, pin_day in pinned:
        if pin_day >= day.isoformat():
            keep.append([chat_id, message_id, pin_day])
            continue
        try:
            await bot.unpin_chat_message(chat_id, message_id=message_id)
        except Exception as e:
            log.warning("Unpin qilib bo‘lmadi (%s): %s", message_id, e)
    if len(keep) != len(pinned):
        db.set_setting("pinned", json.dumps(keep))


async def notify_admins(bot: Bot, text: str) -> None:
    for admin_id in db.all_admin_ids():
        try:
            await bot.send_message(admin_id, text)
        except Exception as e:  # admin botni bloklagan bo‘lishi mumkin
            log.warning("Admin %s ga yuborib bo‘lmadi: %s", admin_id, e)


async def tick(bot: Bot) -> None:
    current = now()
    day = current.date()
    await unpin_old(bot, day)
    if current.time() < send_time() or not db.get_setting("group_id"):
        return

    sent_now = []
    for emp in db.birthdays_on(day):
        key = (emp["id"], day)
        if db.was_sent(emp["id"], day) or _failures[key] >= MAX_ATTEMPTS:
            continue
        try:
            await send_greeting(bot, emp, day)
            sent_now.append(emp)
            await asyncio.sleep(1.5)  # Telegram limitlari uchun
        except Exception as e:
            _failures[key] += 1
            log.exception("Tabrik yuborilmadi: %s", emp["full_name"])
            if _failures[key] == MAX_ATTEMPTS:
                await notify_admins(
                    bot,
                    f"⚠️ <b>{html.escape(emp['full_name'])}</b> uchun tabrik guruhga yuborilmadi.\n"
                    f"Xato: <code>{html.escape(str(e))}</code>\n"
                    "Bot guruhda borligini va yozish huquqi borligini tekshiring.",
                )

    if db.get_setting("notify_admins") == "1" and db.get_setting("last_digest") != day.isoformat():
        db.set_setting("last_digest", day.isoformat())
        tomorrow = db.birthdays_on(day + timedelta(days=1))
        if sent_now or tomorrow:
            lines = []
            if sent_now:
                lines.append("✅ <b>Bugun tabriklandi:</b>")
                lines += [f"• {html.escape(e['full_name'])}" for e in sent_now]
            if tomorrow:
                lines.append("\n🔔 <b>Ertaga tug‘ilgan kun:</b>")
                lines += [
                    f"• {html.escape(e['full_name'])} ({age_on(e, day + timedelta(days=1))} yosh)"
                    for e in tomorrow
                ]
            await notify_admins(bot, "\n".join(lines))


async def run(bot: Bot) -> None:
    log.info("Scheduler ishga tushdi (%s)", config.TIMEZONE)
    while True:
        try:
            await tick(bot)
        except Exception:
            log.exception("Scheduler xatosi")
        await asyncio.sleep(30)
