import logging
from playwright.async_api import Page

logger = logging.getLogger(__name__)

class MarketNameExtractor:
    def __init__(self):
        pass
    
    async def extract_market_name(self, page: Page):
        """Извлечение названия рынка"""
        try:
            # Ищем название рынка в заголовке
            name_selectors = [
                'h1[data-testid="event-title"]',
                'h1.event-title',
                'h1.title',
                '[data-testid="event-title"]',
                'h1'
            ]
            
            for selector in name_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        name = await element.text_content()
                        if name and name.strip():
                            name = name.strip()
                            logger.info(f"✅ Извлечено название рынка: {name}")
                            return name
                except Exception as e:
                    logger.debug(f"Не удалось извлечь название с селектором {selector}: {e}")
                    continue
            
            # Если не нашли, пробуем извлечь из URL
            url = page.url
            if 'polymarket.com/event/' in url:
                slug = url.split('/event/')[-1].split('?')[0]
                # Преобразуем slug в читаемое название
                name = slug.replace('-', ' ').title()
                logger.info(f"✅ Извлечено название из URL: {name}")
                return name
            
            logger.warning("⚠️ Не удалось извлечь название рынка")
            return "Unknown Market"
            
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения названия рынка: {e}")
            return "Unknown Market" 