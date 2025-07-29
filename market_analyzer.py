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
    
    def close_driver(self):
        """Синхронное закрытие браузера"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.close_driver_async())
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Ошибка синхронного закрытия браузера: {e}")
    
    def close_driver_sync(self):
        """Синхронное закрытие браузера (для совместимости)"""
        return self.close_driver()
    
    async def close_driver_async(self):
        """Асинхронное закрытие браузера"""
        try:
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
        except Exception as e:
            logger.error(f"Ошибка закрытия браузера: {e}")
    
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
    
    def get_market_data(self, slug):
        """Синхронная обертка для анализа рынка"""
        try:
            # Инициализируем браузер, если он не инициализирован
            if not self.page:
                logger.info(f"🔄 Инициализируем браузер для анализа {slug}...")
                if not self.init_browser_sync():
                    logger.error(f"❌ Не удалось инициализировать браузер для {slug}")
                    return None
                logger.info(f"✅ Браузер инициализирован для {slug}")
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Добавляем таймаут для анализа
                result = loop.run_until_complete(asyncio.wait_for(self.analyze_market(slug), timeout=120))
                return result
            except asyncio.TimeoutError:
                logger.error(f"⏰ Таймаут анализа рынка {slug} (120 секунд)")
                return None
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"❌ Ошибка синхронного анализа рынка {slug}: {e}")
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
            logger.info(f"🌐 Переходим на страницу: {url}")
            await self.page.goto(url, wait_until='networkidle', timeout=60000)  # Увеличиваем таймаут до 60 секунд
            
            # Ждем загрузки контента
            logger.info(f"⏳ Ждем загрузки контента...")
            await self.page.wait_for_timeout(5000)  # Увеличиваем ожидание до 5 секунд
            
            # Извлекаем данные
            logger.info(f"🔍 Начинаем извлечение данных...")
            market_data = await self.extract_market_data()
            
            return market_data
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа рынка {slug}: {e}")
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
            
            # Проверяем категорию рынка
            category_check = await self.check_market_category()
            if not category_check['is_boolean']:
                data['is_boolean'] = False
                data['reason'] = category_check['reason']
                return data
            
            # Извлекаем процент Yes
            logger.info(f"🔍 Извлекаем процент Yes для рынка...")
            yes_percentage = await self.extract_yes_percentage()
            if yes_percentage:
                data['yes_percentage'] = yes_percentage
                logger.info(f"✅ Процент Yes извлечен: {yes_percentage}%")
            else:
                logger.warning(f"⚠️ Не удалось извлечь процент Yes")
            
            # Извлекаем Volume
            logger.info(f"🔍 Извлекаем Volume для рынка...")
            volume = await self.extract_volume()
            if volume:
                data['volume'] = volume
                logger.info(f"✅ Volume извлечен: {volume}")
            else:
                logger.warning(f"⚠️ Не удалось извлечь Volume")
            
            # Извлекаем контракт
            logger.info(f"🔍 Извлекаем контракт для рынка...")
            contract = await self.extract_contract()
            if contract:
                data['contract_address'] = contract
                logger.info(f"✅ Контракт извлечен: {contract[:20]}...")
            else:
                logger.warning(f"⚠️ Не удалось извлечь контракт")
            
            logger.info(f"📊 Итоговые извлеченные данные: {data}")
            return data
            
        except Exception as e:
            logger.error(f"Ошибка извлечения данных: {e}")
            return None
    
    async def check_market_category(self):
        """Проверка категории рынка"""
        try:
            # Ищем элементы категорий
            category_elements = await self.page.query_selector_all('[class*="category"], [class*="tag"], span:has-text("Sports"), span:has-text("Crypto"), span:has-text("Politics"), span:has-text("Tech"), span:has-text("Culture"), span:has-text("World"), span:has-text("Economy")')
            
            for element in category_elements:
                text = await element.text_content()
                if text:
                    text_lower = text.lower().strip()
                    
                    # Проверяем категории, которые мы не анализируем
                    if any(cat in text_lower for cat in ['sports', 'crypto', 'cryptocurrency', 'bitcoin', 'ethereum']):
                        logger.info(f"⚠️ Рынок относится к категории: {text}")
                        return {
                            'is_boolean': False,
                            'reason': f'category_{text_lower}'
                        }
            
            # Если не нашли исключающие категории, считаем булевым
            return {
                'is_boolean': True,
                'reason': 'boolean'
            }
            
        except Exception as e:
            logger.error(f"Ошибка проверки категории: {e}")
            # В случае ошибки считаем булевым
            return {
                'is_boolean': True,
                'reason': 'boolean'
            }
    
    async def extract_yes_percentage(self):
        """Извлечение процента Yes из '67% chance' и 'Yes 67¢'"""
        try:
            # Ищем элемент с процентом chance
            chance_elements = await self.page.query_selector_all('div:has-text("chance"), span:has-text("chance")')
            chance_percentage = None
            
            for element in chance_elements:
                text = await element.text_content()
                if text:
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
                            if float(volume) > 1000: # Filter out small dollar values that might be prices
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
                        href = await element.get_attribute('href')
                        text = await element.text_content()
                        
                        if href and '0x' in href:
                            contract_match = re.search(r'0x[a-fA-F0-9]{40}', href)
                            if contract_match:
                                contract = contract_match.group()
                                logger.info(f"Найден контракт из href: {contract}")
                                return contract
                        
                        if text and '0x' in text:
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