import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta, timezone
from config import POLYMARKET_DB_CONFIG, ANALYTIC_DB_CONFIG
import logging

# Импортируем настройку логирования
import logging_config

def convert_naive_to_aware(dt):
    """Конвертирует naive datetime в timezone-aware UTC datetime"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

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

    def get_new_markets_after_time(self, start_time):
        """Получение только новых рынков, созданных после указанного времени"""
        try:
            if not self.conn:
                if not self.connect():
                    return []
            
            cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT id, question, created_at, active, enable_order_book, slug
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
            logger.info(f"🔄 Попытка вставки рынка: {market_data.get('slug', 'unknown')}")
            
            if not self.conn:
                logger.info("📡 Подключаемся к БД...")
                if not self.connect():
                    logger.error("❌ Не удалось подключиться к БД")
                    return None
            
            # Проверяем, существует ли уже рынок с таким slug
            if self.market_exists_in_analytic(market_data['slug']):
                logger.info(f"ℹ️ Рынок {market_data['slug']} уже существует в аналитической БД")
                # Получаем ID существующего рынка
                cursor = self.conn.cursor()
                cursor.execute("SELECT id FROM mkrt_analytic WHERE slug = %s", (market_data['slug'],))
                result = cursor.fetchone()
                cursor.close()
                return result[0] if result else None
            
            logger.info(f"📝 Вставляем новый рынок: {market_data['slug']}")
            
            cursor = self.conn.cursor()
            
            # Подготавливаем данные для вставки
            current_time = datetime.now(timezone.utc)  # Используем UTC время для точности
            insert_data = (
                market_data['id'],
                market_data['question'],
                market_data['created_at'],
                market_data['active'],
                market_data['enable_order_book'],
                market_data['slug'],
                market_data.get('market_exists', True),  # По умолчанию True
                market_data.get('is_boolean', True),     # По умолчанию True
                market_data.get('yes_percentage', 0),
                market_data.get('volume', 'New'),        # Volume или "New"
                market_data.get('contract_address', ''),
                market_data.get('status', 'в работе'),
                current_time,  # last_updated
                current_time   # created_at_analytic
            )
            
            logger.info(f"📊 Данные для вставки: {insert_data}")
            
            cursor.execute("""
                INSERT INTO mkrt_analytic 
                (polymarket_id, question, created_at, active, enable_order_book, slug, 
                 market_exists, is_boolean, yes_percentage, volume, contract_address, status, last_updated, created_at_analytic)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (polymarket_id) DO UPDATE SET
                last_updated = EXCLUDED.last_updated
                RETURNING id
            """, insert_data)
            
            result = cursor.fetchone()
            if result:
                market_id = result[0]
                self.conn.commit()
                cursor.close()
                logger.info(f"✅ Рынок {market_data['slug']} успешно вставлен/обновлен! ID: {market_id}")
                return market_id
            else:
                logger.error("❌ Не удалось получить ID вставленной записи")
                self.conn.rollback()
                cursor.close()
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка вставки рынка в аналитическую БД: {e}")
            if self.conn:
                self.conn.rollback()
            return None
    
    def update_market_analysis(self, market_id, analysis_data):
        """Обновление данных анализа рынка"""
        try:
            logger.info(f"🔄 Обновление анализа для рынка ID: {market_id}")
            
            if not self.conn:
                logger.info("📡 Подключаемся к БД...")
                if not self.connect():
                    logger.error("❌ Не удалось подключиться к БД")
                    return False
            
            cursor = self.conn.cursor()
            
            # Подготавливаем данные для обновления
            current_time = datetime.now(timezone.utc)  # Используем UTC время для точности
            update_data = (
                analysis_data.get('market_exists', True),  # По умолчанию True
                analysis_data.get('is_boolean', True),     # По умолчанию True
                analysis_data.get('yes_percentage', 0),
                analysis_data.get('volume', 'New'),        # Volume или "New"
                analysis_data.get('contract_address', ''),
                analysis_data.get('status', 'в работе'),
                current_time,
                market_id
            )
            
            logger.info(f"📊 Данные для обновления: {update_data}")
            
            cursor.execute("""
                UPDATE mkrt_analytic 
                SET market_exists = %s, is_boolean = %s, yes_percentage = %s,
                    volume = %s, contract_address = %s, status = %s, last_updated = %s
                WHERE id = %s
            """, update_data)
            
            rows_affected = cursor.rowcount
            self.conn.commit()
            cursor.close()
            
            if rows_affected > 0:
                logger.info(f"✅ Анализ рынка ID {market_id} обновлен! Затронуто строк: {rows_affected}")
                return True
            else:
                logger.warning(f"⚠️ Не найдено записей для обновления (ID: {market_id})")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка обновления анализа рынка: {e}")
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
            
            # Конвертируем naive datetime в timezone-aware
            if market:
                if 'created_at_analytic' in market:
                    market['created_at_analytic'] = convert_naive_to_aware(market['created_at_analytic'])
                if 'last_updated' in market:
                    market['last_updated'] = convert_naive_to_aware(market['last_updated'])
            
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
            
            # Конвертируем naive datetime в timezone-aware
            for market in markets:
                if 'created_at_analytic' in market:
                    market['created_at_analytic'] = convert_naive_to_aware(market['created_at_analytic'])
                if 'last_updated' in market:
                    market['last_updated'] = convert_naive_to_aware(market['last_updated'])
            
            return markets
        except Exception as e:
            logger.error(f"Error getting active markets: {e}")
            return []
    
    def get_markets_exceeded_analysis_time(self, analysis_time_minutes):
        """Получение рынков из mkrt_analytic, которые превысили время анализа"""
        try:
            if not self.conn:
                if not self.connect():
                    return []
            
            # Вычисляем время, до которого рынки должны быть активны (от времени создания)
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=analysis_time_minutes)
            
            cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT id, slug, created_at_analytic, status
                FROM mkrt_analytic
                WHERE created_at_analytic < %s AND status = 'в работе'
            """, (cutoff_time,))
            
            markets = cursor.fetchall()
            cursor.close()
            
            # Конвертируем naive datetime в timezone-aware
            for market in markets:
                if 'created_at_analytic' in market:
                    market['created_at_analytic'] = convert_naive_to_aware(market['created_at_analytic'])
                if 'last_updated' in market:
                    market['last_updated'] = convert_naive_to_aware(market['last_updated'])
            
            logger.info(f"Found {len(markets)} markets that exceeded analysis time ({analysis_time_minutes} minutes)")
            return markets
        except Exception as e:
            logger.error(f"Error getting markets exceeded analysis time: {e}")
            return []

    def get_markets_in_progress(self):
        """Получение рынков, которые уже в работе (статус 'в работе')"""
        try:
            if not self.conn:
                if not self.connect():
                    return []
            
            cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT id, slug, status, last_updated, created_at_analytic, question
                FROM mkrt_analytic
                WHERE status = 'в работе'
            """)
            
            markets = cursor.fetchall()
            cursor.close()
            
            # Конвертируем naive datetime в timezone-aware
            for market in markets:
                if 'created_at_analytic' in market:
                    market['created_at_analytic'] = convert_naive_to_aware(market['created_at_analytic'])
                if 'last_updated' in market:
                    market['last_updated'] = convert_naive_to_aware(market['last_updated'])
            
            return markets
        except Exception as e:
            logger.error(f"Error getting markets in progress: {e}")
            return []

    def get_closed_markets_slugs(self):
        """Получение slug'ов закрытых рынков для исключения из проверки"""
        try:
            if not self.conn:
                if not self.connect():
                    return []
            
            cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT slug
                FROM mkrt_analytic
                WHERE status LIKE 'закрыт%'
            """)
            
            markets = cursor.fetchall()
            cursor.close()
            return [market['slug'] for market in markets]
        except Exception as e:
            logger.error(f"Error getting closed markets slugs: {e}")
            return []
    
    def get_recently_closed_markets(self, limit=10):
        """Получение недавно закрытых рынков для проверки на ошибочное закрытие"""
        try:
            if not self.conn:
                if not self.connect():
                    return []
            
            cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT id, slug, status, last_updated, created_at_analytic, question
                FROM mkrt_analytic
                WHERE status LIKE 'закрыт%%'
                ORDER BY last_updated DESC
                LIMIT %s
            """, (limit,))
            
            markets = cursor.fetchall()
            cursor.close()
            
            # Конвертируем naive datetime в timezone-aware
            for market in markets:
                if 'created_at_analytic' in market:
                    market['created_at_analytic'] = convert_naive_to_aware(market['created_at_analytic'])
                if 'last_updated' in market:
                    market['last_updated'] = convert_naive_to_aware(market['last_updated'])
            
            logger.info(f"Retrieved {len(markets)} recently closed markets")
            return markets
        except Exception as e:
            logger.error(f"Error getting recently closed markets: {e}")
            return []
    
    def get_last_3_markets_for_verification(self):
        """Получение последних 3 рынков для детальной проверки времени"""
        try:
            if not self.conn:
                if not self.connect():
                    return []
            
            cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT id, slug, status, last_updated, created_at_analytic, question
                FROM mkrt_analytic
                ORDER BY last_updated DESC
                LIMIT 3
            """)
            
            markets = cursor.fetchall()
            cursor.close()
            
            # Конвертируем naive datetime в timezone-aware
            for market in markets:
                if 'created_at_analytic' in market:
                    market['created_at_analytic'] = convert_naive_to_aware(market['created_at_analytic'])
                if 'last_updated' in market:
                    market['last_updated'] = convert_naive_to_aware(market['last_updated'])
            
            logger.info(f"Retrieved {len(markets)} last markets for verification")
            return markets
        except Exception as e:
            logger.error(f"Error getting last 3 markets: {e}")
            return []
    
    def get_market_by_id(self, market_id):
        """Получение рынка по ID из аналитической таблицы"""
        try:
            if not self.conn:
                if not self.connect():
                    return None
            
            cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT * FROM mkrt_analytic WHERE id = %s
            """, (market_id,))
            
            market = cursor.fetchone()
            cursor.close()
            return market
        except Exception as e:
            logger.error(f"Error getting market by ID: {e}")
            return None
    
    def close_connections(self):
        """Закрытие соединения с базой данных"""
        if self.conn:
            self.conn.close()
        logger.info("Database connection closed") 