import os
import logging

logger = logging.getLogger(__name__)

class ConfigLoader:
    def __init__(self):
        self.load_config()
    
    def load_config(self):
        """Загрузка конфигурации из переменных окружения"""
        # Database config
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'polymarket'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', '')
        }
        
        # Telegram config
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
        
        # Analysis config
        self.analysis_time_minutes = int(os.getenv('ANALYSIS_TIME_MINUTES', '60'))
        self.max_retries = int(os.getenv('MAX_RETRIES', '3'))
        self.retry_delay_seconds = int(os.getenv('RETRY_DELAY_SECONDS', '30'))
        self.logging_interval_minutes = int(os.getenv('LOGGING_INTERVAL_MINUTES', '10'))
    
    def get_database_config(self):
        """Получение конфигурации базы данных"""
        return self.db_config
    
    def get_telegram_bot_token(self):
        """Получение токена Telegram бота"""
        return self.telegram_bot_token
    
    def get_telegram_chat_id(self):
        """Получение ID чата Telegram"""
        return self.telegram_chat_id
    
    def get_analysis_time_minutes(self):
        """Получение времени анализа в минутах"""
        return self.analysis_time_minutes
    
    def get_max_retries(self):
        """Получение максимального количества повторов"""
        return self.max_retries
    
    def get_retry_delay_seconds(self):
        """Получение задержки между повторами в секундах"""
        return self.retry_delay_seconds
    
    def get_logging_interval_minutes(self):
        """Получение интервала логирования в минутах"""
        return self.logging_interval_minutes 