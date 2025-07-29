#!/bin/bash

echo "🔄 Возвращаемся к старой архитектуре..."

# Останавливаем модульный бот если запущен
if pgrep -f "python main.py" > /dev/null; then
    echo "🛑 Останавливаем модульный бот..."
    pkill -f "python main.py"
    sleep 2
fi

# Восстанавливаем старые файлы
if [ -f "main_old.py" ]; then
    echo "📦 Восстанавливаем старую версию..."
    mv main.py main_modular.py
    mv main_old.py main.py
fi

if [ -f "market_analyzer_old.py" ]; then
    mv market_analyzer_old.py market_analyzer.py
fi

if [ -f "ocr_screenshot_analyzer_old.py" ]; then
    mv ocr_screenshot_analyzer_old.py ocr_screenshot_analyzer.py
fi

echo "✅ Возврат к старой версии завершен!"
echo "📝 Для запуска используйте: python main.py"
echo "🔄 Для переключения на модульную версию: ./switch_to_modular.sh" 