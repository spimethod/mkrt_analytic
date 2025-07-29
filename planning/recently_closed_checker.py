import logging
import threading
import time
from datetime import datetime, timedelta
from database.active_markets_reader import ActiveMarketsReader
from database.analytic_updater import AnalyticUpdater
from analysis.category_filter import CategoryFilter
from active_markets.market_lifecycle_manager import MarketLifecycleManager

logger = logging.getLogger(__name__)

class RecentlyClosedChecker:
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.reader = ActiveMarketsReader()
        self.updater = AnalyticUpdater()
        self.category_filter = CategoryFilter()
        self.lifecycle_manager = MarketLifecycleManager(bot_instance)
    
    def check_recently_closed_markets(self):
        """Проверка недавно закрытых рынков на предмет ошибочного закрытия"""
        try:
            logger.info("🔍 Проверяем недавно закрытые рынки...")
            
            # Получаем рынки, закрытые в последние 10 минут
            recently_closed = self.reader.get_recently_closed_markets()
            
            if not recently_closed:
                logger.debug("ℹ️ Нет недавно закрытых рынков для проверки")
                return
            
            logger.info(f"📊 Найдено {len(recently_closed)} недавно закрытых рынков")
            
            current_time = datetime.now()
            
            for market in recently_closed:
                try:
                    market_id = market['id']
                    slug = market['slug']
                    created_at = market['created_at_analytic']
                    
                    # Проверяем, не истекло ли время анализа
                    analysis_end_time_from_created = created_at + timedelta(minutes=60)  # 60 минут по умолчанию
                    remaining_time_from_created = (analysis_end_time_from_created - current_time).total_seconds() / 60
                    
                    if current_time < analysis_end_time_from_created:
                        logger.warning(f"⚠️ Рынок {slug} был ошибочно закрыт! Время еще не истекло")
                        
                        # Проверяем категорию рынка с таймаутом
                        try:
                            category_check = self.category_filter.check_category(slug)
                            if not category_check['is_boolean']:
                                logger.info(f"⚠️ Рынок {slug} не подходит по категории, оставляем закрытым")
                                continue
                        except Exception as e:
                            logger.error(f"❌ Ошибка проверки категории для {slug}: {e}")
                            continue
                        
                        # Рынок подходит для анализа - восстанавливаем
                        logger.info(f"✅ Восстанавливаем ошибочно закрытый рынок {slug}, осталось {remaining_time_from_created:.1f} минут")
                        
                        # Обновляем статус
                        update_success = self.updater.update_market_analysis(market_id, {'status': 'в работе'})
                        if not update_success:
                            logger.error(f"❌ Не удалось обновить статус рынка {slug}")
                            continue
                        
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
                        
                        logger.info(f"✅ Рынок {slug} восстановлен после ошибочного закрытия")
                    else:
                        logger.debug(f"ℹ️ Рынок {slug} правильно закрыт, время истекло")
                        
                except Exception as e:
                    logger.error(f"❌ Ошибка обработки рынка {market.get('slug', 'unknown')}: {e}")
                    continue
            
            logger.info("✅ Проверка недавно закрытых рынков завершена")
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки недавно закрытых рынков: {e}") 