from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy import func, select

from bot.services.admin import is_admin
from db.models import ReferralMode, User
from db.session import get_session
from db.settings import get_setting, set_setting

router = Router(name="referral")


@router.message(Command("referral"))
async def cmd_referral(message: Message, bot_username_url: str):
    async with get_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        if user is None:
            await message.answer("Сначала нажми /start")
            return

        invited_result = await session.execute(select(func.count(User.id)).where(User.referred_by_id == user.id))
        invited_count = invited_result.scalar_one()

        mode = await get_setting(session, "referral_mode", default=ReferralMode.off.value)

    link = f"{bot_username_url}?start={user.telegram_id}"

    lines = [
        "👥 <b>Реферальная программа</b>",
        "",
        f"Твоя ссылка: {link}",
        f"Приглашено: {invited_count}",
        f"Баланс: {float(user.balance or 0):.2f}₽",
    ]
    if mode == ReferralMode.off.value:
        lines.append("\nРеферальные начисления сейчас выключены — но ссылка уже работает, начисления включатся позже.")
    await message.answer("\n".join(lines))


# --- Админ-команды настройки рефералки (без правки кода, см. Фазу 2 в README) ---


@router.message(Command("referral_mode"))
async def cmd_referral_mode(message: Message, command: CommandObject, admin_ids: set[int]):
    if not is_admin(message.from_user.id, admin_ids):
        return

    arg = (command.args or "").strip()
    if arg not in {m.value for m in ReferralMode}:
        await message.answer(f"Использование: /referral_mode <{'|'.join(m.value for m in ReferralMode)}>")
        return

    async with get_session() as session:
        await set_setting(session, "referral_mode", arg)

    await message.answer(f"✅ Режим рефералки: {arg}")


@router.message(Command("referral_days"))
async def cmd_referral_days(message: Message, command: CommandObject, admin_ids: set[int]):
    if not is_admin(message.from_user.id, admin_ids):
        return

    arg = (command.args or "").strip()
    if not arg.isdigit():
        await message.answer("Использование: /referral_days <N> — сколько дней получают приглашённый и пригласивший")
        return

    async with get_session() as session:
        await set_setting(session, "referral_bonus_days", arg)

    await message.answer(f"✅ Бонус за реферала (режим days): {arg} дней")


@router.message(Command("referral_percent"))
async def cmd_referral_percent(message: Message, command: CommandObject, admin_ids: set[int]):
    if not is_admin(message.from_user.id, admin_ids):
        return

    arg = (command.args or "").strip()
    try:
        percent = float(arg)
    except ValueError:
        await message.answer("Использование: /referral_percent <N> — % от суммы заказа (режим revenue_share)")
        return

    async with get_session() as session:
        await set_setting(session, "referral_revenue_share_percent", str(percent))

    await message.answer(f"✅ Revenue share: {percent}% от суммы заказа приглашённого")
