import logging
from datetime import datetime, timedelta
from database.active_markets_reader import ActiveMarketsReader
from telegram.market_data_logger import MarketDataLogger

logger = logging.getLogger(__name__)

class MarketSummariesLogger:
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.reader = ActiveMarketsReader()
        self.data_logger = MarketDataLogger()
    
    def log_market_summaries(self):
        """Логирование сводки по рынкам каждые 10 минут"""
        try:
            active_markets = self.reader.get_active_markets()
            
            for market in active_markets:
                if market['id'] in self.bot.active_markets:
                    # Проверяем, прошло ли 10 минут с последнего логирования
                    last_log = self.bot.active_markets[market['id']]['last_log']
                    if datetime.now() - last_log > timedelta(minutes=10):
                        # Логируем данные рынка
                        self.data_logger.log_market_data(market)
                        self.bot.active_markets[market['id']]['last_log'] = datetime.now()
        
        except Exception as e:
            error_msg = f"Error logging market summaries: {e}"
            logger.error(error_msg)
            from telegram.error_logger import ErrorLogger
            error_logger = ErrorLogger()
            error_logger.log_error(error_msg) 