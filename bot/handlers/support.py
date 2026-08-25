from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy import select

from bot.services.admin import is_admin
from db.models import SupportTicket, TicketMessage, TicketStatus, User
from db.session import get_session

router = Router(name="support")


@router.message(Command("support"))
async def cmd_support(message: Message, command: CommandObject, admin_chat_id: int | None):
    text = (command.args or "").strip()
    if not text:
        await message.answer("Опиши проблему прямо в команде, например:\n/support не открывается ссылка на подписку")
        return

    async with get_session() as session:
        user_result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = user_result.scalar_one_or_none()
        if user is None:
            await message.answer("Сначала нажми /start")
            return

        open_ticket_result = await session.execute(
            select(SupportTicket).where(SupportTicket.user_id == user.id, SupportTicket.status == TicketStatus.open)
        )
        ticket = open_ticket_result.scalar_one_or_none()

        if ticket is None:
            ticket = SupportTicket(user_id=user.id, status=TicketStatus.open)
            session.add(ticket)
            await session.commit()
            await session.refresh(ticket)

        session.add(TicketMessage(ticket_id=ticket.id, text=text, is_from_operator=False))
        await session.commit()

    await message.answer(f"✅ Тикет #{ticket.id} создан, мы скоро ответим. Дальнейшие сообщения сюда тоже попадут в тикет.")

    if admin_chat_id:
        username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
        await message.bot.send_message(
            admin_chat_id,
            f"🆕 Тикет #{ticket.id} от {username} (id {message.from_user.id}):\n{text}\n\n"
            f"Ответить: /reply {ticket.id} <текст>",
        )


@router.message(Command("reply"))
async def cmd_reply(message: Message, command: CommandObject, admin_ids: set[int]):
    if not is_admin(message.from_user.id, admin_ids):
        return

    parts = (command.args or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[0].isdigit():
        await message.answer("Использование: /reply <ticket_id> <текст>")
        return

    ticket_id, text = int(parts[0]), parts[1]

    async with get_session() as session:
        ticket = await session.get(SupportTicket, ticket_id)
        if ticket is None:
            await message.answer("Тикет не найден")
            return

        user = await session.get(User, ticket.user_id)
        session.add(TicketMessage(ticket_id=ticket.id, text=text, is_from_operator=True))
        await session.commit()

    await message.bot.send_message(user.telegram_id, f"💬 Ответ поддержки (тикет #{ticket_id}):\n{text}")
    await message.answer("✅ Отправлено клиенту")


@router.message(Command("close_ticket"))
async def cmd_close_ticket(message: Message, command: CommandObject, admin_ids: set[int]):
    if not is_admin(message.from_user.id, admin_ids):
        return

    arg = (command.args or "").strip()
    if not arg.isdigit():
        await message.answer("Использование: /close_ticket <id>")
        return

    async with get_session() as session:
        from datetime import datetime

        ticket = await session.get(SupportTicket, int(arg))
        if ticket is None:
            await message.answer("Тикет не найден")
            return
        ticket.status = TicketStatus.closed
        ticket.closed_at = datetime.utcnow()
        user = await session.get(User, ticket.user_id)
        await session.commit()

    await message.bot.send_message(user.telegram_id, f"✅ Тикет #{arg} закрыт. Если проблема не решена — напиши /support ещё раз.")
    await message.answer(f"Тикет #{arg} закрыт")


@router.message(F.text, ~F.text.startswith("/"))
async def on_client_message(message: Message, admin_chat_id: int | None):
    """
    Ловит обычные (не команды) сообщения от клиента в личке бота и, если у него
    есть открытый тикет, добавляет их в переписку — чтобы не заставлять писать
    каждую реплику через /support.
    """
    async with get_session() as session:
        user_result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = user_result.scalar_one_or_none()
        if user is None:
            return

        ticket_result = await session.execute(
            select(SupportTicket).where(SupportTicket.user_id == user.id, SupportTicket.status == TicketStatus.open)
        )
        ticket = ticket_result.scalar_one_or_none()
        if ticket is None:
            return

        session.add(TicketMessage(ticket_id=ticket.id, text=message.text, is_from_operator=False))
        await session.commit()

    if admin_chat_id:
        username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
        await message.bot.send_message(
            admin_chat_id,
            f"💬 Тикет #{ticket.id} от {username}:\n{message.text}\n\nОтветить: /reply {ticket.id} <текст>",
        )
