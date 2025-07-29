import logging
from datetime import datetime, timezone
from database.database_connection import DatabaseConnection

logger = logging.getLogger(__name__)

class AnalyticUpdater:
    def __init__(self):
        self.db_connection = DatabaseConnection()
    
    def update_market_analysis(self, market_id, analysis_data):
        """Обновление данных анализа рынка"""
        try:
            logger.info(f"🔄 Обновление анализа для рынка ID: {market_id}")
            
            conn = self.db_connection.get_connection()
            if not conn:
                logger.error("❌ Не удалось подключиться к БД")
                return False
            
            cursor = conn.cursor()
            current_time = datetime.now(timezone.utc)
            
            # Подготавливаем данные для обновления
            update_fields = []
            update_values = []
            
            if 'yes_percentage' in analysis_data:
                update_fields.append("yes_percentage = %s")
                update_values.append(analysis_data['yes_percentage'])
            
            if 'volume' in analysis_data:
                update_fields.append("volume = %s")
                update_values.append(analysis_data['volume'])
            
            if 'contract_address' in analysis_data:
                update_fields.append("contract_address = %s")
                update_values.append(analysis_data['contract_address'])
            
            if 'status' in analysis_data:
                update_fields.append("status = %s")
                update_values.append(analysis_data['status'])
            
            # Всегда обновляем last_updated
            update_fields.append("last_updated = %s")
            update_values.append(current_time)
            
            if update_fields:
                update_values.append(market_id)  # для WHERE clause
                
                query = f"""
                    UPDATE mkrt_analytic 
                    SET {', '.join(update_fields)}
                    WHERE id = %s
                """
                
                cursor.execute(query, update_values)
                conn.commit()
                cursor.close()
                
                logger.info(f"✅ Анализ рынка ID: {market_id} успешно обновлен")
                return True
            else:
                logger.warning(f"⚠️ Нет данных для обновления рынка ID: {market_id}")
                cursor.close()
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка обновления анализа рынка: {e}")
            if conn:
                conn.rollback()
            return False 