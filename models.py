"""
Общий интерфейс для платёжных провайдеров.

Идея: бот работает с любым провайдером через один и тот же метод
create_payment() / check_payment(), не зная деталей ЮKassa/крипты/Stars.
Чтобы добавить новый способ оплаты — наследуемся от PaymentProvider
и регистрируем в payments/registry.py.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class PaymentStatus(str, Enum):
    pending = "pending"
    paid = "paid"
    failed = "failed"
    expired = "expired"


@dataclass
class PaymentResult:
    external_id: str          # id платежа в системе провайдера
    status: PaymentStatus
    pay_url: str | None = None      # ссылка на оплату (для ЮKassa/крипты)
    raw: dict | None = None


class PaymentProvider(ABC):
    """Базовый класс для всех способов оплаты."""

    name: str  # человекочитаемое имя, для отображения в боте

    @abstractmethod
    async def create_payment(self, amount: float, currency: str, description: str, order_id: int) -> PaymentResult:
        """Создаёт платёж и возвращает ссылку/реквизиты для оплаты клиентом."""
        raise NotImplementedError

    @abstractmethod
    async def check_payment(self, external_id: str) -> PaymentStatus:
        """Проверяет текущий статус платежа (используется и в поллинге, и в вебхуках)."""
        raise NotImplementedError
