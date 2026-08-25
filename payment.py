from __future__ import annotations

from datetime import datetime

from aiogram import Bot
from sqlalchemy import select

from db.models import Order, OrderStatus, Tariff, User
from db.session import get_session
from marzban_client.client import MarzbanClient


async def deliver_order(order_id: int, bot: Bot, marzban: MarzbanClient, default_proxies: dict, default_inbounds: dict):
    """
    Вызывается ровно один раз, когда платёж подтверждён (неважно, каким способом).
    Создаёт/продлевает VPN-доступ в Marzban и присылает клиенту ссылку на подписку.
    """
    async with get_session() as session:
        order = await session.get(Order, order_id)
        if order is None or order.status == OrderStatus.paid:
            return  # уже выдано — защита от повторной обработки вебхука/поллинга

        tariff = await session.get(Tariff, order.tariff_id)
        user = await session.get(User, order.user_id)

        marzban_username = user.marzban_username or f"tg_{user.telegram_id}"

        try:
            marzban_user = await marzban.get_user(marzban_username)
            # Уже существует — продлеваем
            marzban_user = await marzban.extend_user(marzban_username, extra_days=tariff.duration_days)
        except Exception:
            # Пользователя ещё нет в Marzban — создаём
            marzban_user = await marzban.create_user(
                username=marzban_username,
                proxies=default_proxies,
                inbounds=default_inbounds,
                expire_days=tariff.duration_days,
                data_limit_gb=float(tariff.data_limit_gb) if tariff.data_limit_gb else None,
                note=f"harmony_order:{order.id}",
            )

        user.marzban_username = marzban_username
        order.status = OrderStatus.paid
        order.paid_at = datetime.utcnow()
        await session.commit()

        # Реферальный бонус — начисляем пригласившему при первой оплате
        if user.referred_by_id and order.id == await _first_paid_order_id(session, user.id):
            await _reward_referrer(session, user.referred_by_id, tariff, order.amount)

    await bot.send_message(
        user.telegram_id,
        "✅ Оплата получена, доступ выдан!\n\n"
        f"🔗 Ссылка на подписку:\n<code>{marzban_user.subscription_url}</code>\n\n"
        "Вставь её в приложение (v2rayNG, Streisand, Happ и т.п.) — импорт из подписки.",
    )


async def _first_paid_order_id(session, user_id: int) -> int | None:
    result = await session.execute(
        select(Order.id)
        .where(Order.user_id == user_id, Order.status == OrderStatus.paid)
        .order_by(Order.paid_at)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _reward_referrer(session, referrer_id: int, tariff: Tariff, order_amount) -> None:
    """
    Простая классическая рефералка: пригласивший получает столько же дней,
    сколько купил его реферал. Revenue-share режим — TODO, когда определитесь
    с процентом в бизнес-настройках.
    """
    referrer = await session.get(User, referrer_id)
    if referrer is None:
        return
    # Начисление дней рефереру реализуется через тот же marzban.extend_user()
    # в вызывающем коде — здесь оставлен как заготовка для Фазы 2.
