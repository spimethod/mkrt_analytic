-- Команды для исправления БД (выполнять по одной)

-- 1. Проверяем существующие колонки
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_name = 'mkrt_analytic' 
ORDER BY ordinal_position;

-- 2. Удаляем колонку yes_order_book_total (если существует)
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'mkrt_analytic' AND column_name = 'yes_order_book_total') THEN
        ALTER TABLE mkrt_analytic DROP COLUMN yes_order_book_total;
        RAISE NOTICE 'Колонка yes_order_book_total удалена';
    ELSE
        RAISE NOTICE 'Колонка yes_order_book_total не существует';
    END IF;
END $$;

-- 3. Удаляем колонку no_order_book_total (если существует)
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'mkrt_analytic' AND column_name = 'no_order_book_total') THEN
        ALTER TABLE mkrt_analytic DROP COLUMN no_order_book_total;
        RAISE NOTICE 'Колонка no_order_book_total удалена';
    ELSE
        RAISE NOTICE 'Колонка no_order_book_total не существует';
    END IF;
END $$;

-- 4. Добавляем колонку volume (если её нет)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'mkrt_analytic' AND column_name = 'volume') THEN
        ALTER TABLE mkrt_analytic ADD COLUMN volume VARCHAR(50) DEFAULT 'New';
        RAISE NOTICE 'Колонка volume добавлена';
    ELSE
        RAISE NOTICE 'Колонка volume уже существует';
    END IF;
END $$;

-- 5. Обновляем существующие записи
UPDATE mkrt_analytic SET volume = 'New' WHERE volume IS NULL OR volume = '';

-- 6. Проверяем результат
SELECT slug, market_exists, is_boolean, yes_percentage, volume, contract_address 
FROM mkrt_analytic 
ORDER BY id DESC 
LIMIT 10; 