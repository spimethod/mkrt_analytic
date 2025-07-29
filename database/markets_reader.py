import psycopg2.extras
import logging
from database.database_connection import DatabaseConnection

logger = logging.getLogger(__name__)

class MarketsReader:
    def __init__(self):
        self.db_connection = DatabaseConnection()
    
    def get_new_markets(self):
        """Получение новых рынков из таблицы markets"""
        try:
            conn = self.db_connection.get_connection()
            if not conn:
                return []
            
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT id, question, slug, created_at, active
                FROM markets
                ORDER BY created_at DESC
                LIMIT 10
            """)
            
            markets = cursor.fetchall()
            cursor.close()
            return markets
        except Exception as e:
            logger.error(f"Error getting new markets: {e}")
            return []
    
    def get_new_markets_after_time(self, start_time):
        """Получение только новых рынков, созданных после указанного времени"""
        try:
            conn = self.db_connection.get_connection()
            if not conn:
                return []
            
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT id, question, slug, created_at, active
                FROM markets
                WHERE created_at > %s
                ORDER BY created_at DESC
                LIMIT 10
            """, (start_time,))
            
            markets = cursor.fetchall()
            cursor.close()
            return markets
        except Exception as e:
            logger.error(f"Error getting new markets after time: {e}")
            return [] 