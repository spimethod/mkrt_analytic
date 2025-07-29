import logging
from telegram.telegram_connector import TelegramConnector
from datetime import datetime

logger = logging.getLogger(__name__)

class ErrorLogger:
    def __init__(self):
        self.telegram = TelegramConnector()
    
    def log_error(self, error_msg, slug=None):
        """Логирование ошибки"""
        try:
            message = f"❌ <b>Ошибка в работе бота</b>\n\n"
            message += f"🔍 <b>Описание:</b> {error_msg}\n"
            if slug:
                message += f"📊 <b>Рынок:</b> {slug}\n"
            message += f"⏰ <b>Время:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            message += "⚠️ <i>Проверьте логи для деталей</i>"
            
            return self.telegram.send_message(message)
        except Exception as e:
            logger.error(f"Error logging error: {e}")
            return False 