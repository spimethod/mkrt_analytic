import logging
import threading
from datetime import datetime
from database.active_markets_reader import ActiveMarketsReader
from database.analytic_updater import AnalyticUpdater
from analysis.category_filter import CategoryFilter
from active_markets.market_lifecycle_manager import MarketLifecycleManager

logger = logging.getLogger(__name__)

class StuckMarketsRestorer:
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.reader = ActiveMarketsReader()
        self.updater = AnalyticUpdater()
        self.category_filter = CategoryFilter()
        self.lifecycle_manager = MarketLifecycleManager(bot_instance)
    
    def restore_stuck_markets(self):
        """Восстановление зависших рынков при запуске"""
        try:
            logger.info("🔄 Восстанавливаем зависшие рынки...")
            
            # Получаем рынки со статусом "в работе"
            in_progress_markets = self.reader.get_in_progress_markets()
            
            for market in in_progress_markets:
                market_id = market['id']
                slug = market['slug']
                
                logger.info(f"🔄 Восстанавливаем рынок: {slug}")
                
                # Проверяем категорию рынка
                try:
                    category_check = self.category_filter.check_category(slug)
                    if not category_check['is_boolean']:
                        logger.info(f"⚠️ Рынок {slug} не подходит по категории, пропускаем")
                        self.updater.update_market_analysis(market_id, {'status': 'закрыт'})
                        continue
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось проверить категорию для {slug}: {e}")
                    # Продолжаем анализ даже при ошибке проверки категории
                
                # Добавляем в активные рынки
                self.bot.active_markets[market_id] = {
                    'start_time': datetime.now(),
                    'last_log': datetime.now(),
                    'slug': slug,
                    'question': market.get('question', f"Market: {slug}")
                }
                
                # Запускаем анализ в отдельном потоке
                analysis_thread = threading.Thread(
                    target=self.lifecycle_manager.analyze_market_continuously_restored,
                    args=(market_id, slug)
                )
                analysis_thread.daemon = True
                analysis_thread.start()
                
                logger.info(f"✅ Рынок {slug} восстановлен")
            
            logger.info(f"✅ Восстановление завершено, активных рынков: {len(self.bot.active_markets)}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка восстановления зависших рынков: {e}") 