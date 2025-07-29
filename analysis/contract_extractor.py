import logging
import re

logger = logging.getLogger(__name__)

class ContractExtractor:
    def __init__(self):
        self.contract_patterns = [
            r'0x[a-fA-F0-9]{40}',  # Ethereum адрес
            r'Contract:\s*(0x[a-fA-F0-9]{40})',
            r'href="[^"]*/(0x[a-fA-F0-9]{40})"'
        ]
    
    async def extract_contract(self, page):
        """Извлечение адреса контракта из страницы"""
        try:
            # Получаем весь текст страницы
            page_text = await page.text_content()
            
            # Ищем адрес контракта по различным паттернам
            for pattern in self.contract_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    # Берем первое совпадение
                    contract = matches[0]
                    
                    # Проверяем, что это валидный адрес
                    if len(contract) == 42 and contract.startswith('0x'):
                        logger.info(f"✅ Найден адрес контракта: {contract}")
                        return contract
                    else:
                        logger.warning(f"⚠️ Некорректный адрес контракта: {contract}")
            
            # Попробуем найти в ссылках
            try:
                links = await page.query_selector_all('a[href*="0x"]')
                for link in links:
                    href = await link.get_attribute('href')
                    if href:
                        contract_match = re.search(r'0x[a-fA-F0-9]{40}', href)
                        if contract_match:
                            contract = contract_match.group(0)
                            logger.info(f"✅ Найден адрес контракта в ссылке: {contract}")
                            return contract
            except Exception as e:
                logger.warning(f"⚠️ Ошибка поиска контракта в ссылках: {e}")
            
            logger.warning("⚠️ Адрес контракта не найден")
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения адреса контракта: {e}")
            return None 