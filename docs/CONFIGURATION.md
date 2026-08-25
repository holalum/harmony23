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
| `ADMIN_CHAT_ID` | нет | Telegram chat_id админа/группы поддержки, куда будут приходить уведомления о новых тикетах поддержки и сообщениях в них. Узнать chat_id можно через [@userinfobot](https://t.me/userinfobot). |
| `ADMIN_IDS` | нет | Telegram user_id администраторов через запятую (например `111111,222222`) — только им доступны админ-команды: `/referral_mode`, `/referral_days`, `/referral_percent`, `/broadcast_add`, `/broadcast_list`, `/broadcast_toggle`, `/broadcast_del`, `/reply`, `/close_ticket`. Без этой переменной админ-команды не выполнит никто. |
| `DEFAULT_PROXIES` | нет | JSON с proxy-протоколами, которые выдаются новым пользователям в Marzban. По умолчанию `{"vless": {}}`. Раньше было захардкожено в `bot/config.py` — теперь настраивается здесь. |
| `DEFAULT_INBOUNDS` | нет | JSON с inbound'ами, которые выдаются новым пользователям в Marzban. По умолчанию `{"vless": ["VLESS TCP REALITY"]}`. Значения должны совпадать с именами inbound'ов, настроенными в самой Marzban-панели (Core Settings → Inbounds). |

## Настройки Фазы 2 (в БД, не в .env)

Режим реферальной программы и revenue-share % хранятся в таблице `settings`
(key/value) и меняются на лету админ-командами в боте — без деплоя:

| Команда | Описание |
|---|---|
| `/referral_mode <off\|days\|revenue_share>` | Глобальный режим рефералки. По умолчанию `off`. |
| `/referral_days <N>` | Сколько дней получают пригласивший и приглашённый при первой оплате (режим `days`). По умолчанию 7. |
| `/referral_percent <N>` | % от суммы каждого заказа приглашённого, зачисляемый пригласившему на баланс (режим `revenue_share`). По умолчанию 10. |

Управление правилами умных рассылок — тоже без деплоя, через команды:

| Команда | Описание |
|---|---|
| `/broadcast_add <before_expiry\|after_expiry> <N> <days\|hours> <all\|id1,id2> <текст>` | Создать правило: например `/broadcast_add before_expiry 3 days all Подписка истекает через 3 дня, продли: /buy`. |
| `/broadcast_list` | Список всех правил. |
| `/broadcast_toggle <id>` | Включить/выключить правило. |
| `/broadcast_del <id>` | Удалить правило. |

Фоновая задача проверяет правила раз в час и не отправляет повторно одному
пользователю одно и то же правило (таблица `broadcast_logs`).

**Важно:** значения `DEFAULT_PROXIES`/`DEFAULT_INBOUNDS` должны быть валидным
JSON в одну строку и точно соответствовать тому, что настроено в Marzban —
иначе `create_user()` в Marzban вернёт ошибку валидации.
