#!/bin/bash

echo "🔄 Запуск обновления структуры таблицы markets..."

# Активируем виртуальное окружение
source venv/bin/activate

# Запускаем скрипт обновления
python update_markets_structure.py

# Проверяем результат
if [ $? -eq 0 ]; then
    echo "✅ Обновление структуры таблицы завершено успешно!"
else
    echo "❌ Ошибка при обновлении структуры таблицы"
    exit 1
fi 