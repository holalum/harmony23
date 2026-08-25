"""
Асинхронный клиент для Marzban REST API.

Marzban — панель управления Xray-core (VLESS/VMess/Trojan/Reality),
на которую опирается Harmony для реальной выдачи VPN-доступа.
Harmony сам не трогает Xray напрямую — всё идёт через этот клиент.

Документация Marzban API: {panel_url}/docs (Swagger)
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Optional

import httpx


class MarzbanAPIError(Exception):
    """Общая ошибка при обращении к Marzban API."""

    def __init__(self, status_code: int, detail: Any):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Marzban API error {status_code}: {detail}")


class MarzbanAuthError(MarzbanAPIError):
    """Неверный логин/пароль администратора Marzban."""


@dataclass
class MarzbanUser:
    username: str
    status: str
    subscription_url: str
    expire: Optional[int]  # unix timestamp или None (бессрочно)
    data_limit: Optional[int]  # байты или None (безлимит)
    used_traffic: int
    raw: dict


class MarzbanClient:
    """
    Обёртка над Marzban REST API.

    Использование:
        client = MarzbanClient("https://panel.example.com", "admin", "password")
        await client.login()
        user = await client.create_user(
            username="tg_123456",
            proxies={"vless": {}},
            inbounds={"vless": ["VLESS TCP REALITY"]},
            expire_days=30,
        )
        print(user.subscription_url)
    """

    def __init__(self, base_url: str, username: str, password: str, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._timeout = timeout
        self._token: Optional[str] = None
        self._token_obtained_at: float = 0.0
        # Marzban не всегда возвращает expires_in — обновляем токен раз в час на всякий случай
        self._token_ttl_seconds = 3600
        self._http = httpx.AsyncClient(base_url=self.base_url, timeout=self._timeout)

    async def close(self):
        await self._http.aclose()

    # ------------------------------------------------------------------ #
    # Авторизация
    # ------------------------------------------------------------------ #

    async def login(self) -> str:
        """Получает admin access-token. Вызывается автоматически при первом запросе."""
        resp = await self._http.post(
            "/api/admin/token",
            data={
                "grant_type": "password",
                "username": self._username,
                "password": self._password,
                "scope": "",
                "client_id": "",
                "client_secret": "",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if resp.status_code == 401:
            raise MarzbanAuthError(resp.status_code, "Неверный логин или пароль администратора Marzban")
        if resp.status_code != 200:
            raise MarzbanAPIError(resp.status_code, resp.text)

        data = resp.json()
        self._token = data["access_token"]
        self._token_obtained_at = time.time()
        return self._token

    async def _ensure_token(self) -> str:
        token_is_stale = (time.time() - self._token_obtained_at) > self._token_ttl_seconds
        if self._token is None or token_is_stale:
            await self.login()
        return self._token  # type: ignore[return-value]

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        token = await self._ensure_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"

        resp = await self._http.request(method, path, headers=headers, **kwargs)

        # Токен протух раньше времени (например, панель перезапустили) — обновляем один раз и повторяем
        if resp.status_code == 401:
            await self.login()
            headers["Authorization"] = f"Bearer {self._token}"
            resp = await self._http.request(method, path, headers=headers, **kwargs)

        if resp.status_code >= 400:
            raise MarzbanAPIError(resp.status_code, resp.text)
        return resp

    # ------------------------------------------------------------------ #
    # Пользователи
    # ------------------------------------------------------------------ #

    async def create_user(
        self,
        username: str,
        proxies: dict[str, Any],
        inbounds: dict[str, list[str]],
        expire_days: Optional[int] = None,
        data_limit_gb: Optional[float] = None,
        note: Optional[str] = None,
    ) -> MarzbanUser:
        """
        Создаёт пользователя в Marzban (= выдаёт VPN-доступ).

        expire_days — через сколько дней истечёт доступ (None = бессрочно).
        data_limit_gb — лимит трафика в ГБ (None = безлимит).
        """
        payload: dict[str, Any] = {
            "username": username,
            "proxies": proxies,
            "inbounds": inbounds,
            "status": "active",
            "data_limit_reset_strategy": "no_reset",
        }
        if expire_days is not None:
            payload["expire"] = int(time.time()) + expire_days * 86400
        if data_limit_gb is not None:
            payload["data_limit"] = int(data_limit_gb * 1024**3)
        if note is not None:
            payload["note"] = note

        resp = await self._request("POST", "/api/user", json=payload)
        return self._parse_user(resp.json())

    async def get_user(self, username: str) -> MarzbanUser:
        resp = await self._request("GET", f"/api/user/{username}")
        return self._parse_user(resp.json())

    async def modify_user(self, username: str, **fields) -> MarzbanUser:
        """Частичное изменение пользователя (например продление: expire=...)."""
        resp = await self._request("PUT", f"/api/user/{username}", json=fields)
        return self._parse_user(resp.json())

    async def extend_user(self, username: str, extra_days: int) -> MarzbanUser:
        """Продлевает подписку на N дней от текущей даты истечения (или от сейчас, если уже истекла)."""
        user = await self.get_user(username)
        base = user.expire if user.expire and user.expire > time.time() else int(time.time())
        new_expire = base + extra_days * 86400
        return await self.modify_user(username, expire=new_expire)

    async def set_status(self, username: str, status: str) -> MarzbanUser:
        """status: 'active' | 'disabled' — используем для бана/разбана."""
        return await self.modify_user(username, status=status)

    async def delete_user(self, username: str) -> None:
        await self._request("DELETE", f"/api/user/{username}")

    async def reset_traffic(self, username: str) -> MarzbanUser:
        resp = await self._request("POST", f"/api/user/{username}/reset")
        return self._parse_user(resp.json())

    @staticmethod
    def _parse_user(data: dict) -> MarzbanUser:
        return MarzbanUser(
            username=data["username"],
            status=data["status"],
            subscription_url=data.get("subscription_url", ""),
            expire=data.get("expire"),
            data_limit=data.get("data_limit"),
            used_traffic=data.get("used_traffic", 0),
            raw=data,
        )

    # ------------------------------------------------------------------ #
    # Система / ноды (пригодится для дашборда "инфраструктура")
    # ------------------------------------------------------------------ #

    async def get_system_stats(self) -> dict:
        resp = await self._request("GET", "/api/system")
        return resp.json()

    async def list_nodes(self) -> list[dict]:
        resp = await self._request("GET", "/api/nodes")
        return resp.json()
