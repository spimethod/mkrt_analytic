import re
import logging

logger = logging.getLogger(__name__)

class BooleanMarketValidator:
    def __init__(self):
        # Индикаторы булевых рынков (простой Yes/No)
        self.boolean_indicators = [
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
        
        # Индикаторы не-булевых рынков (множественные варианты исхода)
        self.non_boolean_indicators = [
            # Множественные варианты исхода
            r'bps\s*(?:decrease|increase)',  # bps decrease/increase
            r'\d+\s*bps',  # 25 bps, 50 bps
            r'Buy\s*Yes.*Buy\s*No',  # Buy Yes ... Buy No (множественные кнопки)
            r'Outcome\s*\d+',  # Outcome 1, Outcome 2
            r'Option\s*\d+',  # Option 1, Option 2
            r'Choice\s*\d+',  # Choice 1, Choice 2
            r'Result\s*\d+',  # Result 1, Result 2
            
            # Множественные страны/варианты
            r'China.*India.*Canada',  # Множественные страны
            r'China.*Mexico.*Brazil',  # Множественные страны
            r'Which\s+countries',  # Вопросы о множественных странах
            r'Which\s+of\s+the',  # Вопросы о выборе из множества
            r'Multiple\s+outcomes',  # Множественные исходы
            r'Select\s+all',  # Выберите все
            r'Choose\s+from',  # Выберите из
            
            # Процентные ставки и экономические показатели
            r'interest\s+rate',  # Процентная ставка
            r'fed\s+rate',  # Ставка ФРС
            r'inflation\s+rate',  # Инфляция
            r'unemployment\s+rate',  # Безработица
            
            # Политические множественные выборы
            r'which\s+candidate',  # Какой кандидат
            r'who\s+will\s+win',  # Кто выиграет
            r'which\s+party',  # Какая партия
            r'which\s+state',  # Какой штат
            
            # Спортивные множественные выборы
            r'which\s+team',  # Какая команда
            r'who\s+will\s+score',  # Кто забьет
            r'which\s+player',  # Какой игрок
            
            # Криптовалютные множественные выборы
            r'which\s+crypto',  # Какая криптовалюта
            r'which\s+token',  # Какой токен
            r'which\s+blockchain',  # Какой блокчейн
        ]
        
        # Ключевые слова для множественных вариантов
        self.multiple_outcome_keywords = [
            'countries', 'candidates', 'teams', 'players', 'states', 'parties',
            'options', 'choices', 'outcomes', 'results', 'alternatives',
            'which', 'who', 'what', 'where', 'when', 'how many'
        ]
    
    def validate_market_boolean(self, page_text, market_name=""):
        """
        Определяет, является ли рынок булевым
        
        Args:
            page_text (str): Текст страницы
            market_name (str): Название рынка
            
        Returns:
            dict: {'is_boolean': bool, 'reason': str}
        """
        try:
            # Приводим к нижнему регистру для поиска
            text_lower = page_text.lower()
            name_lower = market_name.lower()
            
            # Проверяем на проблемы с браузером - в этом случае не определяем булевость
            if "failed to verify your browser" in text_lower or "security checkpoint" in text_lower:
                logger.warning("⚠️ Обнаружена проблема с браузером - не определяем булевость")
                return {
                    'is_boolean': True,  # По умолчанию считаем булевым при проблемах с браузером
                    'reason': 'Проблема с браузером - используем значение по умолчанию'
                }
            
            # 1. Проверяем на явные не-булевые индикаторы (приоритет)
            for pattern in self.non_boolean_indicators:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    logger.warning(f"⚠️ Найден не-булевый индикатор: {pattern}")
                    return {
                        'is_boolean': False,
                        'reason': f'Не-булевый индикатор: {pattern}'
                    }
            
            # 2. Проверяем название рынка на множественные варианты
            for keyword in self.multiple_outcome_keywords:
                if keyword in name_lower:
                    logger.warning(f"⚠️ Название содержит множественный индикатор: {keyword}")
                    return {
                        'is_boolean': False,
                        'reason': f'Название содержит: {keyword}'
                    }
            
            # 3. Проверяем на множественные варианты в тексте
            multiple_patterns = [
                r'\d+%\s+chance.*\d+%\s+chance',  # Множественные проценты
                r'Buy\s+Yes.*Buy\s+Yes',  # Множественные кнопки Buy Yes
                r'Buy\s+No.*Buy\s+No',    # Множественные кнопки Buy No
                r'Outcome.*Outcome',       # Множественные исходы
                r'Option.*Option',         # Множественные опции
            ]
            
            for pattern in multiple_patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    logger.warning(f"⚠️ Найдены множественные варианты: {pattern}")
                    return {
                        'is_boolean': False,
                        'reason': f'Множественные варианты: {pattern}'
                    }
            
            # 4. Проверяем на булевые индикаторы (Yes/No кнопки)
            boolean_button_patterns = [
                r'Yes\s+\d+[¢%]',  # Yes 57.3¢
                r'No\s+\d+[¢%]',   # No 65¢
                r'Trade\s+Yes',     # Trade Yes
                r'Trade\s+No',      # Trade No
                r'Buy\s+Yes',       # Buy Yes
                r'Buy\s+No',        # Buy No
            ]
            
            boolean_buttons_found = False
            for pattern in boolean_button_patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    boolean_buttons_found = True
                    logger.info(f"✅ Найдены булевые кнопки: {pattern}")
                    break
            
            # 5. Проверяем на общие булевые индикаторы
            boolean_found = False
            for pattern in self.boolean_indicators:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    boolean_found = True
                    logger.info(f"✅ Найден булевый индикатор: {pattern}")
                    break
            
            # Если найдены булевые кнопки или индикаторы - рынок булевый
            if boolean_buttons_found or boolean_found:
                return {
                    'is_boolean': True,
                    'reason': 'Найден булевый индикатор'
                }
            else:
                logger.warning("⚠️ Булевые индикаторы не найдены")
                return {
                    'is_boolean': False,
                    'reason': 'Булевые индикаторы не найдены'
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка валидации булевости: {e}")
            return {
                'is_boolean': True,  # По умолчанию считаем булевым при ошибках
                'reason': f'Ошибка валидации: {e}'
            } 