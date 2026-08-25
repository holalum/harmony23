from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy import select

from bot.services.admin import is_admin
from db.models import BroadcastEvent, BroadcastRule, BroadcastUnit
from db.session import get_session

router = Router(name="broadcast_admin")


@router.message(Command("broadcast_add"))
async def cmd_broadcast_add(message: Message, command: CommandObject, admin_ids: set[int]):
    """
    /broadcast_add <before_expiry|after_expiry> <value> <days|hours> <all|id1,id2,...> <текст сообщения>
    """
    if not is_admin(message.from_user.id, admin_ids):
        return

    parts = (command.args or "").split(maxsplit=4)
    if len(parts) < 5:
        await message.answer(
            "Использование:\n"
            "/broadcast_add <before_expiry|after_expiry> <N> <days|hours> <all|id1,id2> <текст>"
        )
        return

    event_raw, value_raw, unit_raw, tariffs_raw, text = parts
    if event_raw not in {e.value for e in BroadcastEvent}:
        await message.answer(f"event_type должен быть одним из: {', '.join(e.value for e in BroadcastEvent)}")
        return
    if unit_raw not in {u.value for u in BroadcastUnit}:
        await message.answer(f"unit должен быть одним из: {', '.join(u.value for u in BroadcastUnit)}")
        return
    if not value_raw.isdigit():
        await message.answer("N (value) должно быть целым числом")
        return

    target_tariff_ids = None if tariffs_raw == "all" else tariffs_raw

    async with get_session() as session:
        rule = BroadcastRule(
            event_type=BroadcastEvent(event_raw),
            value=int(value_raw),
            unit=BroadcastUnit(unit_raw),
            message_template=text,
            target_tariff_ids=target_tariff_ids,
            is_active=True,
        )
        session.add(rule)
        await session.commit()
        await session.refresh(rule)

    await message.answer(f"✅ Правило #{rule.id} создано и активно")


@router.message(Command("broadcast_list"))
async def cmd_broadcast_list(message: Message, admin_ids: set[int]):
    if not is_admin(message.from_user.id, admin_ids):
        return

    async with get_session() as session:
        result = await session.execute(select(BroadcastRule).order_by(BroadcastRule.id))
        rules = list(result.scalars())

    if not rules:
        await message.answer("Правил рассылки пока нет. Создать: /broadcast_add ...")
        return

    lines = []
    for r in rules:
        status = "🟢" if r.is_active else "⚪️"
        target = r.target_tariff_ids or "все тарифы"
        lines.append(
            f"{status} #{r.id}: {r.event_type.value} {r.value} {r.unit.value}, тарифы: {target}\n"
            f"   «{r.message_template}»"
        )
    await message.answer("\n\n".join(lines))


@router.message(Command("broadcast_toggle"))
async def cmd_broadcast_toggle(message: Message, command: CommandObject, admin_ids: set[int]):
    if not is_admin(message.from_user.id, admin_ids):
        return

    arg = (command.args or "").strip()
    if not arg.isdigit():
        await message.answer("Использование: /broadcast_toggle <id>")
        return

    async with get_session() as session:
        rule = await session.get(BroadcastRule, int(arg))
        if rule is None:
            await message.answer("Правило не найдено")
            return
        rule.is_active = not rule.is_active
        await session.commit()
        state = "включено" if rule.is_active else "выключено"

    await message.answer(f"Правило #{arg} теперь {state}")


@router.message(Command("broadcast_del"))
async def cmd_broadcast_del(message: Message, command: CommandObject, admin_ids: set[int]):
    if not is_admin(message.from_user.id, admin_ids):
        return

    arg = (command.args or "").strip()
    if not arg.isdigit():
        await message.answer("Использование: /broadcast_del <id>")
        return

    async with get_session() as session:
        rule = await session.get(BroadcastRule, int(arg))
        if rule is None:
            await message.answer("Правило не найдено")
            return
        await session.delete(rule)
        await session.commit()

    await message.answer(f"Правило #{arg} удалено")
