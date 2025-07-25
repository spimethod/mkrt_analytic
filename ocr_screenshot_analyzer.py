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

# Импортируем настройку логирования
import logging_config

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
                            # Проверяем, что это не просто частичный адрес
                            if len(href) > 20:  # Должен быть достаточно длинным
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
            
            # Проверяем, что href - это валидный URL
            if not href.startswith('http'):
                # Если это относительный URL, делаем его абсолютным
                current_url = self.page.url
                if href.startswith('/'):
                    href = f"https://polymarket.com{href}"
                else:
                    href = f"{current_url.rstrip('/')}/{href}"
            
            logger.info(f"🔗 Используем URL: {href}")
            
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
            
            # Если не нашли полный адрес, ищем частичный и попробуем его расширить
            partial_matches = re.findall(r'0x[a-fA-F0-9]{10,}', page_text)
            if partial_matches:
                logger.info(f"🔍 Найден частичный адрес: {partial_matches[0]}")
                # Попробуем найти полный адрес в других местах
                for match in partial_matches:
                    if len(match) >= 20:  # Если достаточно длинный, может быть полным
                        logger.info(f"✅ Используем найденный адрес: {match}")
                        return match
            
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
    
    async def detect_market_category(self):
        """Определение категории рынка (Sports/Crypto/Other) через скрабинг"""
        try:
            # 1. Ищем только активные/выделенные табы (как показано на скрине)
            active_selectors = [
                '[class*="active"]',
                '[class*="selected"]',
                '[aria-selected="true"]',
                '[data-active="true"]',
                '[class*="current"]',
                '[class*="highlight"]'
            ]
            
            active_text = ""
            for selector in active_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    for element in elements:
                        text = await element.text_content()
                        if text and len(text.strip()) > 1:
                            # Фильтруем технические элементы
                            filtered_text = text.strip().lower()
                            if not any(tech in filtered_text for tech in ['1h', '6h', '1d', '1w', '1m', 'all', 'comments', 'holders', 'activity', 'post', 'trade', 'max', 'gear', 'chevron', 'dots', 'arrows', 'circle', 'link', 'show less', 'show more', 'united states', 'how it works', 'log in', 'sign up']):
                                active_text += filtered_text + " "
                                logger.info(f"Найден активный элемент: {text}")
                except Exception as e:
                    logger.debug(f"Ошибка поиска активных элементов: {e}")
                    continue
            
            # 2. Ищем в URL и заголовке страницы
            current_url = self.page.url.lower()
            page_title = await self.page.title()
            if page_title:
                page_title = page_title.lower()
            
            # 3. Ищем в полном тексте страницы
            full_text = await self.page.text_content('body')
            full_text = full_text.lower()
            
            # Объединяем весь текст для анализа
            all_text = f"{active_text} {current_url} {page_title} {full_text}"
            
            logger.info(f"Анализируем текст для определения категории...")
            
            # Определяем категорию с более точными индикаторами
            sports_indicators = [
                'sports', 'mlb', 'nba', 'nfl', 'wnba', 'golf', 'epl', 'cfb',
                'baseball', 'basketball', 'football', 'soccer', 'tennis',
                'game', 'match', 'team', 'player', 'score'
            ]
            
            crypto_indicators = [
                'crypto', 'bitcoin', 'ethereum', 'btc', 'eth', 'blockchain',
                'token', 'coin', 'defi', 'nft', 'web3', 'mining',
                'cryptocurrency', 'digital currency'
            ]
            
            # Проверяем Sports с подсчетом совпадений
            sports_score = 0
            for indicator in sports_indicators:
                if indicator in all_text:
                    sports_score += 1
                    logger.info(f"Найден Sports индикатор: {indicator}")
            
            # Проверяем Crypto с подсчетом совпадений
            crypto_score = 0
            for indicator in crypto_indicators:
                if indicator in all_text:
                    crypto_score += 1
                    logger.info(f"Найден Crypto индикатор: {indicator}")
            
            logger.info(f"Sports score: {sports_score}, Crypto score: {crypto_score}")
            
            # Определяем категорию на основе количества совпадений (более строгие критерии)
            if sports_score >= 3:  # Требуем минимум 3 совпадения для Sports
                logger.info(f"⚠️ Рынок определен как Sports (score: {sports_score})")
                return 'sports'
            elif crypto_score >= 2:  # Требуем минимум 2 совпадения для Crypto
                logger.info(f"⚠️ Рынок определен как Crypto (score: {crypto_score})")
                return 'crypto'
            else:
                logger.info("✅ Рынок не относится к Sports/Crypto категориям")
                return 'other'
            
        except Exception as e:
            logger.error(f"Ошибка определения категории рынка: {e}")
            return 'other'
    
    def parse_data_with_regex(self, extracted_data):
        """Парсинг данных с помощью RegEx"""
        try:
            parsed_data = {}
            
            # Извлекаем текст из всех областей
            full_text = extracted_data.get('full_page_text', '')
            title_text = extracted_data.get('title_text', '')
            price_text = extracted_data.get('price_text', '')
            
            # Объединяем весь текст для поиска
            all_text = f"{full_text} {title_text} {price_text}".lower()
            
            # Проверяем наличие не-булевых индикаторов
            non_boolean_indicators = [
                'multiple choice', 'choose', 'select', 'option',
                'winner', 'winner takes all', 'multi-outcome',
                'prediction', 'forecast', 'outcome'
            ]
            
            is_boolean_market = True
            for indicator in non_boolean_indicators:
                if indicator in all_text:
                    is_boolean_market = False
                    logger.info(f"⚠️ Найден не-булевый индикатор: {indicator}")
                    break
            
            # Если рынок не булевый, возвращаем специальный статус
            if not is_boolean_market:
                logger.warning("⚠️ Рынок не является булевым - закрываем анализ")
                return {
                    'market_exists': True,
                    'is_boolean': False,
                    'status': 'closed',
                    'reason': 'non_boolean_market'
                }
            
            # Определяем существование рынка - если мы дошли до парсинга, значит рынок существует
            market_exists = True
            
            # Извлекаем название рынка
            title_match = re.search(r'([A-Z][^.!?]*[.!?])', full_text)
            if title_match:
                parsed_data['title'] = title_match.group(1).strip()
            else:
                parsed_data['title'] = 'Market Title Not Found'
            
            # Извлекаем цены (проценты)
            price_patterns = [
                r'(\d+(?:\.\d+)?)\s*%',  # 50%
                r'(\d+(?:\.\d+)?)\s*¢',   # 50¢
                r'(\d+(?:\.\d+)?)\s*chance'  # 50% chance
            ]
            
            yes_percentage = 0
            for pattern in price_patterns:
                matches = re.findall(pattern, all_text)
                if matches:
                    try:
                        value = float(matches[0])
                        if '¢' in pattern or 'chance' in pattern:
                            # Конвертируем центы в проценты
                            yes_percentage = value
                        else:
                            yes_percentage = value
                        break
                    except ValueError:
                        continue
            
            parsed_data['yes_percentage'] = yes_percentage
            
            # Извлекаем объем
            volume_patterns = [
                r'\$([\d,]+(?:\.\d{2})?)',  # $1,234.56
                r'volume[:\s]*\$?([\d,]+)',  # volume: $1,234
                r'total[:\s]*\$?([\d,]+)'    # total: $1,234
            ]
            
            volume = 'New'
            for pattern in volume_patterns:
                match = re.search(pattern, all_text)
                if match:
                    try:
                        volume_value = match.group(1).replace(',', '')
                        volume = f"${float(volume_value):,.2f}"
                        break
                    except ValueError:
                        continue
            
            parsed_data['volume'] = volume
            
            # Извлекаем контракт (если есть)
            contract_match = re.search(r'0x[a-fA-F0-9]{40}', all_text)
            if contract_match:
                parsed_data['contract_address'] = contract_match.group()
            else:
                # Ищем частичный адрес
                partial_match = re.search(r'0x[a-fA-F0-9]{10,}', all_text)
                if partial_match:
                    parsed_data['contract_address'] = partial_match.group()
                else:
                    parsed_data['contract_address'] = ''
            
            # Добавляем флаг существования рынка
            parsed_data['market_exists'] = market_exists
            parsed_data['is_boolean'] = is_boolean_market
            
            logger.info(f"RegEx парсинг завершен: найдено {len(parsed_data)} полей")
            return parsed_data
            
        except Exception as e:
            logger.error(f"Ошибка парсинга данных: {e}")
            return {}
    
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
            
            # Определяем категорию рынка
            market_category = await self.detect_market_category()
            
            # Если рынок Sports или Crypto - закрываем анализ
            if market_category in ['sports', 'crypto']:
                logger.warning(f"⚠️ Рынок {slug} относится к категории {market_category.upper()} - закрываем анализ")
                return {
                    'market_exists': True,
                    'is_boolean': False,
                    'status': 'closed',
                    'reason': f'category_{market_category}',
                    'category': market_category
                }
            
            # Извлекаем контракт отдельно
            contract_address = await self.extract_contract_address()
            if contract_address:
                extracted_data['extracted_contract'] = contract_address
                logger.info(f"✅ Контракт извлечен: {contract_address}")
            
            # Парсим данные с помощью RegEx
            parsed_data = self.parse_data_with_regex(extracted_data)
            
            # Если контракт был извлечен, используем его
            if contract_address and not parsed_data.get('contract_address'):
                parsed_data['contract_address'] = contract_address
            
            # Добавляем категорию в данные
            parsed_data['category'] = market_category
            
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
            # Обрабатываем специальный статус 'closed'
            if parsed_data.get('status') == 'closed':
                return {
                    'market_exists': True,
                    'is_boolean': False,
                    'yes_percentage': 0,
                    'contract_address': '',
                    'title': parsed_data.get('title', ''),
                    'description': '',
                    'volume': parsed_data.get('volume', '')
                }

            return {
                'market_exists': parsed_data.get('market_exists', True),  # По умолчанию True
                'is_boolean': parsed_data.get('is_boolean', True),  # По умолчанию True
                'yes_percentage': parsed_data.get('yes_percentage', 0),
                'contract_address': parsed_data.get('contract_address', ''),
                'title': parsed_data.get('title', ''),
                'description': '', # Убираем поле "Описание:"
                'volume': parsed_data.get('volume', '')
            }
            
        except Exception as e:
            logger.error(f"Ошибка преобразования формата: {e}")
            return {
                'market_exists': True,  # По умолчанию True
                'is_boolean': True,  # По умолчанию True
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
            
            if not result:
                logger.warning(f"Используем fallback данные для {slug}")
                # Используем fallback если анализ не удался
                fallback_data = self.get_fallback_data(slug)
                return {
                    'market_exists': True,
                    'is_boolean': True,
                    'yes_percentage': 50.0,
                    'contract_address': fallback_data.get('contract_address', ''),
                    'title': fallback_data.get('market_name', f"Рынок {slug}"),
                    'volume': fallback_data.get('total_volume', 'New')
                }
            
            # Проверяем, является ли рынок булевым
            if not result.get('is_boolean', True):
                logger.info(f"Рынок {slug} не является булевым - закрываем анализ")
                return {
                    'market_exists': True,
                    'is_boolean': False,
                    'yes_percentage': 0,
                    'contract_address': result.get('contract_address', ''),
                    'title': result.get('title', f"Рынок {slug}"),
                    'volume': result.get('volume', 'New')
                }
            
            # Возвращаем данные булевого рынка
            return {
                'market_exists': result.get('market_exists', True),
                'is_boolean': result.get('is_boolean', True),
                'yes_percentage': result.get('yes_percentage', 0),
                'contract_address': result.get('contract_address', ''),
                'title': result.get('title', f"Рынок {slug}"),
                'volume': result.get('volume', 'New')
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения данных рынка: {e}")
            # Используем fallback при любой ошибке
            fallback_data = self.get_fallback_data(slug)
            return {
                'market_exists': True,
                'is_boolean': True,
                'yes_percentage': 50.0,
                'contract_address': fallback_data.get('contract_address', ''),
                'title': fallback_data.get('market_name', f"Рынок {slug}"),
                'volume': fallback_data.get('total_volume', 'New')
            } 