import logging
import re

logger = logging.getLogger(__name__)

class VolumeExtractor:
    def __init__(self):
        self.volume_patterns = [
            r'\$(\d+(?:,\d{3})*(?:\.\d+)?)\s*Vol',
            r'Volume:\s*\$(\d+(?:,\d{3})*(?:\.\d+)?)',
            r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*USD',
            r'\$(\d+(?:,\d{3})*(?:\.\d+)?)'
        ]
    
    async def extract_volume(self, page):
        """Извлечение объема торгов из страницы"""
        try:
            # Получаем весь текст страницы
            page_text = await page.text_content()
            
            # Ищем объем по различным паттернам
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
                            logger.info(f"✅ Найден объем: ${volume}")
                            return f"${volume}"
                    except ValueError:
                        logger.warning(f"⚠️ Некорректный объем: {volume}")
            
            logger.warning("⚠️ Объем не найден")
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения объема: {e}")
            return None 