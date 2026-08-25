from __future__ import annotations

import json
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

    admin_chat_id: int | None
    admin_ids: set[int]

    # какие inbounds/протоколы выдавать новым пользователям
    default_proxies: dict
    default_inbounds: dict


def load_settings() -> Settings:
    admin_chat_id_raw = os.environ.get("ADMIN_CHAT_ID")
    admin_ids_raw = os.environ.get("ADMIN_IDS", "")
    admin_ids = {int(v) for v in admin_ids_raw.split(",") if v.strip()}
    return Settings(
        bot_token=_require("BOT_TOKEN"),
        bot_username_url=os.environ.get("BOT_USERNAME_URL", "https://t.me/harmony_vpn_bot"),
        marzban_url=_require("MARZBAN_URL"),
        marzban_admin_username=_require("MARZBAN_ADMIN_USERNAME"),
        marzban_admin_password=_require("MARZBAN_ADMIN_PASSWORD"),
        database_url=os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./harmony.db"),
        yookassa_shop_id=os.environ.get("YOOKASSA_SHOP_ID") or None,
        yookassa_secret_key=os.environ.get("YOOKASSA_SECRET_KEY") or None,
        cryptobot_api_token=os.environ.get("CRYPTOBOT_API_TOKEN") or None,
        rub_per_star=float(os.environ.get("RUB_PER_STAR", "2.0")),
        admin_chat_id=int(admin_chat_id_raw) if admin_chat_id_raw else None,
        admin_ids=admin_ids,
        default_proxies=_load_json_env("DEFAULT_PROXIES", {"vless": {}}),
        default_inbounds=_load_json_env("DEFAULT_INBOUNDS", {"vless": ["VLESS TCP REALITY"]}),
    )


def _require(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(f"Не задана переменная окружения {key} (см. .env.example)")
    return value


def _load_json_env(key: str, default: dict) -> dict:
    """
    DEFAULT_PROXIES/DEFAULT_INBOUNDS раньше были захардкожены в коде — теперь
    настраиваются через .env (см. docs/CONFIGURATION.md), чтобы менять набор
    протоколов/inbound'ов без правки кода бота.
    """
    raw = os.environ.get(key)
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Переменная {key} должна быть валидным JSON: {exc}") from exc
