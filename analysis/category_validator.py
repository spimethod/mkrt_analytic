#!/usr/bin/env python3
"""
Модуль для проверки категорий рынков
Проверяет, не является ли рынок из раздела Крипто или Спорт
"""

import logging
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

class CategoryValidator:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
    
    def init_browser(self):
        """Инициализация браузера"""
        try:
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
            self.page.set_viewport_size({"width": 1920, "height": 1080})
            logger.info("✅ Браузер инициализирован для проверки категорий")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации браузера: {e}")
            return False
    
    def goto_page(self, url):
        """Переход на страницу"""
        try:
            logger.info(f"🌐 Переходим на страницу: {url}")
            self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            logger.info("✅ Страница загружена")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки страницы: {e}")
            return False
    
    def check_category_color(self, category_name):
        """Проверка цвета категории"""
        try:
            # Селекторы для категорий
            category_selectors = [
                f'text={category_name}',
                f'[data-testid="{category_name.lower()}"]',
                f'[class*="{category_name.lower()}"]',
                f'a:has-text("{category_name}")',
                f'button:has-text("{category_name}")'
            ]
            
            for selector in category_selectors:
                try:
                    element = self.page.query_selector(selector)
                    if element:
                        # Получаем цвет элемента
                        color = element.evaluate("""
                            (element) => {
                                const style = window.getComputedStyle(element);
                                return style.color;
                            }
                        """)
                        
                        logger.info(f"🎨 Категория '{category_name}' имеет цвет: {color}")
                        
                        # Проверяем, является ли цвет черным или близким к черному
                        if color and ('rgb(0, 0, 0)' in color or 'black' in color or '#000' in color):
                            logger.info(f"✅ Категория '{category_name}' активна (черный цвет)")
                            return True
                        else:
                            logger.info(f"ℹ️ Категория '{category_name}' неактивна (серый цвет)")
                            return False
                            
                except Exception as e:
                    logger.debug(f"Не удалось проверить селектор {selector}: {e}")
                    continue
            
            logger.warning(f"⚠️ Категория '{category_name}' не найдена")
            return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки цвета категории '{category_name}': {e}")
            return False
    
    def validate_market_category(self, slug):
        """Проверка категории рынка"""
        try:
            logger.info(f"🔍 Проверяем категорию рынка: {slug}")
            
            # Инициализируем браузер
            if not self.init_browser():
                return {'is_valid': True, 'status': 'в работе', 'reason': 'браузер не инициализирован'}
            
            # Переходим на страницу
            url = f"https://polymarket.com/event/{slug}"
            if not self.goto_page(url):
                return {'is_valid': True, 'status': 'в работе', 'reason': 'страница не загружена'}
            
            # Ждем загрузки контента
            self.page.wait_for_timeout(3000)
            
            # Проверяем категорию Крипто
            is_crypto = self.check_category_color("Crypto")
            if is_crypto:
                logger.warning(f"⚠️ Рынок {slug} относится к категории Крипто")
                return {'is_valid': False, 'status': 'закрыт (Крипто)', 'reason': 'категория Крипто'}
            
            # Проверяем категорию Спорт
            is_sports = self.check_category_color("Sports")
            if is_sports:
                logger.warning(f"⚠️ Рынок {slug} относится к категории Спорт")
                return {'is_valid': False, 'status': 'закрыт (Спорт)', 'reason': 'категория Спорт'}
            
            # Если ни одна категория не активна, рынок валиден
            logger.info(f"✅ Рынок {slug} не относится к запрещенным категориям")
            return {'is_valid': True, 'status': 'в работе', 'reason': 'валидная категория'}
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки категории рынка {slug}: {e}")
            return {'is_valid': True, 'status': 'в работе', 'reason': f'ошибка проверки: {e}'}
        finally:
            # Закрываем браузер
            self.close_browser()
    
    def close_browser(self):
        """Закрытие браузера"""
        try:
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            logger.info("🔒 Браузер закрыт")
        except Exception as e:
            logger.error(f"❌ Ошибка закрытия браузера: {e}") 