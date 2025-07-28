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
    
    def init_browser_sync(self):
        """Синхронная инициализация браузера"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.init_browser())
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Ошибка синхронной инициализации браузера: {e}")
    
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
        """Извлечение процента Yes из '67% chance' и 'Yes 67¢'"""
        try:
            # Ищем элемент с процентом chance
            chance_elements = await self.page.query_selector_all('div:has-text("chance"), span:has-text("chance")')
            chance_percentage = None
            
            for element in chance_elements:
                text = await element.text_content()
                if text:
                    logger.info(f"📄 Найден элемент с chance: '{text.strip()}'")
                    
                    # Ищем процент в формате "67% chance"
                    percentage_match = re.search(r'(\d{1,2}(?:\.\d+)?)\s*%\s*chance', text, re.IGNORECASE)
                    if percentage_match:
                        percentage = float(percentage_match.group(1))
                        if 0 <= percentage <= 100:
                            chance_percentage = percentage
                            logger.info(f"✅ Найден процент из chance: {percentage}%")
                            break
            
            # Ищем элемент с ценой Yes
            yes_price_elements = await self.page.query_selector_all('div:has-text("Yes"), span:has-text("Yes"), button:has-text("Yes")')
            yes_price_percentage = None
            
            for element in yes_price_elements:
                text = await element.text_content()
                if text:
                    logger.info(f"📄 Найден элемент с Yes: '{text.strip()}'")
                    
                    # Ищем цену в формате "Yes 67¢"
                    price_match = re.search(r'Yes\s*(\d{1,2}(?:\.\d+)?)\s*¢', text)
                    if price_match:
                        price_cents = float(price_match.group(1))
                        if 0 <= price_cents <= 100:
                            yes_price_percentage = price_cents
                            logger.info(f"✅ Найден процент из цены Yes: {price_cents}%")
                            break
            
            # Сравниваем значения
            if chance_percentage is not None and yes_price_percentage is not None:
                if abs(chance_percentage - yes_price_percentage) <= 2:  # Допускаем разницу в 2%
                    logger.info(f"✅ Значения совпадают: {chance_percentage}% = {yes_price_percentage}%")
                    return chance_percentage
                else:
                    logger.warning(f"⚠️ Значения не совпадают: chance={chance_percentage}%, price={yes_price_percentage}%")
                    # Возвращаем значение из цены Yes, так как оно более точное
                    logger.info(f"✅ Используем значение из цены Yes: {yes_price_percentage}%")
                    return yes_price_percentage
            elif yes_price_percentage is not None:
                logger.info(f"✅ Используем значение из цены Yes: {yes_price_percentage}%")
                return yes_price_percentage
            elif chance_percentage is not None:
                logger.info(f"✅ Используем значение из chance: {chance_percentage}%")
                return chance_percentage
            
            # Если не нашли ни одного, ищем просто процент
            percentage_elements = await self.page.query_selector_all('div:has-text("%"), span:has-text("%")')
            
            for element in percentage_elements:
                text = await element.text_content()
                if text:
                    logger.info(f"📄 Найден элемент с %: '{text.strip()}'")
                    
                    # Ищем просто процент (только 1-2 цифры)
                    percentage_match = re.search(r'(\d{1,2}(?:\.\d+)?)\s*%', text)
                    if percentage_match:
                        percentage = float(percentage_match.group(1))
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