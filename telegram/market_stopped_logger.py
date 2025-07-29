import logging
from telegram.telegram_connector import TelegramConnector

logger = logging.getLogger(__name__)

class MarketStoppedLogger:
    def __init__(self):
        self.telegram = TelegramConnector()
    
    def log_market_stopped(self, market_data):
        """Логирование остановки рынка"""
        try:
            message = f"🛑 <b>Анализ рынка остановлен</b>\n\n"
            message += f"📝 <b>Вопрос:</b> {market_data['question']}\n"
            message += f"🔗 <b>Slug:</b> {market_data['slug']}\n"
            message += f"📊 <b>Статус:</b> {market_data['status']}\n\n"
            message += "⏰ <i>Анализ завершен</i>"
            
            return self.telegram.send_message(message)
        except Exception as e:
            logger.error(f"Error logging market stopped: {e}")
            return False 