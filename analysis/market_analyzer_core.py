import logging
import asyncio
import threading
from analysis.browser_manager import BrowserManager
from analysis.data_extractor import DataExtractor
from analysis.category_filter import CategoryFilter
from analysis.sync_market_analyzer import SyncMarketAnalyzer

logger = logging.getLogger(__name__)

class MarketAnalyzerCore:
    def __init__(self):
        self.browser_manager = BrowserManager()
        self.data_extractor = DataExtractor()
        self.category_filter = CategoryFilter()
        self.sync_analyzer = SyncMarketAnalyzer()
    
    def analyze_market(self, slug):
        """Синхронная обертка для анализа рынка"""
        try:
            logger.info(f"🔄 Начинаем синхронный анализ рынка: {slug}")
            
            # Используем синхронный анализатор в отдельном потоке
            # чтобы не блокировать асинхронный код
            result = None
            exception = None
            
            def run_sync_analysis():
                nonlocal result, exception
                try:
                    result = self.sync_analyzer.analyze_market(slug)
                except Exception as e:
                    exception = e
            
            # Запускаем синхронный анализ в отдельном потоке
            thread = threading.Thread(target=run_sync_analysis)
            thread.start()
            thread.join(timeout=120)  # Таймаут 120 секунд
            
            if thread.is_alive():
                logger.error(f"⏰ Таймаут синхронного анализа рынка {slug} (120 секунд)")
                return None
            
            if exception:
                logger.error(f"❌ Ошибка синхронного анализа рынка {slug}: {exception}")
                return None
            
            if result:
                logger.info(f"✅ Синхронный анализ рынка {slug} завершен успешно")
                return result
            else:
                logger.warning(f"⚠️ Синхронный анализ рынка {slug} не вернул данных")
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка синхронного анализа рынка {slug}: {e}")
            return None
    
    async def analyze_market_async(self, slug):
        """Асинхронный анализ рынка"""
        try:
            if not self.browser_manager.is_initialized():
                if not await self.browser_manager.init_browser():
                    return None
            
            # Переходим на страницу рынка
            url = f"https://polymarket.com/event/{slug}"
            logger.info(f"🌐 Переходим на страницу: {url}")
            try:
                await self.browser_manager.goto_page(url)
            except Exception as e:
                logger.error(f"❌ Ошибка перехода на страницу {url}: {e}")
                return None
            
            # Ждем загрузки контента
            logger.info(f"⏳ Ждем загрузки контента...")
            try:
                await self.browser_manager.wait_for_content()
            except Exception as e:
                logger.error(f"❌ Ошибка ожидания контента: {e}")
                return None
            
            # Извлекаем данные
            logger.info(f"🔍 Начинаем извлечение данных...")
            market_data = await self.data_extractor.extract_market_data(self.browser_manager.get_page())
            
            if market_data:
                logger.info(f"✅ Анализ рынка {slug} завершен успешно")
                return market_data
            else:
                logger.warning(f"⚠️ Не удалось извлечь данные для {slug}")
                return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа рынка {slug}: {e}")
            return None
    
    def check_market_category_sync(self, slug):
        """Синхронная проверка категории рынка"""
        return self.category_filter.check_category(slug)
    
    def close_driver(self):
        """Закрытие браузера"""
        return self.browser_manager.close_browser_sync() 