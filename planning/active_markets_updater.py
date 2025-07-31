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
                    # Проверяем время создания из базы данных, а не из active_markets
                    created_at = market.get('created_at_analytic')
                    if created_at:
                        # Если время создания не имеет timezone, добавляем UTC
                        if created_at.tzinfo is None:
                            from datetime import timezone
                            created_at = created_at.replace(tzinfo=timezone.utc)
                        
                        current_time = datetime.now(timezone.utc)
                        time_diff = current_time - created_at
                        
                        if time_diff > timedelta(minutes=self.analysis_time_minutes):
                            logger.warning(f"⚠️ Рынок {market['id']} закрыт по истечении времени анализа ({self.analysis_time_minutes} мин)")
                            logger.info(f"📅 Время создания: {created_at}, текущее время: {current_time}, разница: {time_diff}")
                            self.lifecycle_manager.stop_market_analysis(market['id'], "закрыт")
                        else:
                            remaining_minutes = (timedelta(minutes=self.analysis_time_minutes) - time_diff).total_seconds() / 60
                            logger.debug(f"⏰ Рынок {market['id']} активен еще {remaining_minutes:.1f} минут")
                    else:
                        logger.warning(f"⚠️ Не удалось получить время создания для рынка {market['id']}")
        
        except Exception as e:
            error_msg = f"Error updating active markets: {e}"
            logger.error(error_msg)
            from telegram.error_logger import ErrorLogger
            error_logger = ErrorLogger()
            error_logger.log_error(error_msg) 