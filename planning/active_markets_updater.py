import logging
from datetime import datetime, timedelta
from database.active_markets_reader import ActiveMarketsReader
from active_markets.market_lifecycle_manager import MarketLifecycleManager
import os

logger = logging.getLogger(__name__)

class ActiveMarketsUpdater:
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.reader = ActiveMarketsReader()
        self.lifecycle_manager = MarketLifecycleManager(bot_instance)
        # Получаем время анализа из переменной окружения
        self.analysis_time_minutes = int(os.getenv('MKRT_ANALYTIC_TIME_MIN', '60'))
    
    def update_active_markets(self):
        """Обновление активных рынков каждую минуту"""
        try:
            active_markets = self.reader.get_active_markets()
            
            for market in active_markets:
                if market['id'] in self.bot.active_markets:
                    # Проверяем, не истекло ли время анализа
                    start_time = self.bot.active_markets[market['id']]['start_time']
                    if datetime.now() - start_time > timedelta(minutes=self.analysis_time_minutes):
                        logger.warning(f"⚠️ Рынок {market['id']} закрыт по истечении времени анализа ({self.analysis_time_minutes} мин)")
                        self.lifecycle_manager.stop_market_analysis(market['id'], "закрыт")
        
        except Exception as e:
            error_msg = f"Error updating active markets: {e}"
            logger.error(error_msg)
            from telegram.error_logger import ErrorLogger
            error_logger = ErrorLogger()
            error_logger.log_error(error_msg) 