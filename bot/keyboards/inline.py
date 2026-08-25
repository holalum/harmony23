from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from db.models import Tariff


class TariffCallback(CallbackData, prefix="tariff"):
    tariff_id: int


class PayMethodCallback(CallbackData, prefix="pay"):
    order_id: int
    method: str  # "yookassa" | "crypto" | "stars"


def tariffs_keyboard(tariffs: list[Tariff]) -> InlineKeyboardMarkup:
    rows = []
    for t in tariffs:
        label = f"{t.name} — {t.price:.0f}₽"
        rows.append([InlineKeyboardButton(text=label, callback_data=TariffCallback(tariff_id=t.id).pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def payment_methods_keyboard(order_id: int, available: list[str]) -> InlineKeyboardMarkup:
    labels = {
        "yookassa": "💳 Банковская карта",
        "crypto": "🪙 Криптовалюта",
        "stars": "⭐ Telegram Stars",
    }
    rows = [
        [InlineKeyboardButton(text=labels[m], callback_data=PayMethodCallback(order_id=order_id, method=m).pack())]
        for m in available
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
