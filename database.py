import psycopg2
import psycopg2.extras
from datetime import datetime
from config import POLYMARKET_DB_CONFIG, ANALYTIC_DB_CONFIG
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.polymarket_conn = None
        self.analytic_conn = None
    
    def connect_polymarket(self):
        """Подключение к базе данных Polymarket"""
        try:
            self.polymarket_conn = psycopg2.connect(**POLYMARKET_DB_CONFIG)
            logger.info("Connected to Polymarket database")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Polymarket database: {e}")
            return False
    
    def connect_analytic(self):
        """Подключение к аналитической базе данных"""
        try:
            self.analytic_conn = psycopg2.connect(**ANALYTIC_DB_CONFIG)
            logger.info("Connected to Analytic database")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Analytic database: {e}")
            return False
    
    def get_new_markets(self):
        """Получение новых рынков из базы Polymarket"""
        try:
            if not self.polymarket_conn:
                if not self.connect_polymarket():
                    return []
            
            cursor = self.polymarket_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT id, question, created_at, active, enable_order_book, slug
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
    
    def insert_market_to_analytic(self, market_data):
        """Добавление рынка в аналитическую базу"""
        try:
            if not self.analytic_conn:
                if not self.connect_analytic():
                    return False
            
            cursor = self.analytic_conn.cursor()
            cursor.execute("""
                INSERT INTO mkrt_analytic 
                (polymarket_id, question, created_at, active, enable_order_book, slug, 
                 market_exists, is_boolean, yes_percentage, yes_order_book_total, 
                 no_order_book_total, contract_address, status, last_updated)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (polymarket_id) DO UPDATE SET
                last_updated = EXCLUDED.last_updated
                RETURNING id
            """, (
                market_data['id'],
                market_data['question'],
                market_data['created_at'],
                market_data['active'],
                market_data['enable_order_book'],
                market_data['slug'],
                market_data.get('market_exists', False),
                market_data.get('is_boolean', False),
                market_data.get('yes_percentage', 0),
                market_data.get('yes_order_book_total', 0),
                market_data.get('no_order_book_total', 0),
                market_data.get('contract_address', ''),
                market_data.get('status', 'в работе'),
                datetime.now()
            ))
            
            market_id = cursor.fetchone()[0]
            self.analytic_conn.commit()
            cursor.close()
            logger.info(f"Market {market_data['slug']} inserted/updated in analytic database")
            return market_id
        except Exception as e:
            logger.error(f"Error inserting market to analytic: {e}")
            if self.analytic_conn:
                self.analytic_conn.rollback()
            return None
    
    def update_market_analysis(self, market_id, analysis_data):
        """Обновление данных анализа рынка"""
        try:
            if not self.analytic_conn:
                if not self.connect_analytic():
                    return False
            
            cursor = self.analytic_conn.cursor()
            cursor.execute("""
                UPDATE mkrt_analytic 
                SET market_exists = %s, is_boolean = %s, yes_percentage = %s,
                    yes_order_book_total = %s, no_order_book_total = %s,
                    contract_address = %s, status = %s, last_updated = %s
                WHERE id = %s
            """, (
                analysis_data.get('market_exists', False),
                analysis_data.get('is_boolean', False),
                analysis_data.get('yes_percentage', 0),
                analysis_data.get('yes_order_book_total', 0),
                analysis_data.get('no_order_book_total', 0),
                analysis_data.get('contract_address', ''),
                analysis_data.get('status', 'в работе'),
                datetime.now(),
                market_id
            ))
            
            self.analytic_conn.commit()
            cursor.close()
            logger.info(f"Market analysis updated for ID {market_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating market analysis: {e}")
            if self.analytic_conn:
                self.analytic_conn.rollback()
            return False
    
    def get_market_by_slug(self, slug):
        """Получение рынка по slug из аналитической базы"""
        try:
            if not self.analytic_conn:
                if not self.connect_analytic():
                    return None
            
            cursor = self.analytic_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT * FROM mkrt_analytic WHERE slug = %s
            """, (slug,))
            
            market = cursor.fetchone()
            cursor.close()
            return market
        except Exception as e:
            logger.error(f"Error getting market by slug: {e}")
            return None
    
    def get_active_markets(self):
        """Получение всех активных рынков"""
        try:
            if not self.analytic_conn:
                if not self.connect_analytic():
                    return []
            
            cursor = self.analytic_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT * FROM mkrt_analytic WHERE status = 'в работе'
            """)
            
            markets = cursor.fetchall()
            cursor.close()
            return markets
        except Exception as e:
            logger.error(f"Error getting active markets: {e}")
            return []
    
    def close_connections(self):
        """Закрытие соединений с базами данных"""
        if self.polymarket_conn:
            self.polymarket_conn.close()
        if self.analytic_conn:
            self.analytic_conn.close()
        logger.info("Database connections closed") 