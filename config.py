import os
from dotenv import load_dotenv

load_dotenv()

# Database configurations - using Railway's standard PostgreSQL variables
# For Polymarket database (markets)
POLYMARKET_DB_CONFIG = {
    'host': os.getenv('POLYMARKET_PGHOST', os.getenv('PGHOST', 'localhost')),
    'port': os.getenv('POLYMARKET_PGPORT', os.getenv('PGPORT', '5432')),
    'database': os.getenv('POLYMARKET_PGDATABASE', 'markets'),
    'user': os.getenv('POLYMARKET_PGUSER', os.getenv('PGUSER', 'postgres')),
    'password': os.getenv('POLYMARKET_PGPASSWORD', os.getenv('PGPASSWORD', '')),
}

# For Analytic database (mkrt_analytic)
ANALYTIC_DB_CONFIG = {
    'host': os.getenv('ANALYTIC_PGHOST', os.getenv('PGHOST', 'localhost')),
    'port': os.getenv('ANALYTIC_PGPORT', os.getenv('PGPORT', '5432')),
    'database': os.getenv('ANALYTIC_PGDATABASE', 'mkrt_analytic'),
    'user': os.getenv('ANALYTIC_PGUSER', os.getenv('PGUSER', 'postgres')),
    'password': os.getenv('ANALYTIC_PGPASSWORD', os.getenv('PGPASSWORD', '')),
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