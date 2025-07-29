import logging
import asyncio
from analysis.browser_manager import BrowserManager
from analysis.data_extractor import DataExtractor
from analysis.category_filter import CategoryFilter

logger = logging.getLogger(__name__)

class MarketAnalyzerCore:
    def __init__(self):
        self.browser_manager = BrowserManager()
        self.data_extractor = DataExtractor()
        self.category_filter = CategoryFilter()
    
    def analyze_market(self, slug):
        """Синхронная обертка для анализа рынка"""
        try:
            # Инициализируем браузер, если он не инициализирован
            if not self.browser_manager.is_initialized():
                logger.info(f"🔄 Инициализируем браузер для анализа {slug}...")
                if not self.browser_manager.init_browser_sync():
                    logger.error(f"❌ Не удалось инициализировать браузер для {slug}")
                    return None
                logger.info(f"✅ Браузер инициализирован для {slug}")
            
            # Используем существующий event loop или создаем новый
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            try:
                # Добавляем таймаут для анализа
                result = loop.run_until_complete(asyncio.wait_for(self.analyze_market_async(slug), timeout=120))
                return result
            except asyncio.TimeoutError:
                logger.error(f"⏰ Таймаут анализа рынка {slug} (120 секунд)")
                return None
            except Exception as e:
                logger.error(f"❌ Ошибка анализа рынка {slug}: {e}")
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
            await self.browser_manager.goto_page(url)
            
            # Ждем загрузки контента
            logger.info(f"⏳ Ждем загрузки контента...")
            await self.browser_manager.wait_for_content()
            
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