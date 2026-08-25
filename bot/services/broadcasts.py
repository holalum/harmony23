from __future__ import annotations

import asyncio
import logging
import time

from aiogram import Bot
from sqlalchemy import select

from db.models import BroadcastLog, BroadcastRule, BroadcastEvent, BroadcastUnit, Order, OrderStatus, User
from db.session import get_session
from marzban_client.client import MarzbanClient

logger = logging.getLogger("harmony.broadcasts")

_UNIT_SECONDS = {BroadcastUnit.days: 86400, BroadcastUnit.hours: 3600}


async def broadcast_loop(bot: Bot, marzban: MarzbanClient, interval_seconds: int = 3600) -> None:
    """Фоновая задача: раз в interval_seconds проверяет триггерные правила рассылок."""
    while True:
        try:
            await check_broadcast_rules_once(bot, marzban)
        except Exception:
            logger.exception("Ошибка при проверке правил рассылки")
        await asyncio.sleep(interval_seconds)


async def check_broadcast_rules_once(bot: Bot, marzban: MarzbanClient) -> None:
    async with get_session() as session:
        result = await session.execute(select(BroadcastRule).where(BroadcastRule.is_active.is_(True)))
        rules = list(result.scalars())
        if not rules:
            return

        marzban_users = await marzban.list_users(status=None)
        now = time.time()

        for marzban_user in marzban_users:
            if marzban_user.expire is None:
                continue  # безлимитная подписка — не участвует в рассылках по сроку истечения

            user_result = await session.execute(select(User).where(User.marzban_username == marzban_user.username))
            user = user_result.scalar_one_or_none()
            if user is None:
                continue

            delta_seconds = marzban_user.expire - now

            for rule in rules:
                if not _rule_matches(rule, delta_seconds):
                    continue
                if rule.target_tariff_ids:
                    tariff_id = await _current_tariff_id(session, user.id)
                    allowed = {int(x) for x in rule.target_tariff_ids.split(",") if x.strip()}
                    if tariff_id not in allowed:
                        continue

                already_sent = await session.execute(
                    select(BroadcastLog).where(BroadcastLog.rule_id == rule.id, BroadcastLog.user_id == user.id)
                )
                if already_sent.scalar_one_or_none() is not None:
                    continue

                try:
                    await bot.send_message(user.telegram_id, rule.message_template)
                except Exception:
                    logger.exception("Не удалось отправить рассылку user_id=%s rule_id=%s", user.id, rule.id)
                    continue

                session.add(BroadcastLog(rule_id=rule.id, user_id=user.id))
                await session.commit()


def _rule_matches(rule: BroadcastRule, delta_seconds: float) -> bool:
    threshold = rule.value * _UNIT_SECONDS[rule.unit]
    if rule.event_type == BroadcastEvent.before_expiry:
        return 0 <= delta_seconds <= threshold
    return -threshold <= delta_seconds < 0  # after_expiry


async def _current_tariff_id(session, user_id: int) -> int | None:
    result = await session.execute(
        select(Order.tariff_id)
        .where(Order.user_id == user_id, Order.status == OrderStatus.paid)
        .order_by(Order.paid_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
