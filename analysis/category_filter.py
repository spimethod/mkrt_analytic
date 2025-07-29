import logging

logger = logging.getLogger(__name__)

class CategoryFilter:
    def __init__(self):
        self.sports_keywords = [
            'sports', 'football', 'basketball', 'soccer', 'tennis', 
            'baseball', 'hockey', 'golf', 'olympics', 'championship', 
            'league', 'cup', 'tournament', 'match', 'game', 'team'
        ]
        self.crypto_keywords = [
            'crypto', 'bitcoin', 'ethereum', 'btc', 'eth', 'blockchain', 
            'defi', 'nft', 'token', 'coin', 'cryptocurrency', 'altcoin'
        ]
    
    def check_category(self, slug):
        """Проверка категории рынка по slug"""
        try:
            slug_lower = slug.lower()
            
            # Проверяем Sports категорию
            for keyword in self.sports_keywords:
                if keyword in slug_lower:
                    logger.info(f"⚠️ Рынок {slug} исключен по категории Sports (содержит '{keyword}')")
                    return {'is_boolean': False, 'category': 'sports'}
            
            # Проверяем Crypto категорию
            for keyword in self.crypto_keywords:
                if keyword in slug_lower:
                    logger.info(f"⚠️ Рынок {slug} исключен по категории Crypto (содержит '{keyword}')")
                    return {'is_boolean': False, 'category': 'crypto'}
            
            # По умолчанию разрешаем все остальные рынки
            logger.info(f"✅ Рынок {slug} прошел проверку категории")
            return {'is_boolean': True, 'category': 'boolean'}
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки категории для {slug}: {e}")
            return {'is_boolean': True, 'category': 'unknown'}  # По умолчанию разрешаем 