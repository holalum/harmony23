from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import load_settings
from bot.handlers import broadcast_admin, payment, referral, start, support, tariffs
from bot.services.broadcasts import broadcast_loop
from db.session import create_all_tables, init_db
from marzban_client.client import MarzbanClient
from payments.registry import build_registry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("harmony")


async def main():
    settings = load_settings()

    init_db(settings.database_url)
    await create_all_tables()

    marzban = MarzbanClient(
        base_url=settings.marzban_url,
        username=settings.marzban_admin_username,
        password=settings.marzban_admin_password,
    )
    await marzban.login()
    logger.info("Подключение к Marzban успешно (%s)", settings.marzban_url)

    payment_registry = build_registry(settings)
    logger.info("Активные способы оплаты: %s", list(payment_registry.all().keys()))

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(start.router)
    dp.include_router(tariffs.router)
    dp.include_router(payment.router)
    dp.include_router(referral.router)
    dp.include_router(broadcast_admin.router)
    # support.router — последним: содержит catch-all на обычные текстовые сообщения
    dp.include_router(support.router)

    broadcast_task = asyncio.create_task(broadcast_loop(bot, marzban))

    try:
        await dp.start_polling(
            bot,
            marzban=marzban,
            payment_registry=payment_registry,
            default_proxies=settings.default_proxies,
            default_inbounds=settings.default_inbounds,
            admin_ids=settings.admin_ids,
            admin_chat_id=settings.admin_chat_id,
            bot_username_url=settings.bot_username_url,
        )
    finally:
        broadcast_task.cancel()
        await marzban.close()


if __name__ == "__main__":
    asyncio.run(main())
