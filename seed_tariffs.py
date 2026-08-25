"""
Создаёт стартовый набор тарифов.

Идемпотентен: тарифы ищутся по name, при повторном запуске существующие
обновляются (цена/срок/лимит), а не дублируются. Полезно и для первого
разворачивания, и для последующей правки тарифной сетки через .env/скрипт.

Запуск: python seed_tariffs.py
"""
from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv
from sqlalchemy import select

from db.models import Tariff
from db.session import create_all_tables, get_session, init_db

DEFAULT_TARIFFS = [
    {"name": "1 месяц", "price": 199, "duration_days": 30, "data_limit_gb": None, "sort_order": 1},
    {"name": "3 месяца", "price": 499, "duration_days": 90, "data_limit_gb": None, "sort_order": 2},
    {"name": "12 месяцев", "price": 1499, "duration_days": 365, "data_limit_gb": None, "sort_order": 3},
]


async def seed() -> None:
    load_dotenv()
    init_db(os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./harmony.db"))
    await create_all_tables()

    async with get_session() as session:
        for data in DEFAULT_TARIFFS:
            result = await session.execute(select(Tariff).where(Tariff.name == data["name"]))
            tariff = result.scalar_one_or_none()
            if tariff is None:
                session.add(Tariff(is_active=True, **data))
                print(f"+ создан тариф: {data['name']}")
            else:
                for field, value in data.items():
                    setattr(tariff, field, value)
                print(f"= обновлён тариф: {data['name']}")
        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())
