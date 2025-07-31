import logging
import re

logger = logging.getLogger(__name__)

class VolumeExtractor:
    def __init__(self):
        self.volume_patterns = [
            # Специфичные для Polymarket паттерны
            r'\$(\d+(?:,\d{3})*)\s*Vol\.?',  # $1,629,831 Vol.
            r'(\d+(?:,\d{3})*)\s*Vol\.?',    # 1,629,831 Vol.
            r'Volume:\s*\$(\d+(?:,\d{3})*)',  # Volume: $1,629,831
            r'\$(\d+(?:,\d{3})*)\s*USD',      # $1,629,831 USD
            r'(\d+(?:,\d{3})*)\s*USD',        # 1,629,831 USD
            # Общие паттерны
            r'\$(\d+(?:,\d{3})*(?:\.\d+)?)',  # $1,629,831
            r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*USD'
        ]
        
        # CSS селекторы для более точного поиска
        self.volume_selectors = [
            # Специфичные для Polymarket селекторы
            '[class*="volume"]',
            '[class*="Volume"]',
            '[data-testid*="volume"]',
            '[data-testid*="Volume"]',
            '[class*="market-volume"]',
            '[class*="trading-volume"]',
            'span:contains("Vol")',
            'div:contains("Vol")',
            '[class*="stats"] span:contains("Vol")',
            '[class*="market-stats"] span:contains("Vol")',
            # Дополнительные селекторы для Polymarket
            '[class*="market-info"] span:contains("Vol")',
            '[class*="market-details"] span:contains("Vol")',
            '[class*="header"] span:contains("Vol")',
            '[class*="title"] + span:contains("Vol")',
            '[class*="market-title"] + div span:contains("Vol")',
            # Поиск по тексту "Vol" в ближайших элементах
            'div:has(span:contains("Vol"))',
            'span:contains("Vol")',
            'div:contains("Vol")',
            # Поиск в элементах с числовыми значениями рядом с "Vol"
            '[class*="numeric"]:contains("Vol")',
            '[class*="value"]:contains("Vol")'
        ]
    
    async def extract_volume(self, page):
        """Извлечение объема торгов из страницы"""
        try:
            # Сначала пробуем найти через CSS селекторы
            volume_from_selectors = await self._extract_volume_from_selectors(page)
            if volume_from_selectors:
                return volume_from_selectors
            
            # Если не нашли через селекторы, ищем в тексте страницы
            volume_from_text = await self._extract_volume_from_text(page)
            if volume_from_text:
                return volume_from_text
            
            logger.warning("⚠️ Объем не найден")
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения объема: {e}")
            return None
    
    async def _extract_volume_from_selectors(self, page):
        """Извлечение объема через CSS селекторы"""
        try:
            for selector in self.volume_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        element_text = await element.text_content()
                        if element_text:
                            # Ищем объем в тексте элемента
                            for pattern in self.volume_patterns:
                                matches = re.findall(pattern, element_text, re.IGNORECASE)
                                if matches:
                                    volume = matches[0]
                                    volume_clean = volume.replace(',', '')
                                    
                                    try:
                                        volume_float = float(volume_clean)
                                        if volume_float > 0:
                                            logger.info(f"✅ Найден объем через селектор {selector}: ${volume}")
                                            return f"${volume}"
                                    except ValueError:
                                        continue
                except Exception as e:
                    logger.debug(f"Ошибка селектора {selector}: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения объема через селекторы: {e}")
            return None
    
    async def _extract_volume_from_text(self, page):
        """Извлечение объема из текста страницы"""
        try:
            page_text = await page.text_content()
            
            # Сначала ищем точные совпадения с "Vol"
            vol_context_patterns = [
                r'\$(\d+(?:,\d{3})*)\s*Vol\.?',  # $1,629,831 Vol.
                r'(\d+(?:,\d{3})*)\s*Vol\.?',    # 1,629,831 Vol.
                r'Vol\.?\s*\$(\d+(?:,\d{3})*)',  # Vol. $1,629,831
                r'Vol\.?\s*(\d+(?:,\d{3})*)',    # Vol. 1,629,831
            ]
            
            for pattern in vol_context_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    volume = matches[0]
                    volume_clean = volume.replace(',', '')
                    
                    try:
                        volume_float = float(volume_clean)
                        if volume_float > 0:
                            logger.info(f"✅ Найден объем в контексте Vol: ${volume}")
                            return f"${volume}"
                    except ValueError:
                        continue
            
            # Если не нашли в контексте Vol, ищем в ближайшем контексте
            volume_in_context = await self._find_volume_near_vol_text(page_text)
            if volume_in_context:
                return volume_in_context
            
            # Если не нашли в контексте Vol, ищем общие паттерны
            for pattern in self.volume_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    # Берем первое совпадение
                    volume = matches[0]
                    
                    # Очищаем от запятых
                    volume_clean = volume.replace(',', '')
                    
                    # Проверяем, что это число
                    try:
                        volume_float = float(volume_clean)
                        if volume_float > 0:
                            logger.info(f"✅ Найден объем в тексте: ${volume}")
                            return f"${volume}"
                    except ValueError:
                        logger.warning(f"⚠️ Некорректный объем: {volume}")
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения объема из текста: {e}")
            return None
    
    def _find_volume_near_vol_text(self, page_text):
        """Поиск объема в ближайшем контексте к тексту 'Vol'"""
        try:
            # Ищем все вхождения "Vol" в тексте
            vol_positions = []
            for match in re.finditer(r'Vol\.?', page_text, re.IGNORECASE):
                vol_positions.append(match.start())
            
            for pos in vol_positions:
                # Ищем объем в окне ±50 символов вокруг "Vol"
                start = max(0, pos - 50)
                end = min(len(page_text), pos + 50)
                context = page_text[start:end]
                
                # Ищем объем в этом контексте
                volume_patterns = [
                    r'\$(\d+(?:,\d{3})*)',  # $1,629,831
                    r'(\d+(?:,\d{3})*)\s*USD',  # 1,629,831 USD
                ]
                
                for pattern in volume_patterns:
                    matches = re.findall(pattern, context)
                    if matches:
                        volume = matches[0]
                        volume_clean = volume.replace(',', '')
                        
                        try:
                            volume_float = float(volume_clean)
                            if volume_float > 0:
                                logger.info(f"✅ Найден объем рядом с Vol: ${volume}")
                                return f"${volume}"
                        except ValueError:
                            continue
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска объема рядом с Vol: {e}")
            return None 