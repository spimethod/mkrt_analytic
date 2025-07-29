import logging
import re
from analysis.yes_percentage_extractor import YesPercentageExtractor
from analysis.volume_extractor import VolumeExtractor
from analysis.contract_extractor import ContractExtractor

logger = logging.getLogger(__name__)

class DataExtractor:
    def __init__(self):
        self.yes_extractor = YesPercentageExtractor()
        self.volume_extractor = VolumeExtractor()
        self.contract_extractor = ContractExtractor()
    
    async def extract_market_data(self, page):
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
            
            # Извлекаем процент Yes
            yes_percentage = await self.yes_extractor.extract_yes_percentage(page)
            if yes_percentage is not None:
                data['yes_percentage'] = yes_percentage
                logger.info(f"✅ Извлечен процент Yes: {yes_percentage}%")
            
            # Извлекаем объем
            volume = await self.volume_extractor.extract_volume(page)
            if volume is not None:
                data['volume'] = volume
                logger.info(f"✅ Извлечен объем: {volume}")
            
            # Извлекаем адрес контракта
            contract = await self.contract_extractor.extract_contract(page)
            if contract is not None:
                data['contract_address'] = contract
                logger.info(f"✅ Извлечен адрес контракта: {contract}")
            
            return data
            
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения данных рынка: {e}")
            return None 