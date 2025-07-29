import logging
import re
import asyncio
from analysis.yes_percentage_extractor import YesPercentageExtractor
from analysis.volume_extractor import VolumeExtractor
from analysis.contract_extractor import ContractExtractor
from analysis.market_name_extractor import MarketNameExtractor

logger = logging.getLogger(__name__)

class DataExtractor:
    def __init__(self):
        self.yes_extractor = YesPercentageExtractor()
        self.volume_extractor = VolumeExtractor()
        self.contract_extractor = ContractExtractor()
        self.name_extractor = MarketNameExtractor()
    
    async def extract_text_from_screenshot(self, page):
        """Извлечение текста из скриншота с помощью pytesseract"""
        try:
            import pytesseract
            from PIL import Image
            import io
            
            # Делаем скриншот страницы
            logger.info("📸 Делаем скриншот страницы...")
            screenshot = await page.screenshot(full_page=True)
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
            return await page.text_content()
        except Exception as e:
            logger.error(f"Ошибка извлечения текста: {e}")
            return await page.text_content()
    
    async def extract_market_data(self, page):
        """Извлечение данных рынка через OCR + RegEx"""
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
            
            # Извлекаем текст через OCR
            page_text = await self.extract_text_from_screenshot(page)
            logger.info(f"📄 Извлеченный текст со страницы: {page_text[:300]}...")
            
            # Извлекаем название рынка
            market_name = await self.name_extractor.extract_market_name(page)
            if market_name:
                data['market_name'] = market_name
                logger.info(f"✅ Извлечено название рынка: {market_name}")
            
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
                r'\$(\d+(?:,\d{3})*(?:\.\d+)?)\s*Vol',
                r'Volume:\s*\$(\d+(?:,\d{3})*(?:\.\d+)?)',
                r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*USD',
                r'\$(\d+(?:,\d{3})*(?:\.\d+)?)'
            ]
            
            for pattern in volume_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    volume = matches[0].replace(',', '')
                    try:
                        volume_float = float(volume)
                        if volume_float > 0:
                            data['volume'] = f"${volume}"
                            logger.info(f"✅ Извлечен объем: {data['volume']}")
                            break
                    except ValueError:
                        continue
            
            # Извлекаем адрес контракта через RegEx
            contract_patterns = [
                r'0x[a-fA-F0-9]{40}',  # Ethereum адрес
                r'Contract:\s*(0x[a-fA-F0-9]{40})',
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