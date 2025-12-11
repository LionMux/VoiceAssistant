"""
Менеджер Spotify API
Управление воспроизведением через голосовые команды
"""

import spotipy
from spotipy.oauth2 import SpotifyOAuth
import integrations.proxy_config as proxy_config

SPOTIFY_CLIENT_ID = "e51abd3aa42e47bba4019125cc5bb075"
SPOTIFY_CLIENT_SECRET = "aebc1f2c583b4366bd5b7070f56c39bb"
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"

SPOTIFY_SCOPE = [
    "user-modify-playback-state",
    "user-read-playback-state",
    "user-read-currently-playing",
    "user-read-recently-played"
]


class SpotifyManager:
    """Управление Spotify через API"""
    
    def __init__(self):
        """Инициализация Spotify клиента"""
        proxies = proxy_config.get_proxy()
        
        try:
            auth_manager = SpotifyOAuth(
                client_id=SPOTIFY_CLIENT_ID,
                client_secret=SPOTIFY_CLIENT_SECRET,
                redirect_uri=SPOTIFY_REDIRECT_URI,
                scope=" ".join(SPOTIFY_SCOPE),
                proxies=proxies
            )
            
            self.sp = spotipy.Spotify(
                auth_manager=auth_manager,
                proxies=proxies
            )
            
        except Exception as e:
            print(f"❌ Ошибка инициализации Spotify: {e}")
            self.sp = None
    
    
    def play(self):
        """Запускает воспроизведение"""
        try:
            self.sp.start_playback()
            return True
        except Exception as e:
            print(f"❌ Ошибка play: {e}")
            return False
    
    
    def pause(self):
        """Ставит на паузу"""
        try:
            self.sp.pause_playback()
            return True
        except Exception as e:
            print(f"❌ Ошибка pause: {e}")
            return False
    
    
    def next_track(self):
        """Следующий трек"""
        try:
            self.sp.next_track()
            return True
        except Exception as e:
            print(f"❌ Ошибка next: {e}")
            return False
    
    
    def previous_track(self):
        """Предыдущий трек"""
        try:
            self.sp.previous_track()
            return True
        except Exception as e:
            error_msg = str(e)
            if "403" in error_msg and "Restriction violated" in error_msg:
                print("⚠️  Нельзя вернуться назад (ограничение Spotify)")
            else:
                print(f"❌ Ошибка previous: {e}")
            return False
    
    
    def get_current_track(self):
        """Получает информацию о текущем треке"""
        try:
            current = self.sp.current_playback()
            
            if current and current['item']:
                track = current['item']
                artist = track['artists'][0]['name']
                song = track['name']
                
                print(f"🎵 Сейчас играет: {artist} - {song}")
                return f"{artist} - {song}"
            else:
                return None
                
        except Exception as e:
            print(f"❌ Ошибка get_current: {e}")
            return None
    
    def play_by_smart_search(self, query):
        """Ищет и включает трек используя умный поиск"""
        from spotify_smart_search import get_smart_search
        
        try:
            smart_search = get_smart_search()
            
            # Умный поиск с fuzzy matching
            improved_query = smart_search.smart_search(query)
            
            if not improved_query:
                print(f"❌ Не удалось обработать запрос: '{query}'")
                return False
            
            print(f"🎵 Ищу в Spotify: '{improved_query}'")
            
            # Ищем трек
            track_info = self.search_track(improved_query)
            
            if track_info:
                print(f"✅ Найден: {track_info['artist']} - {track_info['name']}")
                return self.play_track(track_info['uri'])
            else:
                print(f"❌ Трек не найден: '{improved_query}'")
                return False
            
        except Exception as e:
            print(f"❌ Ошибка smart search: {e}")
            return False

    
    def search_track(self, query):
        """Ищет трек по названию"""
        try:
            results = self.sp.search(q=query, type='track', limit=1)
            
            if results['tracks']['items']:
                track = results['tracks']['items'][0]
                return {
                    'uri': track['uri'],
                    'name': track['name'],
                    'artist': track['artists'][0]['name'],
                    'album': track['album']['name']
                }
            return None
        except Exception as e:
            print(f"❌ Ошибка поиска: {e}")
            return None
    
    
    def play_track(self, track_uri, device_id=None):
        """Включает трек по URI (с автозапуском Spotify)"""
        import subprocess
        import os
        import time
        
        try:
            # Шаг 1: Проверяем устройства
            devices_response = self.sp.devices()
            devices = devices_response.get('devices', [])
            
            # Шаг 2: Если устройств нет - запускаем Spotify
            if not devices:
                spotify_path = os.path.expanduser(r"~\AppData\Roaming\Spotify\Spotify.exe")
                
                if not os.path.exists(spotify_path):
                    print(f"❌ Spotify не найден")
                    return False
                
                subprocess.Popen([spotify_path])
                
                # Ждем появления устройств (до 20 сек)
                for i in range(20):
                    time.sleep(1)
                    devices_response = self.sp.devices()
                    devices = devices_response.get('devices', [])
                    
                    if devices:
                        break
            
            if not devices:
                print(f"❌ Устройства не найдены")
                return False
            
            # Шаг 3: Берем первое устройство и включаем трек
            device = devices[0]
            device_id = device['id']
            self.sp.start_playback(device_id=device_id, uris=[track_uri])

            # ← ВСТАВЬ ЭТОТ БЛОК СЮДА ↓
            # Шаг 4: Добавляем похожие треки в очередь
            try:
                # Извлекаем track_id
                track_id = track_uri.split(':')[-1]
                track_data = self.sp.track(track_id)
                artist_id = track_data['artists'][0]['id']
                
                # Получаем топ треки артиста
                top_tracks = self.sp.artist_top_tracks(artist_id, country='US')
                
                # Формируем список URI: первый трек + до 20 похожих
                playlist_uris = [track_uri]  # Начинаем с запрошенного трека
                for track in top_tracks['tracks'][:20]:
                    if track['uri'] != track_uri:  # Не дублируем первый трек
                        playlist_uris.append(track['uri'])
                
                # Включаем ВСЁ СРАЗУ - это очистит старую очередь!
                self.sp.start_playback(device_id=device_id, uris=playlist_uris)
                print(f"✅ Запущен плейлист из {len(playlist_uris)} треков")
                
            except Exception as e:
                print(f"⚠️ Очередь недоступна")
            # ← КОНЕЦ БЛОКА

            return True
            
        except Exception as e:
            print(f"❌ Ошибка воспроизведения: {e}")
            return False
    
    
    def play_by_name(self, track_name):
        """Ищет и включает трек по названию"""
        try:
            track_info = self.search_track(track_name)
            
            if track_info:
                return self.play_track(track_info['uri'])
            else:
                print(f"❌ Трек '{track_name}' не найден")
                return False
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False

    def get_liked_songs_uri(self):
        """Получает URI плейлиста 'Любимые треки'"""
        # Spotify API возвращает liked songs как специальный контекст
        # URI: spotify:user:{user_id}:collection
        current_user = self.sp.current_user()
        return f"spotify:user:{current_user['id']}:collection"

    def play_liked_songs(self):
        """Включает плейлист Любимые треки"""
        import subprocess
        import os
        import time
        
        try:
            # Получаем устройства
            devices_response = self.sp.devices()
            devices = devices_response.get('devices', [])
            
            # Если устройств нет - запускаем Spotify
            if not devices:
                spotify_path = os.path.expanduser(r"~\AppData\Roaming\Spotify\Spotify.exe")
                
                if not os.path.exists(spotify_path):
                    print(f"❌ Spotify не найден")
                    return False
                
                subprocess.Popen([spotify_path])
                
                # Ждем появления устройств (до 20 сек)
                for i in range(20):
                    time.sleep(1)
                    devices_response = self.sp.devices()
                    devices = devices_response.get('devices', [])
                    
                    if devices:
                        break
            
            if not devices:
                print(f"❌ Устройства не найдены")
                return False
            
            # Берем первое устройство
            device = devices[0]
            device_id = device['id']
            
            # Получаем URI плейлиста Любимые треки
            uri = self.get_liked_songs_uri()
            
            # Включаем плейлист
            self.sp.start_playback(device_id=device_id, context_uri=uri)
            return True
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False


spotify_manager = None

def init_spotify():
    """Инициализирует Spotify Manager"""
    global spotify_manager
    
    if spotify_manager is None:
        spotify_manager = SpotifyManager()
    
    return spotify_manager
