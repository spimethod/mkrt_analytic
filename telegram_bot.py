import asyncio
import time
from telegram import Bot
from telegram.error import TelegramError
import logging
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, ANALYSIS_TIME_MINUTES, LOGGING_INTERVAL_MINUTES
from datetime import datetime

logger = logging.getLogger(__name__)

class TelegramLogger:
    def __init__(self):
        self.token = TELEGRAM_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.last_message_time = 0
        self.min_interval = 1.0  # Минимальный интервал между сообщениями (секунды)
    
    async def send_message(self, message):
        """Отправка сообщения в Telegram с защитой от flood control"""
        if not self.token or not self.chat_id:
            logger.warning("Telegram bot not configured, skipping message")
            return False
        
        # Проверяем интервал между сообщениями
        current_time = time.time()
        if current_time - self.last_message_time < self.min_interval:
            logger.info(f"Waiting {self.min_interval - (current_time - self.last_message_time):.1f}s to avoid flood control")
            await asyncio.sleep(self.min_interval - (current_time - self.last_message_time))
        
        try:
            # Создаем новый экземпляр бота для каждого сообщения
            bot = Bot(token=self.token)
            await bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
            await bot.close()  # Закрываем соединение
            self.last_message_time = time.time()
            logger.info("Telegram message sent successfully")
            return True
        except TelegramError as e:
            if "Flood control exceeded" in str(e):
                logger.warning(f"Telegram flood control: {e}")
                # Увеличиваем интервал при flood control
                self.min_interval = min(self.min_interval * 2, 60.0)
                return False
            else:
                logger.error(f"Failed to send Telegram message: {e}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error sending Telegram message: {e}")
            return False
    
    def send_message_sync(self, message):
        """Синхронная отправка сообщения в Telegram"""
        try:
            # Создаем новый event loop для каждого сообщения
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.send_message(message))
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Error in sync telegram send: {e}")
    
    def log_new_market(self, market_data):
        """Логирование нового рынка"""
        message = f"""
🆕 <b>Новый рынок обнаружен</b>

📊 <b>Вопрос:</b> {market_data['question']}
🔗 <b>Slug:</b> {market_data['slug']}
📅 <b>Создан:</b> {market_data['created_at']}
✅ <b>Активен:</b> {'Да' if market_data['active'] else 'Нет'}
📚 <b>Ордер бук:</b> {'Включен' if market_data['enable_order_book'] else 'Отключен'}
        """
        self.send_message_sync(message)
    
    def log_market_data(self, market_data):
        """Логирование данных о рынке каждые 10 минут"""
        message = f"""
📊 <b>Данные рынка (каждые 10 мин)</b>

📋 <b>Вопрос:</b> {market_data['question']}
🔗 <b>Slug:</b> {market_data['slug']}
✅ <b>Рынок существует:</b> {'Да' if market_data['market_exists'] else 'Нет'}
🔢 <b>Булевый:</b> {'Да' if market_data['is_boolean'] else 'Нет'}
📈 <b>Процент Yes:</b> {market_data['yes_percentage']}%
💰 <b>Ордер бук Yes:</b> ${market_data['yes_order_book_total']:,.2f}
💰 <b>Ордер бук No:</b> ${market_data['no_order_book_total']:,.2f}
📄 <b>Контракт:</b> {market_data['contract_address']}
🔄 <b>Статус:</b> {market_data['status']}
⏰ <b>Обновлено:</b> {market_data['last_updated']}
        """
        self.send_message_sync(message)
    
    def log_market_stopped(self, market_data):
        """Логирование прекращения анализа рынка"""
        message = f"""
🛑 <b>Анализ рынка прекращен</b>

📋 <b>Вопрос:</b> {market_data['question']}
🔗 <b>Slug:</b> {market_data['slug']}
🔄 <b>Статус:</b> {market_data['status']}
⏰ <b>Время остановки:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        self.send_message_sync(message)
    
    def log_error(self, error_message, market_slug=None):
        """Логирование ошибок"""
        message = f"""
❌ <b>Ошибка в работе бота</b>

🔗 <b>Рынок:</b> {market_slug if market_slug else 'Неизвестно'}
⚠️ <b>Ошибка:</b> {error_message}
⏰ <b>Время:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        self.send_message_sync(message)
    
    def log_bot_start(self):
        """Логирование запуска бота"""
        message = f"""
🚀 <b>Бот запущен</b>

⏰ <b>Время запуска:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📊 <b>Время анализа:</b> {ANALYSIS_TIME_MINUTES} минут
🔄 <b>Интервал логирования:</b> {LOGGING_INTERVAL_MINUTES} минут
        """
        self.send_message_sync(message)
    
    def log_bot_stop(self):
        """Логирование остановки бота"""
        message = f"""
🛑 <b>Бот остановлен</b>

⏰ <b>Время остановки:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        self.send_message_sync(message) 