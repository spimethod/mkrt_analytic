-- Создание таблицы для аналитической базы данных
CREATE TABLE IF NOT EXISTS mkrt_analytic (
    id SERIAL PRIMARY KEY,
    polymarket_id INTEGER UNIQUE NOT NULL,
    question TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    active BOOLEAN NOT NULL,
    enable_order_book BOOLEAN NOT NULL,
    slug VARCHAR(255) NOT NULL,
    
    -- Данные анализа
    market_exists BOOLEAN DEFAULT FALSE,
    is_boolean BOOLEAN DEFAULT FALSE,
    yes_percentage DECIMAL(5,2) DEFAULT 0,
    yes_order_book_total DECIMAL(15,2) DEFAULT 0,
    no_order_book_total DECIMAL(15,2) DEFAULT 0,
    contract_address VARCHAR(42) DEFAULT '',
    status VARCHAR(50) DEFAULT 'в работе',
    
    -- Метаданные
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at_analytic TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание индексов для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_mkrt_analytic_slug ON mkrt_analytic(slug);
CREATE INDEX IF NOT EXISTS idx_mkrt_analytic_status ON mkrt_analytic(status);
CREATE INDEX IF NOT EXISTS idx_mkrt_analytic_polymarket_id ON mkrt_analytic(polymarket_id);
CREATE INDEX IF NOT EXISTS idx_mkrt_analytic_last_updated ON mkrt_analytic(last_updated);

-- Комментарии к таблице
COMMENT ON TABLE mkrt_analytic IS 'Таблица для хранения аналитических данных о рынках Polymarket';
COMMENT ON COLUMN mkrt_analytic.polymarket_id IS 'ID рынка из базы Polymarket';
COMMENT ON COLUMN mkrt_analytic.question IS 'Вопрос рынка';
COMMENT ON COLUMN mkrt_analytic.created_at IS 'Дата создания рынка';
COMMENT ON COLUMN mkrt_analytic.active IS 'Активен ли рынок';
COMMENT ON COLUMN mkrt_analytic.enable_order_book IS 'Включен ли ордер бук';
COMMENT ON COLUMN mkrt_analytic.slug IS 'Slug рынка для URL';
COMMENT ON COLUMN mkrt_analytic.market_exists IS 'Существует ли рынок (действителен ли адрес)';
COMMENT ON COLUMN mkrt_analytic.is_boolean IS 'Булевый ли рынок (Да/Нет)';
COMMENT ON COLUMN mkrt_analytic.yes_percentage IS 'Текущий процент шанса Yes';
COMMENT ON COLUMN mkrt_analytic.yes_order_book_total IS 'Общая сумма в ордер бук по Yes';
COMMENT ON COLUMN mkrt_analytic.no_order_book_total IS 'Общая сумма в ордер бук по No';
COMMENT ON COLUMN mkrt_analytic.contract_address IS 'Адрес контракта (0x...)';
COMMENT ON COLUMN mkrt_analytic.status IS 'Статус: в работе/закрыт';
COMMENT ON COLUMN mkrt_analytic.last_updated IS 'Время последнего обновления';
COMMENT ON COLUMN mkrt_analytic.created_at_analytic IS 'Время создания записи в аналитической базе'; 