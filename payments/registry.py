from __future__ import annotations

from payments.base import PaymentProvider


class PaymentRegistry:
    """Реестр активных способов оплаты: только те, для которых заданы креды в .env."""

    def __init__(self):
        self._providers: dict[str, PaymentProvider] = {}

    def register(self, key: str, provider: PaymentProvider) -> None:
        self._providers[key] = provider

    def get(self, key: str) -> PaymentProvider:
        try:
            return self._providers[key]
        except KeyError:
            raise KeyError(f"Способ оплаты '{key}' не подключён (проверь .env)") from None

    def all(self) -> dict[str, PaymentProvider]:
        return dict(self._providers)


def build_registry(settings) -> PaymentRegistry:
    """
    Собирает реестр способов оплаты по настройкам из .env: способ включается,
    только если для него заполнены все необходимые переменные.
    """
    registry = PaymentRegistry()

    if settings.yookassa_shop_id and settings.yookassa_secret_key:
        from payments.yookassa_provider import YooKassaProvider

        registry.register(
            "yookassa",
            YooKassaProvider(
                shop_id=settings.yookassa_shop_id,
                secret_key=settings.yookassa_secret_key,
                return_url=settings.bot_username_url,
            ),
        )

    if settings.cryptobot_api_token:
        from payments.cryptobot_provider import CryptoBotProvider

        registry.register("crypto", CryptoBotProvider(api_token=settings.cryptobot_api_token))

    from payments.stars_provider import StarsProvider

    registry.register("stars", StarsProvider(rub_per_star=settings.rub_per_star))

    return registry
