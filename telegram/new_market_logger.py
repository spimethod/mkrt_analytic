import logging
from telegram.telegram_connector import TelegramConnector

logger = logging.getLogger(__name__)

class NewMarketLogger:
    def __init__(self):
        self.telegram = TelegramConnector()
    
    def log_new_market(self, market):
        """Логирование нового рынка"""
        try:
            message = f"🆕 <b>Новый рынок обнаружен!</b>\n\n"
            message += f"📝 <b>Вопрос:</b> {market['question']}\n"
            message += f"🔗 <b>Slug:</b> {market['slug']}\n"
            message += f"⏰ <b>Время:</b> {market.get('created_at', 'N/A')}\n\n"
            message += "🔄 <i>Начинаем анализ...</i>"
            
            return self.telegram.send_message(message)
        except Exception as e:
            logger.error(f"Error logging new market: {e}")
            return False 