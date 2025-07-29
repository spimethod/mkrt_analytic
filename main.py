import time
import threading
import schedule
import logging
from datetime import datetime, timedelta, timezone
from database import DatabaseManager
from market_analyzer import MarketAnalyzer
from telegram_bot import TelegramLogger
from config import ANALYSIS_TIME_MINUTES, MAX_RETRIES, RETRY_DELAY_SECONDS, LOGGING_INTERVAL_MINUTES

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class MarketAnalysisBot:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.market_analyzer = MarketAnalyzer()
        self.telegram_logger = TelegramLogger()
        self.active_markets = {}  # {market_id: {'start_time': datetime, 'last_log': datetime}}
        self.running = False
    
    def start(self):
        """Запуск бота"""
        logger.info("Starting Market Analysis Bot")
        self.telegram_logger.log_bot_start()
        self.running = True
        
        # Восстанавливаем зависшие рынки при запуске
        self.restore_in_progress_markets()
        
        # Планируем задачи
        schedule.every(30).seconds.do(self.check_new_markets)
        schedule.every(1).minutes.do(self.update_active_markets)
        schedule.every(10).minutes.do(self.log_market_summaries)
        schedule.every(5).minutes.do(self.check_recently_closed_markets)
        
        # Запускаем планировщик в отдельном потоке
        scheduler_thread = threading.Thread(target=self.run_scheduler)
        scheduler_thread.daemon = True
        scheduler_thread.start()
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            self.stop()
    
    def stop(self):
        """Остановка бота"""
        logger.info("Stopping Market Analysis Bot")
        self.running = False
        self.telegram_logger.log_bot_stop()
        self.market_analyzer.close_driver()
        self.db_manager.close_connections()
    
    def run_scheduler(self):
        """Запуск планировщика задач"""
        while self.running:
            schedule.run_pending()
            time.sleep(1)
    
    def add_market_by_slug(self, slug):
        """Добавление рынка в аналитическую базу по slug"""
        try:
            logger.info(f"🔄 Добавляем рынок по slug: {slug}")
            
            # Проверяем, существует ли рынок в аналитической базе
            if self.db_manager.market_exists_in_analytic(slug):
                logger.info(f"ℹ️ Рынок {slug} уже существует в аналитической БД")
                return False
            
            # Получаем данные рынка
            market_data = {
                'id': 0,  # Временный ID
                'question': f"Market: {slug}",
                'slug': slug
            }
            
            # Добавляем в аналитическую базу
            market_id = self.db_manager.insert_market_to_analytic(market_data)
            
            if market_id:
                logger.info(f"✅ Рынок {slug} успешно добавлен в аналитическую БД")
                
                # Начинаем анализ
                self.active_markets[market_id] = {
                    'start_time': datetime.now(),
                    'last_log': datetime.now(),
                    'slug': slug,
                    'question': market_data['question']
                }
                
                # Запускаем анализ в отдельном потоке
                analysis_thread = threading.Thread(
                    target=self.analyze_market_continuously,
                    args=(market_id, slug)
                )
                analysis_thread.daemon = True
                analysis_thread.start()
                
                return True
            else:
                logger.error(f"❌ Не удалось добавить рынок {slug}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка добавления рынка {slug}: {e}")
            return False
    
    def restore_in_progress_markets(self):
        """Восстановление зависших рынков при запуске"""
        try:
            logger.info("🔄 Восстанавливаем зависшие рынки...")
            
            # Получаем рынки со статусом "в работе"
            in_progress_markets = self.db_manager.get_in_progress_markets()
            
            for market in in_progress_markets:
                market_id = market['id']
                slug = market['slug']
                
                logger.info(f"🔄 Восстанавливаем рынок: {slug}")
                
                # Проверяем категорию рынка
                try:
                    category_check = self.market_analyzer.check_market_category_sync(slug)
                    if not category_check['is_boolean']:
                        logger.info(f"⚠️ Рынок {slug} не подходит по категории, пропускаем")
                        self.db_manager.update_market_analysis(market_id, {'status': 'закрыт'})
                        continue
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось проверить категорию для {slug}: {e}")
                    # Продолжаем анализ даже при ошибке проверки категории
                
                # Добавляем в активные рынки
                self.active_markets[market_id] = {
                    'start_time': datetime.now(),
                    'last_log': datetime.now(),
                    'slug': slug,
                    'question': market.get('question', f"Market: {slug}")
                }
                
                # Запускаем анализ в отдельном потоке
                analysis_thread = threading.Thread(
                    target=self.analyze_market_continuously_restored,
                    args=(market_id, slug)
                )
                analysis_thread.daemon = True
                analysis_thread.start()
                
                logger.info(f"✅ Рынок {slug} восстановлен")
            
            logger.info(f"✅ Восстановление завершено, активных рынков: {len(self.active_markets)}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка восстановления зависших рынков: {e}")
    
    def check_recently_closed_markets(self):
        """Проверка недавно закрытых рынков на предмет ошибочного закрытия"""
        try:
            logger.info("🔍 Проверяем недавно закрытые рынки...")
            
            # Получаем рынки, закрытые в последние 10 минут
            recently_closed = self.db_manager.get_recently_closed_markets()
            
            current_time = datetime.now()
            
            for market in recently_closed:
                market_id = market['id']
                slug = market['slug']
                created_at = market['created_at_analytic']
                
                # Проверяем, не истекло ли время анализа
                analysis_end_time_from_created = created_at + timedelta(minutes=ANALYSIS_TIME_MINUTES)
                remaining_time_from_created = (analysis_end_time_from_created - current_time).total_seconds() / 60
                
                if current_time < analysis_end_time_from_created:
                    logger.warning(f"⚠️ Рынок {slug} был ошибочно закрыт! Время еще не истекло")
                    
                    # Проверяем категорию рынка
                    try:
                        category_check = self.market_analyzer.check_market_category_sync(slug)
                        if not category_check['is_boolean']:
                            logger.info(f"⚠️ Рынок {slug} не подходит по категории, оставляем закрытым")
                            continue
                    except Exception as e:
                        logger.warning(f"⚠️ Не удалось проверить категорию для {slug}: {e}")
                        # Продолжаем восстановление даже при ошибке проверки категории
                    
                    # Рынок подходит для анализа - восстанавливаем
                    logger.info(f"✅ Восстанавливаем ошибочно закрытый рынок {slug}, осталось {remaining_time_from_created:.1f} минут")
                    
                    # Обновляем статус
                    self.db_manager.update_market_analysis(market_id, {'status': 'в работе'})
                    
                    # Добавляем в активные рынки
                    self.active_markets[market_id] = {
                        'start_time': datetime.now(),
                        'last_log': datetime.now(),
                        'slug': slug,
                        'question': market.get('question', f"Market: {slug}")
                    }
                    
                    # Запускаем анализ в отдельном потоке
                    analysis_thread = threading.Thread(
                        target=self.analyze_market_continuously_restored,
                        args=(market_id, slug)
                    )
                    analysis_thread.daemon = True
                    analysis_thread.start()
                    
                    logger.info(f"✅ Рынок {slug} восстановлен после ошибочного закрытия")
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки недавно закрытых рынков: {e}")
    
    def check_new_markets(self):
        """Проверка новых рынков каждые 30 секунд"""
        try:
            markets = self.db_manager.get_new_markets()
            
            for market in markets:
                # Проверяем, не анализируем ли уже этот рынок
                if market['id'] not in self.active_markets:
                    # Проверяем категорию рынка
                    try:
                        category_check = self.market_analyzer.check_market_category_sync(market['slug'])
                        if not category_check['is_boolean']:
                            logger.info(f"⚠️ Рынок {market['slug']} не подходит по категории, пропускаем")
                            continue
                    except Exception as e:
                        logger.warning(f"⚠️ Не удалось проверить категорию для {market['slug']}: {e}")
                        # Продолжаем анализ даже при ошибке проверки категории
                    
                    # Добавляем рынок в аналитическую базу
                    market_id = self.db_manager.insert_market_to_analytic(market)
                    
                    if market_id:
                        # Начинаем анализ рынка
                        self.active_markets[market_id] = {
                            'start_time': datetime.now(),
                            'last_log': datetime.now(),
                            'slug': market['slug'],
                            'question': market['question']
                        }
                        
                        # Логируем новый рынок
                        self.telegram_logger.log_new_market(market)
                        logger.info(f"Started analysis for market: {market['slug']}")
                        
                        # Запускаем анализ в отдельном потоке
                        analysis_thread = threading.Thread(
                            target=self.analyze_market_continuously,
                            args=(market_id, market['slug'])
                        )
                        analysis_thread.daemon = True
                        analysis_thread.start()
        
        except Exception as e:
            error_msg = f"Error checking new markets: {e}"
            logger.error(error_msg)
            self.telegram_logger.log_error(error_msg)
    
    def analyze_market_continuously(self, market_id, slug):
        """Непрерывный анализ рынка в течение заданного времени"""
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=ANALYSIS_TIME_MINUTES)
        retry_count = 0
        
        logger.info(f"Starting continuous analysis for market {slug} for {ANALYSIS_TIME_MINUTES} minutes")
        
        while datetime.now() < end_time and self.running:
            try:
                # Анализируем рынок
                analysis_data = self.market_analyzer.analyze_market(slug)
                
                if analysis_data:
                    # Обновляем данные в базе
                    self.db_manager.update_market_analysis(market_id, analysis_data)
                    retry_count = 0  # Сбрасываем счетчик ошибок при успехе
                else:
                    retry_count += 1
                    if retry_count >= MAX_RETRIES:
                        logger.error(f"Max retries reached for market {slug}, stopping analysis")
                        self.stop_market_analysis(market_id, "закрыт")
                        break
                    else:
                        logger.warning(f"Analysis failed for market {slug}, retry {retry_count}/{MAX_RETRIES}")
                        time.sleep(RETRY_DELAY_SECONDS)
                        continue
                
                # Ждем 1 минуту перед следующим анализом
                time.sleep(60)
                
            except Exception as e:
                retry_count += 1
                error_msg = f"Error analyzing market {slug}: {e}"
                logger.error(error_msg)
                self.telegram_logger.log_error(error_msg, slug)
                
                if retry_count >= MAX_RETRIES:
                    logger.error(f"Max retries reached for market {slug}, stopping analysis")
                    self.stop_market_analysis(market_id, "закрыт")
                    break
                else:
                    time.sleep(RETRY_DELAY_SECONDS)
        
        # Завершаем анализ рынка
        if market_id in self.active_markets:
            self.stop_market_analysis(market_id, "закрыт")
    
    def analyze_market_continuously_restored(self, market_id, slug):
        """Непрерывный анализ восстановленного рынка"""
        try:
            # Получаем время создания из базы
            market_info = self.db_manager.get_market_info(market_id)
            if not market_info:
                logger.error(f"❌ Не удалось получить информацию о рынке {market_id}")
                return
            
            created_at = market_info['created_at_analytic']
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            
            # Вычисляем время окончания анализа
            end_time = created_at + timedelta(minutes=ANALYSIS_TIME_MINUTES)
            current_time = datetime.now(timezone.utc)
            
            if current_time >= end_time:
                logger.info(f"⏰ Время анализа для восстановленного рынка {slug} истекло")
                self.stop_market_analysis(market_id, "закрыт")
                return
            
            # Продолжаем анализ до истечения времени
            remaining_minutes = (end_time - current_time).total_seconds() / 60
            logger.info(f"🔄 Продолжаем анализ восстановленного рынка {slug}, осталось {remaining_minutes:.1f} минут")
            
            retry_count = 0
            
            while datetime.now(timezone.utc) < end_time and self.running:
                try:
                    # Анализируем рынок
                    analysis_data = self.market_analyzer.analyze_market(slug)
                    
                    if analysis_data:
                        # Обновляем данные в базе
                        self.db_manager.update_market_analysis(market_id, analysis_data)
                        retry_count = 0
                    else:
                        retry_count += 1
                        if retry_count >= MAX_RETRIES:
                            logger.error(f"Max retries reached for restored market {slug}, stopping analysis")
                            self.stop_market_analysis(market_id, "закрыт")
                            break
                        else:
                            logger.warning(f"Analysis failed for restored market {slug}, retry {retry_count}/{MAX_RETRIES}")
                            time.sleep(RETRY_DELAY_SECONDS)
                            continue
                    
                    # Ждем 1 минуту перед следующим анализом
                    time.sleep(60)
                    
                except Exception as e:
                    retry_count += 1
                    error_msg = f"Error analyzing restored market {slug}: {e}"
                    logger.error(error_msg)
                    self.telegram_logger.log_error(error_msg, slug)
                    
                    if retry_count >= MAX_RETRIES:
                        logger.error(f"Max retries reached for restored market {slug}, stopping analysis")
                        self.stop_market_analysis(market_id, "закрыт")
                        break
                    else:
                        time.sleep(RETRY_DELAY_SECONDS)
            
            # Завершаем анализ рынка
            if market_id in self.active_markets:
                self.stop_market_analysis(market_id, "закрыт")
                
        except Exception as e:
            logger.error(f"❌ Ошибка анализа восстановленного рынка {slug}: {e}")
            self.stop_market_analysis(market_id, "закрыт")
    
    def stop_market_analysis(self, market_id, status):
        """Остановка анализа рынка"""
        if market_id in self.active_markets:
            market_info = self.active_markets[market_id]
            
            # Обновляем статус в базе
            self.db_manager.update_market_analysis(market_id, {'status': status})
            
            # Логируем остановку
            market_data = {
                'question': market_info['question'],
                'slug': market_info['slug'],
                'status': status
            }
            self.telegram_logger.log_market_stopped(market_data)
            
            # Удаляем из активных рынков
            del self.active_markets[market_id]
            logger.info(f"Stopped analysis for market {market_info['slug']}")
    
    def update_active_markets(self):
        """Обновление активных рынков каждую минуту"""
        try:
            active_markets = self.db_manager.get_active_markets()
            
            for market in active_markets:
                if market['id'] in self.active_markets:
                    # Проверяем, не истекло ли время анализа
                    start_time = self.active_markets[market['id']]['start_time']
                    if datetime.now() - start_time > timedelta(minutes=ANALYSIS_TIME_MINUTES):
                        self.stop_market_analysis(market['id'], "закрыт")
        
        except Exception as e:
            error_msg = f"Error updating active markets: {e}"
            logger.error(error_msg)
            self.telegram_logger.log_error(error_msg)
    
    def log_market_summaries(self):
        """Логирование сводки по рынкам каждые 10 минут"""
        try:
            active_markets = self.db_manager.get_active_markets()
            
            for market in active_markets:
                if market['id'] in self.active_markets:
                    # Проверяем, прошло ли 10 минут с последнего логирования
                    last_log = self.active_markets[market['id']]['last_log']
                    if datetime.now() - last_log > timedelta(minutes=LOGGING_INTERVAL_MINUTES):
                        # Логируем данные рынка
                        self.telegram_logger.log_market_data(market)
                        self.active_markets[market['id']]['last_log'] = datetime.now()
        
        except Exception as e:
            error_msg = f"Error logging market summaries: {e}"
            logger.error(error_msg)
            self.telegram_logger.log_error(error_msg)

def main():
    """Главная функция"""
    bot = MarketAnalysisBot()
    try:
        bot.start()
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
        bot.stop()

if __name__ == "__main__":
    main() 