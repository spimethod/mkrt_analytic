#!/usr/bin/env python3
"""
Скрипт для добавления рынка в аналитическую базу по слаг
Использование: python add_market_by_slug.py <slug>
"""

import sys
import logging
from main import MarketAnalysisBot

# Импортируем настройку логирования
import logging_config

def main():
    if len(sys.argv) != 2:
        print("Использование: python add_market_by_slug.py <slug>")
        print("Пример: python add_market_by_slug.py will-trump-remove-jerome-powell")
        sys.exit(1)
    
    slug = sys.argv[1]
    print(f"🚀 Добавление рынка по слаг: {slug}")
    
    try:
        # Создаем экземпляр бота
        bot = MarketAnalysisBot()
        
        # Инициализируем компоненты
        bot.db_manager.connect()
        bot.market_analyzer.init_browser_sync()
        
        # Добавляем рынок
        success = bot.add_market_by_slug(slug)
        
        if success:
            print(f"✅ Рынок {slug} успешно добавлен и анализ запущен!")
        else:
            print(f"❌ Не удалось добавить рынок {slug}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)
    finally:
        # Закрываем соединения
        try:
            bot.market_analyzer.close_driver_sync()
            bot.db_manager.close_connections()
        except:
            pass

if __name__ == "__main__":
    main() 