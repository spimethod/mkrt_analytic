import logging
import threading
from datetime import datetime, timedelta, timezone
from database.markets_reader import MarketsReader
from database.analytic_writer import AnalyticWriter
from analysis.category_filter import CategoryFilter
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
        self.new_market_logger = NewMarketLogger()
        self.lifecycle_manager = MarketLifecycleManager(bot_instance)
        self.config = ConfigLoader()
    
    def check_new_markets(self):
        """Проверка новых рынков каждые 30 секунд"""
        try:
            markets = self.markets_reader.get_new_markets()
            
            for market in markets:
                # Проверяем, не анализируем ли уже этот рынок
                if market['id'] not in self.bot.active_markets:
                    # Проверяем время создания рынка
                    market_created_at = market['created_at']
                    if market_created_at.tzinfo is None:
                        market_created_at = market_created_at.replace(tzinfo=timezone.utc)
                    
                    current_time = datetime.now(timezone.utc)
                    time_diff_minutes = (current_time - market_created_at).total_seconds() / 60
                    
                    # Проверяем, не слишком ли старый рынок
                    max_age_minutes = self.config.get_mkrt_analytic_time_min()
                    if time_diff_minutes > max_age_minutes:
                        logger.info(f"⚠️ Рынок {market['slug']} слишком старый ({time_diff_minutes:.1f} мин), пропускаем")
                        continue
                    
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