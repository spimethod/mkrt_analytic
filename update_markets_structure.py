#!/usr/bin/env python3
"""
Скрипт для обновления структуры таблицы markets
Запускается при деплое бота
"""

import psycopg2
import logging
from datetime import datetime
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Параметры подключения к базе данных
DB_CONFIG = {
    'host': os.getenv('PGHOST', 'shinkansen.proxy.rlwy.net'),
    'port': os.getenv('PGPORT', '13578'),
    'database': os.getenv('PGDATABASE', 'railway'),
    'user': os.getenv('PGUSER', 'postgres'),
    'password': os.getenv('PGPASSWORD', 'lfNeFtRHaVGdQka0wPXEfJdvxrqX0xzw')
}

def connect_to_db():
    """Подключение к базе данных"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info("✅ Подключение к базе данных успешно")
        return conn
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к базе данных: {e}")
        return None

def check_table_exists(conn, table_name):
    """Проверка существования таблицы"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = %s
            )
        """, (table_name,))
        exists = cursor.fetchone()[0]
        cursor.close()
        return exists
    except Exception as e:
        logger.error(f"❌ Ошибка проверки существования таблицы {table_name}: {e}")
        return False

def get_table_structure(conn, table_name):
    """Получение структуры таблицы"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = %s 
            ORDER BY ordinal_position
        """, (table_name,))
        columns = cursor.fetchall()
        cursor.close()
        return columns
    except Exception as e:
        logger.error(f"❌ Ошибка получения структуры таблицы {table_name}: {e}")
        return []

def update_markets_table_structure():
    """Обновление структуры таблицы markets"""
    try:
        logger.info("🔄 Начинаем обновление структуры таблицы markets")
        
        # Подключаемся к базе данных
        conn = connect_to_db()
        if not conn:
            return False
        
        # Проверяем существование таблицы
        if not check_table_exists(conn, 'markets'):
            logger.error("❌ Таблица markets не существует")
            conn.close()
            return False
        
        # Получаем текущую структуру
        current_columns = get_table_structure(conn, 'markets')
        column_names = [col[0] for col in current_columns]
        logger.info(f"📊 Текущая структура таблицы markets: {column_names}")
        
        # Проверяем, нужна ли обновление
        if set(column_names) == {'id', 'question', 'slug', 'created_at'}:
            logger.info("✅ Структура таблицы markets уже обновлена")
            conn.close()
            return True
        
        logger.info("🔄 Создаем резервную копию...")
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS markets_backup AS SELECT * FROM markets")
        logger.info("✅ Резервная копия создана")
        
        # Создаем новую таблицу
        logger.info("🔄 Создаем новую таблицу...")
        cursor.execute("""
            CREATE TABLE markets_new (
                id SERIAL PRIMARY KEY,
                question TEXT NOT NULL,
                slug VARCHAR(255) NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX idx_markets_slug ON markets_new(slug)")
        cursor.execute("CREATE INDEX idx_markets_created_at ON markets_new(created_at)")
        logger.info("✅ Новая таблица создана")
        
        # Копируем данные
        logger.info("🔄 Копируем данные...")
        cursor.execute("""
            INSERT INTO markets_new (id, question, slug, created_at)
            SELECT id, question, slug, created_at FROM markets
        """)
        logger.info("✅ Данные скопированы")
        
        # Заменяем старую таблицу
        logger.info("🔄 Заменяем старую таблицу...")
        cursor.execute("DROP TABLE markets")
        cursor.execute("ALTER TABLE markets_new RENAME TO markets")
        logger.info("✅ Таблица заменена")
        
        # Проверяем новую структуру
        new_columns = get_table_structure(conn, 'markets')
        new_column_names = [col[0] for col in new_columns]
        logger.info(f"✅ Новая структура таблицы markets: {new_column_names}")
        
        cursor.close()
        conn.commit()
        conn.close()
        logger.info("🎉 Обновление структуры таблицы markets завершено успешно!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка обновления структуры таблицы: {e}")
        if 'conn' in locals() and conn:
            conn.rollback()
            conn.close()
        return False

def main():
    """Главная функция"""
    logger.info("🚀 Запуск скрипта обновления структуры таблицы markets")
    
    success = update_markets_table_structure()
    
    if success:
        logger.info("✅ Скрипт выполнен успешно")
        return 0
    else:
        logger.error("❌ Скрипт завершился с ошибкой")
        return 1

if __name__ == "__main__":
    exit(main()) 