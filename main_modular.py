import time
import threading
import logging
from core.bot_startup import BotStartup
from core.bot_shutdown import BotShutdown
from planning.task_scheduler import TaskScheduler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class MarketAnalysisBot:
    def __init__(self):
        self.running = False
        self.active_markets = {}
        
        # Инициализируем модули
        self.startup = BotStartup(self)
        self.shutdown = BotShutdown(self)
        self.scheduler = TaskScheduler(self)
    
    def start(self):
        """Запуск бота"""
        try:
            # Запускаем бота
            self.startup.start()
            
            # Запускаем планировщик в отдельном потоке
            scheduler_thread = threading.Thread(target=self.run_scheduler)
            scheduler_thread.daemon = True
            scheduler_thread.start()
            
            # Основной цикл
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                self.stop()
                
        except Exception as e:
            logger.error(f"Fatal error in main: {e}")
            self.stop()
    
    def stop(self):
        """Остановка бота"""
        self.shutdown.stop()
    
    def run_scheduler(self):
        """Запуск планировщика задач"""
        while self.running:
            self.scheduler.run_pending_tasks()
            time.sleep(1)

def main():
    """Главная функция"""
    bot = MarketAnalysisBot()
    try:
        bot.start()
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
        bot.stop()

if __name__ == "__main__":
    main() 