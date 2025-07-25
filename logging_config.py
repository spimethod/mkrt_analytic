#!/usr/bin/env python3
"""
Централизованная настройка логирования для Railway
"""

import logging
import sys

def setup_logging():
    """Настройка логирования для Railway (stdout вместо stderr)"""
    # Создаем handler для stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    # Настраиваем базовое логирование
    logging.basicConfig(
        level=logging.INFO,
        handlers=[handler]
    )
    
    # Настраиваем логгеры для всех модулей
    loggers = [
        'main',
        'database', 
        'telegram_bot',
        'ocr_screenshot_analyzer',
        'config'
    ]
    
    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        # Убираем дублирующие handlers
        logger.handlers = []
        logger.addHandler(handler)
        logger.propagate = False

# Инициализируем логирование при импорте
setup_logging() 