# 🤖 Market Analysis Bot - Модульная Архитектура

## 📁 Структура проекта

```
mkrt_analytic/
├── main_modular.py          # Главный файл (только импорты и запуск)
├── core/                    # Ядро бота
│   ├── bot_startup.py      # Запуск бота
│   └── bot_shutdown.py     # Остановка бота
├── database/               # Работа с базой данных
│   ├── database_connection.py
│   ├── markets_reader.py
│   ├── analytic_writer.py
│   ├── analytic_updater.py
│   └── active_markets_reader.py
├── analysis/               # Анализ рынков
│   ├── market_analyzer_core.py
│   ├── browser_manager.py
│   ├── category_filter.py
│   ├── data_extractor.py
│   ├── yes_percentage_extractor.py
│   ├── volume_extractor.py
│   └── contract_extractor.py
├── planning/               # Планирование задач
│   ├── task_scheduler.py
│   ├── new_markets_checker.py
│   ├── active_markets_updater.py
│   ├── market_summaries_logger.py
│   └── recently_closed_checker.py
├── restoration/            # Восстановление
│   └── stuck_markets_restorer.py
├── active_markets/         # Активные рынки
│   └── market_lifecycle_manager.py
├── telegram/               # Telegram логирование
│   ├── telegram_connector.py
│   ├── new_market_logger.py
│   ├── error_logger.py
│   ├── market_data_logger.py
│   └── market_stopped_logger.py
└── config/                 # Конфигурация
    └── config_loader.py
```

## 🚀 Запуск

### Локально

```bash
python main_modular.py
```

### Docker

```bash
docker build -f Dockerfile_modular -t market-bot-modular .
docker run -e DB_HOST=localhost -e DB_PASSWORD=your_password market-bot-modular
```

### Docker Compose

```bash
docker-compose up -d
```

## 🔧 Переменные окружения

```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=polymarket
DB_USER=postgres
DB_PASSWORD=your_password

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Analysis
ANALYSIS_TIME_MINUTES=60
MAX_RETRIES=3
RETRY_DELAY_SECONDS=30
LOGGING_INTERVAL_MINUTES=10
```

## 🎯 Преимущества модульной архитектуры

1. **🔍 Изолированная диагностика** - проблема в конкретном файле
2. **🛠️ Легкое исправление** - правим только проблемный модуль
3. **📦 Модульность** - каждый файл отвечает за одну функцию
4. **🔄 Переиспользование** - модули можно использовать в других проектах
5. **📖 Читаемость** - код структурирован и понятен

## 🐛 Диагностика проблем

- **Проблема с БД** → `database/` папка
- **Проблема с анализом** → `analysis/` папка
- **Проблема с Telegram** → `telegram/` папка
- **Проблема с планированием** → `planning/` папка

## 📊 Логирование

Логи сохраняются в `bot.log` и отправляются в Telegram при ошибках.

## 🔄 Railway Deploy

Для деплоя на Railway используется `Dockerfile_modular` и `railway.json`.
