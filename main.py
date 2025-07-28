import time
import threading
import schedule
import logging
import sys
from datetime import datetime, timedelta, timezone
from database import DatabaseManager
from market_analyzer import MarketAnalyzer
from telegram_bot import TelegramLogger
from config import ANALYSIS_TIME_MINUTES, MAX_RETRIES, RETRY_DELAY_SECONDS, LOGGING_INTERVAL_MINUTES, PING_INTERVAL_MINUTES

# Импортируем настройку логирования
import logging_config

logger = logging.getLogger(__name__)

class MarketAnalysisBot:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.market_analyzer = MarketAnalyzer()
        self.telegram_logger = TelegramLogger()
        self.active_markets = {}  # {market_id: {'start_time': datetime, 'last_log': datetime}}
        self.running = False
        self.bot_start_time = None  # Время запуска бота для фильтрации новых рынков
    
    def start(self):
        """Запуск бота"""
        try:
            logger.info("🚀 Запуск Market Analysis Bot...")
            
            # Устанавливаем флаг работы бота
            self.running = True
            
            # Устанавливаем время запуска бота
            self.bot_start_time = datetime.now(timezone.utc)
            logger.info(f"📅 Время запуска бота: {self.bot_start_time}")
            
            # Закрываем истекшие рынки при запуске
            self.close_expired_markets()
            
            # Проверяем недавно закрытые рынки на предмет ошибочного закрытия
            self.check_recently_closed_markets()
            
            # Детальная проверка последних 3 рынков
            self.verify_last_3_markets_timing()
            
            # Восстанавливаем рынки, которые были в работе до перезапуска
            self.restore_in_progress_markets()
            
            # Запускаем планировщик
            self.run_scheduler()
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска бота: {e}")
            self.telegram_logger.log_error(f"Ошибка запуска бота: {e}")
            raise
    
    def stop(self):
        """Остановка бота"""
        logger.info("Stopping Market Analysis Bot")
        self.running = False
        self.telegram_logger.log_bot_stop()
        
        # Закрываем HTTP клиент Telegram
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.telegram_logger.close())
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Error closing Telegram HTTP client: {e}")
        
        self.market_analyzer.close_driver_sync()
        self.db_manager.close_connections()
    
    def run_scheduler(self):
        """Запуск планировщика задач"""
        try:
            logger.info("📅 Запуск планировщика задач...")
            
            # Логируем запуск бота
            self.telegram_logger.log_bot_start()
            
            # Планируем задачи
            schedule.every(30).seconds.do(self.check_new_markets)
            schedule.every(1).minutes.do(self.update_active_markets)
            schedule.every(10).minutes.do(self.log_market_summaries)
            
            logger.info("✅ Планировщик запущен")
            
            # Запускаем основной цикл
            while self.running:
                schedule.run_pending()
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("⏹️ Бот остановлен пользователем")
            self.stop()
        except Exception as e:
            logger.error(f"❌ Ошибка планировщика: {e}")
            self.telegram_logger.log_error(f"Ошибка планировщика: {e}")
            raise
    
    def check_new_markets(self):
        """Проверка новых рынков каждые 30 секунд"""
        try:
            # Получаем только рынки, созданные после запуска бота
            if self.bot_start_time:
                markets = self.db_manager.get_new_markets_after_time(self.bot_start_time)
                logger.info(f"Checking for new markets created after {self.bot_start_time}")
            else:
                markets = self.db_manager.get_new_markets()
                logger.warning("Bot start time not set, using all markets")
            
            # Получаем список уже работающих рынков из mkrt_analytic
            markets_in_progress = self.db_manager.get_markets_in_progress()
            in_progress_slugs = {market['slug'] for market in markets_in_progress}
            logger.info(f"Found {len(in_progress_slugs)} markets already in progress")
            
            # Получаем список закрытых рынков для исключения
            closed_slugs = self.db_manager.get_closed_markets_slugs()
            logger.info(f"Found {len(closed_slugs)} closed markets to exclude")
            
            # Получаем рынки, которые превысили время анализа
            exceeded_markets = self.db_manager.get_markets_exceeded_analysis_time(ANALYSIS_TIME_MINUTES)
            exceeded_slugs = {market['slug'] for market in exceeded_markets}
            
            if exceeded_slugs:
                logger.info(f"Found {len(exceeded_slugs)} markets that exceeded analysis time: {exceeded_slugs}")
                # Закрываем рынки, превысившие время анализа
                for market in exceeded_markets:
                    self.db_manager.update_market_analysis(market['id'], {'status': 'закрыт (время истекло)'})
                    logger.info(f"Closed market {market['slug']} - analysis time exceeded")
            
            for market in markets:
                # Проверяем, не анализируем ли уже этот рынок (по ID и slug)
                market_id = market['id']
                market_slug = market['slug']
                
                # Проверяем, не в работе ли уже этот рынок
                if market_slug in in_progress_slugs:
                    logger.info(f"Market {market_slug} is already in progress in database, skipping")
                    continue
                
                # Проверяем, не закрыт ли уже этот рынок
                if market_slug in closed_slugs:
                    logger.info(f"Market {market_slug} is already closed, skipping")
                    continue
                
                # Проверяем, не превысил ли рынок время анализа
                if market_slug in exceeded_slugs:
                    logger.info(f"Market {market_slug} exceeded analysis time, skipping")
                    continue
                
                # Проверяем по ID
                if market_id not in self.active_markets:
                    # Дополнительно проверяем по slug
                    slug_in_use = any(
                        active_market['slug'] == market_slug 
                        for active_market in self.active_markets.values()
                    )
                    
                    if not slug_in_use:
                        # Добавляем рынок в аналитическую базу
                        analytic_market_id = self.db_manager.insert_market_to_analytic(market)
                        
                        if analytic_market_id:
                            # Начинаем анализ рынка
                            self.active_markets[market_id] = {
                                'start_time': datetime.now(timezone.utc),
                                'last_log': datetime.now(timezone.utc),
                                'slug': market['slug'],
                                'question': market['question']
                            }
                            
                            # Логируем новый рынок
                            self.telegram_logger.log_new_market(market)
                            logger.info(f"Started analysis for NEW market: {market['slug']} (created: {market['created_at']})")
                            
                            # Запускаем анализ в отдельном потоке
                            analysis_thread = threading.Thread(
                                target=self.analyze_market_continuously,
                                args=(analytic_market_id, market['slug'])
                            )
                            analysis_thread.daemon = True
                            analysis_thread.start()
                        else:
                            logger.warning(f"Failed to insert market {market_slug} to analytic database")
                    else:
                        logger.info(f"Market {market_slug} is already being analyzed, skipping")
                else:
                    logger.info(f"Market ID {market_id} is already in active markets, skipping")
        
        except Exception as e:
            error_msg = f"Error checking new markets: {e}"
            logger.error(error_msg)
            self.telegram_logger.log_error(error_msg)
    
    def analyze_market_continuously(self, market_id, slug):
        """Непрерывный анализ рынка в течение заданного времени"""
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(minutes=ANALYSIS_TIME_MINUTES)
        retry_count = 0
        
        logger.info(f"Starting continuous analysis for market {slug} for {ANALYSIS_TIME_MINUTES} minutes")
        
        while datetime.now(timezone.utc) < end_time and self.running:
            try:
                # Анализируем рынок
                analysis_data = self.market_analyzer.get_market_data(slug)
                
                if analysis_data:
                    # Проверяем, является ли рынок булевым
                    if not analysis_data.get('is_boolean', True):
                        reason = analysis_data.get('reason', 'non_boolean')
                        if reason.startswith('category_'):
                            category = reason.replace('category_', '')
                            logger.info(f"Market {slug} is {category.upper()} category - closing analysis")
                            self.stop_market_analysis(market_id, f"закрыт ({category})")
                        else:
                            logger.info(f"Market {slug} is not boolean - closing analysis")
                            self.stop_market_analysis(market_id, "закрыт (не булевый)")
                        break
                    
                    # Конвертируем данные в нужный формат для базы
                    db_data = {
                        'market_exists': analysis_data.get('market_exists', False),
                        'is_boolean': analysis_data.get('is_boolean', False),
                        'yes_percentage': analysis_data.get('yes_percentage', 0),
                        'volume': analysis_data.get('volume', 'New'),
                        'contract_address': analysis_data.get('contract_address', ''),
                        'status': 'в работе'
                    }
                    
                    # Обновляем данные в базе
                    success = self.db_manager.update_market_analysis(market_id, db_data)
                    if success:
                        logger.info(f"✅ Данные обновлены для {slug}: %Yes={db_data['yes_percentage']}%, Volume={db_data['volume']}, Contract={db_data['contract_address'][:10]}...")
                    else:
                        logger.warning(f"⚠️ Не удалось обновить данные для {slug}")
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
                
                # Ждем PING_INTERVAL_MINUTES минут перед следующим анализом
                time.sleep(PING_INTERVAL_MINUTES * 60)
                
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
                    if datetime.now(timezone.utc) - start_time > timedelta(minutes=ANALYSIS_TIME_MINUTES):
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
                    if datetime.now(timezone.utc) - last_log > timedelta(minutes=LOGGING_INTERVAL_MINUTES):
                        # Логируем данные рынка
                        self.telegram_logger.log_market_data(market)
                        self.active_markets[market['id']]['last_log'] = datetime.now(timezone.utc)
        
        except Exception as e:
            error_msg = f"Error logging market summaries: {e}"
            logger.error(error_msg)
            self.telegram_logger.log_error(error_msg)

    def close_expired_markets(self):
        """Закрытие рынков, превысивших время анализа при запуске"""
        try:
            logger.info("⏰ Проверяем истекшие рынки при запуске...")
            
            # Получаем рынки, которые превысили время анализа
            exceeded_markets = self.db_manager.get_markets_exceeded_analysis_time(ANALYSIS_TIME_MINUTES)
            
            if exceeded_markets:
                logger.info(f"⏰ Найдено {len(exceeded_markets)} рынков, превысивших время анализа")
                for market in exceeded_markets:
                    market_id = market['id']
                    slug = market['slug']
                    logger.info(f"⏰ Закрываем истекший рынок: {slug}")
                    self.db_manager.update_market_analysis(market_id, {'status': 'закрыт (время истекло)'})
            else:
                logger.info("ℹ️ Нет истекших рынков при запуске")
                
        except Exception as e:
            logger.error(f"Error closing expired markets: {e}")

    def restore_in_progress_markets(self):
        """Восстановление анализа для рынков, которые были в работе до перезапуска"""
        try:
            logger.info("🔄 Проверяем рынки, которые были в работе до перезапуска...")
            
            # Получаем все рынки со статусом "в работе"
            in_progress_markets = self.db_manager.get_markets_in_progress()
            
            if not in_progress_markets:
                logger.info("ℹ️ Нет рынков в работе для восстановления")
                return
            
            logger.info(f"📊 Найдено {len(in_progress_markets)} рынков в работе")
            
            current_time = datetime.now(timezone.utc)
            logger.info(f"🕐 Текущее время: {current_time}")
            logger.info(f"⏰ Время анализа (минут): {ANALYSIS_TIME_MINUTES}")
            
            for market in in_progress_markets:
                try:
                    # Правильно обращаемся к словарю
                    market_id = market['id']
                    slug = market['slug']
                    created_at_analytic = market['created_at_analytic']
                    last_updated = market['last_updated']
                    
                    logger.info(f"🔍 Проверяем рынок: {slug} (ID: {market_id})")
                    logger.info(f"📅 Время создания: {created_at_analytic}")
                    logger.info(f"📅 Последнее обновление: {last_updated}")
                    
                    # Проверяем время от создания
                    analysis_end_time_from_created = created_at_analytic + timedelta(minutes=ANALYSIS_TIME_MINUTES)
                    remaining_time_from_created = (analysis_end_time_from_created - current_time).total_seconds() / 60
                    
                    # Проверяем время от последнего обновления
                    analysis_end_time_from_updated = last_updated + timedelta(minutes=ANALYSIS_TIME_MINUTES)
                    remaining_time_from_updated = (analysis_end_time_from_updated - current_time).total_seconds() / 60
                    
                    logger.info(f"⏰ Время анализа истекает (от создания): {analysis_end_time_from_created}")
                    logger.info(f"⏰ Осталось времени (от создания): {remaining_time_from_created:.1f} минут")
                    logger.info(f"⏰ Время анализа истекает (от обновления): {analysis_end_time_from_updated}")
                    logger.info(f"⏰ Осталось времени (от обновления): {remaining_time_from_updated:.1f} минут")
                    
                    # Используем время создания для проверки истечения
                    if current_time >= analysis_end_time_from_created:
                        logger.info(f"⏰ Время анализа истекло для рынка {slug} (от создания) - закрываем")
                        self.db_manager.update_market_analysis(market_id, {'status': 'закрыт (время истекло)'})
                        continue
                    
                    # Проверяем, не анализируем ли уже этот рынок
                    if market_id in self.active_markets:
                        logger.info(f"ℹ️ Рынок {slug} уже в активном анализе, пропускаем")
                        continue
                    
                    # Проверяем, не закрыт ли уже этот рынок
                    closed_slugs = self.db_manager.get_closed_markets_slugs()
                    if slug in closed_slugs:
                        logger.info(f"ℹ️ Рынок {slug} уже закрыт, пропускаем")
                        continue
                    
                    # Проверяем категорию рынка (Sports/Crypto)
                    logger.info(f"🔍 Проверяем категорию для восстановленного рынка: {slug}")
                    
                    # Анализируем рынок для определения категории
                    analysis_data = self.market_analyzer.get_market_data(slug)
                    
                    if analysis_data:
                        # Проверяем, является ли рынок булевым
                        if not analysis_data.get('is_boolean', True):
                            reason = analysis_data.get('reason', 'non_boolean')
                            if reason.startswith('category_'):
                                category = reason.replace('category_', '')
                                logger.info(f"⚠️ Восстановленный рынок {slug} относится к категории {category.upper()} - закрываем")
                                self.db_manager.update_market_analysis(market_id, {'status': f'закрыт ({category})'})
                            else:
                                logger.info(f"⚠️ Восстановленный рынок {slug} не булевый - закрываем")
                                self.db_manager.update_market_analysis(market_id, {'status': 'закрыт (не булевый)'})
                            continue
                        
                        # Рынок подходит для анализа - восстанавливаем мониторинг
                        logger.info(f"✅ Восстанавливаем анализ для рынка {slug}, осталось {remaining_time_from_created:.1f} минут")
                        
                        # Добавляем в активные рынки
                        self.active_markets[market_id] = {
                            'start_time': created_at_analytic,  # Используем время создания
                            'last_log': current_time,
                            'slug': slug,
                            'question': market.get('question', '')
                        }
                        
                        # Запускаем анализ в отдельном потоке
                        analysis_thread = threading.Thread(
                            target=self.analyze_market_continuously,
                            args=(market_id, slug)
                        )
                        analysis_thread.daemon = True
                        analysis_thread.start()
                        
                        logger.info(f"🔄 Восстановлен мониторинг для рынка: {slug}")
                        
                    else:
                        logger.warning(f"⚠️ Не удалось получить данные для восстановленного рынка {slug}")
                        continue
                        
                except Exception as e:
                    logger.error(f"❌ Ошибка восстановления рынка {market.get('slug', 'unknown')}: {e}")
                    continue
            
            logger.info(f"✅ Восстановление завершено. Активных рынков: {len(self.active_markets)}")
            
        except Exception as e:
            error_msg = f"Ошибка восстановления рынков: {e}"
            logger.error(error_msg)
            self.telegram_logger.log_error(error_msg)

    def check_recently_closed_markets(self):
        """Проверка недавно закрытых рынков на предмет ошибочного закрытия"""
        try:
            logger.info("🔍 Проверяем недавно закрытые рынки на предмет ошибочного закрытия...")
            
            # Получаем последние 10 закрытых рынков
            recently_closed = self.db_manager.get_recently_closed_markets(10)
            
            if not recently_closed:
                logger.info("ℹ️ Нет недавно закрытых рынков для проверки")
                return
            
            logger.info(f"📊 Найдено {len(recently_closed)} недавно закрытых рынков")
            
            current_time = datetime.now(timezone.utc)
            
            for market in recently_closed:
                try:
                    market_id = market['id']
                    slug = market['slug']
                    status = market['status']
                    created_at_analytic = market['created_at_analytic']
                    last_updated = market['last_updated']
                    
                    logger.info(f"🔍 Проверяем закрытый рынок: {slug} (ID: {market_id})")
                    logger.info(f"📅 Статус: {status}")
                    logger.info(f"📅 Время создания: {created_at_analytic}")
                    logger.info(f"📅 Последнее обновление: {last_updated}")
                    
                    # Проверяем время от создания
                    analysis_end_time_from_created = created_at_analytic + timedelta(minutes=ANALYSIS_TIME_MINUTES)
                    remaining_time_from_created = (analysis_end_time_from_created - current_time).total_seconds() / 60
                    
                    # Проверяем время от последнего обновления
                    analysis_end_time_from_updated = last_updated + timedelta(minutes=ANALYSIS_TIME_MINUTES)
                    remaining_time_from_updated = (analysis_end_time_from_updated - current_time).total_seconds() / 60
                    
                    logger.info(f"⏰ Время анализа истекает (от создания): {analysis_end_time_from_created}")
                    logger.info(f"⏰ Осталось времени (от создания): {remaining_time_from_created:.1f} минут")
                    logger.info(f"⏰ Время анализа истекает (от обновления): {analysis_end_time_from_updated}")
                    logger.info(f"⏰ Осталось времени (от обновления): {remaining_time_from_updated:.1f} минут")
                    
                    # Проверяем, не истекло ли время на самом деле
                    if current_time < analysis_end_time_from_created:
                        logger.warning(f"⚠️ Рынок {slug} был ошибочно закрыт! Время еще не истекло")
                        
                        # Проверяем категорию рынка
                        logger.info(f"🔍 Проверяем категорию для ошибочно закрытого рынка: {slug}")
                        
                        analysis_data = self.market_analyzer.get_market_data(slug)
                        
                        if analysis_data:
                            # Проверяем, является ли рынок булевым
                            if not analysis_data.get('is_boolean', True):
                                reason = analysis_data.get('reason', 'non_boolean')
                                if reason.startswith('category_'):
                                    category = reason.replace('category_', '')
                                    logger.info(f"⚠️ Рынок {slug} действительно относится к категории {category.upper()} - оставляем закрытым")
                                else:
                                    logger.info(f"⚠️ Рынок {slug} действительно не булевый - оставляем закрытым")
                            else:
                                # Рынок подходит для анализа - восстанавливаем
                                logger.info(f"✅ Восстанавливаем ошибочно закрытый рынок {slug}, осталось {remaining_time_from_created:.1f} минут")
                                
                                # Проверяем, не истекло ли время анализа
                                current_time = datetime.now(timezone.utc)
                                analysis_end_time = created_at_analytic + timedelta(minutes=ANALYSIS_TIME_MINUTES)
                                remaining_time = (analysis_end_time - current_time).total_seconds() / 60
                                
                                if remaining_time <= 0:
                                    logger.warning(f"⚠️ Время анализа уже истекло для восстановленного рынка {slug}")
                                    self.db_manager.update_market_analysis(market_id, {'status': 'закрыт (время истекло)'})
                                else:
                                    logger.info(f"⏰ Осталось времени для анализа: {remaining_time:.1f} минут")
                                    
                                    # Возвращаем статус "в работе"
                                    self.db_manager.update_market_analysis(market_id, {'status': 'в работе'})
                                    
                                    # Добавляем в активные рынки
                                    self.active_markets[market_id] = {
                                        'start_time': created_at_analytic,
                                        'last_log': current_time,
                                        'slug': slug,
                                        'question': market.get('question', '')
                                    }
                                    
                                    # Запускаем анализ в отдельном потоке
                                    analysis_thread = threading.Thread(
                                        target=self.analyze_market_continuously_restored,
                                        args=(market_id, slug)
                                    )
                                    analysis_thread.daemon = True
                                    analysis_thread.start()
                                    
                                    logger.info(f"🔄 Восстановлен ошибочно закрытый рынок: {slug}")
                        else:
                            logger.warning(f"⚠️ Не удалось получить данные для ошибочно закрытого рынка {slug}")
                    else:
                        logger.info(f"ℹ️ Рынок {slug} был правильно закрыт - время истекло")
                        
                except Exception as e:
                    logger.error(f"❌ Ошибка проверки закрытого рынка {market.get('slug', 'unknown')}: {e}")
                    continue
            
            logger.info(f"✅ Проверка закрытых рынков завершена. Активных рынков: {len(self.active_markets)}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки закрытых рынков: {e}")
            self.telegram_logger.log_error(f"Ошибка проверки закрытых рынков: {e}")

    def verify_last_3_markets_timing(self):
        """Детальная проверка времени последних 3 рынков"""
        try:
            logger.info("🔍 Детальная проверка времени последних 3 рынков...")
            
            # Получаем последние 3 рынка
            last_3_markets = self.db_manager.get_last_3_markets_for_verification()
            
            if not last_3_markets:
                logger.info("ℹ️ Нет рынков для детальной проверки")
                return
            
            logger.info(f"📊 Найдено {len(last_3_markets)} последних рынков для проверки")
            
            current_time = datetime.now(timezone.utc)
            
            for i, market in enumerate(last_3_markets, 1):
                try:
                    market_id = market['id']
                    slug = market['slug']
                    status = market['status']
                    created_at_analytic = market['created_at_analytic']
                    last_updated = market['last_updated']
                    
                    logger.info(f"🔍 Рынок #{i}: {slug} (ID: {market_id})")
                    logger.info(f"📅 Статус: {status}")
                    logger.info(f"📅 Время создания: {created_at_analytic}")
                    logger.info(f"📅 Последнее обновление: {last_updated}")
                    
                    # Вычисляем время анализа
                    analysis_end_time_from_created = created_at_analytic + timedelta(minutes=ANALYSIS_TIME_MINUTES)
                    remaining_time_from_created = (analysis_end_time_from_created - current_time).total_seconds() / 60
                    
                    analysis_end_time_from_updated = last_updated + timedelta(minutes=ANALYSIS_TIME_MINUTES)
                    remaining_time_from_updated = (analysis_end_time_from_updated - current_time).total_seconds() / 60
                    
                    logger.info(f"⏰ Время анализа истекает (от создания): {analysis_end_time_from_created}")
                    logger.info(f"⏰ Осталось времени (от создания): {remaining_time_from_created:.1f} минут")
                    logger.info(f"⏰ Время анализа истекает (от обновления): {analysis_end_time_from_updated}")
                    logger.info(f"⏰ Осталось времени (от обновления): {remaining_time_from_updated:.1f} минут")
                    
                    # Проверяем, был ли рынок ошибочно закрыт
                    if status.startswith('закрыт') and current_time < analysis_end_time_from_created:
                        logger.warning(f"⚠️ РЫНОК #{i} БЫЛ ОШИБОЧНО ЗАКРЫТ!")
                        logger.warning(f"⚠️ {slug} - время еще не истекло, осталось {remaining_time_from_created:.1f} минут")
                        
                        # Проверяем категорию и булевость
                        logger.info(f"🔍 Проверяем категорию для ошибочно закрытого рынка: {slug}")
                        
                        analysis_data = self.market_analyzer.get_market_data(slug)
                        
                        if analysis_data:
                            if not analysis_data.get('is_boolean', True):
                                reason = analysis_data.get('reason', 'non_boolean')
                                if reason.startswith('category_'):
                                    category = reason.replace('category_', '')
                                    logger.info(f"⚠️ Рынок {slug} действительно относится к категории {category.upper()} - оставляем закрытым")
                                else:
                                    logger.info(f"⚠️ Рынок {slug} действительно не булевый - оставляем закрытым")
                            else:
                                # Восстанавливаем ошибочно закрытый рынок
                                logger.info(f"✅ ВОССТАНАВЛИВАЕМ ОШИБОЧНО ЗАКРЫТЫЙ РЫНОК #{i}: {slug}")
                                
                                # Проверяем, не истекло ли время анализа
                                current_time = datetime.now(timezone.utc)
                                analysis_end_time = created_at_analytic + timedelta(minutes=ANALYSIS_TIME_MINUTES)
                                remaining_time = (analysis_end_time - current_time).total_seconds() / 60
                                
                                if remaining_time <= 0:
                                    logger.warning(f"⚠️ Время анализа уже истекло для восстановленного рынка {slug}")
                                    self.db_manager.update_market_analysis(market_id, {'status': 'закрыт (время истекло)'})
                                else:
                                    logger.info(f"⏰ Осталось времени для анализа: {remaining_time:.1f} минут")
                                    
                                    # Возвращаем статус "в работе"
                                    self.db_manager.update_market_analysis(market_id, {'status': 'в работе'})
                                    
                                    # Добавляем в активные рынки
                                    self.active_markets[market_id] = {
                                        'start_time': created_at_analytic,
                                        'last_log': current_time,
                                        'slug': slug,
                                        'question': market.get('question', '')
                                    }
                                    
                                    # Запускаем анализ в отдельном потоке БЕЗ повторной проверки категории
                                    analysis_thread = threading.Thread(
                                        target=self.analyze_market_continuously_restored,
                                        args=(market_id, slug)
                                    )
                                    analysis_thread.daemon = True
                                    analysis_thread.start()
                                    
                                    logger.info(f"🔄 Восстановлен ошибочно закрытый рынок #{i}: {slug}")
                        else:
                            logger.warning(f"⚠️ Не удалось получить данные для ошибочно закрытого рынка {slug}")
                    elif status.startswith('закрыт'):
                        logger.info(f"ℹ️ Рынок #{i} {slug} был правильно закрыт - время истекло")
                    else:
                        logger.info(f"ℹ️ Рынок #{i} {slug} в статусе: {status}")
                        
                except Exception as e:
                    logger.error(f"❌ Ошибка проверки рынка #{i} {market.get('slug', 'unknown')}: {e}")
                    continue
            
            logger.info(f"✅ Детальная проверка завершена. Активных рынков: {len(self.active_markets)}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка детальной проверки рынков: {e}")
            self.telegram_logger.log_error(f"Ошибка детальной проверки рынков: {e}")
    
    def analyze_market_continuously_restored(self, market_id, slug):
        """Непрерывный анализ восстановленного рынка БЕЗ повторной проверки категории"""
        # Получаем время создания рынка из базы данных
        market_data = self.db_manager.get_market_by_id(market_id)
        if not market_data:
            logger.error(f"Cannot find market data for ID {market_id}")
            return
        
        created_at_analytic = market_data['created_at_analytic']
        end_time = created_at_analytic + timedelta(minutes=ANALYSIS_TIME_MINUTES)
        retry_count = 0
        
        logger.info(f"Starting continuous analysis for RESTORED market {slug} until {end_time}")
        
        while datetime.now(timezone.utc) < end_time and self.running:
            try:
                # Анализируем рынок
                analysis_data = self.market_analyzer.get_market_data(slug)
                
                if analysis_data:
                    # Конвертируем данные в нужный формат для базы
                    db_data = {
                        'market_exists': analysis_data.get('market_exists', False),
                        'is_boolean': analysis_data.get('is_boolean', False),
                        'yes_percentage': analysis_data.get('yes_percentage', 0),
                        'volume': analysis_data.get('volume', 'New'),
                        'contract_address': analysis_data.get('contract_address', ''),
                        'status': 'в работе'
                    }
                    
                    # Обновляем данные в базе
                    success = self.db_manager.update_market_analysis(market_id, db_data)
                    if success:
                        logger.info(f"✅ Данные обновлены для {slug}: %Yes={db_data['yes_percentage']}%, Volume={db_data['volume']}, Contract={db_data['contract_address'][:10]}...")
                    else:
                        logger.warning(f"⚠️ Не удалось обновить данные для {slug}")
                    retry_count = 0  # Сбрасываем счетчик ошибок при успехе
                else:
                    retry_count += 1
                    if retry_count >= MAX_RETRIES:
                        logger.error(f"Max retries reached for RESTORED market {slug}, stopping analysis")
                        self.stop_market_analysis(market_id, "закрыт")
                        break
                    else:
                        logger.warning(f"Analysis failed for RESTORED market {slug}, retry {retry_count}/{MAX_RETRIES}")
                        time.sleep(RETRY_DELAY_SECONDS)
                        continue
                
                # Ждем PING_INTERVAL_MINUTES минут перед следующим анализом
                time.sleep(PING_INTERVAL_MINUTES * 60)
                
            except Exception as e:
                retry_count += 1
                error_msg = f"Error analyzing RESTORED market {slug}: {e}"
                logger.error(error_msg)
                self.telegram_logger.log_error(error_msg, slug)
                
                if retry_count >= MAX_RETRIES:
                    logger.error(f"Max retries reached for RESTORED market {slug}, stopping analysis")
                    self.stop_market_analysis(market_id, "закрыт")
                    break
                else:
                    time.sleep(RETRY_DELAY_SECONDS)
        
        # Завершаем анализ рынка только если время действительно истекло
        if datetime.now(timezone.utc) >= end_time:
            logger.info(f"Analysis time expired for RESTORED market {slug}")
            self.stop_market_analysis(market_id, "закрыт (время истекло)")
        elif market_id in self.active_markets:
            logger.info(f"Stopping analysis for RESTORED market {slug} due to bot shutdown")
            self.stop_market_analysis(market_id, "закрыт")

    def add_market_by_slug(self, slug):
        """Добавление рынка в аналитическую базу по слаг для анализа"""
        try:
            logger.info(f"🔍 Добавление рынка по слаг: {slug}")
            
            # Проверяем, не анализируется ли уже этот рынок
            existing_market = self.db_manager.get_market_by_slug(slug)
            if existing_market:
                logger.warning(f"Рынок {slug} уже существует в аналитической базе")
                return False
            
            # Получаем данные рынка через MarketAnalyzer
            analysis_data = self.market_analyzer.get_market_data(slug)
            
            if not analysis_data:
                logger.error(f"Не удалось получить данные для рынка {slug}")
                return False
            
            # Создаем базовые данные рынка
            market_data = {
                'id': None,  # Будет сгенерирован автоматически
                'question': f"Market: {slug}",  # Временное название
                'created_at': datetime.now(timezone.utc),
                'active': True,
                'enable_order_book': True,
                'slug': slug,
                'market_exists': analysis_data.get('market_exists', True),
                'is_boolean': analysis_data.get('is_boolean', True),
                'yes_percentage': analysis_data.get('yes_percentage', 0),
                'volume': analysis_data.get('volume', 'New'),
                'contract_address': analysis_data.get('contract_address', ''),
                'status': 'в работе'
            }
            
            # Добавляем рынок в аналитическую базу
            analytic_market_id = self.db_manager.insert_market_to_analytic(market_data)
            
            if analytic_market_id:
                logger.info(f"✅ Рынок {slug} успешно добавлен в аналитическую базу (ID: {analytic_market_id})")
                
                # Добавляем в активные рынки
                self.active_markets[analytic_market_id] = {
                    'start_time': datetime.now(timezone.utc),
                    'last_log': datetime.now(timezone.utc),
                    'slug': slug,
                    'question': market_data['question']
                }
                
                # Логируем новый рынок
                self.telegram_logger.log_new_market({
                    'slug': slug,
                    'question': market_data['question']
                })
                
                # Запускаем анализ в отдельном потоке
                analysis_thread = threading.Thread(
                    target=self.analyze_market_continuously,
                    args=(analytic_market_id, slug)
                )
                analysis_thread.daemon = True
                analysis_thread.start()
                
                logger.info(f"🚀 Анализ рынка {slug} запущен")
                return True
            else:
                logger.error(f"❌ Не удалось добавить рынок {slug} в аналитическую базу")
                return False
                
        except Exception as e:
            error_msg = f"Ошибка добавления рынка {slug}: {e}"
            logger.error(error_msg)
            self.telegram_logger.log_error(error_msg)
            return False

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