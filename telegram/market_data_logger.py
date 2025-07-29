import logging
from telegram.telegram_connector import TelegramConnector

logger = logging.getLogger(__name__)

class MarketDataLogger:
    def __init__(self):
        self.telegram = TelegramConnector()
    
    def log_market_data(self, market):
        """Логирование данных рынка"""
        try:
            message = f"📊 <b>Данные рынка</b>\n\n"
            message += f"📝 <b>Вопрос:</b> {market['question']}\n"
            message += f"🔗 <b>Slug:</b> {market['slug']}\n"
            message += f"📈 <b>Процент Yes:</b> {market.get('yes_percentage', 'N/A')}%\n"
            message += f"💰 <b>Объем:</b> {market.get('volume', 'N/A')}\n"
            message += f"📋 <b>Контракт:</b> {market.get('contract_address', 'N/A')}\n"
            message += f"⏰ <b>Время:</b> {market.get('created_at_analytic', 'N/A')}\n\n"
            message += "🔄 <i>Анализ продолжается...</i>"
            
            return self.telegram.send_message(message)
        except Exception as e:
            logger.error(f"Error logging market data: {e}")
            return False 