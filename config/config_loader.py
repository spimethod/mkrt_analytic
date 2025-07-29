import os
import logging

logger = logging.getLogger(__name__)

class ConfigLoader:
    def __init__(self):
        self.load_config()
    
    def load_config(self):
        """Загрузка конфигурации из переменных окружения"""
        # Railway PostgreSQL variables
        pg_host = os.getenv('PGHOST') or os.getenv('DB_HOST', 'localhost')
        pg_port = os.getenv('PGPORT') or os.getenv('DB_PORT', '5432')
        # Принудительно используем markets, игнорируя PGDATABASE от Railway
        pg_database = os.getenv('DB_NAME', 'markets')
        pg_user = os.getenv('PGUSER') or os.getenv('DB_USER', 'postgres')
        pg_password = os.getenv('PGPASSWORD') or os.getenv('DB_PASSWORD', '')
        
        # Логируем конфигурацию только один раз при инициализации
        if not hasattr(self, '_config_logged'):
            logger.info(f"Database config: host={pg_host}, port={pg_port}, database={pg_database}, user={pg_user}")
            self._config_logged = True
        else:
            # Убираем логирование для повторных вызовов
            pass
        
        # Database config
        self.db_config = {
            'host': pg_host,
            'port': pg_port,
            'database': pg_database,
            'user': pg_user,
            'password': pg_password
        }
        
        # Telegram config
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
        
        # Analysis config
        self.analysis_time_minutes = int(os.getenv('ANALYSIS_TIME_MINUTES', '60'))
        self.max_retries = int(os.getenv('MAX_RETRIES', '3'))
        self.retry_delay_seconds = int(os.getenv('RETRY_DELAY_SECONDS', '30'))
        self.logging_interval_minutes = int(os.getenv('LOGGING_INTERVAL_MINUTES', '10'))
        
        # MKRT Analytic config
        self.mkrt_analytic_time_min = int(os.getenv('MKRT_ANALYTIC_TIME_MIN', '60'))
        self.mkrt_analytic_ping_min = int(os.getenv('MKRT_ANALYTIC_PING_MIN', '5'))
    
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
    
    def get_mkrt_analytic_time_min(self):
        """Получение минимального времени для анализа рынка в минутах"""
        return self.mkrt_analytic_time_min
    
    def get_mkrt_analytic_ping_min(self):
        """Получение интервала пинга для анализа рынка в минутах"""
        return self.mkrt_analytic_ping_min 