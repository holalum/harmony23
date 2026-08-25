from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from bot.keyboards.inline import TariffCallback, payment_methods_keyboard, tariffs_keyboard
from db.models import Order, OrderStatus, PaymentMethod, Tariff, User
from db.session import get_session
from payments.registry import PaymentRegistry

router = Router(name="tariffs")


@router.message(Command("buy"))
async def cmd_buy(message: Message):
    async with get_session() as session:
        result = await session.execute(
            select(Tariff).where(Tariff.is_active.is_(True)).order_by(Tariff.sort_order)
        )
        tariffs = list(result.scalars())

    if not tariffs:
        await message.answer("Пока нет доступных тарифов — загляни позже 🙌")
        return

    await message.answer("Выбери тариф:", reply_markup=tariffs_keyboard(tariffs))


@router.callback_query(TariffCallback.filter())
async def on_tariff_selected(
    callback: CallbackQuery,
    callback_data: TariffCallback,
    payment_registry: PaymentRegistry,
):
    async with get_session() as session:
        tariff = await session.get(Tariff, callback_data.tariff_id)
        if tariff is None or not tariff.is_active:
            await callback.answer("Этот тариф больше недоступен", show_alert=True)
            return

        user_result = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
        user = user_result.scalar_one_or_none()
        if user is None:
            await callback.answer("Сначала нажми /start", show_alert=True)
            return

        order = Order(
            user_id=user.id,
            tariff_id=tariff.id,
            amount=tariff.price,
            # payment_method проставится, когда клиент выберет способ оплаты ниже
            payment_method=PaymentMethod.yookassa,
            status=OrderStatus.pending,
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)

    available_methods = list(payment_registry.all().keys())
    if user.balance and float(user.balance) >= float(tariff.price):
        available_methods.append("balance")

    await callback.message.edit_text(
        f"Тариф: <b>{tariff.name}</b>\nСумма: <b>{tariff.price:.0f}₽</b>\n\nВыбери способ оплаты:",
        reply_markup=payment_methods_keyboard(order.id, available_methods),
    )
    await callback.answer()
