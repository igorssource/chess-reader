# Chess Reader — распознаватель бланков шахматных партий

Фото рукописного бланка → ходы с проверкой по правилам → PGN. Для клуба STRATEG Stuttgart.

## Как устроено

| Часть | Где | Что делает |
|---|---|---|
| `docs/` | GitHub Pages | Страница: фото/загрузка, пояснение о данных, ходы с цветовой разметкой, правка шапки, скачивание PGN. Интерфейс DE/RU. |
| `api/index.py`, `server/` | Vercel | API: `/api/process`, `/api/pgn`, `/api/health`, `/api/stats`. Дневной бюджет в евро, журнал партий, сохранение фото. |
| `core/chessreader/model/` | сервер | Всё общение с моделью (по умолчанию Anthropic). Ключ только на сервере. Провайдер меняется настройкой. |
| `core/chessreader/notation.py` | сервер | Языки нотации (немецкий; английский и русский заготовлены). |
| `core/chessreader/decoder.py` | сервер | python-chess: проверка ходов и автоисправления (похожие символы, пропущенный ход, перепутанные колонки, пустые клетки, скачок нумерации). |
| `core/chessreader/pipeline.py` | сервер | Чтение → проверка → уточняющие запросы к модели (с потолком) → PGN. |
| `core/chessreader/sheet.py` | сервер | Партия = список листов (на будущее: второй лист, бланк соперника). |

## Настройки (переменные окружения в Vercel)

| Переменная | По умолчанию | Смысл |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Ключ API (обязателен). |
| `MODEL_NAME` | `claude-sonnet-5-5` | Модель. |
| `MODEL_EFFORT` | `medium` | Глубина размышления модели (`low`…`max`). |
| `MAX_CALLS_PER_GAME` | `10` | Потолок обращений к модели на партию. |
| `DAILY_BUDGET_EUR` | `2.0` | Дневной лимит расходов в евро (временно поднят с 1.0 на время проверки точности, 13.11.2026). |
| `USD_TO_EUR` | `0.95` | Курс для пересчёта цен. |
| `STORE_PHOTOS` | `true` | Сохранять фото (нужен Vercel Blob). |
| `NOTATION_LANGUAGE` | `de` | Язык нотации. |
| `PGN_COMMENTS_LANGUAGE` | `de` | Язык комментариев в PGN. |
| `ADMIN_TOKEN` | — | Пароль для `/api/stats?token=…` (среднее число обращений на партию и т. п.). |
| `ALLOWED_ORIGINS` | `*` | Адрес страницы, с которого разрешены запросы. |

Счётчик бюджета и журнал: Upstash Redis из Vercel Marketplace (`KV_REST_API_URL`, `KV_REST_API_TOKEN`). Фото: Vercel Blob (`BLOB_READ_WRITE_TOKEN`).

## Разработка

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt pytest uvicorn
.venv/bin/python -m pytest -q tests                  # автотесты
.venv/bin/python eval/synthetic_benchmark.py 20      # точность на искусственных бланках
MODEL_PROVIDER=fake .venv/bin/python -m uvicorn api.index:app --port 8787   # сервер без модели
```

## Образцы

Код написан заново. Идеи взяты у [Zugwise](https://github.com/GerhardTrippen/Zugwise) (AGPL-3.0, код не копировался): ответ модели в виде «ход + уверенность + альтернатива», разметка ходов зелёный/жёлтый/красный, быстрые исправления по сходству написания и поиск ошибки на несколько ходов назад. getpgn недоступен; chess-scoresheet-ocr и Chess Scribe без лицензии (только идеи); ни один проект не поддерживает немецкую нотацию.
