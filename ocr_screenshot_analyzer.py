#!/usr/bin/env python3
"""
OCR анализатор: Playwright + pytesseract + RegEx
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from playwright.async_api import async_playwright
from config import POLYMARKET_BASE_URL

logger = logging.getLogger(__name__)

class OCRScreenshotAnalyzer:
    def __init__(self):
        self.browser = None
        self.page = None
        
    async def init_browser(self):
        """Инициализация браузера"""
        try:
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
            
            logger.info("Браузер инициализирован для OCR анализа")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка инициализации браузера: {e}")
            return False
    
    def get_fallback_data(self, slug):
        """Fallback метод когда Playwright не работает"""
        logger.warning(f"Используем fallback данные для {slug}")
        
        # Возвращаем базовые данные без анализа
        return {
            'market_exists': True,
            'market_name': f"Market: {slug}",
            'is_boolean': True,
            'prices': {'Yes': '50.00%', 'No': '50.00%'},
            'contract_address': '0x0000000000000000000000000000000000000000',
            'total_volume': 'New',
            'analysis_time': datetime.now().isoformat(),
            'status': 'fallback'
        }
    
    async def close_browser(self):
        """Закрытие браузера"""
        try:
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
            logger.info("Браузер закрыт")
        except Exception as e:
            logger.error(f"Ошибка закрытия браузера: {e}")
    
    async def capture_and_extract_text(self, slug):
        """Захват скриншотов и извлечение текста"""
        try:
            url = f"{POLYMARKET_BASE_URL}{slug}"
            
            # Увеличиваем timeout и используем более мягкие условия
            await self.page.goto(url, wait_until='domcontentloaded', timeout=60000)
            
            # Ждем загрузки контента
            await asyncio.sleep(3)
            
            extracted_data = {}
            
            # 1. Полный скриншот страницы
            full_screenshot = await self.page.screenshot(full_page=True)
            full_text = await self.extract_text_from_image(full_screenshot)
            extracted_data['full_page_text'] = full_text
            
            # 2. Скриншот области с заголовком
            try:
                title_area = await self.page.query_selector('h1, [class*="title"], [class*="heading"]')
                if title_area:
                    title_screenshot = await title_area.screenshot()
                    title_text = await self.extract_text_from_image(title_screenshot)
                    extracted_data['title_text'] = title_text
            except:
                pass
            
            # 3. Скриншот области с ценами/процентами
            try:
                price_area = await self.page.query_selector('[class*="price"], [class*="odds"], [class*="probability"], [class*="percentage"]')
                if price_area:
                    price_screenshot = await price_area.screenshot()
                    price_text = await self.extract_text_from_image(price_screenshot)
                    extracted_data['price_text'] = price_text
            except:
                pass
            
            # 4. Извлечение контракта через клик
            logger.info("🔍 Начинаем извлечение контракта...")
            contract_address = await self.extract_contract_address()
            if contract_address:
                logger.info(f"✅ Контракт извлечен: {contract_address}")
                # Передаем контракт в extracted_data для парсинга
                extracted_data['extracted_contract'] = contract_address
            else:
                logger.warning("⚠️ Контракт не извлечен")
            
            logger.info(f"Извлечен текст из {len(extracted_data)} областей для {slug}")
            return extracted_data
            
        except Exception as e:
            logger.error(f"Ошибка захвата и извлечения текста: {e}")
            return {}
    
    async def extract_contract_address(self):
        """Извлечение адреса контракта через клик на Show more"""
        try:
            # 1. Ищем кнопку "Show more"
            show_more_selectors = [
                'button:has-text("Show more")',
                'a:has-text("Show more")',
                '[class*="show-more"]',
                '[class*="expand"]',
                'button[aria-label*="more"]',
                'a[aria-label*="more"]'
            ]
            
            show_more_button = None
            for selector in show_more_selectors:
                try:
                    show_more_button = await self.page.query_selector(selector)
                    if show_more_button:
                        logger.info(f"✔ Найдена кнопка Show more: {selector}")
                        break
                except:
                    continue
            
            if not show_more_button:
                logger.warning("❌ Кнопка Show more не найдена")
                return await self.extract_full_contract_from_page()
            
            # 2. Кликаем на Show more
            await show_more_button.click()
            logger.info("✔ Кликнули на Show more")
            await asyncio.sleep(2)  # Ждем загрузки контента
            
            # 3. Ищем ссылку с частичным адресом контракта
            contract_link_selectors = [
                'a[href*="0x"]',
                '[class*="contract"] a',
                '[class*="address"] a',
                'a[href*="/event/"]',
                'a[href*="/market/"]'
            ]
            
            contract_link = None
            for selector in contract_link_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    logger.info(f"🔍 Проверяем селектор {selector}: найдено {len(elements)} элементов")
                    
                    for element in elements:
                        href = await element.get_attribute('href')
                        if href and '0x' in href:
                            contract_link = element
                            logger.info(f"✔ Найдена ссылка с контрактом: {href}")
                            break
                    
                    if contract_link:
                        break
                except Exception as e:
                    logger.warning(f"Ошибка поиска по селектору {selector}: {e}")
                    continue
            
            if not contract_link:
                logger.warning("❌ Ссылка с контрактом не найдена")
                return await self.extract_full_contract_from_page()
            
            # 4. Получаем href ссылки
            href = await contract_link.get_attribute('href')
            if not href:
                logger.warning("❌ Href ссылки пустой")
                return await self.extract_full_contract_from_page()
            
            # 5. Открываем новую страницу с полным адресом
            try:
                # Создаем новую страницу
                new_page = await self.browser.new_page()
                await new_page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                })
                
                # Переходим по ссылке
                await new_page.goto(href, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(2)
                
                # Извлекаем полный адрес с новой страницы
                full_contract = await self.extract_full_contract_from_page_new_page(new_page)
                
                if full_contract:
                    logger.info(f"✅ Полный контракт извлечен: {full_contract}")
                    await new_page.close()
                    return full_contract
                else:
                    # Если не нашли на новой странице, ищем в URL
                    current_url = new_page.url
                    contract_match = re.search(r'0x[a-fA-F0-9]{40}', current_url)
                    if contract_match:
                        full_contract = contract_match.group()
                        logger.info(f"✅ Контракт найден в URL: {full_contract}")
                        await new_page.close()
                        return full_contract
                    
                    await new_page.close()
                    logger.warning("❌ Полный контракт не найден на новой странице")
                    return await self.extract_full_contract_from_page()
                    
            except Exception as e:
                logger.error(f"❌ Ошибка при открытии новой страницы: {e}")
                return await self.extract_full_contract_from_page()
            
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения контракта: {e}")
            return None
    
    async def extract_full_contract_from_page(self):
        """Извлечение полного адреса контракта с текущей страницы"""
        try:
            # Ищем полный адрес контракта на странице
            contract_selectors = [
                '[class*="contract"]',
                '[class*="address"]',
                '[class*="hex"]',
                'code',
                'pre',
                '[data-testid*="contract"]',
                '[class*="token"]'
            ]
            
            for selector in contract_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    for element in elements:
                        element_text = await element.text_content()
                        if element_text:
                            # Ищем полный адрес контракта (40 символов)
                            contract_match = re.search(r'0x[a-fA-F0-9]{40}', element_text)
                            if contract_match:
                                return contract_match.group()
                except Exception as e:
                    continue
            
            # Если не нашли через селекторы, ищем в полном тексте страницы
            page_text = await self.page.text_content('body')
            contract_matches = re.findall(r'0x[a-fA-F0-9]{40}', page_text)
            if contract_matches:
                return contract_matches[0]
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения контракта со страницы: {e}")
            return None
    
    async def extract_full_contract_from_page_new_page(self, page):
        """Извлечение полного адреса контракта с новой страницы"""
        try:
            # Ищем полный адрес контракта на странице
            contract_selectors = [
                '[class*="contract"]',
                '[class*="address"]',
                '[class*="hex"]',
                'code',
                'pre',
                '[data-testid*="contract"]',
                '[class*="token"]'
            ]
            
            for selector in contract_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        element_text = await element.text_content()
                        if element_text:
                            # Ищем полный адрес контракта (40 символов)
                            contract_match = re.search(r'0x[a-fA-F0-9]{40}', element_text)
                            if contract_match:
                                return contract_match.group()
                except Exception as e:
                    continue
            
            # Если не нашли через селекторы, ищем в полном тексте страницы
            page_text = await page.text_content('body')
            contract_matches = re.findall(r'0x[a-fA-F0-9]{40}', page_text)
            if contract_matches:
                return contract_matches[0]
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения контракта со страницы: {e}")
            return None
    
    async def extract_text_from_image(self, image_data):
        """Извлечение текста из изображения с помощью pytesseract"""
        try:
            import pytesseract
            from PIL import Image
            import io
            
            # Конвертируем bytes в PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Извлекаем текст
            text = pytesseract.image_to_string(image, lang='eng')
            
            return text.strip()
            
        except ImportError:
            logger.warning("pytesseract не установлен, используем fallback")
            return ""
        except Exception as e:
            logger.error(f"Ошибка извлечения текста: {e}")
            return ""
    
    def parse_data_with_regex(self, extracted_data):
        """Парсинг данных с помощью RegEx"""
        try:
            parsed_data = {
                'title': '',
                'yes_percentage': 0.0,
                'no_percentage': 0.0,
                'contract_address': '',
                'volume': '',
                'market_exists': False
            }
            
            # Объединяем весь текст для поиска
            all_text = ' '.join(extracted_data.values())
            
            # 1. Ищем заголовок
            title_text = extracted_data.get('title_text', '')
            if title_text:
                parsed_data['title'] = title_text.strip()
            else:
                # Ищем в полном тексте
                title_patterns = [
                    r'Will.*?\?',
                    r'[A-Z][^.!?]*\?',
                    r'[A-Z][^.!?]*market',
                    r'[A-Z][^.!?]*prediction'
                ]
                for pattern in title_patterns:
                    matches = re.findall(pattern, all_text, re.IGNORECASE)
                    if matches:
                        parsed_data['title'] = matches[0].strip()
                        break
            
            # 2. Ищем проценты Yes/No
            # Ищем кнопки с ценами в центах
            price_patterns = [
                r'Yes\s*(\d+(?:\.\d+)?)¢',
                r'(\d+(?:\.\d+)?)¢\s*Yes',
                r'No\s*(\d+(?:\.\d+)?)¢',
                r'(\d+(?:\.\d+)?)¢\s*No',
                r'Yes\s*(\d+(?:\.\d+)?)%',
                r'(\d+(?:\.\d+)?)%\s*Yes',
                r'No\s*(\d+(?:\.\d+)?)%',
                r'(\d+(?:\.\d+)?)%\s*No',
                r'(\d+(?:\.\d+)?)%\s*chance',
                r'chance\s*(\d+(?:\.\d+)?)%'
            ]
            
            yes_price = None
            no_price = None
            
            for pattern in price_patterns:
                matches = re.findall(pattern, all_text, re.IGNORECASE)
                if matches:
                    try:
                        value = float(matches[0])
                        if 'yes' in pattern.lower():
                            yes_price = value
                        elif 'no' in pattern.lower():
                            no_price = value
                        elif 'chance' in pattern.lower():
                            # Если найден процент chance, это обычно для Yes
                            yes_price = value
                            no_price = 100 - value
                        break
                    except:
                        continue
            
            # Если нашли цены в центах, конвертируем в проценты
            if yes_price and no_price:
                if yes_price < 100 and no_price < 100:  # Это центы
                    parsed_data['yes_percentage'] = yes_price
                    parsed_data['no_percentage'] = no_price
                else:  # Это уже проценты
                    parsed_data['yes_percentage'] = yes_price
                    parsed_data['no_percentage'] = no_price
            elif yes_price:
                parsed_data['yes_percentage'] = yes_price
                parsed_data['no_percentage'] = 100 - yes_price
            elif no_price:
                parsed_data['yes_percentage'] = 100 - no_price
                parsed_data['no_percentage'] = no_price
            
            # 3. Ищем адрес контракта
            # Сначала проверяем извлеченный контракт
            extracted_contract = extracted_data.get('extracted_contract', '')
            if extracted_contract:
                parsed_data['contract_address'] = extracted_contract
                logger.info(f"✅ Используем извлеченный контракт: {extracted_contract}")
            else:
                # Ищем в полном тексте как fallback
                contract_pattern = r'0x[a-fA-F0-9]{40}'
                contract_matches = re.findall(contract_pattern, all_text)
                if contract_matches:
                    parsed_data['contract_address'] = contract_matches[0]
                    logger.info(f"✅ Найден контракт в тексте: {contract_matches[0]}")
                else:
                    logger.warning("⚠️ Контракт не найден")
            
            # 4. Ищем объем торгов
            volume_patterns = [
                r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)',
                r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*USD',
                r'Volume.*?(\d+(?:,\d{3})*(?:\.\d{2})?)'
            ]
            
            for pattern in volume_patterns:
                matches = re.findall(pattern, all_text)
                if matches:
                    parsed_data['volume'] = f"${matches[0]}"
                    break
            
            # 5. Определяем существование рынка
            parsed_data['market_exists'] = bool(
                parsed_data['title'] or 
                'polymarket' in all_text.lower() or
                'prediction' in all_text.lower() or
                'market' in all_text.lower()
            )
            
            logger.info(f"RegEx парсинг завершен: найдено {len([k for k, v in parsed_data.items() if v])} полей")
            return parsed_data
            
        except Exception as e:
            logger.error(f"Ошибка RegEx парсинга: {e}")
            return {
                'title': '',
                'yes_percentage': 0.0,
                'no_percentage': 0.0,
                'contract_address': '',
                'volume': '',
                'market_exists': False
            }
    
    async def analyze_market(self, slug):
        """Полный анализ рынка через OCR"""
        try:
            logger.info(f"🔍 OCR анализ рынка: {slug}")
            
            if not await self.init_browser():
                return None
            
            # Захватываем скриншоты и извлекаем текст
            extracted_data = await self.capture_and_extract_text(slug)
            
            if not extracted_data:
                logger.warning(f"Не удалось извлечь данные для {slug}")
                return None
            
            # Парсим данные с помощью RegEx
            parsed_data = self.parse_data_with_regex(extracted_data)
            
            # Сохраняем извлеченные данные
            await self.save_extracted_data(extracted_data, parsed_data, slug)
            
            # Преобразуем в стандартный формат
            result = self.convert_to_standard_format(parsed_data)
            
            logger.info(f"OCR анализ завершен для {slug}: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка OCR анализа {slug}: {e}")
            return None
        finally:
            await self.close_browser()
    
    async def save_extracted_data(self, extracted_data, parsed_data, slug):
        """Сохранение извлеченных данных"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Сохраняем извлеченный текст
            extracted_filename = f"ocr_extracted_text_{slug}_{timestamp}.json"
            with open(extracted_filename, 'w', encoding='utf-8') as f:
                json.dump(extracted_data, f, indent=2, ensure_ascii=False)
            
            # Сохраняем распарсенные данные
            parsed_filename = f"ocr_parsed_data_{slug}_{timestamp}.json"
            with open(parsed_filename, 'w', encoding='utf-8') as f:
                json.dump(parsed_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Данные сохранены: {extracted_filename}, {parsed_filename}")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения данных: {e}")
    
    def convert_to_standard_format(self, parsed_data):
        """Преобразование в стандартный формат"""
        try:
            return {
                'market_exists': parsed_data.get('market_exists', False),
                'is_boolean': True,  # Предполагаем булевый рынок
                'yes_percentage': parsed_data.get('yes_percentage', 0),
                'contract_address': parsed_data.get('contract_address', ''),
                'title': parsed_data.get('title', ''),
                'description': '', # Убираем поле "Описание:"
                'volume': parsed_data.get('volume', '')
            }
            
        except Exception as e:
            logger.error(f"Ошибка преобразования формата: {e}")
            return {
                'market_exists': False,
                'is_boolean': False,
                'yes_percentage': 0,
                'contract_address': '',
                'title': '',
                'description': '',
                'volume': ''
            }
    
    def get_market_data(self, slug):
        """Получение данных рынка (синхронная обертка)"""
        try:
            result = asyncio.run(self.analyze_market(slug))
            
            if not result or not result.get('market_exists'):
                # Используем fallback если анализ не удался
                fallback_data = self.get_fallback_data(slug)
                return {
                    'title': fallback_data.get('market_name', f"Рынок {slug}"),
                    'odds': fallback_data.get('prices', {'Yes': '50.00%', 'No': '50.00%'}),
                    'contract_address': fallback_data.get('contract_address', ''),
                    'volume': fallback_data.get('total_volume', 'New')
                }
            
            return {
                'title': result.get('title', f"Рынок {slug}"),
                'odds': {
                    'Yes': f"{result.get('yes_percentage', 0):.2f}%",
                    'No': f"{100 - result.get('yes_percentage', 0):.2f}%"
                },
                'contract_address': result.get('contract_address', ''),
                'volume': result.get('volume', '')
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения данных рынка: {e}")
            # Используем fallback при любой ошибке
            fallback_data = self.get_fallback_data(slug)
            return {
                'title': fallback_data.get('market_name', f"Рынок {slug}"),
                'odds': fallback_data.get('prices', {'Yes': '50.00%', 'No': '50.00%'}),
                'contract_address': fallback_data.get('contract_address', ''),
                'volume': fallback_data.get('total_volume', 'New')
            } 