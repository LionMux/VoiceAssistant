# Создай файл: telegram_bot_runner.py

import sys
import io
import logging
from telebot import TeleBot
from config import TELEGRAM_TOKEN, OWNER_ID

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(commands=['start'])
def handle_start(message):
    """Handle /start command"""
    bot.reply_to(message, f"Привет! Я бот Тоня Ассистент 🤖\nТвой ID: {message.from_user.id}")
    logger.info(f"Получена команда /start от {message.from_user.id}")

@bot.message_handler(func=lambda m: True)
def handle_any_message(message):
    """Handle any other message"""
    bot.reply_to(message, f"Ты написал: {message.text}")
    logger.info(f"Получено сообщение: {message.text}")

if __name__ == "__main__":
    logger.info(f"Запуск бота с polling (OWNER_ID: {OWNER_ID})...")
    logger.info("Жди сообщения /start в Telegram...")
    bot.infinity_polling()  # ← ЭТО ГЛАВНАЯ СТРОКА!
