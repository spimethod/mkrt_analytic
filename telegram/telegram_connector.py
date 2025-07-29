import logging
import httpx
from config.config_loader import ConfigLoader

logger = logging.getLogger(__name__)

class TelegramConnector:
    def __init__(self):
        self.config = ConfigLoader()
        self.bot_token = self.config.get_telegram_bot_token()
        self.chat_id = self.config.get_telegram_chat_id()
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def send_message(self, message):
        """Отправка сообщения в Telegram"""
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            
            with httpx.Client() as client:
                response = client.post(url, json=data, timeout=10)
                response.raise_for_status()
                
            logger.info("Telegram message sent successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    def log_bot_start(self):
        """Логирование запуска бота"""
        message = "🤖 <b>Market Analysis Bot запущен</b>\n\nБот начал работу и готов к анализу рынков."
        return self.send_message(message)
    
    def log_bot_stop(self):
        """Логирование остановки бота"""
        message = "🛑 <b>Market Analysis Bot остановлен</b>\n\nБот завершил работу."
        return self.send_message(message) 