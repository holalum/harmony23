from __future__ import annotations

import httpx

from payments.base import PaymentProvider, PaymentResult, PaymentStatus

_STATUS_MAP = {
    "active": PaymentStatus.pending,
    "paid": PaymentStatus.paid,
    "expired": PaymentStatus.expired,
}


class CryptoBotProvider(PaymentProvider):
    """Провайдер оплаты криптой через @CryptoBot (Crypto Pay API)."""

    name = "CryptoBot"

    def __init__(self, api_token: str, base_url: str = "https://pay.crypt.bot"):
        self._http = httpx.AsyncClient(base_url=base_url, headers={"Crypto-Pay-API-Token": api_token}, timeout=15.0)

    async def create_payment(self, amount: float, currency: str, description: str, order_id: int) -> PaymentResult:
        resp = await self._http.post(
            "/api/createInvoice",
            json={
                "currency_type": "fiat",
                "fiat": currency,
                "amount": f"{amount:.2f}",
                "description": description,
                "payload": str(order_id),
            },
        )
        resp.raise_for_status()
        data = resp.json()["result"]
        return PaymentResult(
            external_id=str(data["invoice_id"]),
            status=_STATUS_MAP.get(data["status"], PaymentStatus.pending),
            pay_url=data["pay_url"],
            raw=data,
        )

    async def check_payment(self, external_id: str) -> PaymentStatus:
        resp = await self._http.get("/api/getInvoices", params={"invoice_ids": external_id})
        resp.raise_for_status()
        items = resp.json()["result"]["items"]
        if not items:
            return PaymentStatus.pending
        return _STATUS_MAP.get(items[0]["status"], PaymentStatus.pending)
