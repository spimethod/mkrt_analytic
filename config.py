# Совместимый config.py для обратной совместимости
import os

# Database config
DB_HOST = os.getenv('PGHOST') or os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('PGPORT') or os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('PGDATABASE') or os.getenv('DB_NAME', 'polymarket')
DB_USER = os.getenv('PGUSER') or os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('PGPASSWORD') or os.getenv('DB_PASSWORD', '')

# Telegram config
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

# Analysis config
ANALYSIS_TIME_MINUTES = int(os.getenv('ANALYSIS_TIME_MINUTES', '60'))
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
RETRY_DELAY_SECONDS = int(os.getenv('RETRY_DELAY_SECONDS', '30'))
LOGGING_INTERVAL_MINUTES = int(os.getenv('LOGGING_INTERVAL_MINUTES', '10'))

# Polymarket base URL
POLYMARKET_BASE_URL = 'https://polymarket.com/event/' 