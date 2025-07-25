#!/bin/bash

# Скрипт для активации виртуального окружения

echo "🔧 Активация виртуального окружения..."

# Проверяем наличие виртуального окружения
if [ ! -d "venv" ]; then
    echo "❌ Виртуальное окружение не найдено. Создаю новое..."
    python3 -m venv venv
fi

# Активируем виртуальное окружение
source venv/bin/activate

echo "✅ Виртуальное окружение активировано!"
echo "💡 Теперь вы можете запускать бота:"
echo "   python main.py"
echo ""
echo "🔍 Для тестирования подключений:"
echo "   python test_connection.py"
echo ""
echo "📦 Для установки зависимостей:"
echo "   pip install -r requirements.txt" 