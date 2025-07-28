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
    
    def analyze_market(self, slug):
        """Синхронная обертка для анализа рынка (для совместимости)"""
        return self.get_market_data(slug)
    
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
        """Извлечение процента Yes из '67% chance'"""
        try:
            # Ищем элемент, который содержит и Volume и chance в одном блоке
            main_container = await self.page.query_selector('div:has-text("Vol"):has-text("chance")')
            if main_container:
                text = await main_container.text_content()
                logger.info(f"📄 Найден основной контейнер: '{text.strip()}'")
                
                # Ищем процент в формате "67% chance"
                percentage_match = re.search(r'(\d{1,2}(?:\.\d+)?)\s*%\s*chance', text, re.IGNORECASE)
                if percentage_match:
                    percentage = float(percentage_match.group(1))
                    if 0 <= percentage <= 100:
                        logger.info(f"✅ Найден процент Yes: {percentage}% (из основного контейнера)")
                        return percentage
            
            # Ищем конкретные значения, которые видны на странице
            specific_selectors = [
                'div:has-text("16%")',
                'span:has-text("16%")',
                'div:has-text("67%")',
                'span:has-text("67%")',
                'div:has-text("85%")',
                'span:has-text("85%")'
            ]
            
            for selector in specific_selectors:
                elements = await self.page.query_selector_all(selector)
                logger.info(f"🔍 Поиск по конкретному селектору '{selector}': найдено {len(elements)} элементов")
                
                for i, element in enumerate(elements):
                    text = await element.text_content()
                    if text:
                        logger.info(f"📄 Конкретный элемент {i+1}: '{text.strip()}'")
                        
                        # Ищем процент в формате "67% chance"
                        percentage_match = re.search(r'(\d{1,2}(?:\.\d+)?)\s*%\s*chance', text, re.IGNORECASE)
                        if percentage_match:
                            percentage = float(percentage_match.group(1))
                            if 0 <= percentage <= 100:
                                logger.info(f"✅ Найден процент Yes: {percentage}% (из конкретного элемента)")
                                return percentage
                        
                        # Ищем просто процент (только 1-2 цифры)
                        percentage_match = re.search(r'(\d{1,2}(?:\.\d+)?)\s*%', text)
                        if percentage_match:
                            percentage = float(percentage_match.group(1))
                            if 0 <= percentage <= 100:
                                logger.info(f"✅ Найден процент Yes: {percentage}%")
                                return percentage
            
            # Если не нашли в основном контейнере, ищем в других местах
            fallback_selectors = [
                'div:has-text("chance")',
                '[class*="chance"]',
                '[class*="percentage"]',
                'div:has-text("67%")',
                'span:has-text("67%")'
            ]
            
            for selector in fallback_selectors:
                elements = await self.page.query_selector_all(selector)
                logger.info(f"🔍 Поиск по fallback селектору '{selector}': найдено {len(elements)} элементов")
                
                for i, element in enumerate(elements):
                    text = await element.text_content()
                    if text:
                        logger.info(f"📄 Fallback элемент {i+1}: '{text.strip()}'")
                        
                        # Ищем процент в формате "67% chance"
                        percentage_match = re.search(r'(\d{1,2}(?:\.\d+)?)\s*%\s*chance', text, re.IGNORECASE)
                        if percentage_match:
                            percentage = float(percentage_match.group(1))
                            # Проверяем, что это разумное значение (между 0 и 100)
                            if 0 <= percentage <= 100:
                                logger.info(f"✅ Найден процент Yes: {percentage}% (из chance)")
                                return percentage
                        
                        # Ищем просто процент (только 1-2 цифры)
                        percentage_match = re.search(r'(\d{1,2}(?:\.\d+)?)\s*%', text)
                        if percentage_match:
                            percentage = float(percentage_match.group(1))
                            # Проверяем, что это разумное значение (между 0 и 100)
                            if 0 <= percentage <= 100:
                                logger.info(f"✅ Найден процент Yes: {percentage}%")
                                return percentage
            
            return 0
            
        except Exception as e:
            logger.error(f"Ошибка извлечения процента Yes: {e}")
            return 0
    
    async def extract_volume(self):
        """Извлечение Volume из '$264,156 Vol.'"""
        try:
            # Ищем элемент с Volume - более широкий поиск
            selectors = [
                '[class*="volume"]',
                '[class*="Vol"]',
                '[class*="Volume"]',
                'div:has-text("Vol")',
                'span:has-text("Vol")',
                'p:has-text("Vol")',
                '[class*="trading"]',
                '[class*="market"]'
            ]
            
            for selector in selectors:
                elements = await self.page.query_selector_all(selector)
                for element in elements:
                    text = await element.text_content()
                    if text:
                        # Ищем сумму в долларах с "Vol"
                        volume_match = re.search(r'\$([\d,]+(?:\.\d{2})?)\s*Vol', text, re.IGNORECASE)
                        if volume_match:
                            volume = volume_match.group(1).replace(',', '')
                            logger.info(f"Найден Volume: ${volume} Vol")
                            return f"${float(volume):,.2f}"
                        
                        # Ищем просто сумму в долларах
                        dollar_match = re.search(r'\$([\d,]+(?:\.\d{2})?)', text)
                        if dollar_match:
                            volume = dollar_match.group(1).replace(',', '')
                            # Проверяем, что это большая сумма (не цена)
                            if float(volume) > 1000:  # Исключаем цены
                                logger.info(f"Найден Volume: ${volume}")
                                return f"${float(volume):,.2f}"
            
            return 'New'
            
        except Exception as e:
            logger.error(f"Ошибка извлечения Volume: {e}")
            return 'New'
    
    async def extract_contract(self):
        """Извлечение контракта через Show more -> левый контракт"""
        try:
            # Ищем кнопку "Show more"
            show_more_buttons = await self.page.query_selector_all('button:has-text("Show more")')
            
            for button in show_more_buttons:
                try:
                    # Кликаем на Show more
                    await button.click()
                    await self.page.wait_for_timeout(1000)
                    
                    # Ищем левый контракт (первый контракт в списке)
                    contract_elements = await self.page.query_selector_all('[class*="contract"], [class*="address"], a[href*="0x"]')
                    
                    for element in contract_elements:
                        # Получаем href или текст
                        href = await element.get_attribute('href')
                        text = await element.text_content()
                        
                        if href and '0x' in href:
                            # Извлекаем адрес из URL
                            contract_match = re.search(r'0x[a-fA-F0-9]{40}', href)
                            if contract_match:
                                contract = contract_match.group()
                                logger.info(f"Найден контракт из href: {contract}")
                                return contract
                        
                        if text and '0x' in text:
                            # Извлекаем адрес из текста
                            contract_match = re.search(r'0x[a-fA-F0-9]{40}', text)
                            if contract_match:
                                contract = contract_match.group()
                                logger.info(f"Найден контракт из текста: {contract}")
                                return contract
                    
                    # Если не нашли, попробуем кликнуть на первый контракт
                    contract_links = await self.page.query_selector_all('a[href*="0x"], [class*="contract"]')
                    if contract_links:
                        await contract_links[0].click()
                        await self.page.wait_for_timeout(2000)
                        
                        # Получаем URL после клика
                        current_url = self.page.url
                        if '0x' in current_url:
                            contract_match = re.search(r'0x[a-fA-F0-9]{40}', current_url)
                            if contract_match:
                                contract = contract_match.group()
                                logger.info(f"Найден контракт из URL: {contract}")
                                return contract
                
                except Exception as e:
                    logger.warning(f"Ошибка при обработке Show more: {e}")
                    continue
            
            return ''
            
        except Exception as e:
            logger.error(f"Ошибка извлечения контракта: {e}")
            return '' 