-- SQL команды для обновления структуры БД mkrt_analytic

-- 1. Удаляем ненужные колонки
ALTER TABLE mkrt_analytic DROP COLUMN IF EXISTS yes_order_book_total;
ALTER TABLE mkrt_analytic DROP COLUMN IF EXISTS no_order_book_total;

-- 2. Добавляем новую колонку volume
ALTER TABLE mkrt_analytic ADD COLUMN IF NOT EXISTS volume VARCHAR(50) DEFAULT 'New';

-- 3. Проверяем структуру таблицы
\d mkrt_analytic

-- 4. Обновляем существующие записи (устанавливаем volume = 'New' для записей без volume)
UPDATE mkrt_analytic SET volume = 'New' WHERE volume IS NULL OR volume = '';

-- 5. Проверяем результат
SELECT slug, market_exists, is_boolean, yes_percentage, volume, contract_address FROM mkrt_analytic LIMIT 10; 