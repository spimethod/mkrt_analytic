import psycopg2
import psycopg2.extras
from datetime import datetime
from config import POLYMARKET_DB_CONFIG, ANALYTIC_DB_CONFIG
import logging

# Импортируем настройку логирования
import logging_config

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.conn = None
    
    def connect(self):
        """Подключение к базе данных"""
        try:
            # Используем одну конфигурацию для обеих таблиц
            self.conn = psycopg2.connect(**POLYMARKET_DB_CONFIG)
            logger.info("Connected to database")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False
    
    def get_new_markets(self):
        """Получение новых рынков из таблицы markets"""
        try:
            if not self.conn:
                if not self.connect():
                    return []
            
            cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
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
    
    def market_exists_in_analytic(self, slug):
        """Проверка существования рынка в аналитической таблице по slug"""
        try:
            if not self.conn:
                if not self.connect():
                    return False
            
            cursor = self.conn.cursor()
            cursor.execute("SELECT id FROM mkrt_analytic WHERE slug = %s", (slug,))
            result = cursor.fetchone()
            cursor.close()
            
            return result is not None
        except Exception as e:
            logger.error(f"Error checking market existence: {e}")
            return False

    def insert_market_to_analytic(self, market_data):
        """Добавление рынка в аналитическую таблицу mkrt_analytic"""
        try:
            if not self.conn:
                if not self.connect():
                    return None
            
            # Проверяем, существует ли уже рынок с таким slug
            if self.market_exists_in_analytic(market_data['slug']):
                logger.info(f"Market {market_data['slug']} already exists in analytic database")
                # Получаем ID существующего рынка
                cursor = self.conn.cursor()
                cursor.execute("SELECT id FROM mkrt_analytic WHERE slug = %s", (market_data['slug'],))
                result = cursor.fetchone()
                cursor.close()
                return result[0] if result else None
            
            cursor = self.conn.cursor()
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
            self.conn.commit()
            cursor.close()
            logger.info(f"Market {market_data['slug']} inserted/updated in analytic database")
            return market_id
        except Exception as e:
            logger.error(f"Error inserting market to analytic: {e}")
            if self.conn:
                self.conn.rollback()
            return None
    
    def update_market_analysis(self, market_id, analysis_data):
        """Обновление данных анализа рынка"""
        try:
            if not self.conn:
                if not self.connect():
                    return False
            
            cursor = self.conn.cursor()
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
            
            self.conn.commit()
            cursor.close()
            logger.info(f"Market analysis updated for ID {market_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating market analysis: {e}")
            if self.conn:
                self.conn.rollback()
            return False
    
    def get_market_by_slug(self, slug):
        """Получение рынка по slug из аналитической таблицы"""
        try:
            if not self.conn:
                if not self.connect():
                    return None
            
            cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
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
            if not self.conn:
                if not self.connect():
                    return []
            
            cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
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
        """Закрытие соединения с базой данных"""
        if self.conn:
            self.conn.close()
        logger.info("Database connection closed") 