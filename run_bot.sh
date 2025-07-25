#!/bin/bash

# Скрипт для запуска Market Analysis Bot

echo "🚀 Запуск Market Analysis Bot..."

# Проверяем наличие Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден. Установите Python 3.8+"
    exit 1
fi

# Проверяем наличие файла .env
if [ ! -f .env ]; then
    echo "⚠️ Файл .env не найден. Скопируйте env_example.txt в .env и настройте переменные"
    exit 1
fi

# Проверяем зависимости
echo "📦 Проверка зависимостей..."
python3 -c "import psycopg2, requests, beautifulsoup4, telegram, schedule, selenium" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📦 Установка зависимостей..."
    pip3 install -r requirements.txt
fi

# Тестируем подключения
echo "🔍 Тестирование подключений..."
python3 test_connection.py

if [ $? -eq 0 ]; then
    echo "✅ Все тесты пройдены. Запуск бота..."
    python3 main.py
else
    echo "❌ Тесты не пройдены. Исправьте проблемы перед запуском."
    exit 1
fi 