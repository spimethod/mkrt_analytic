import logging
import threading
from datetime import datetime, timedelta, timezone
from database.markets_reader import MarketsReader
from database.analytic_writer import AnalyticWriter
from analysis.category_filter import CategoryFilter
from analysis.category_validator import CategoryValidator
from telegram.new_market_logger import NewMarketLogger
from active_markets.market_lifecycle_manager import MarketLifecycleManager
from config.config_loader import ConfigLoader

logger = logging.getLogger(__name__)

class NewMarketsChecker:
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.markets_reader = MarketsReader()
        self.analytic_writer = AnalyticWriter()
        self.category_filter = CategoryFilter()
        self.category_validator = CategoryValidator()
        self.new_market_logger = NewMarketLogger()
        self.lifecycle_manager = MarketLifecycleManager(bot_instance)
        self.config = ConfigLoader()
    
    def check_new_markets(self):
        """Проверка новых рынков каждые 30 секунд"""
        try:
            # Получаем только рынки, которые еще не анализировались
            markets = self.markets_reader.get_new_markets_after_time(
                datetime.now(timezone.utc) - timedelta(minutes=self.config.get_mkrt_analytic_time_min())
            )
            
            if not markets:
                # Нет новых рынков для анализа
                logger.debug("ℹ️ Новых рынков для анализа не найдено")
                return
            
            logger.info(f"🔍 Найдено {len(markets)} новых рынков для проверки")
            
            for market in markets:
                # Проверяем, не анализируем ли уже этот рынок
                if market['id'] not in self.bot.active_markets:
                    # Проверяем, не анализировался ли уже этот рынок в прошлом
                    if self.analytic_writer.market_exists_in_analytic(market['slug']):
                        logger.debug(f"ℹ️ Рынок {market['slug']} уже анализировался ранее, пропускаем")
                        continue
                    
                    # Проверяем категорию рынка (Крипто/Спорт)
                    category_validation = self.category_validator.validate_market_category(market['slug'])
                    if not category_validation['is_valid']:
                        logger.warning(f"⚠️ Рынок {market['slug']} заблокирован: {category_validation['status']}")
                        
                        # Добавляем рынок в аналитическую базу с заблокированным статусом
                        market_id = self.analytic_writer.insert_market_to_analytic(market)
                        if market_id:
                            # Обновляем статус на заблокированный
                            self.analytic_writer.update_market_status(market_id, category_validation['status'])
                            logger.info(f"✅ Рынок {market['slug']} добавлен с статусом: {category_validation['status']}")
                        continue
                    
                    # Проверяем булевость рынка
                    category_check = self.category_filter.check_category(market['slug'])
                    if not category_check['is_boolean']:
                        logger.info(f"⚠️ Рынок {market['slug']} не подходит по категории, пропускаем")
                        continue
                    
                    # Добавляем рынок в аналитическую базу
                    market_id = self.analytic_writer.insert_market_to_analytic(market)
                    
                    if market_id:
                        # Начинаем анализ рынка
                        self.lifecycle_manager.start_market_analysis(market_id, market)
                        
                        # Логируем новый рынок
                        self.new_market_logger.log_new_market(market)
                        logger.info(f"Started analysis for market: {market['slug']}")
                        
                        # Запускаем анализ в отдельном потоке
                        analysis_thread = threading.Thread(
                            target=self.lifecycle_manager.analyze_market_continuously,
                            args=(market_id, market['slug'])
                        )
                        analysis_thread.daemon = True
                        analysis_thread.start()
        
        except Exception as e:
            error_msg = f"Error checking new markets: {e}"
            logger.error(error_msg)
            from telegram.error_logger import ErrorLogger
            error_logger = ErrorLogger()
            error_logger.log_error(error_msg) 