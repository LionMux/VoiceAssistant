import subprocess
import os
import re
from integrations import spotify_manager


YANDEX_BROWSER_PATH = r"C:\Users\{}\AppData\Local\Yandex\YandexBrowser\Application\browser.exe".format(
    os.getenv('USERNAME')
)
TELEGRAM_PATH = r"C:\Users\{}\AppData\Roaming\Telegram Desktop\Telegram.exe".format(
    os.getenv('USERNAME')
)

def clean_track_name(text):
    """
    ✅ НОВАЯ ФУНКЦИЯ: Очистка названия трека от мусора
    
    Удаляет:
    - Пунктуацию (кроме дефиса и апострофа)
    - Множественные пробелы
    - Пробелы в начале/конце
    
    Примеры:
    "МЦ-клучник, князь за лупа." → "МЦ-клучник князь за лупа"
    "The Weeknd - Blinding Lights!!!" → "The Weeknd - Blinding Lights"
    "tveth: Paramedic..." → "tveth Paramedic"
    """
    if not text:
        return text
    
    # Удаляем пунктуацию (оставляем дефис и апостроф для названий типа "MC-name" или "don't")
    # Шаблон: удаляет всё кроме букв, цифр, пробелов, дефиса и апострофа
    cleaned = re.sub(r"[^\w\s\-'']", "", text)
    
    # Убираем множественные пробелы
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Убираем пробелы в начале/конце
    cleaned = cleaned.strip()
    
    return cleaned

def open_youtube():
    try:
        print("🌐 Открываю YouTube в Яндекс браузере...")
        
        if not os.path.exists(YANDEX_BROWSER_PATH):
            print(f"Браузер не найден: {YANDEX_BROWSER_PATH}")
            print("Укажите правильный путь в YANDEX_BROWSER_PATH")
            return False
        
        subprocess.Popen([YANDEX_BROWSER_PATH, "https://www.youtube.com"])
        print("YouTube открыт")
        return True
        
    except Exception as e:
        print(f"Ошибка открытия YouTube: {e}")
        return False


def open_google():
    try:
        print("Открываю Google...")
        subprocess.Popen([YANDEX_BROWSER_PATH, "https://www.google.com"])
        print("Google открыт")
        return True
    except Exception as e:
        print(f"Ошибка: {e}")
        return False


def open_vk():
    try:
        print("Открываю ВКонтакте...")
        subprocess.Popen([YANDEX_BROWSER_PATH, "https://vk.com"])
        print("ВКонтакте открыт")
        return True
    except Exception as e:
        print(f"Ошибка: {e}")
        return False

def open_telegram():
    try:
        print("Открываю Telegram...")
        
        if not os.path.exists(TELEGRAM_PATH):
            print(f"Telegram не найден: {TELEGRAM_PATH}")
            print("Укажите правильный путь в TELEGRAM_PATH")
            return False
        
        subprocess.Popen([TELEGRAM_PATH])
        print("Telegram открыт")
        return True
        
    except Exception as e:
        print(f"Ошибка: {e}")
        return False

def spotify_play():
    """Запускает воспроизведение Spotify"""
    manager = spotify_manager.init_spotify()
    if manager and manager.sp:
        return manager.play()
    return False

def spotify_pause():
    """Ставит Spotify на паузу"""
    manager = spotify_manager.init_spotify()
    if manager and manager.sp:
        return manager.pause()
    return False

def spotify_next():
    """Следующий трек"""
    manager = spotify_manager.init_spotify()
    if manager and manager.sp:
        return manager.next_track()
    return False

def spotify_previous():
    """Предыдущий трек"""
    manager = spotify_manager.init_spotify()
    if manager and manager.sp:
        return manager.previous_track()
    return False

def spotify_current():
    """Показывает текущий трек"""
    manager = spotify_manager.init_spotify()
    if manager and manager.sp:
        track = manager.get_current_track()
        return track is not None
    return False

def spotify_play_track(whisper_recognizer=None):
    """
    Включает трек по названию через голосовой ввод
    
    Args:
        whisper_recognizer: Экземпляр WhisperRecognizer (передаётся из main.py)
    """
    manager = spotify_manager.init_spotify()
    if not manager or not manager.sp:
        print("❌ Spotify Manager не инициализирован")
        return False
    
    # ✅ Используем переданный Whisper (НЕ создаём новый!)
    if whisper_recognizer is None:
        print("⚠️ Whisper не передан, используется fallback (медленно)")
        import whisper_recognizer
        recognizer = whisper_recognizer.WhisperRecognizer(model_size="small")
    else:
        recognizer = whisper_recognizer
    
    
    print("🎵 Скажите название трека (на русском или английском)...")
    
    # ✅ АВТООПРЕДЕЛЕНИЕ ЯЗЫКА для английских названий
    track_name = recognizer.listen_for_text(
        timeout=10
    )
    track_name_cleaned = clean_track_name(track_name)
    
    if not track_name:
        print("❌ Название трека не распознано")
        return False
    
    print(f"🔍 Ищу трек: '{track_name_cleaned}'")
    track_info = manager.search_track(track_name_cleaned)
    
    if not track_info:
        print(f"❌ Трек '{track_name}' не найден")
        return False
    
    print(f"✅ Найден: {track_info['artist']} - {track_info['name']}")
    return manager.play_track(track_info['uri'])

def sleep_mode():
    """Переводит компьютер в спящий режим"""
    try:
        import os
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def spotify_play_liked():
    """Включает плейлист Любимые треки"""
    manager = spotify_manager.init_spotify()
    if manager and manager.sp:
        return manager.play_liked_songs()
    return False

ACTIONS = {
    "open_youtube": open_youtube,
    "open_google": open_google,
    "open_vk": open_vk,
    "open_tg": open_telegram,
    "spotify_play": spotify_play,
    "spotify_pause": spotify_pause,
    "spotify_next": spotify_next,
    "spotify_previous": spotify_previous,
    "spotify_current": spotify_current,
    "spotify_play_track": spotify_play_track,
    "sleep_mode": sleep_mode,
    "spotify_play_liked": spotify_play_liked,
}
