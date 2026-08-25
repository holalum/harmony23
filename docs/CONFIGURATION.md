# Конфигурация (.env)

Скопируй `.env.example` в `.env` и заполни. Ниже — описание каждой переменной.

## Telegram-бот

| Переменная | Обязательна | Описание |
|---|---|---|
| `BOT_TOKEN` | да | Токен бота от [@BotFather](https://t.me/BotFather). |
| `BOT_USERNAME_URL` | нет | `https://t.me/<username>` бота. Используется как `return_url` для ЮKassa и для формирования реферальных ссылок. |

## Marzban

Harmony не управляет Xray сама — все VPN-аккаунты создаются/продлеваются через
REST API Marzban.

| Переменная | Обязательна | Описание |
|---|---|---|
| `MARZBAN_URL` | да | Базовый URL твоей Marzban-панели, например `https://panel.example.com`. |
| `MARZBAN_ADMIN_USERNAME` | да | Логин администратора Marzban (для получения access-токена). |
| `MARZBAN_ADMIN_PASSWORD` | да | Пароль администратора Marzban. |

## База данных

| Переменная | Обязательна | Описание |
|---|---|---|
| `DATABASE_URL` | нет (по умолчанию SQLite) | Строка подключения SQLAlchemy async. Для разработки: `sqlite+aiosqlite:///./harmony.db`. Для docker-compose это значение переопределяется автоматически на Postgres — см. `docker-compose.yml`. |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | только для docker-compose | Креды сервиса `db` (Postgres) в Docker Compose. |

## Способы оплаты

Каждый способ оплаты появляется в боте, только если для него заполнены все
нужные переменные — просто оставь их пустыми, чтобы отключить способ.

| Переменная | Способ | Описание |
|---|---|---|
| `YOOKASSA_SHOP_ID` | ЮKassa | ID магазина в ЮKassa. |
| `YOOKASSA_SECRET_KEY` | ЮKassa | Секретный ключ ЮKassa. |
| `CRYPTOBOT_API_TOKEN` | CryptoBot | Токен API из [@CryptoBot](https://t.me/CryptoBot) → Crypto Pay → My Apps. |
| `RUB_PER_STAR` | Telegram Stars | Курс "рублей за 1 звезду" — используется для расчёта, сколько Stars нужно списать за тариф с ценой в рублях. |

Telegram Stars не требует отдельных ключей — способ всегда включён, если
задан `RUB_PER_STAR`.

## Прочее

| Переменная | Обязательна | Описание |
|---|---|---|
| `ADMIN_CHAT_ID` | нет | Telegram chat_id админа/группы поддержки, куда будут приходить уведомления (тикеты, алерты и т.п. в Фазе 2+). Узнать chat_id можно через [@userinfobot](https://t.me/userinfobot). |
| `DEFAULT_PROXIES` | нет | JSON с proxy-протоколами, которые выдаются новым пользователям в Marzban. По умолчанию `{"vless": {}}`. Раньше было захардкожено в `bot/config.py` — теперь настраивается здесь. |
| `DEFAULT_INBOUNDS` | нет | JSON с inbound'ами, которые выдаются новым пользователям в Marzban. По умолчанию `{"vless": ["VLESS TCP REALITY"]}`. Значения должны совпадать с именами inbound'ов, настроенными в самой Marzban-панели (Core Settings → Inbounds). |

**Важно:** значения `DEFAULT_PROXIES`/`DEFAULT_INBOUNDS` должны быть валидным
JSON в одну строку и точно соответствовать тому, что настроено в Marzban —
иначе `create_user()` в Marzban вернёт ошибку валидации.
