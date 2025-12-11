"""
Telegram Bot Setup and Initialization Module.

This module handles:
- Bot token validation
- Initial bot connection test
- Bot information retrieval
- Error handling and logging

Usage:
    python telegram_bot_setup.py  # Test bot connection
"""

import logging
import requests
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

import telebot

from config import TELEGRAM_TOKEN, OWNER_ID, validate_config

# ============================================================================
# LOGGER SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/telegram_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class BotInfo:
    """Represents Telegram bot information."""
    bot_id: int
    bot_username: str
    first_name: str
    is_bot: bool
    can_join_groups: bool
    can_read_all_group_messages: bool
    supports_inline_queries: bool


class BotStatus(Enum):
    """Enum for bot connection status."""
    CONNECTED = "✅ Connected"
    INVALID_TOKEN = "❌ Invalid token"
    CONNECTION_ERROR = "❌ Connection error"
    UNKNOWN_ERROR = "❌ Unknown error"


# ============================================================================
# BOT SETUP FUNCTIONS
# ============================================================================

def validate_telegram_token(token: str) -> bool:
    """
    Validate Telegram bot token format.
    
    Args:
        token: Telegram bot token from BotFather.
        
    Returns:
        bool: True if token format is valid, False otherwise.
        
    Note:
        This only checks format, not if token is actually valid with Telegram API.
        Use test_bot_connection() for full validation.
    """
    if not isinstance(token, str):
        logger.error("❌ Token must be a string")
        return False
    
    if len(token) < 20:
        logger.error("❌ Token is too short (expected 40+ characters)")
        return False
    
    if ":" not in token:
        logger.error("❌ Token doesn't contain ':' separator")
        return False
    
    parts = token.split(":")
    if len(parts) != 2:
        logger.error("❌ Token format invalid (should be ID:TOKEN)")
        return False
    
    try:
        int(parts[0])  # Bot ID should be numeric
    except ValueError:
        logger.error("❌ Token ID part is not numeric")
        return False
    
    logger.info(f"✅ Token format is valid (ID: {parts[0]}...)")
    return True


def test_bot_connection(token: str) -> tuple[BotStatus, Optional[BotInfo]]:
    """
    Test connection to Telegram API and retrieve bot information.
    
    Args:
        token: Telegram bot token from BotFather.
        
    Returns:
        tuple: (BotStatus, BotInfo) if successful, (BotStatus, None) if failed.
        
    Raises:
        None - All exceptions are caught and logged.
    """
    logger.info("🔌 Testing bot connection...")
    
    try:
        bot = telebot.TeleBot(token)
        bot_user = bot.get_me()
        
        bot_info = BotInfo(
            bot_id=bot_user.id,
            bot_username=bot_user.username,
            first_name=bot_user.first_name,
            is_bot=bot_user.is_bot,
            can_join_groups=bot_user.can_join_groups,
            can_read_all_group_messages=bot_user.can_read_all_group_messages,
            supports_inline_queries=bot_user.supports_inline_queries
        )
        
        logger.info(f"✅ Bot connected successfully!")
        logger.info(f"   Bot ID: {bot_info.bot_id}")
        logger.info(f"   Bot Username: @{bot_info.bot_username}")
        logger.info(f"   Bot Name: {bot_info.first_name}")
        
        return BotStatus.CONNECTED, bot_info
        
    except telebot.apihelper.ApiException as e:
        if "401" in str(e):
            logger.error("❌ Invalid token (401 Unauthorized)")
            return BotStatus.INVALID_TOKEN, None
        else:
            logger.error(f"❌ Telegram API error: {e}")
            return BotStatus.UNKNOWN_ERROR, None
            
    except requests.exceptions.ConnectionError:
        logger.error("❌ Connection error (check internet connection)")
        return BotStatus.CONNECTION_ERROR, None
        
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return BotStatus.UNKNOWN_ERROR, None


def get_bot_info_string(bot_info: BotInfo) -> str:
    """
    Format bot information as readable string.
    
    Args:
        bot_info: BotInfo dataclass instance.
        
    Returns:
        str: Formatted bot information.
    """
    return f"""
╔═══════════════════════════════════╗
║         BOT INFORMATION           ║
╠═══════════════════════════════════╣
║ ID:                 {bot_info.bot_id}
║ Username:           @{bot_info.bot_username}
║ Display Name:       {bot_info.first_name}
║ Is Bot:             {bot_info.is_bot}
║ Can Join Groups:    {bot_info.can_join_groups}
║ Read Group Messages:{bot_info.can_read_all_group_messages}
║ Inline Queries:     {bot_info.supports_inline_queries}
╚═══════════════════════════════════╝
    """


def initialize_bot() -> Optional[telebot.TeleBot]:
    """
    Initialize and validate Telegram bot.
    
    Returns:
        telebot.TeleBot: Initialized bot instance if successful, None otherwise.
        
    Raises:
        None - All exceptions are caught and logged.
    """
    logger.info("=" * 50)
    logger.info("TELEGRAM BOT SETUP")
    logger.info("=" * 50)
    
    # Validate config
    try:
        validate_config()
    except ValueError as e:
        logger.error(f"❌ Configuration validation failed: {e}")
        return None
    
    # Validate token format
    if not validate_telegram_token(TELEGRAM_TOKEN):
        logger.error("❌ Token format validation failed")
        return None
    
    # Test connection
    status, bot_info = test_bot_connection(TELEGRAM_TOKEN)
    
    if status != BotStatus.CONNECTED or not bot_info:
        logger.error(f"❌ Bot connection failed: {status.value}")
        return None
    
    logger.info(get_bot_info_string(bot_info))
    logger.info(f"✅ Owner ID: {OWNER_ID}")
    
    # Create and return bot instance
    bot = telebot.TeleBot(TELEGRAM_TOKEN)
    logger.info("✅ Bot instance created and ready to use")
    
    return bot


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    """
    Test script: Check if bot is properly configured and can connect to Telegram.
    
    Run: python telegram_bot_setup.py
    """
    logger.info("Starting bot setup verification...")
    
    bot = initialize_bot()
    
    if bot:
        logger.info("\n✅ Setup successful! Bot is ready for use.")
        logger.info(f"Next step: Run main.py to start the bot")
    else:
        logger.error("\n❌ Setup failed! Check configuration and try again.")
        logger.error("Steps to fix:")
        logger.error("1. Open Telegram and find @BotFather")
        logger.error("2. Create a new bot with /newbot")
        logger.error("3. Copy the token to TELEGRAM_TOKEN in config.py")
        logger.error("4. Find @userinfobot and get your ID")
        logger.error("5. Copy your ID to OWNER_ID in config.py")