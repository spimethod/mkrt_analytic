import schedule
import logging
from planning.new_markets_checker import NewMarketsChecker
from planning.active_markets_updater import ActiveMarketsUpdater
from planning.market_summaries_logger import MarketSummariesLogger
from planning.recently_closed_checker import RecentlyClosedChecker

logger = logging.getLogger(__name__)

class TaskScheduler:
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.new_markets_checker = NewMarketsChecker(bot_instance)
        self.active_markets_updater = ActiveMarketsUpdater(bot_instance)
        self.market_summaries_logger = MarketSummariesLogger(bot_instance)
        self.recently_closed_checker = RecentlyClosedChecker(bot_instance)
    
    def schedule_all_tasks(self):
        """Планирование всех задач"""
        try:
            # Планируем задачи
            schedule.every(30).seconds.do(self.new_markets_checker.check_new_markets)
            schedule.every(1).minutes.do(self.active_markets_updater.update_active_markets)
            schedule.every(10).minutes.do(self.market_summaries_logger.log_market_summaries)
            schedule.every(5).minutes.do(self.recently_closed_checker.check_recently_closed_markets)
            
            logger.info("✅ Все задачи запланированы успешно")
        except Exception as e:
            logger.error(f"❌ Ошибка планирования задач: {e}")
    
    def run_pending_tasks(self):
        """Запуск ожидающих задач"""
        try:
            schedule.run_pending()
        except Exception as e:
            logger.error(f"❌ Ошибка выполнения задач: {e}") 