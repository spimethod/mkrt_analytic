import asyncio
import logging
import re
from datetime import datetime
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

class MarketAnalyzer:
    def __init__(self):
        self.browser = None
        self.page = None
        
    async def init_browser(self):
        """Инициализация браузера"""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=True)
            self.page = await self.browser.new_page()
            return True
        except Exception as e:
            logger.error(f"Ошибка инициализации браузера: {e}")
            return False
    
    async def close_driver(self):
        """Закрытие браузера"""
        try:
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
        except Exception as e:
            logger.error(f"Ошибка закрытия браузера: {e}")
    
    def close_driver_sync(self):
        """Синхронное закрытие браузера"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.close_driver())
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Ошибка синхронного закрытия браузера: {e}")
    
    def get_market_data(self, slug):
        """Синхронная обертка для анализа рынка"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self.analyze_market(slug))
                return result
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Ошибка синхронного анализа рынка {slug}: {e}")
            return None
    
    async def analyze_market(self, slug):
        """Анализ рынка"""
        try:
            if not self.page:
                if not await self.init_browser():
                    return None
            
            # Переходим на страницу рынка
            url = f"https://polymarket.com/event/{slug}"
            await self.page.goto(url, wait_until='networkidle')
            
            # Ждем загрузки контента
            await self.page.wait_for_timeout(3000)
            
            # Извлекаем данные
            market_data = await self.extract_market_data()
            
            return market_data
            
        except Exception as e:
            logger.error(f"Ошибка анализа рынка {slug}: {e}")
            return None
    
    async def extract_market_data(self):
        """Извлечение данных рынка"""
        try:
            data = {
                'market_exists': True,
                'is_boolean': True,
                'yes_percentage': 0,
                'volume': 'New',
                'contract_address': '',
                'status': 'в работе'
            }
            
            # Извлекаем процент Yes
            yes_percentage = await self.extract_yes_percentage()
            if yes_percentage:
                data['yes_percentage'] = yes_percentage
            
            # Извлекаем Volume
            volume = await self.extract_volume()
            if volume:
                data['volume'] = volume
            
            # Извлекаем контракт
            contract = await self.extract_contract()
            if contract:
                data['contract_address'] = contract
            
            logger.info(f"Извлеченные данные: {data}")
            return data
            
        except Exception as e:
            logger.error(f"Ошибка извлечения данных: {e}")
            return None
    
    async def extract_yes_percentage(self):
        """Извлечение процента Yes"""
        try:
            # Ищем элементы с ценами Yes
            yes_elements = await self.page.query_selector_all('button:has-text("Yes")')
            
            for element in yes_elements:
                text = await element.text_content()
                if text:
                    # Ищем процент в тексте
                    percentage_match = re.search(r'(\d+(?:\.\d+)?)\s*%', text)
                    if percentage_match:
                        percentage = float(percentage_match.group(1))
                        logger.info(f"Найден процент Yes: {percentage}%")
                        return percentage
                    
                    # Ищем центы
                    cents_match = re.search(r'(\d+(?:\.\d+)?)\s*¢', text)
                    if cents_match:
                        cents = float(cents_match.group(1))
                        # Конвертируем центы в проценты
                        percentage = cents
                        logger.info(f"Найдены центы Yes: {cents}¢ -> {percentage}%")
                        return percentage
            
            return 0
            
        except Exception as e:
            logger.error(f"Ошибка извлечения процента Yes: {e}")
            return 0
    
    async def extract_volume(self):
        """Извлечение Volume"""
        try:
            # Ищем элементы с Volume
            volume_elements = await self.page.query_selector_all('[class*="volume"], [class*="Volume"]')
            
            for element in volume_elements:
                text = await element.text_content()
                if text:
                    # Ищем сумму в долларах
                    dollar_match = re.search(r'\$([\d,]+(?:\.\d{2})?)', text)
                    if dollar_match:
                        volume = dollar_match.group(1).replace(',', '')
                        logger.info(f"Найден Volume: ${volume}")
                        return f"${float(volume):,.2f}"
            
            return 'New'
            
        except Exception as e:
            logger.error(f"Ошибка извлечения Volume: {e}")
            return 'New'
    
    async def extract_contract(self):
        """Извлечение адреса контракта"""
        try:
            # Ищем контракт на странице
            contract_elements = await self.page.query_selector_all('code, pre, [class*="contract"], [class*="address"]')
            
            for element in contract_elements:
                text = await element.text_content()
                if text:
                    # Ищем адрес контракта
                    contract_match = re.search(r'0x[a-fA-F0-9]{40}', text)
                    if contract_match:
                        contract = contract_match.group()
                        logger.info(f"Найден контракт: {contract}")
                        return contract
            
            return ''
            
        except Exception as e:
            logger.error(f"Ошибка извлечения контракта: {e}")
            return '' 