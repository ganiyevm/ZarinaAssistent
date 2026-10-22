import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import ExceptionTypeFilter
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats, ErrorEvent

from . import config, db, excel, scheduler
from .handlers import common, employees, excel_io, settings, templates

log = logging.getLogger("bot")


def seed() -> None:
    """Baza bo‘sh bo‘lsa SEED_FILE dagi Excel dan xodimlarni yuklaydi."""
    if db.count_employees() or not config.SEED_FILE or not os.path.exists(config.SEED_FILE):
        return
    with open(config.SEED_FILE, "rb") as f:
        parsed = excel.parse(f.read(), config.SEED_FILE)
    excel.apply(excel.plan(parsed.rows, sync=False))
    log.info("Seed: %d xodim yuklandi, %d xato", len(parsed.rows), len(parsed.errors))


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not config.BOT_TOKEN:
        raise SystemExit("BOT_TOKEN .env faylda ko‘rsatilmagan")
    if not config.SUPER_ADMINS:
        log.warning("SUPER_ADMINS bo‘sh — hech kim botni boshqara olmaydi")
    db.init()
    seed()

    bot = Bot(config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_routers(
        common.group_router,
        common.router,
        settings.router,
        templates.router,
        excel_io.router,
        employees.router,  # oxirida: erkin matnni qidiruv deb qabul qiladi
        common.fallback_router,
    )
    @dp.errors(ExceptionTypeFilter(TelegramBadRequest))
    async def ignore_not_modified(event: ErrorEvent) -> bool:
        # Bir tugmani ikki marta bosganda Telegram «message is not modified» qaytaradi
        if "message is not modified" in str(event.exception):
            if event.update.callback_query:
                await event.update.callback_query.answer()
            return True
        raise event.exception

    await bot.set_my_commands(
        [BotCommand(command="start", description="Asosiy menyu"),
         BotCommand(command="cancel", description="Bekor qilish")],
        scope=BotCommandScopeAllPrivateChats(),
    )
    asyncio.create_task(scheduler.run(bot))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
