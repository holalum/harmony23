from __future__ import annotations

from aiogram import Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    PreCheckoutQuery,
    Message,
)

from bot.keyboards.inline import PayMethodCallback
from bot.services.delivery import deliver_order
from db.models import Order, OrderStatus, PaymentMethod, Tariff, User
from db.session import get_session
from marzban_client.client import MarzbanClient
from payments.base import PaymentStatus
from payments.registry import PaymentRegistry
from payments.stars_provider import StarsProvider

router = Router(name="payment")

_METHOD_ENUM = {
    "yookassa": PaymentMethod.yookassa,
    "crypto": PaymentMethod.crypto,
    "stars": PaymentMethod.telegram_stars,
    "balance": PaymentMethod.balance,
}


@router.callback_query(PayMethodCallback.filter())
async def on_payment_method_selected(
    callback: CallbackQuery,
    callback_data: PayMethodCallback,
    payment_registry: PaymentRegistry,
    marzban: MarzbanClient,
    default_proxies: dict,
    default_inbounds: dict,
):
    async with get_session() as session:
        order = await session.get(Order, callback_data.order_id)
        if order is None or order.status != OrderStatus.pending:
            await callback.answer("Заказ уже неактуален, начни заново: /buy", show_alert=True)
            return

        tariff = await session.get(Tariff, order.tariff_id)
        order.payment_method = _METHOD_ENUM[callback_data.method]
        await session.commit()

    # --- Оплата с внутреннего баланса (реферальные начисления revenue_share) ---
    if callback_data.method == "balance":
        async with get_session() as session:
            order = await session.get(Order, callback_data.order_id)
            user = await session.get(User, order.user_id)
            if float(user.balance or 0) < float(order.amount):
                await callback.answer("Недостаточно средств на балансе", show_alert=True)
                return
            user.balance = float(user.balance) - float(order.amount)
            order.external_payment_id = "balance"
            await session.commit()

        await deliver_order(order.id, callback.bot, marzban, default_proxies, default_inbounds)
        await callback.answer("Готово! Проверь личные сообщения 🎉")
        return

    provider = payment_registry.get(callback_data.method)

    # --- Telegram Stars: отдельная логика, платёж через нативный инвойс бота ---
    if callback_data.method == "stars":
        stars_provider: StarsProvider = provider  # type: ignore[assignment]
        stars_amount = stars_provider.rub_to_stars(float(order.amount))
        await callback.message.answer_invoice(
            title=tariff.name,
            description=f"Harmony VPN — {tariff.name}",
            payload=str(order.id),
            currency="XTR",
            prices=[LabeledPrice(label=tariff.name, amount=stars_amount)],
        )
        await callback.answer()
        return

    # --- ЮKassa / CryptoBot: создаём платёж и даём ссылку ---
    result = await provider.create_payment(
        amount=float(order.amount),
        currency="RUB",
        description=f"Harmony VPN — {tariff.name}",
        order_id=order.id,
    )

    async with get_session() as session:
        order = await session.get(Order, order.id)
        order.external_payment_id = result.external_id
        await session.commit()

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Перейти к оплате", url=result.pay_url)],
            [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"check_payment:{order.id}")],
        ]
    )
    await callback.message.edit_text(
        f"Тариф: <b>{tariff.name}</b>\nСумма: <b>{order.amount:.0f}₽</b>\n\n"
        "Оплати по ссылке ниже, после оплаты доступ придёт автоматически "
        "(обычно занимает до минуты).",
        reply_markup=kb,
    )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("check_payment:"))
async def on_check_payment(
    callback: CallbackQuery,
    payment_registry: PaymentRegistry,
    marzban: MarzbanClient,
    default_proxies: dict,
    default_inbounds: dict,
):
    order_id = int(callback.data.split(":")[1])
    async with get_session() as session:
        order = await session.get(Order, order_id)

    if order is None:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    if order.status == OrderStatus.paid:
        await callback.answer("Уже выдано ✅", show_alert=True)
        return

    provider_key = {
        PaymentMethod.yookassa: "yookassa",
        PaymentMethod.crypto: "crypto",
    }.get(order.payment_method)
    provider = payment_registry.get(provider_key)

    status = await provider.check_payment(order.external_payment_id)
    if status != PaymentStatus.paid:
        await callback.answer("Оплата пока не найдена, попробуй через минуту", show_alert=True)
        return

    await deliver_order(order_id, callback.bot, marzban, default_proxies, default_inbounds)
    await callback.answer("Готово! Проверь личные сообщения 🎉")


# --- Telegram Stars: обязательные хендлеры платёжного цикла ---


@router.pre_checkout_query()
async def on_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    # Тут можно перепроверить, что заказ ещё актуален (не отменён, тариф не удалён)
    await pre_checkout_query.answer(ok=True)


@router.message(lambda m: m.successful_payment is not None)
async def on_successful_payment(
    message: Message,
    payment_registry: PaymentRegistry,
    marzban: MarzbanClient,
    default_proxies: dict,
    default_inbounds: dict,
):
    order_id = int(message.successful_payment.invoice_payload)
    stars_provider: StarsProvider = payment_registry.get("stars")  # type: ignore[assignment]
    stars_provider.mark_paid(order_id)

    await deliver_order(order_id, message.bot, marzban, default_proxies, default_inbounds)
