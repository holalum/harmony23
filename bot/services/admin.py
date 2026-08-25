from __future__ import annotations


def is_admin(telegram_id: int, admin_ids: set[int]) -> bool:
    return telegram_id in admin_ids
