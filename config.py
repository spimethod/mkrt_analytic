import os
from dotenv import load_dotenv

load_dotenv()

# Database configurations - using Railway's standard PostgreSQL variables
# For Polymarket database (markets) - using the same connection for both databases
POLYMARKET_DB_CONFIG = {
    'host': os.getenv('PGHOST', 'localhost'),
    'port': os.getenv('PGPORT', '5432'),
    'database': os.getenv('PGDATABASE', 'railway'),  # Using 'railway' as default
    'user': os.getenv('PGUSER', 'postgres'),
    'password': os.getenv('PGPASSWORD', ''),
}

ANALYTIC_DB_CONFIG = {
    'host': os.getenv('PGHOST', 'localhost'),
    'port': os.getenv('PGPORT', '5432'),
    'database': os.getenv('PGDATABASE', 'railway'),  # Using 'railway' as default
    'user': os.getenv('PGUSER', 'postgres'),
    'password': os.getenv('PGPASSWORD', ''),
}

# Telegram configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

# Analysis time in minutes
ANALYSIS_TIME_MINUTES = int(os.getenv('MKRT_ANALYTIC_TIME_MIN', '60'))

# Ping interval in minutes (how often to update market data)
PING_INTERVAL_MINUTES = int(os.getenv('MKRT_ANALYTIC_PING_MIN', '3'))

# Polymarket base URL
POLYMARKET_BASE_URL = 'https://polymarket.com/event/'

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 60

# Logging interval (every 10 minutes)
LOGGING_INTERVAL_MINUTES = 10 