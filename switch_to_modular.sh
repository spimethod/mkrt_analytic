#!/bin/bash

echo "🔄 Переключаемся на модульную архитектуру..."

# Останавливаем старый бот если запущен
if pgrep -f "python main.py" > /dev/null; then
    echo "🛑 Останавливаем старый бот..."
    pkill -f "python main.py"
    sleep 2
fi

# Переименовываем старые файлы
if [ -f "main.py" ]; then
    echo "📦 Архивируем старую версию..."
    mv main.py main_old.py
fi

if [ -f "market_analyzer.py" ]; then
    mv market_analyzer.py market_analyzer_old.py
fi

if [ -f "ocr_screenshot_analyzer.py" ]; then
    mv ocr_screenshot_analyzer.py ocr_screenshot_analyzer_old.py
fi

# Переименовываем модульную версию
echo "🚀 Активируем модульную версию..."
mv main_modular.py main.py

echo "✅ Переключение завершено!"
echo "📝 Для запуска используйте: python main.py"
echo "🔄 Для возврата к старой версии: ./switch_to_old.sh" 