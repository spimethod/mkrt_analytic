import logging
import re

logger = logging.getLogger(__name__)

class YesPercentageExtractor:
    def __init__(self):
        self.percentage_patterns = [
            r'(\d+(?:\.\d+)?)%\s*chance',
            r'Yes\s+(\d+(?:\.\d+)?)¢',
            r'(\d+(?:\.\d+)?)%\s*Yes',
            r'Yes\s+(\d+(?:\.\d+)?)%'
        ]
    
    async def extract_yes_percentage(self, page):
        """Извлечение процента Yes из страницы"""
        try:
            # Получаем весь текст страницы
            page_text = await page.text_content()
            
            # Ищем процент Yes по различным паттернам
            for pattern in self.percentage_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    # Берем первое совпадение
                    percentage = float(matches[0])
                    
                    # Проверяем валидность процента
                    if 0 <= percentage <= 100:
                        logger.info(f"✅ Найден процент Yes: {percentage}%")
                        return percentage
                    else:
                        logger.warning(f"⚠️ Некорректный процент Yes: {percentage}%")
            
            logger.warning("⚠️ Процент Yes не найден")
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения процента Yes: {e}")
            return None 