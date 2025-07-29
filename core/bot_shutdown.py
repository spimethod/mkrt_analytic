import logging
from telegram.telegram_connector import TelegramConnector

logger = logging.getLogger(__name__)

class BotShutdown:
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.telegram = TelegramConnector()
    
    def stop(self):
        """Остановка бота"""
        logger.info("Stopping Market Analysis Bot")
        self.bot.running = False
        self.telegram.log_bot_stop()
        
        # Закрываем браузер
        if hasattr(self.bot, 'market_analyzer'):
            self.bot.market_analyzer.close_driver()
        
        # Закрываем соединения с БД
        if hasattr(self.bot, 'db_manager'):
            self.bot.db_manager.close_connections()
        
        logger.info("Bot shutdown completed successfully") 