"""
Тест: Проверка устройств → Открытие Spotify → Включение трека
"""

import subprocess
import os
import time
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Твои credentials
CLIENT_ID = "e51abd3aa42e47bba4019125cc5bb075"
CLIENT_SECRET = "aebc1f2c583b4366bd5b7070f56c39bb"

# Тестовый трек
TEST_TRACK_URI = "spotify:track:31iOUkjc3pqOqgkAq143Bp"  # TVETH - Paramedic

print("=" * 60)
print("ТЕСТ: Умное открытие Spotify + Включение трека")
print("=" * 60)

# Подключаемся к API
print("\n🔌 Подключение к Spotify API...")
auth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri="http://127.0.0.1:8888/callback",
    scope="user-read-playback-state user-modify-playback-state"
)

sp = spotipy.Spotify(auth_manager=auth)
print("✅ Подключено")

print("\n" + "=" * 60)
print("ШАГ 1: Проверка доступных устройств")
print("=" * 60)

devices_response = sp.devices()
devices = devices_response.get('devices', [])

if devices:
    print(f"✅ УСТРОЙСТВА УЖЕ ЕСТЬ: {len(devices)}\n")
    
    for d in devices:
        status = "🟢 АКТИВНО" if d['is_active'] else "⚪ НЕАКТИВНО"
        print(f"{status} {d['name']} ({d['type']})")
    
    print("\n💡 Spotify уже открыт, переходим к включению трека")
    
else:
    print("❌ Устройств нет")
    
    print("\n" + "=" * 60)
    print("ШАГ 2: Открытие Spotify Desktop")
    print("=" * 60)
    
    spotify_path = os.path.expanduser(r"~\AppData\Roaming\Spotify\Spotify.exe")
    print(f"Путь: {spotify_path}")
    
    if not os.path.exists(spotify_path):
        print("❌ Spotify не найден!")
        exit(1)
    
    print("\n🚀 Запускаю Spotify...")
    subprocess.Popen([spotify_path])
    print("✅ Команда запуска выполнена")
    
    print("\n" + "=" * 60)
    print("ШАГ 3: Ожидание появления устройств")
    print("=" * 60)
    
    # Проверяем устройства 20 раз с интервалом 1 сек
    for i in range(20):
        print(f"⏳ Попытка {i+1}/20...", end='\r')
        
        devices_response = sp.devices()
        devices = devices_response.get('devices', [])
        
        if devices:
            print(f"\n✅ УСТРОЙСТВА ПОЯВИЛИСЬ!\n")
            
            for d in devices:
                status = "🟢 АКТИВНО" if d['is_active'] else "⚪ НЕАКТИВНО"
                print(f"{status}")
                print(f"  Название: {d['name']}")
                print(f"  Тип: {d['type']}")
                print(f"  ID: {d['id']}")
                print()
            
            break
        
        time.sleep(1)
    
    if not devices:
        print("\n❌ Устройства не появились за 20 сек")
        exit(1)

# ========== НОВЫЙ ШАГ: ВКЛЮЧЕНИЕ ТРЕКА ==========
print("=" * 60)
print("ШАГ 4: Включение тестового трека")
print("=" * 60)

# Берем первое устройство
device = devices[0]
device_id = device['id']

print(f"📱 Выбрано устройство: {device['name']}")
print(f"🎵 Трек: TVETH - Paramedic")
print(f"▶️  Включаю трек на device_id={device_id}...\n")

try:
    # Включаем трек
    sp.start_playback(device_id=device_id, uris=[TEST_TRACK_URI])
    print("✅ ТРЕК ВКЛЮЧЕН!")
    
    # Проверяем что играет
    time.sleep(2)
    current = sp.current_playback()
    
    if current and current['item']:
        track_name = current['item']['name']
        artist_name = current['item']['artists'][0]['name']
        print(f"🎵 Сейчас играет: {artist_name} - {track_name}")
    
except Exception as e:
    print(f"❌ ОШИБКА ВКЛЮЧЕНИЯ ТРЕКА: {e}")
    exit(1)

print("\n" + "=" * 60)
print("ТЕСТ ПОЛНОСТЬЮ ПРОЙДЕН!")
print("=" * 60)