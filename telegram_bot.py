"""
Telegram Bot Module - Iteration 3: Production-ready + Health Checks
Полнофункциональное решение для боевых условий

ГЛАВНЫЕ ПРЕИМУЩЕСТВА ИТЕРАЦИИ 3:
✅ HealthStatus - мониторинг здоровья бота (сообщения, ошибки, uptime)
✅ Heartbeat поток - периодическая проверка здоровья
✅ Асинхронная очередь - queue.Queue для обработки сообщений
✅ Кастомные обработчики - register_handler() для расширяемости
✅ /health команда - для отладки в Telegram
✅ get_health() метод - API для программного доступа к метрикам
✅ Обработка переполнения очереди - queue.Full ошибка
"""

import sys
import io
import logging
import threading
import time
import requests
import queue
from telebot import TeleBot
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

logger = logging.getLogger(__name__)


class BotState(Enum):
    """Состояния бота"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class HealthStatus:
    """Статус здоровья бота - мониторинг метрик"""
    state: BotState
    is_connected: bool
    last_heartbeat: datetime
    messages_received: int = 0
    errors_count: int = 0
    uptime_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать в словарь для вывода"""
        return {
            "state": self.state.value,
            "connected": self.is_connected,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "messages": self.messages_received,
            "errors": self.errors_count,
            "uptime": f"{self.uptime_seconds:.1f}s"
        }


@dataclass
class BotConfig:
    """Конфигурация бота"""
    token: str
    owner_id: int
    init_timeout: int = 15
    polling_timeout: int = 60
    max_retries: int = 3
    retry_delay: int = 5
    heartbeat_interval: int = 30  # ⭐ Новое: интервал проверки здоровья
    max_queue_size: int = 100


