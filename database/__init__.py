# Database module initialization
from .database_connection import DatabaseConnection
from .markets_reader import MarketsReader
from .analytic_writer import AnalyticWriter
from .analytic_updater import AnalyticUpdater
from .active_markets_reader import ActiveMarketsReader

class DatabaseManager:
    """Совместимый класс для обратной совместимости со старым кодом"""
    
    def __init__(self):
        self.connection = DatabaseConnection()
        self.reader = MarketsReader()
        self.writer = AnalyticWriter()
        self.updater = AnalyticUpdater()
        self.active_reader = ActiveMarketsReader()
    
    def insert_market_to_analytic(self, market_data):
        """Добавление рынка в аналитическую таблицу"""
        return self.writer.insert_market_to_analytic(market_data)
    
    def update_market_analysis(self, market_id, analysis_data):
        """Обновление данных анализа рынка"""
        return self.updater.update_market_analysis(market_id, analysis_data)
    
    def market_exists_in_analytic(self, slug):
        """Проверка существования рынка в аналитической таблице"""
        return self.writer.market_exists_in_analytic(slug)
    
    def get_new_markets(self):
        """Получение новых рынков"""
        return self.reader.get_new_markets()
    
    def get_new_markets_after_time(self, start_time):
        """Получение новых рынков после времени"""
        return self.reader.get_new_markets_after_time(start_time)
    
    def get_active_markets(self):
        """Получение активных рынков"""
        return self.active_reader.get_active_markets()
    
    def get_in_progress_markets(self):
        """Получение рынков в работе"""
        return self.active_reader.get_in_progress_markets()
    
    def get_recently_closed_markets(self):
        """Получение недавно закрытых рынков"""
        return self.active_reader.get_recently_closed_markets()
    
    def get_market_info(self, market_id):
        """Получение информации о рынке"""
        return self.active_reader.get_market_info(market_id)
    
    def close_connections(self):
        """Закрытие соединений с БД"""
        return self.connection.close_connections() 