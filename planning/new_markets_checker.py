import logging
import threading
from datetime import datetime
from database.markets_reader import MarketsReader
from database.analytic_writer import AnalyticWriter
from analysis.category_filter import CategoryFilter
from telegram.new_market_logger import NewMarketLogger
from active_markets.market_lifecycle_manager import MarketLifecycleManager

logger = logging.getLogger(__name__)

class NewMarketsChecker:
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.markets_reader = MarketsReader()
        self.analytic_writer = AnalyticWriter()
        self.category_filter = CategoryFilter()
        self.new_market_logger = NewMarketLogger()
        self.lifecycle_manager = MarketLifecycleManager(bot_instance)
    
    def check_new_markets(self):
        """Проверка новых рынков каждые 30 секунд"""
        try:
            markets = self.markets_reader.get_new_markets()
            
            for market in markets:
                # Проверяем, не анализируем ли уже этот рынок
                if market['id'] not in self.bot.active_markets:
                    # Проверяем категорию рынка
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