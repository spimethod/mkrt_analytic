import logging
import re
import requests
from analysis.boolean_market_validator import BooleanMarketValidator

logger = logging.getLogger(__name__)

class MarketBooleanPrechecker:
    def __init__(self):
        self.boolean_validator = BooleanMarketValidator()
    
    def precheck_market_boolean(self, slug):
        """
        Предварительная проверка булевости рынка по названию и базовой информации
        
        Args:
            slug (str): Slug рынка
            
        Returns:
            dict: {'is_boolean': bool, 'reason': str, 'should_analyze': bool}
        """
        try:
            logger.info(f"🔍 Предварительная проверка булевости для рынка: {slug}")
            
            # Проверяем название рынка на не-булевые индикаторы
            name_lower = slug.lower()
            
            # Ключевые слова для множественных вариантов
            multiple_outcome_keywords = [
                'countries', 'candidates', 'teams', 'players', 'states', 'parties',
                'options', 'choices', 'outcomes', 'results', 'alternatives',
                'which', 'who', 'what', 'where', 'when', 'how many'
            ]
            
            # Проверяем название на множественные варианты
            for keyword in multiple_outcome_keywords:
                if keyword in name_lower:
                    logger.warning(f"⚠️ Название содержит множественный индикатор: {keyword}")
                    return {
                        'is_boolean': False,
                        'reason': f'Название содержит: {keyword}',
                        'should_analyze': False
                    }
            
            # Проверяем на специфичные не-булевые паттерны в названии
            non_boolean_name_patterns = [
                r'which\s+countries',  # Which countries
                r'which\s+of\s+the',  # Which of the
                r'which\s+candidate',  # Which candidate
                r'which\s+team',       # Which team
                r'which\s+player',     # Which player
                r'which\s+state',      # Which state
                r'which\s+party',      # Which party
                r'who\s+will\s+win',   # Who will win
                r'who\s+will\s+score', # Who will score
                r'what\s+will\s+happen', # What will happen
                r'how\s+many',         # How many
                r'multiple\s+outcomes', # Multiple outcomes
                r'select\s+all',       # Select all
                r'choose\s+from',      # Choose from
            ]
            
            for pattern in non_boolean_name_patterns:
                if re.search(pattern, name_lower, re.IGNORECASE):
                    logger.warning(f"⚠️ Название содержит не-булевый паттерн: {pattern}")
                    return {
                        'is_boolean': False,
                        'reason': f'Название содержит паттерн: {pattern}',
                        'should_analyze': False
                    }
            
            # Проверяем на булевые паттерны в названии
            boolean_name_patterns = [
                r'will\s+.*\s+before',  # Will X before Y
                r'will\s+.*\s+by',      # Will X by Y
                r'will\s+.*\s+in',      # Will X in Y
                r'will\s+.*\s+on',      # Will X on Y
                r'will\s+.*\s+after',   # Will X after Y
                r'will\s+.*\s+until',   # Will X until Y
                r'will\s+.*\s+by\s+the\s+end',  # Will X by the end
                r'will\s+.*\s+resolve',  # Will X resolve
                r'will\s+.*\s+end',     # Will X end
                r'will\s+.*\s+start',   # Will X start
                r'will\s+.*\s+begin',   # Will X begin
                r'will\s+.*\s+stop',    # Will X stop
                r'will\s+.*\s+continue', # Will X continue
                r'will\s+.*\s+change',  # Will X change
                r'will\s+.*\s+increase', # Will X increase
                r'will\s+.*\s+decrease', # Will X decrease
                r'will\s+.*\s+rise',    # Will X rise
                r'will\s+.*\s+fall',    # Will X fall
                r'will\s+.*\s+go\s+up', # Will X go up
                r'will\s+.*\s+go\s+down', # Will X go down
            ]
            
            boolean_found = False
            for pattern in boolean_name_patterns:
                if re.search(pattern, name_lower, re.IGNORECASE):
                    boolean_found = True
                    logger.info(f"✅ Найден булевый паттерн в названии: {pattern}")
                    break
            
            if boolean_found:
                return {
                    'is_boolean': True,
                    'reason': 'Название содержит булевый паттерн',
                    'should_analyze': True
                }
            else:
                # Если не нашли явных индикаторов, разрешаем анализ для дальнейшей проверки
                logger.info(f"ℹ️ Неопределенный паттерн в названии, разрешаем анализ для дальнейшей проверки")
                return {
                    'is_boolean': True,  # По умолчанию считаем булевым
                    'reason': 'Неопределенный паттерн - требуется дальнейший анализ',
                    'should_analyze': True
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка предварительной проверки булевости: {e}")
            return {
                'is_boolean': True,  # По умолчанию разрешаем анализ
                'reason': f'Ошибка проверки: {e}',
                'should_analyze': True
            } 