import asyncio
import time
import httpx
import logging
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, ANALYSIS_TIME_MINUTES, LOGGING_INTERVAL_MINUTES
from datetime import datetime

# Импортируем настройку логирования
import logging_config

# Совместимый TelegramLogger для обратной совместимости
from telegram.telegram_connector import TelegramConnector
from telegram.new_market_logger import NewMarketLogger
from telegram.error_logger import ErrorLogger

logger = logging.getLogger(__name__)

class TelegramLogger:
    """Совместимый класс для обратной совместимости"""
    
    def __init__(self):
        self.connector = TelegramConnector()
        self.new_market_logger = NewMarketLogger()
        self.error_logger = ErrorLogger()
    
    def log_bot_start(self):
        """Логирование запуска бота"""
        return self.connector.log_bot_start()
    
    def log_bot_stop(self):
        """Логирование остановки бота"""
        return self.connector.log_bot_stop()
    
    def log_new_market(self, market):
        """Логирование нового рынка"""
        return self.new_market_logger.log_new_market(market)
    
    def log_error(self, error_msg, slug=None):
        """Логирование ошибки"""
        return self.error_logger.log_error(error_msg, slug) 