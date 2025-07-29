import psycopg2
import logging
from config.config_loader import ConfigLoader

logger = logging.getLogger(__name__)

class DatabaseConnection:
    def __init__(self):
        self.conn = None
        self.config = ConfigLoader()
    
    def connect(self):
        """Подключение к базе данных"""
        try:
            db_config = self.config.get_database_config()
            self.conn = psycopg2.connect(**db_config)
            logger.info("Connected to database")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False
    
    def get_connection(self):
        """Получение соединения с БД"""
        if not self.conn:
            if not self.connect():
                return None
        return self.conn
    
    def close_connections(self):
        """Закрытие соединений с БД"""
        try:
            if self.conn:
                self.conn.close()
                logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database connections: {e}") 