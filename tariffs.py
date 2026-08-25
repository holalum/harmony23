from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Settings:
    bot_token: str
    bot_username_url: str  # https://t.me/your_bot — для return_url ЮKassa

    marzban_url: str
    marzban_admin_username: str
    marzban_admin_password: str

    database_url: str

    yookassa_shop_id: str | None
    yookassa_secret_key: str | None
    cryptobot_api_token: str | None
    rub_per_star: float

    # какие inbounds/протоколы выдавать новым пользователям
    default_proxies: dict
    default_inbounds: dict


def load_settings() -> Settings:
    return Settings(
        bot_token=_require("BOT_TOKEN"),
        bot_username_url=os.environ.get("BOT_USERNAME_URL", "https://t.me/harmony_vpn_bot"),
        marzban_url=_require("MARZBAN_URL"),
        marzban_admin_username=_require("MARZBAN_ADMIN_USERNAME"),
        marzban_admin_password=_require("MARZBAN_ADMIN_PASSWORD"),
        database_url=os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./harmony.db"),
        yookassa_shop_id=os.environ.get("YOOKASSA_SHOP_ID"),
        yookassa_secret_key=os.environ.get("YOOKASSA_SECRET_KEY"),
        cryptobot_api_token=os.environ.get("CRYPTOBOT_API_TOKEN"),
        rub_per_star=float(os.environ.get("RUB_PER_STAR", "2.0")),
        default_proxies={"vless": {}},
        default_inbounds={"vless": ["VLESS TCP REALITY"]},
    )


def _require(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(f"Не задана переменная окружения {key} (см. .env.example)")
    return value
