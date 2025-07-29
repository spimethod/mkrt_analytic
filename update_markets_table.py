#!/usr/bin/env python3
"""
Скрипт для обновления структуры таблицы markets
Использование: python update_markets_table.py
"""

import psycopg2
import logging
from datetime import datetime
import time

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Параметры подключения к базе данных
DB_CONFIG = {
    'host': 'shinkansen.proxy.rlwy.net',
    'port': 13578,
    'database': 'railway',
    'user': 'postgres',
    'password': 'lfNeFtRHaVGdQka0wPXEfJdvxrqX0xzw'
}

def connect_to_db():
    """Подключение к базе данных"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info("✅ Успешное подключение к базе данных")
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
            );
        """, (table_name,))
        exists = cursor.fetchone()[0]
        cursor.close()
        return exists
    except Exception as e:
        logger.error(f"❌ Ошибка проверки таблицы {table_name}: {e}")
        return False

def get_table_structure(conn, table_name):
    """Получение структуры таблицы"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = %s
            ORDER BY ordinal_position;
        """, (table_name,))
        columns = cursor.fetchall()
        cursor.close()
        return columns
    except Exception as e:
        logger.error(f"❌ Ошибка получения структуры таблицы {table_name}: {e}")
        return []

def backup_existing_data(conn):
    """Резервное копирование существующих данных"""
    try:
        cursor = conn.cursor()
        
        # Проверяем, есть ли данные в таблице
        cursor.execute("SELECT COUNT(*) FROM markets")
        count = cursor.fetchone()[0]
        
        if count == 0:
            logger.info("ℹ️ Таблица markets пустая, резервное копирование не требуется")
            cursor.close()
            return True
        
        logger.info(f"📊 Найдено {count} записей в таблице markets")
        
        # Создаем резервную таблицу
        cursor.execute("""
            CREATE TABLE markets_backup AS 
            SELECT * FROM markets
        """)
        
        logger.info("✅ Резервная копия создана: markets_backup")
        cursor.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка резервного копирования: {e}")
        return False

def create_new_table(conn):
    """Создание новой таблицы markets"""
    try:
        cursor = conn.cursor()
        
        # Создаем новую таблицу с нужной структурой
        cursor.execute("""
            CREATE TABLE markets_new (
                id SERIAL PRIMARY KEY,
                question TEXT NOT NULL,
                slug VARCHAR(255) NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Создаем индексы
        cursor.execute("CREATE INDEX idx_markets_slug ON markets_new(slug)")
        cursor.execute("CREATE INDEX idx_markets_created_at ON markets_new(created_at)")
        
        logger.info("✅ Новая таблица markets_new создана")
        cursor.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания новой таблицы: {e}")
        return False

def copy_data_to_new_table(conn):
    """Копирование данных в новую таблицу"""
    try:
        cursor = conn.cursor()
        
        # Проверяем, есть ли данные для копирования
        cursor.execute("SELECT COUNT(*) FROM markets_backup")
        count = cursor.fetchone()[0]
        
        if count == 0:
            logger.info("ℹ️ Нет данных для копирования")
            cursor.close()
            return True
        
        # Копируем данные
        cursor.execute("""
            INSERT INTO markets_new (id, question, slug, created_at)
            SELECT id, question, slug, created_at
            FROM markets_backup
            WHERE id IS NOT NULL 
              AND question IS NOT NULL 
              AND slug IS NOT NULL
        """)
        
        copied_count = cursor.rowcount
        logger.info(f"✅ Скопировано {copied_count} записей в новую таблицу")
        cursor.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка копирования данных: {e}")
        return False

def replace_old_table(conn):
    """Замена старой таблицы новой"""
    try:
        cursor = conn.cursor()
        
        # Удаляем старую таблицу
        cursor.execute("DROP TABLE IF EXISTS markets")
        
        # Переименовываем новую таблицу
        cursor.execute("ALTER TABLE markets_new RENAME TO markets")
        
        logger.info("✅ Старая таблица заменена новой")
        cursor.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка замены таблицы: {e}")
        return False

def verify_new_table(conn):
    """Проверка новой таблицы"""
    try:
        cursor = conn.cursor()
        
        # Проверяем структуру
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'markets'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        
        logger.info("📋 Структура новой таблицы markets:")
        for column in columns:
            logger.info(f"  - {column[0]}: {column[1]} ({'NULL' if column[2] == 'YES' else 'NOT NULL'})")
        
        # Проверяем количество записей
        cursor.execute("SELECT COUNT(*) FROM markets")
        count = cursor.fetchone()[0]
        logger.info(f"📊 Количество записей в новой таблице: {count}")
        
        cursor.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка проверки новой таблицы: {e}")
        return False

def cleanup_backup(conn):
    """Очистка резервной копии"""
    try:
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS markets_backup")
        logger.info("✅ Резервная копия удалена")
        cursor.close()
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка удаления резервной копии: {e}")
        return False

def main():
    """Основная функция"""
    logger.info("🚀 Начинаем обновление структуры таблицы markets")
    
    # Подключаемся к базе данных
    conn = connect_to_db()
    if not conn:
        return
    
    try:
        # Проверяем существование таблицы markets
        if not check_table_exists(conn, 'markets'):
            logger.info("ℹ️ Таблица markets не существует, создаем новую")
            if create_new_table(conn):
                conn.commit()
                logger.info("✅ Новая таблица markets создана")
            return
        
        # Показываем текущую структуру
        logger.info("📋 Текущая структура таблицы markets:")
        columns = get_table_structure(conn, 'markets')
        for column in columns:
            logger.info(f"  - {column[0]}: {column[1]} ({'NULL' if column[2] == 'YES' else 'NOT NULL'})")
        
        # Спрашиваем пользователя
        logger.info("⚠️ ВНИМАНИЕ: Это действие изменит структуру таблицы markets!")
        logger.info("📋 Новая структура будет содержать только:")
        logger.info("  - id (SERIAL PRIMARY KEY)")
        logger.info("  - question (TEXT NOT NULL)")
        logger.info("  - slug (VARCHAR(255) NOT NULL UNIQUE)")
        logger.info("  - created_at (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        
        # Резервное копирование
        if not backup_existing_data(conn):
            logger.error("❌ Не удалось создать резервную копию")
            return
        
        # Создание новой таблицы
        if not create_new_table(conn):
            logger.error("❌ Не удалось создать новую таблицу")
            return
        
        # Копирование данных
        if not copy_data_to_new_table(conn):
            logger.error("❌ Не удалось скопировать данные")
            return
        
        # Замена старой таблицы
        if not replace_old_table(conn):
            logger.error("❌ Не удалось заменить таблицу")
            return
        
        # Проверка новой таблицы
        if not verify_new_table(conn):
            logger.error("❌ Ошибка проверки новой таблицы")
            return
        
        # Фиксируем изменения
        conn.commit()
        logger.info("✅ Обновление структуры таблицы markets завершено успешно!")
        
        # Очистка резервной копии
        cleanup_backup(conn)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в процессе обновления: {e}")
        conn.rollback()
    finally:
        conn.close()
        logger.info("🔌 Соединение с базой данных закрыто")

if __name__ == "__main__":
    main() 