# Market Analysis Bot

Бот для анализа рынков Polymarket с использованием OCR (Optical Character Recognition) технологии.

## 🚀 Возможности

- **OCR анализ**: Извлечение данных с веб-страниц Polymarket с помощью Playwright + pytesseract
- **Автоматическое обновление**: Обновление данных каждые 3 минуты (настраивается)
- **Telegram логирование**: Отправка уведомлений в Telegram
- **PostgreSQL**: Работа с двумя базами данных (markets и mkrt_analytic)
- **Обработка ошибок**: Автоматические повторы при ошибках

## 📋 Требования

- Python 3.8+
- PostgreSQL
- Tesseract OCR
- Playwright браузеры

## 🛠 Установка

### 1. Клонирование репозитория

```bash
git clone https://github.com/spimethod/mkrt_analytic.git
cd mkrt_analytic
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Установка Playwright браузеров

```bash
playwright install
```

### 4. Установка Tesseract OCR

```bash
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# Windows
# Скачайте с https://github.com/UB-Mannheim/tesseract/wiki
```

## ⚙️ Конфигурация

Создайте файл `.env` на основе `env_example.txt`:

```bash
# База данных Polymarket
POLYMARKET_DB_HOST=localhost
POLYMARKET_DB_PORT=5432
POLYMARKET_DB_NAME=markets
POLYMARKET_DB_USER=postgres
POLYMARKET_DB_PASSWORD=your_password

# База данных аналитики
ANALYTIC_DB_HOST=localhost
ANALYTIC_DB_PORT=5432
ANALYTIC_DB_NAME=mkrt_analytic
ANALYTIC_DB_USER=postgres
ANALYTIC_DB_PASSWORD=your_password

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Настройки анализа
MKRT_ANALYTIC_TIME_MIN=60
MKRT_ANALYTIC_PING_MIN=3
```

## 🗄 Создание таблиц

Выполните SQL скрипт для создания таблиц:

```bash
psql -U postgres -d mkrt_analytic -f create_tables.sql
```

## 🚀 Запуск

### Простой запуск

```bash
python main.py
```

### Через скрипт

```bash
chmod +x run_bot.sh
./run_bot.sh
```

### Как systemd сервис

```bash
sudo cp market-analysis-bot.service /etc/systemd/system/
sudo systemctl enable market-analysis-bot
sudo systemctl start market-analysis-bot
```

## 📊 Извлекаемые данные

Бот извлекает следующие данные с рынков Polymarket:

- **Существование рынка**: Действителен ли адрес
- **Название рынка**: Заголовок вопроса
- **Тип рынка**: Булевый (Да/Нет) или вариативный
- **Цены**: Проценты для Yes/No вариантов
- **Контракт**: Полный адрес смарт-контракта
- **Объем**: Общий объем торгов
- **Статус**: новый/в работе/закрыт

## 🔧 Технологии

- **OCR**: Playwright + pytesseract + RegEx
- **База данных**: PostgreSQL
- **Уведомления**: Telegram Bot API
- **Планировщик**: schedule

## 📝 Логирование

Бот логирует:

- Получение новых рынков
- Данные о рынках каждые 10 минут
- Прекращение анализа
- Ошибки

## 🐛 Обработка ошибок

- **3 попытки** при ошибках анализа
- **Автоматическое закрытие** рынка при неудаче
- **Логирование ошибок** в Telegram

## 📈 Мониторинг

Бот автоматически:

- Проверяет новые рынки каждые 30 секунд
- Обновляет данные каждые 3 минуты
- Логирует сводки каждые 10 минут
- Останавливает анализ через заданное время

## 🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для новой функции
3. Внесите изменения
4. Создайте Pull Request

## 📄 Лицензия

MIT License
