import logging
from datetime import datetime
from telegram.telegram_connector import TelegramConnector
from restoration.stuck_markets_restorer import StuckMarketsRestorer
from planning.task_scheduler import TaskScheduler

logger = logging.getLogger(__name__)

class BotStartup:
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.telegram = TelegramConnector()
        self.restorer = StuckMarketsRestorer(bot_instance)
        self.scheduler = TaskScheduler(bot_instance)
    
    def start(self):
        """Запуск бота"""
        logger.info("Starting Market Analysis Bot")
        self.telegram.log_bot_start()
        self.bot.running = True
        
        # Восстанавливаем зависшие рынки при запуске
        self.restorer.restore_stuck_markets()
        
        # Планируем задачи
        self.scheduler.schedule_all_tasks()
        
        logger.info("Bot startup completed successfully") 