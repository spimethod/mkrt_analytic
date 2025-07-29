import schedule
import logging
import threading
import time
from datetime import datetime
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
        
        # Флаги для управления потоками
        self.running = False
        self.last_market_check = None
    
    def schedule_all_tasks(self):
        """Планирование всех задач"""
        try:
            # Планируем задачи (кроме проверки новых рынков - она будет в отдельном потоке)
            schedule.every(1).minutes.do(self.active_markets_updater.update_active_markets)
            schedule.every(10).minutes.do(self.market_summaries_logger.log_market_summaries)
            schedule.every(5).minutes.do(self.recently_closed_checker.check_recently_closed_markets)
            
            logger.info("✅ Все задачи запланированы успешно")
        except Exception as e:
            logger.error(f"❌ Ошибка планирования задач: {e}")
    
    def start_market_checker_thread(self):
        """Запуск отдельного потока для проверки новых рынков"""
        self.running = True
        market_checker_thread = threading.Thread(target=self._run_market_checker)
        market_checker_thread.daemon = True
        market_checker_thread.start()
        logger.info("✅ Поток проверки новых рынков запущен")
    
    def _run_market_checker(self):
        """Отдельный поток для проверки новых рынков каждые 30 секунд"""
        while self.running and self.bot.running:
            try:
                current_time = datetime.now()
                
                # Проверяем, прошло ли 30 секунд с последней проверки
                if (self.last_market_check is None or 
                    (current_time - self.last_market_check).total_seconds() >= 30):
                    
                    logger.debug("🔍 Проверяем новые рынки...")
                    self.new_markets_checker.check_new_markets()
                    self.last_market_check = current_time
                
                time.sleep(1)  # Небольшая пауза между проверками
                
            except Exception as e:
                logger.error(f"❌ Ошибка в потоке проверки новых рынков: {e}")
                time.sleep(5)  # Пауза при ошибке
    
    def stop_market_checker_thread(self):
        """Остановка потока проверки новых рынков"""
        self.running = False
        logger.info("🛑 Поток проверки новых рынков остановлен")
    
    def run_pending_tasks(self):
        """Запуск ожидающих задач"""
        try:
            schedule.run_pending()
        except Exception as e:
            logger.error(f"❌ Ошибка выполнения задач: {e}") 