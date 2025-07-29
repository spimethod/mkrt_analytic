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
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-gpu'
                ]
            )
            self.page = await self.browser.new_page()
            
            # Устанавливаем user agent
            await self.page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            
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
            logger.info(f"🌐 Переходим на страницу: {url}")
            logger.info(f"⏳ Начинаем загрузку страницы...")
            await self.page.goto(url, wait_until='domcontentloaded', timeout=60000)
            logger.info(f"✅ Страница загружена: {url}")
            
            # Ждем дополнительно для загрузки контента
            logger.info("⏳ Ждем загрузки контента...")
            await asyncio.sleep(3)
            logger.info("✅ Контент загружен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка перехода на страницу {url}: {e}")
            raise
    
    async def wait_for_content(self):
        """Ожидание загрузки контента"""
        try:
            logger.info("⏳ Ждем загрузки контента...")
            await self.page.wait_for_timeout(3000)
            logger.info("✅ Контент загружен")
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