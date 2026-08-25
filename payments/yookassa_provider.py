from __future__ import annotations

import uuid

from yookassa import Configuration, Payment

from payments.base import PaymentProvider, PaymentResult, PaymentStatus

_STATUS_MAP = {
    "pending": PaymentStatus.pending,
    "waiting_for_capture": PaymentStatus.pending,
    "succeeded": PaymentStatus.paid,
    "canceled": PaymentStatus.failed,
}


class YooKassaProvider(PaymentProvider):
    name = "ЮKassa"

    def __init__(self, shop_id: str, secret_key: str, return_url: str):
        Configuration.account_id = shop_id
        Configuration.secret_key = secret_key
        self._return_url = return_url

    async def create_payment(self, amount: float, currency: str, description: str, order_id: int) -> PaymentResult:
        payment = Payment.create(
            {
                "amount": {"value": f"{amount:.2f}", "currency": currency},
                "confirmation": {"type": "redirect", "return_url": self._return_url},
                "capture": True,
                "description": description,
                "metadata": {"order_id": order_id},
            },
            uuid.uuid4(),
        )
        return PaymentResult(
            external_id=payment.id,
            status=_STATUS_MAP.get(payment.status, PaymentStatus.pending),
            pay_url=payment.confirmation.confirmation_url,
            raw=payment.__dict__,
        )

    async def check_payment(self, external_id: str) -> PaymentStatus:
        payment = Payment.find_one(external_id)
        return _STATUS_MAP.get(payment.status, PaymentStatus.pending)
