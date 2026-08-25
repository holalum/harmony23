from __future__ import annotations

import math

from payments.base import PaymentProvider, PaymentResult, PaymentStatus


class StarsProvider(PaymentProvider):
    """
    Оплата через Telegram Stars.

    В отличие от ЮKassa/CryptoBot, платёж создаётся не через create_payment(),
    а нативным Telegram-инвойсом (answer_invoice в bot/handlers/payment.py) —
    Telegram сам присылает боту successful_payment, когда клиент оплатил.
    Поэтому create_payment()/check_payment() здесь не используются в основном
    сценарии, но реализованы для соответствия интерфейсу PaymentProvider.
    """

    name = "Telegram Stars"

    def __init__(self, rub_per_star: float):
        self._rub_per_star = rub_per_star
        self._paid_order_ids: set[int] = set()

    def rub_to_stars(self, amount_rub: float) -> int:
        return max(1, math.ceil(amount_rub / self._rub_per_star))

    def mark_paid(self, order_id: int) -> None:
        """Вызывается из on_successful_payment сразу после получения successful_payment от Telegram."""
        self._paid_order_ids.add(order_id)

    async def create_payment(self, amount: float, currency: str, description: str, order_id: int) -> PaymentResult:
        stars_amount = self.rub_to_stars(amount)
        return PaymentResult(external_id=str(order_id), status=PaymentStatus.pending, pay_url=None, raw={"stars": stars_amount})

    async def check_payment(self, external_id: str) -> PaymentStatus:
        order_id = int(external_id)
        return PaymentStatus.paid if order_id in self._paid_order_ids else PaymentStatus.pending
