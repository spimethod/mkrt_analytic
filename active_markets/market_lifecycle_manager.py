import logging
import time
import threading
from datetime import datetime, timedelta
from config.config_loader import ConfigLoader
from analysis.market_analyzer_core import MarketAnalyzerCore
from database.analytic_updater import AnalyticUpdater
from telegram.market_stopped_logger import MarketStoppedLogger

logger = logging.getLogger(__name__)

class MarketLifecycleManager:
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.config = ConfigLoader()
        self.analyzer = MarketAnalyzerCore()
        self.updater = AnalyticUpdater()
        self.stopped_logger = MarketStoppedLogger()
        
        # Конфигурация
        self.analysis_time_minutes = self.config.get_analysis_time_minutes()
        self.max_retries = self.config.get_max_retries()
        self.retry_delay_seconds = self.config.get_retry_delay_seconds()
    
    def start_market_analysis(self, market_id, market):
        """Начало анализа рынка"""
        try:
            self.bot.active_markets[market_id] = {
                'start_time': datetime.now(),
                'last_log': datetime.now(),
                'slug': market['slug'],
                'question': market['question']
            }
            logger.info(f"✅ Анализ рынка {market['slug']} начат")
        except Exception as e:
            logger.error(f"❌ Ошибка начала анализа рынка {market['slug']}: {e}")
    
    def analyze_market_continuously(self, market_id, slug):
        """Непрерывный анализ рынка в течение заданного времени"""
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=self.analysis_time_minutes)
        retry_count = 0
        
        logger.info(f"Starting continuous analysis for market {slug} for {self.analysis_time_minutes} minutes")
        
        while datetime.now() < end_time and self.bot.running:
            try:
                # Анализируем рынок
                analysis_data = self.analyzer.analyze_market(slug)
                
                if analysis_data:
                    # Обновляем данные в базе
                    self.updater.update_market_analysis(market_id, analysis_data)
                    retry_count = 0  # Сбрасываем счетчик ошибок при успехе
                else:
                    retry_count += 1
                    if retry_count >= self.max_retries:
                        logger.error(f"Max retries reached for market {slug}, stopping analysis")
                        self.stop_market_analysis(market_id, "закрыт")
                        break
                    else:
                        logger.warning(f"Analysis failed for market {slug}, retry {retry_count}/{self.max_retries}")
                        time.sleep(self.retry_delay_seconds)
                        continue
                
                # Ждем 1 минуту перед следующим анализом
                time.sleep(60)
                
            except Exception as e:
                retry_count += 1
                error_msg = f"Error analyzing market {slug}: {e}"
                logger.error(error_msg)
                from telegram.error_logger import ErrorLogger
                error_logger = ErrorLogger()
                error_logger.log_error(error_msg, slug)
                
                if retry_count >= self.max_retries:
                    logger.error(f"Max retries reached for market {slug}, stopping analysis")
                    self.stop_market_analysis(market_id, "закрыт")
                    break
                else:
                    time.sleep(self.retry_delay_seconds)
        
        # Завершаем анализ рынка
        if market_id in self.bot.active_markets:
            self.stop_market_analysis(market_id, "закрыт")
    
    def analyze_market_continuously_restored(self, market_id, slug):
        """Непрерывный анализ восстановленного рынка"""
        try:
            # Получаем время создания из базы
            from database.active_markets_reader import ActiveMarketsReader
            reader = ActiveMarketsReader()
            market_info = reader.get_market_info(market_id)
            if not market_info:
                logger.error(f"❌ Не удалось получить информацию о рынке {market_id}")
                return
            
            created_at = market_info['created_at_analytic']
            if created_at.tzinfo is None:
                from datetime import timezone
                created_at = created_at.replace(tzinfo=timezone.utc)
            
            # Вычисляем время окончания анализа
            end_time = created_at + timedelta(minutes=self.analysis_time_minutes)
            current_time = datetime.now(timezone.utc)
            
            if current_time >= end_time:
                logger.info(f"⏰ Время анализа для восстановленного рынка {slug} истекло")
                self.stop_market_analysis(market_id, "закрыт")
                return
            
            # Продолжаем анализ до истечения времени
            remaining_minutes = (end_time - current_time).total_seconds() / 60
            logger.info(f"🔄 Продолжаем анализ восстановленного рынка {slug}, осталось {remaining_minutes:.1f} минут")
            
            retry_count = 0
            
            while datetime.now(timezone.utc) < end_time and self.bot.running:
                try:
                    # Анализируем рынок
                    analysis_data = self.analyzer.analyze_market(slug)
                    
                    if analysis_data:
                        # Обновляем данные в базе
                        self.updater.update_market_analysis(market_id, analysis_data)
                        retry_count = 0
                    else:
                        retry_count += 1
                        if retry_count >= self.max_retries:
                            logger.error(f"Max retries reached for restored market {slug}, stopping analysis")
                            self.stop_market_analysis(market_id, "закрыт")
                            break
                        else:
                            logger.warning(f"Analysis failed for restored market {slug}, retry {retry_count}/{self.max_retries}")
                            time.sleep(self.retry_delay_seconds)
                            continue
                    
                    # Ждем 1 минуту перед следующим анализом
                    time.sleep(60)
                    
                except Exception as e:
                    retry_count += 1
                    error_msg = f"Error analyzing restored market {slug}: {e}"
                    logger.error(error_msg)
                    from telegram.error_logger import ErrorLogger
                    error_logger = ErrorLogger()
                    error_logger.log_error(error_msg, slug)
                    
                    if retry_count >= self.max_retries:
                        logger.error(f"Max retries reached for restored market {slug}, stopping analysis")
                        self.stop_market_analysis(market_id, "закрыт")
                        break
                    else:
                        time.sleep(self.retry_delay_seconds)
            
            # Завершаем анализ рынка
            if market_id in self.bot.active_markets:
                self.stop_market_analysis(market_id, "закрыт")
                
        except Exception as e:
            logger.error(f"❌ Ошибка анализа восстановленного рынка {slug}: {e}")
            self.stop_market_analysis(market_id, "закрыт")
    
    def stop_market_analysis(self, market_id, status):
        """Остановка анализа рынка"""
        if market_id in self.bot.active_markets:
            market_info = self.bot.active_markets[market_id]
            
            # Обновляем статус в базе
            self.updater.update_market_analysis(market_id, {'status': status})
            
            # Логируем остановку
            market_data = {
                'question': market_info['question'],
                'slug': market_info['slug'],
                'status': status
            }
            self.stopped_logger.log_market_stopped(market_data)
            
            # Удаляем из активных рынков
            del self.bot.active_markets[market_id]
            logger.info(f"Stopped analysis for market {market_info['slug']}") 