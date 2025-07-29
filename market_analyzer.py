import asyncio
import logging
import re
from datetime import datetime
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

# Совместимый MarketAnalyzer для обратной совместимости
from analysis.market_analyzer_core import MarketAnalyzerCore

class MarketAnalyzer:
    """Совместимый класс для обратной совместимости"""
    
    def __init__(self):
        self.core = MarketAnalyzerCore()
    
    def analyze_market(self, slug):
        """Анализ рынка"""
        return self.core.analyze_market(slug)
    
    def check_market_category_sync(self, slug):
        """Проверка категории рынка"""
        return self.core.check_market_category_sync(slug)
    
    def close_driver(self):
        """Закрытие браузера"""
        return self.core.close_driver() 