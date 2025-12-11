"""
Асинхронное воспроизведение звука через threading
Можно отключить, вернув на playsound в любой момент
"""

import threading
from playsound3 import playsound

# Флаг для включения/отключения асинхронного режима
USE_ASYNC = True

def play_sound(sound_file):
    """
    Универсальная функция воспроизведения
    Использует асинхронный режим если включен, иначе обычный
    """
    if USE_ASYNC:
        play_sound_async(sound_file)
    else:
        playsound(sound_file)

def play_sound_async(sound_file):
    """Проигрывает звук в отдельном потоке (не блокирует)"""
    thread = threading.Thread(
        target=playsound, 
        args=(sound_file,), 
        daemon=True
    )
    thread.start()

def disable_async():
    """Отключить асинхронный режим (откат на обычный playsound)"""
    global USE_ASYNC
    USE_ASYNC = False
    print("⚠️  Асинхронный режим отключен")

def enable_async():
    """Включить асинхронный режим"""
    global USE_ASYNC
    USE_ASYNC = True
    print("✅ Асинхронный режим включен")