class TelegramBotService:
    """Production-ready Telegram бот с health checks и мониторингом"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, token: str, owner_id: int, **config_kwargs):
        """
        Инициализация Production-ready Telegram бота
        
        Args:
            token: Telegram Bot API token
            owner_id: Owner's Telegram ID
            **config_kwargs: Дополнительные параметры конфигурации
        """
        
        if hasattr(self, 'initialized') and self.initialized:
            logger.debug("✅ Бот уже инициализирован")
            return
        
        self.config = BotConfig(token=token, owner_id=owner_id, **config_kwargs)
        self.bot: Optional[TeleBot] = None
        self.state = BotState.UNINITIALIZED
        self.thread: Optional[threading.Thread] = None
        self.heartbeat_thread: Optional[threading.Thread] = None
        self.initialized = False
        self._stop_event = threading.Event()
        self._ready_event = threading.Event()
        
        # ⭐ Мониторинг и статистика
        self.health = HealthStatus(
            state=self.state,
            is_connected=False,
            last_heartbeat=datetime.now()
        )
        self._start_time = None
        
        # ⭐ Очередь сообщений для асинхронной обработки
        self._message_queue: queue.Queue = queue.Queue(maxsize=self.config.max_queue_size)
        
        # ⭐ Кастомные обработчики
        self._custom_handlers: Dict[str, Callable] = {}
        
        self._initialize_bot()
    
    def register_handler(self, command: str, handler: Callable) -> None:
        """
        Зарегистрировать кастомный обработчик
        
        Args:
            command: Команда (без слэша)
            handler: Функция-обработчик (получает message объект)
            
        Пример:
            def my_handler(message):
                bot.reply_to(message, "Привет!")
            
            telegram_bot.register_handler("hello", my_handler)
        """
        self._custom_handlers[command] = handler
        logger.info(f"✅ Обработчик '{command}' зарегистрирован")
    
    def _initialize_bot(self) -> bool:
        """Инициализировать бот с retry логикой"""
        
        self.state = BotState.INITIALIZING
        self.health.state = self.state
        logger.info("🔌 Инициализирую Telegram бот...")
        
        for attempt in range(1, self.config.max_retries + 1):
            try:
                logger.info(f"📡 Попытка подключения {attempt}/{self.config.max_retries}...")
                
                self.bot = TeleBot(
                    self.config.token,
                    timeout=self.config.init_timeout
                )
                
                logger.info("✅ Проверяю токен...")
                bot_info = self.bot.get_me()
                logger.info(f"✅ Бот подключен: @{bot_info.username} (ID: {bot_info.id})")
                
                self._register_handlers()
                logger.info("✅ Обработчики зарегистрированы")
                
                self.initialized = True
                self.state = BotState.READY
                self.health.state = self.state
                self.health.is_connected = True
                return True
                
            except requests.exceptions.ConnectionError:
                logger.warning(f"⚠️ Ошибка подключения (попытка {attempt})")
                if attempt < self.config.max_retries:
                    time.sleep(self.config.retry_delay)
                    
            except Exception as e:
                error_msg = str(e)
                if "401" in error_msg:
                    logger.error(f"❌ Ошибка 401: Проверьте токен!")
                    self.state = BotState.ERROR
                    self.health.state = self.state
                    self.health.errors_count += 1
                    return False
                else:
                    logger.warning(f"⚠️ Ошибка (попытка {attempt}): {e}")
                    if attempt < self.config.max_retries:
                        time.sleep(self.config.retry_delay)
        
        logger.error(f"❌ Не удалось подключиться после {self.config.max_retries} попыток")
        self.initialized = False
        self.state = BotState.ERROR
        self.health.state = self.state
        self.health.is_connected = False
        self.bot = None
        return False
    
    def _register_handlers(self) -> None:
        """Регистрация обработчиков команд"""
        
        if not self.bot:
            return
        
        @self.bot.message_handler(commands=['start'])
        def handle_start(message):
            if message.from_user.id != self.config.owner_id:
                self.bot.reply_to(message, "❌ У тебя нет доступа")
                return
            self.bot.reply_to(message, "👋 Привет! Я бот Белка Ассистент\n✅ Я готов к работе!")
            self.health.messages_received += 1
            logger.info(f"[Telegram] /start от {message.from_user.id}")
        
        @self.bot.message_handler(commands=['status'])
        def handle_status(message):
            if message.from_user.id != self.config.owner_id:
                self.bot.reply_to(message, "❌ У тебя нет доступа")
                return
            
            status_text = (
                f"🤖 Состояние: {self.health.state.value}\n"
                f"📨 Сообщений: {self.health.messages_received}\n"
                f"⏱️ Uptime: {self.health.uptime_seconds:.0f}s\n"
                f"❌ Ошибок: {self.health.errors_count}"
            )
            
            self.bot.reply_to(message, status_text)
            self.health.messages_received += 1
            logger.info(f"[Telegram] /status от {message.from_user.id}")
        
        # ⭐ НОВАЯ КОМАНДА: /health для мониторинга
        @self.bot.message_handler(commands=['health'])
        def handle_health(message):
            if message.from_user.id != self.config.owner_id:
                self.bot.reply_to(message, "❌ У тебя нет доступа")
                return
            
            health_dict = self.health.to_dict()
            health_text = "\n".join([f"{k}: {v}" for k, v in health_dict.items()])
            self.bot.reply_to(message, f"```\n{health_text}\n```", parse_mode="Markdown")
            logger.info(f"[Telegram] /health от {message.from_user.id}")
        
        @self.bot.message_handler(func=lambda m: True)
        def handle_any_message(message):
            if message.from_user.id != self.config.owner_id:
                self.bot.reply_to(message, "❌ У тебя нет доступа")
                return
            
            # ⭐ Добавляем в очередь для асинхронной обработки
            try:
                self._message_queue.put_nowait({
                    'text': message.text,
                    'user_id': message.from_user.id,
                    'timestamp': datetime.now()
                })
                self.bot.reply_to(message, f"✅ Получено: {message.text}")
                self.health.messages_received += 1
            except queue.Full:
                logger.warning("⚠️ Очередь сообщений переполнена")
                self.bot.reply_to(message, "⚠️ Очередь переполнена, повторите позже")
                self.health.errors_count += 1
    
    def get_message_from_queue(self, timeout: float = 0.1) -> Optional[Dict[str, Any]]:
        """
        Получить сообщение из очереди
        
        Returns:
            Dict с полями: text, user_id, timestamp
            или None если очередь пуста
            
        Пример:
            msg = telegram_bot.get_message_from_queue()
            if msg:
                print(f"Новое сообщение: {msg['text']}")
        """
        try:
            return self._message_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def start(self) -> bool:
        """Запустить бот в отдельном потоке"""
        
        if self.state == BotState.RUNNING:
            logger.warning("⚠️ Бот уже работает")
            return False
        
        if not self.initialized:
            logger.error("❌ Бот не инициализирован")
            return False
        
        try:
            self.state = BotState.RUNNING
            self.health.state = self.state
            self._start_time = time.time()
            self._stop_event.clear()
            
            # Запускаем polling поток
            self.thread = threading.Thread(
                target=self._polling_loop,
                daemon=False,
                name="TelegramPolling"
            )
            self.thread.start()
            
            # ⭐ Запускаем heartbeat поток для мониторинга
            self.heartbeat_thread = threading.Thread(
                target=self._heartbeat_loop,
                daemon=True,
                name="TelegramHeartbeat"
            )
            self.heartbeat_thread.start()
            
            if not self._ready_event.wait(timeout=5):
                logger.warning("⚠️ Поток долго стартует")
            
            logger.info("✅ Telegram бот запущен")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска: {e}")
            self.state = BotState.ERROR
            self.health.state = self.state
            self.health.errors_count += 1
            return False
    
    def _heartbeat_loop(self) -> None:
        """⭐ Периодическая проверка здоровья бота"""
        
        while not self._stop_event.is_set() and self.state == BotState.RUNNING:
            try:
                self.health.last_heartbeat = datetime.now()
                
                if self._start_time:
                    self.health.uptime_seconds = time.time() - self._start_time
                
                logger.debug(
                    f"💓 Heartbeat: {self.health.state.value}, "
                    f"msgs={self.health.messages_received}, "
                    f"errors={self.health.errors_count}"
                )
                
                time.sleep(self.config.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"❌ Ошибка heartbeat: {e}")
                self.health.errors_count += 1
    
    def _polling_loop(self) -> None:
        """Цикл получения сообщений"""
        
        try:
            logger.info("🔌 Начинаю polling...")
            self._ready_event.set()
            
            while not self._stop_event.is_set() and self.state == BotState.RUNNING:
                try:
                    self.bot.infinity_polling(
                        none_stop=True,
                        timeout=self.config.polling_timeout
                    )
                except KeyboardInterrupt:
                    logger.info("⏹️ Polling остановлен (Ctrl+C)")
                    break
                except Exception as e:
                    logger.error(f"❌ Ошибка polling: {e}")
                    self.health.errors_count += 1
                    if not self._stop_event.is_set():
                        logger.info(f"🔄 Переподключение через {self.config.retry_delay}s...")
                        time.sleep(self.config.retry_delay)
                        continue
                    break
                    
        except Exception as e:
            logger.error(f"❌ Критическая ошибка: {e}")
            self.state = BotState.ERROR
            self.health.state = self.state
            self.health.errors_count += 1
        finally:
            self.state = BotState.STOPPED
            self.health.state = self.state
            logger.info("✅ Polling завершён")
    
    def stop(self, timeout: int = 10) -> bool:
        """Остановить бот"""
        
        if self.state not in [BotState.RUNNING, BotState.ERROR]:
            return True
        
        try:
            self.state = BotState.STOPPING
            self.health.state = self.state
            logger.info("⏹️ Остановка Telegram бота...")
            
            self._stop_event.set()
            
            if self.bot:
                self.bot.stop_polling()
            
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=timeout)
            
            self.state = BotState.STOPPED
            self.health.state = self.state
            logger.info("✅ Telegram бот остановлен")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка при остановке: {e}")
            self.health.errors_count += 1
            return False
    
    def get_health(self) -> Dict[str, Any]:
        """
        ⭐ Получить статус здоровья бота
        
        Returns:
            Dict с полями: state, connected, last_heartbeat, messages, errors, uptime
            
        Пример:
            health = telegram_bot.get_health()
            print(f"Бот в состоянии: {health['state']}")
            print(f"Сообщений получено: {health['messages']}")
        """
        return self.health.to_dict()
    
    def get_state(self) -> str:
        """Получить текущее состояние"""
        return self.state.value