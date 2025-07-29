import logging
import asyncio
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

class BrowserManager:
    def __init__(self):
        self.browser = None
        self.page = None
        self.playwright = None
    
    def is_initialized(self):
        """Проверка инициализации браузера"""
        return self.page is not None
    
    async def init_browser(self):
        """Асинхронная инициализация браузера"""
        try:
            logger.info("🔄 Инициализируем браузер...")
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=True)
            self.page = await self.browser.new_page()
            logger.info("✅ Браузер инициализирован успешно")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации браузера: {e}")
            return False
    
    def init_browser_sync(self):
        """Синхронная инициализация браузера"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(asyncio.wait_for(self.init_browser(), timeout=60))
            except asyncio.TimeoutError:
                logger.error(f"⏰ Таймаут инициализации браузера (60 секунд)")
                return False
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"❌ Ошибка синхронной инициализации браузера: {e}")
            return False
        return True
    
    async def goto_page(self, url):
        """Переход на страницу"""
        try:
            await self.page.goto(url, wait_until='networkidle', timeout=60000)
        except Exception as e:
            logger.error(f"❌ Ошибка перехода на страницу {url}: {e}")
            raise
    
    async def wait_for_content(self):
        """Ожидание загрузки контента"""
        try:
            await self.page.wait_for_timeout(5000)
        except Exception as e:
            logger.error(f"❌ Ошибка ожидания контента: {e}")
            raise
    
    def get_page(self):
        """Получение страницы"""
        return self.page
    
    def close_browser_sync(self):
        """Синхронное закрытие браузера"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.close_browser_async())
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Ошибка синхронного закрытия браузера: {e}")
    
    async def close_browser_async(self):
        """Асинхронное закрытие браузера"""
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            logger.error(f"Ошибка закрытия браузера: {e}") 