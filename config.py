
import os
import logging
from pathlib import Path
from typing import Optional

PORCUPINE_ACCESS_KEY = "iBoPeQLsiPNo1gKHVDAU2/6OHsTfRWC8kPddDbVTWrqCwGpkWXXFWA=="

PORCUPINE_ACCESS_KEY_NEW = "/oFwK0x/0iZpmzORwWhFGPKPY0ojVuWry2+IFSHpOlT8b4Pl3vpBtg=="

PORCUPINE_SENSITIVITY = 0.7

MICROPHONE_INDEX = -1

#SOUND_FOLDER = "C:\Users\Lev\Desktop\VoiceAssistant2\voices"

KEYWORD_PATH = "keywords/Belka.ppn"

KEYWORD_PATH_NEW = "keywords/Tonya.ppn"

KEYWORD_NAME = "Белка"

KEYWORD_NAME_NEW = "Тоня"

SOUNDS_PATH = "voices\greet1.wav"

VOSK_MODEL_PATH = r"C:\Users\Lev\Desktop\VoiceAssistant2\vosk_model\vosk-model-small-ru-0.22"

COMMAND_RESPONSES = {
    "understood": "voices/ok1.wav",
    "listening": "voices/greet1.wav",
    "error": "voices/not_found.wav",
    "play music": "play_music"
}

COMMAND_TIMEOUT = 3

logger = logging.getLogger(__name__)

TELEGRAM_TOKEN : str = os.getenv(
    "TELEGRAM_TOKEN",
    "8380874248:AAHzgSUZcTDFmO3nC7MbZ-EtT2DwM3JiRLo"
)

OWNER_ID: int = int(os.getenv("OWNER_ID", "550196385"))

BOT_USERNAM: str = "Tonya_Assistant_2025_bot"

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE: Path = Path("logs") / "telegram_bot.log"

# Create logs directory if it doesn't exist
Path("logs").mkdir(exist_ok=True)

POLLING_TIMEOUT: int = 30

def validate_config() -> bool:
    """
    Validate critical configuration parameters.
    
    Returns:
        bool: True if all validations pass, False otherwise.
        
    Raises:
        ValueError: If TELEGRAM_TOKEN or OWNER_ID is invalid.
    """
    errors: list[str] = []
    
    # Check TELEGRAM_TOKEN format
    if not isinstance(TELEGRAM_TOKEN, str):
        errors.append("TELEGRAM_TOKEN must be a string")
    elif len(TELEGRAM_TOKEN) < 20:
        errors.append("TELEGRAM_TOKEN seems too short (invalid format)")
    elif ":" not in TELEGRAM_TOKEN:
        errors.append("TELEGRAM_TOKEN doesn't contain ':' (invalid format)")
    
    # Check OWNER_ID format
    if not isinstance(OWNER_ID, int):
        errors.append("OWNER_ID must be an integer")
    elif OWNER_ID <= 0:
        errors.append("OWNER_ID must be positive")
    elif len(str(OWNER_ID)) < 5:
        errors.append("OWNER_ID seems too short (invalid format)")
    
    if errors:
        for error in errors:
            logger.error(f"❌ Config validation error: {error}")
        raise ValueError("\n".join(errors))
    
    logger.info("✅ Configuration validated successfully")
    return True

try:
    validate_config()
except ValueError as e:
    logger.error(f"Configuration validation failed: {e}")
    logger.warning(
        "⚠️  Update config.py with real TELEGRAM_TOKEN and OWNER_ID "
        "from BotFather and @userinfobot"
    )

# SPOTIFY_CLIENT_ID = "e51abd3aa42e47bba4019125cc5bb075"

# SPOTIFY_CLIENT_SECRET = "aebc1f2c583b4366bd5b7070f56c39bb"