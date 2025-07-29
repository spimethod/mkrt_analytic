#!/usr/bin/env python3
"""
Синхронный анализатор рынков для использования в асинхронном коде
"""

import asyncio
import logging
import re
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

class SyncMarketAnalyzer:
    def __init__(self):
        self.browser = None
        self.page = None
        self.playwright = None
    
    def init_browser(self):
        """Синхронная инициализация браузера"""
        try:
            logger.info("🔄 Инициализируем браузер синхронно...")
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
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
            self.page = self.browser.new_page()
            
            # Устанавливаем user agent
            self.page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            
            logger.info("✅ Браузер инициализирован синхронно")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации браузера: {e}")
            return False
    
    def goto_page(self, url):
        """Синхронный переход на страницу"""
        try:
            logger.info(f"🌐 Переходим на страницу: {url}")
            logger.info(f"⏳ Начинаем загрузку страницы...")
            self.page.goto(url, wait_until='domcontentloaded', timeout=60000)
            logger.info(f"✅ Страница загружена: {url}")
            
            # Ждем дополнительно для загрузки контента
            logger.info("⏳ Ждем загрузки контента...")
            time.sleep(3)
            logger.info("✅ Контент загружен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка перехода на страницу {url}: {e}")
            raise
    
    def extract_text_from_screenshot(self):
        """Синхронное извлечение текста из скриншота"""
        try:
            import pytesseract
            from PIL import Image
            import io
            
            # Делаем скриншот страницы
            logger.info("📸 Делаем скриншот страницы...")
            screenshot = self.page.screenshot(full_page=True)
            logger.info("✅ Скриншот сделан")
            
            # Конвертируем bytes в PIL Image
            image = Image.open(io.BytesIO(screenshot))
            
            # Извлекаем текст
            logger.info("🔍 Извлекаем текст через OCR...")
            text = pytesseract.image_to_string(image, lang='eng')
            logger.info(f"📄 Извлеченный текст: {text[:200]}...")
            return text.strip()
            
        except ImportError:
            logger.warning("pytesseract не установлен, используем fallback")
            return self.page.text_content()
        except Exception as e:
            logger.error(f"Ошибка извлечения текста: {e}")
            return self.page.text_content()
    
    def extract_market_data(self, page_text):
        """Извлечение данных рынка через RegEx"""
        try:
            logger.info("🔍 Начинаем извлечение данных рынка...")
            data = {
                'market_exists': True,
                'is_boolean': True,
                'yes_percentage': 0,
                'volume': 'New',
                'contract_address': '',
                'status': 'в работе',
                'market_name': 'Unknown Market'
            }
            
            # Извлекаем название рынка
            title_patterns = [
                r'Will any presidential candidate[^.!?]*[.!?]',
                r'Will [^.!?]*[.!?]',
                r'[A-Z][^.!?]*[.!?]',
                r'[A-Z][a-z\s]+[?]'
            ]
            
            for pattern in title_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    title = match.group(0).strip()
                    if len(title) > 10:  # Минимальная длина для названия
                        data['market_name'] = title
                        logger.info(f"✅ Извлечено название рынка: {title}")
                        break
            
            # Проверяем булевость рынка через RegEx
            boolean_indicators = [
                r'yes\s*\d+[¢%]',  # Yes 21¢
                r'no\s*\d+[¢%]',   # No 81¢
                r'yes\s*\$\d+',    # Yes $0.21
                r'no\s*\$\d+',     # No $0.81
                r'yes\s*\d+%',     # Yes 21%
                r'no\s*\d+%',      # No 79%
                r'\d+%',           # 38% (просто процент)
                r'\d+¢',           # 50¢ (просто центы)
                r'\$\d+',          # $0.50 (просто доллары)
            ]
            
            is_boolean_market = False
            for pattern in boolean_indicators:
                if re.search(pattern, page_text, re.IGNORECASE):
                    is_boolean_market = True
                    logger.info(f"✅ Найден булевый индикатор: {pattern}")
                    break
            
            if not is_boolean_market:
                logger.warning("⚠️ Рынок не является булевым - закрываем анализ")
                data['is_boolean'] = False
                data['status'] = 'closed'
                return data
            
            # Извлекаем процент Yes через RegEx
            yes_patterns = [
                r'(\d+(?:\.\d+)?)\s*%',  # 50%
                r'(\d+(?:\.\d+)?)\s*¢',   # 50¢
                r'(\d+(?:\.\d+)?)\s*chance',  # 50% chance
                r'yes\s*(\d+(?:\.\d+)?)\s*%',  # Yes 50%
                r'(\d+(?:\.\d+)?)\s*%\s*yes',  # 50% Yes
            ]
            
            yes_percentage = 0
            for pattern in yes_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    try:
                        value = float(matches[0])
                        if 0 <= value <= 100:
                            yes_percentage = value
                            logger.info(f"✅ Извлечен процент Yes: {yes_percentage}%")
                            break
                    except ValueError:
                        continue
            
            data['yes_percentage'] = yes_percentage
            
            # Извлекаем объем через RegEx
            volume_patterns = [
                r'\$(\d+(?:,\d{3})*(?:\.\d+)?)\s*Vol',  # $8,937 Vol
                r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*Vol',    # 8,937 Vol
                r'Volume:\s*\$(\d+(?:,\d{3})*(?:\.\d+)?)',
                r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*USD',
                r'\$(\d+(?:,\d{3})*(?:\.\d+)?)',        # $8,937
                r'Total Volume:\s*\$(\d+(?:,\d{3})*(?:\.\d+)?)',
                r'Volume\s*\$(\d+(?:,\d{3})*(?:\.\d+)?)',
                r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*volume',
                r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*total',
                r'Vol\s*\$(\d+(?:,\d{3})*(?:\.\d+)?)',  # Vol $8,937
                r'Vol\s*(\d+(?:,\d{3})*(?:\.\d+)?)'     # Vol 8,937
            ]
            
            for pattern in volume_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    volume = matches[0].replace(',', '')
                    try:
                        volume_float = float(volume)
                        if volume_float > 0:
                            # Форматируем объем с запятыми для больших чисел
                            if volume_float >= 1000:
                                formatted_volume = f"${volume_float:,.0f}"
                            else:
                                formatted_volume = f"${volume}"
                            data['volume'] = formatted_volume
                            logger.info(f"✅ Извлечен объем: {data['volume']}")
                            break
                    except ValueError:
                        continue
            
            # Извлекаем адрес контракта через RegEx
            contract_patterns = [
                r'0x[a-fA-F0-9]{40}',  # Ethereum адрес
                r'Contract:\s*(0x[a-fA-F0-9]{40})',
                r'contract\s*(0x[a-fA-F0-9]{40})',
                r'address\s*(0x[a-fA-F0-9]{40})',
                r'(0x[a-fA-F0-9]{40})\s*contract',
                r'(0x[a-fA-F0-9]{40})\s*address'
            ]
            
            for pattern in contract_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    contract = matches[0]
                    if len(contract) == 42 and contract.startswith('0x'):
                        data['contract_address'] = contract
                        logger.info(f"✅ Извлечен адрес контракта: {contract}")
                        break
            
            logger.info("✅ Извлечение данных рынка завершено")
            return data
            
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения данных рынка: {e}")
            return None
    
    def analyze_market(self, slug):
        """Синхронный анализ рынка"""
        try:
            logger.info(f"🔍 Начинаем синхронный анализ рынка: {slug}")
            
            # Инициализируем браузер
            if not self.init_browser():
                return None
            
            # Переходим на страницу
            url = f"https://polymarket.com/event/{slug}"
            self.goto_page(url)
            
            # Извлекаем текст
            page_text = self.extract_text_from_screenshot()
            
            # Извлекаем данные
            market_data = self.extract_market_data(page_text)
            
            if market_data:
                logger.info(f"✅ Синхронный анализ рынка {slug} завершен успешно")
                return market_data
            else:
                logger.warning(f"⚠️ Не удалось извлечь данные для {slug}")
                return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка синхронного анализа рынка {slug}: {e}")
            return None
        finally:
            # Закрываем браузер
            self.close_browser()
    
    def close_browser(self):
        """Синхронное закрытие браузера"""
        try:
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            logger.info("🔒 Браузер закрыт синхронно")
        except Exception as e:
            logger.error(f"❌ Ошибка закрытия браузера: {e}") 