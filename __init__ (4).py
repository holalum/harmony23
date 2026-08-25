from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import Message
from sqlalchemy import select

from db.models import User
from db.session import get_session

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    """
    /start — если пришли по реферальной ссылке, это будет /start <referrer_telegram_id>
    (aiogram передаёт всё после /start в command.args).
    """
    async with get_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()

        if user is None:
            referred_by = None
            if command.args and command.args.isdigit():
                ref_result = await session.execute(
                    select(User).where(User.telegram_id == int(command.args))
                )
                referrer = ref_result.scalar_one_or_none()
                if referrer and referrer.telegram_id != message.from_user.id:
                    referred_by = referrer

            user = User(
                telegram_id=message.from_user.id,
                telegram_username=message.from_user.username,
                referred_by=referred_by,
            )
            session.add(user)
            await session.commit()

    await message.answer(
        "👋 Добро пожаловать в <b>Harmony VPN</b>!\n\n"
        "Быстрый и стабильный доступ на базе VLESS Reality.\n"
        "Команды:\n"
        "/buy — выбрать тариф и оплатить\n"
        "/my — статус моей подписки\n"
        "/support — связаться с поддержкой",
    )
