import logging
from datetime import datetime, timezone
from database.database_connection import DatabaseConnection

logger = logging.getLogger(__name__)

class AnalyticWriter:
    def __init__(self):
        self.db_connection = DatabaseConnection()
    
    def insert_market_to_analytic(self, market_data):
        """Добавление рынка в аналитическую таблицу mkrt_analytic"""
        try:
            logger.info(f"🔄 Попытка вставки рынка: {market_data.get('slug', 'unknown')}")
            
            conn = self.db_connection.get_connection()
            if not conn:
                logger.error("❌ Не удалось подключиться к БД")
                return None
            
            # Проверяем, существует ли уже рынок с таким slug
            if self.market_exists_in_analytic(market_data['slug']):
                logger.info(f"ℹ️ Рынок {market_data['slug']} уже существует в аналитической БД")
                # Получаем ID существующего рынка
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM mkrt_analytic WHERE slug = %s", (market_data['slug'],))
                result = cursor.fetchone()
                cursor.close()
                return result[0] if result else None
            
            logger.info(f"📝 Вставляем новый рынок: {market_data['slug']}")
            
            cursor = conn.cursor()
            
            # Подготавливаем данные для вставки
            current_time = datetime.now(timezone.utc)
            insert_data = (
                market_data['id'],
                market_data['question'],
                current_time,  # created_at
                True,  # active по умолчанию True
                True,  # enable_order_book по умолчанию True
                market_data['slug'],
                market_data.get('market_exists', True),
                market_data.get('is_boolean', True),
                market_data.get('yes_percentage', 0),
                market_data.get('volume', 'New'),
                market_data.get('contract_address', ''),
                market_data.get('status', 'в работе'),
                current_time,  # last_updated
                current_time   # created_at_analytic
            )
            
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
                conn.commit()
                cursor.close()
                logger.info(f"✅ Рынок {market_data['slug']} успешно вставлен/обновлен! ID: {market_id}")
                return market_id
            else:
                logger.error("❌ Не удалось получить ID вставленной записи")
                conn.rollback()
                cursor.close()
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка вставки рынка в аналитическую БД: {e}")
            if conn:
                conn.rollback()
            return None
    
    def market_exists_in_analytic(self, slug):
        """Проверка существования рынка в аналитической таблице по slug"""
        try:
            conn = self.db_connection.get_connection()
            if not conn:
                return False
            
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM mkrt_analytic WHERE slug = %s", (slug,))
            result = cursor.fetchone()
            cursor.close()
            
            return result is not None
        except Exception as e:
            logger.error(f"Error checking market existence: {e}")
            return False
    
    def update_market_status(self, market_id, status):
        """Обновление статуса рынка"""
        try:
            logger.info(f"🔄 Обновление статуса рынка ID: {market_id} на '{status}'")
            
            conn = self.db_connection.get_connection()
            if not conn:
                logger.error("❌ Не удалось подключиться к БД")
                return False
            
            cursor = conn.cursor()
            current_time = datetime.now(timezone.utc)
            
            cursor.execute("""
                UPDATE mkrt_analytic 
                SET status = %s, last_updated = %s
                WHERE id = %s
            """, (status, current_time, market_id))
            
            conn.commit()
            cursor.close()
            
            logger.info(f"✅ Статус рынка ID: {market_id} успешно обновлен на '{status}'")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления статуса рынка: {e}")
            if conn:
                conn.rollback()
            return False 