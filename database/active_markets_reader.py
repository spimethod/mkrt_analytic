import psycopg2.extras
import logging
from database.database_connection import DatabaseConnection

logger = logging.getLogger(__name__)

class ActiveMarketsReader:
    def __init__(self):
        self.db_connection = DatabaseConnection()
    
    def get_active_markets(self):
        """Получение активных рынков из аналитической таблицы"""
        try:
            conn = self.db_connection.get_connection()
            if not conn:
                return []
            
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT id, question, slug, created_at_analytic, status
                FROM mkrt_analytic
                WHERE status = 'в работе'
                ORDER BY created_at_analytic DESC
            """)
            
            markets = cursor.fetchall()
            cursor.close()
            return markets
        except Exception as e:
            logger.error(f"Error getting active markets: {e}")
            return []
    
    def get_in_progress_markets(self):
        """Получение рынков со статусом 'в работе'"""
        try:
            conn = self.db_connection.get_connection()
            if not conn:
                return []
            
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT id, question, slug, created_at_analytic, status
                FROM mkrt_analytic
                WHERE status = 'в работе'
                ORDER BY created_at_analytic DESC
            """)
            
            markets = cursor.fetchall()
            cursor.close()
            return markets
        except Exception as e:
            logger.error(f"Error getting in progress markets: {e}")
            return []
    
    def get_recently_closed_markets(self):
        """Получение недавно закрытых рынков (за последние 10 минут)"""
        try:
            conn = self.db_connection.get_connection()
            if not conn:
                return []
            
            from datetime import datetime, timedelta, timezone
            ten_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=10)
            
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT id, question, slug, created_at_analytic, status, last_updated
                FROM mkrt_analytic
                WHERE status = 'закрыт' 
                AND last_updated > %s
                ORDER BY last_updated DESC
            """, (ten_minutes_ago,))
            
            markets = cursor.fetchall()
            cursor.close()
            return markets
        except Exception as e:
            logger.error(f"Error getting recently closed markets: {e}")
            return []
    
    def get_market_info(self, market_id):
        """Получение информации о рынке по ID"""
        try:
            conn = self.db_connection.get_connection()
            if not conn:
                return None
            
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT id, question, slug, created_at_analytic, status, last_updated
                FROM mkrt_analytic
                WHERE id = %s
            """, (market_id,))
            
            market = cursor.fetchone()
            cursor.close()
            return market
        except Exception as e:
            logger.error(f"Error getting market info: {e}")
            return None 