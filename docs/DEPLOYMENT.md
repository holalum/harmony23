# Деплой: чек-лист от чистого VPS до первого /buy

## 0. Требования

- VPS с Docker и Docker Compose (v2) — Ubuntu 22.04/24.04 подойдёт.
- Домен (для Marzban и, желательно, для самого VPS — TLS у Marzban обязателен
  для панели/подписок).
- Telegram-бот, созданный через [@BotFather](https://t.me/BotFather) (нужен `BOT_TOKEN`).

## 1. Разверни Marzban

Harmony НЕ поднимает Marzban сама — это отдельный сервис. Поставь его по
официальной инструкции: https://github.com/Gozargah/Marzban

Коротко:
1. Установи Marzban (официальный скрипт `marzban-cli` или Docker Compose из их репозитория).
2. Настрой хотя бы один inbound (например VLESS Reality) через `Core Settings`.
3. Создай администратора Marzban (`marzban-cli admin create --sudo`) —
   логин/пароль пойдут в `MARZBAN_ADMIN_USERNAME`/`MARZBAN_ADMIN_PASSWORD`.
4. Убедись, что `https://<marzban-домен>/docs` (Swagger) открывается — значит
   API живой.

Запиши: `MARZBAN_URL`, логин и пароль администратора, имена inbound'ов/протоколов.

## 2. Склонируй Harmony на VPS

```bash
git clone <url-репозитория> harmony
cd harmony
```

## 3. Настрой .env

```bash
cp .env.example .env
nano .env
```

Заполни как минимум: `BOT_TOKEN`, `BOT_USERNAME_URL`, `MARZBAN_URL`,
`MARZBAN_ADMIN_USERNAME`, `MARZBAN_ADMIN_PASSWORD`, `DEFAULT_PROXIES`,
`DEFAULT_INBOUNDS` (должны совпадать с тем, что настроено в Marzban).

Заполни способы оплаты, которые собираешься использовать — см.
[docs/CONFIGURATION.md](CONFIGURATION.md). Способ без заполненных переменных
просто не появится в боте, ошибки не будет.

`DATABASE_URL` в `.env` можно оставить sqlite-значением по умолчанию — при
запуске через `docker-compose.yml` бот всё равно подключается к сервису `db`
(Postgres), это переопределяется автоматически.

## 4. Подними Docker Compose

```bash
docker compose up -d --build
```

Это поднимет два сервиса:
- `bot` — сам Telegram-бот (Dockerfile, `python:3.12-slim`)
- `db` — Postgres для заказов/тарифов/рефералки Harmony

Marzban в этот compose не входит — он уже развёрнут отдельно (шаг 1) и
доступен боту по `MARZBAN_URL`.

Проверь логи:

```bash
docker compose logs -f bot
```

Ожидай строку `Подключение к Marzban успешно (...)` — значит бот достучался
до Marzban API. Если видишь `MarzbanAuthError` — перепроверь логин/пароль
администратора в `.env`.

## 5. Создай стартовые тарифы

```bash
docker compose exec bot python seed_tariffs.py
```

Скрипт идемпотентен — его можно запускать повторно (например после правки
`DEFAULT_TARIFFS` в `seed_tariffs.py`), дубли тарифов не появятся.

## 6. Проверь первый /buy

1. Напиши боту `/start` в Telegram.
2. `/buy` — должен показать список тарифов из шага 5.
3. Выбери тариф → способ оплаты → пройди оплату (тестовыми данными провайдера,
   если ЮKassa/CryptoBot в тестовом режиме, или реальными Stars).
4. После оплаты бот должен прислать `🔗 Ссылка на подписку` — значит связка
   Harmony ↔ Marzban ↔ платёжный провайдер работает целиком.
5. Проверь в Marzban-панели, что появился пользователь `tg_<telegram_id>`.

## 7. Дальше

- Настрой автозапуск после ребута сервера — `restart: unless-stopped` в
  `docker-compose.yml` уже это делает, если сам Docker настроен на автозапуск
  (`systemctl enable docker`).
- Бэкапь volume `harmony_db_data` (Postgres) регулярно — это все заказы,
  тарифы и (в Фазе 2+) баланс рефералки.
- Дальнейшие фазы (реферальная программа, рассылки, тикеты, антифрод) — см.
  корневой [README.md](../README.md).
