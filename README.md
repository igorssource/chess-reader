# Chess Reader — распознаватель бланков шахматных партий

Фото рукописного бланка → ходы с проверкой по правилам → партия на доске и PGN. Для клуба [STRATEG Stuttgart](https://www.strateg-stuttgart.com/).

- Страница: https://igorssource.github.io/chess-reader/ (DE/RU)
- Сервер: Vercel (`chess-reader-seven.vercel.app`), ключ модели только там.
- Рабочая копия на крайний случай: ветка `stable`.

## Как работает

1. На странице делают фото бланка (можно второе: бланк соперника или вторая страница).
2. Сервер читает бланк моделью Anthropic: сначала дешёвая Haiku, при сомнениях — Sonnet (каскад).
   Сомнительные ходы перечитываются по увеличенному кусочку фото.
3. python-chess проверяет каждый ход по правилам и сам исправляет типичные ошибки
   (похожие буквы, пропущенный ход, пустая клетка, сбитая нумерация).
4. Страница показывает партию на доске, сомнительные ходы помечены; ход можно поправить
   в маленьком окошке — остаток партии пересчитывается без модели. Дальше PGN или Lichess.
5. Партии хранятся только в браузере («Мои партии»). Фото хранятся на сервере 90 дней,
   потом удаляются автоматически.

Чтение занимает 1–4 минуты. Экран телефона на это время не гаснет; если связь прервалась,
сервер держит готовый результат сутки, и страница забирает его сама (в том числе после
повторного открытия).

## Части

| Часть | Где | Что делает |
|---|---|---|
| `docs/` | GitHub Pages | Главная страница с доской (`index.html`, `app.js`, `style.css`, `pieces.css`), статистика для админа (`stats.html`), старый вид без доски (`old/`). При каждом изменении css/js поднимать `?v=` в `index.html`. |
| `api/index.py`, `server/` | Vercel | API (см. ниже), дневной бюджет и лимит на адрес (`limits.py`), журнал и статистика, фото (`photos.py`), хранение готовых результатов (`results.py`), эталонные партии (`references.py`). |
| `core/chessreader/model/` | сервер | Всё общение с моделью; `fake` — модель-заглушка для тестов. |
| `core/chessreader/pipeline.py` | сервер | Чтение → проверка → перечитывание сомнительного → каскад моделей → PGN. |
| `core/chessreader/decoder.py`, `notation.py`, `similarity.py` | сервер | Проверка и автоисправление ходов; немецкая и английская нотация. |
| `core/chessreader/combine.py` | сервер | Сверка двух бланков (свой + соперника) или продолжение на второй странице. |
| `core/chessreader/review.py` | сервер | Ручное исправление хода и пересчёт остатка партии без модели. |
| `core/chessreader/openings.py` | сервер | Название дебюта (таблица Lichess, CC0). |

### API

| Путь | Что делает |
|---|---|
| `POST /api/process` | Фото (1–2) → ходы, PGN. Поле `job` — номер чтения, по которому ответ можно забрать позже. |
| `GET /api/result/<job>` | Тот же ответ ещё раз (сутки). |
| `POST /api/redecode`, `POST /api/pgn` | Исправленный ход / правка шапки → новая партия и PGN, без модели. |
| `GET /api/cleanup` | Удаляет фото старше 90 дней. Вызывается раз в сутки расписанием Vercel (`vercel.json`). |
| `GET /api/health`, `GET /api/stats` | Состояние; статистика (нужен `ADMIN_TOKEN`). |

## Настройки (переменные окружения в Vercel)

| Переменная | По умолчанию | Смысл |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Ключ API (обязателен). |
| `CASCADE_MODELS` | `claude-haiku-5-5,claude-sonnet-5-5` | Каскад моделей. Одна модель — без каскада. |
| `MODEL_NAME` | `claude-sonnet-5-5` | Модель, если каскад выключен. |
| `MODEL_EFFORT` | `medium` | Глубина размышления модели. |
| `MAX_CALLS_PER_GAME` | `10` | Потолок обращений к модели на партию. |
| `DAILY_BUDGET_EUR` | `1.0` | Дневной лимит расходов в евро (разовые дни — `DAY_LIMITS` в `server/limits.py`). |
| `GAMES_PER_IP_PER_DAY` | `5` | Партий в день с одного интернет-адреса. |
| `RECHECK_CROP` | `1` | Перечитывать сомнительные ходы по увеличенному кусочку (`0` — выкл.). |
| `STORE_PHOTOS` | `true` | Сохранять фото (Vercel Blob, приватное хранилище). |
| `CRON_SECRET` | — | Если задан, удаление старых фото запускает только расписание Vercel. |
| `ADMIN_TOKEN` | — | Пароль админа: статистика, тест-режим (`…/chess-reader/#admin=<токен>`). |
| `ALLOWED_ORIGINS` | `*` | Адрес страницы, с которого разрешены запросы. |

Ещё: `CASCADE_MAX_PROBLEM_SHARE`, `CASCADE_MAX_DOUBTFUL`, `CASCADE_MIN_PLIES`, `CASCADE_CHEAP_MAX_CALLS`, `TIME_LIMIT_SECONDS`, `NOTATION_LANGUAGE`, `PGN_COMMENTS_LANGUAGE`, `USD_TO_EUR` — см. `core/chessreader/config.py`.

Счётчики, журнал и готовые результаты: Upstash Redis из Vercel Marketplace (`KV_REST_API_URL`, `KV_REST_API_TOKEN`). Фото: Vercel Blob.

## Разработка

Автотесты запускаются на GitHub при каждом pull request и каждом изменении main (`.github/workflows/tests.yml`).

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt pytest httpx uvicorn
.venv/bin/python -m pytest -q tests                  # автотесты
.venv/bin/python eval/synthetic_benchmark.py 20      # точность на искусственных бланках
MODEL_PROVIDER=fake .venv/bin/python -m uvicorn api.index:app --port 8787   # сервер без модели
```

## Образцы

Код написан заново. Идеи взяты у [Zugwise](https://github.com/GerhardTrippen/Zugwise) (AGPL-3.0, код не копировался): ответ модели в виде «ход + уверенность + альтернатива», разметка ходов зелёный/жёлтый/красный, быстрые исправления по сходству написания и поиск ошибки на несколько ходов назад.
