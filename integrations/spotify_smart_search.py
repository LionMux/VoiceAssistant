"""
Интеллектуальный поиск треков Spotify с fuzzy matching
Кэширование артистов и треков для быстрого распознавания голосовых команд
"""

import json
import re
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from thefuzz import fuzz, process
from integrations.spotify_manager import spotify_manager, init_spotify

# Путь к базе данных (создастся автоматически)
DB_PATH = Path("data/spotify_cache.json")
DB_PATH.parent.mkdir(exist_ok=True)

# Пороги схожести для fuzzy matching
ARTIST_MATCH_THRESHOLD = 70  # Минимальная схожесть для артиста
TRACK_MATCH_THRESHOLD = 65   # Минимальная схожесть для трека


class SpotifySmartSearch:
    """Умный поиск с кэшированием и fuzzy matching"""
    
    def __init__(self):
        self.db = self._load_db()
        self.sp_manager = init_spotify()
        
    def _load_db(self) -> Dict:
        """Загружает базу данных из файла"""
        if DB_PATH.exists():
            try:
                with open(DB_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Ошибка загрузки БД: {e}")
        
        # Стартовая БД с популярными вариациями имен
        return {
            "artists": {
                # Формат: "нормализованное_имя": {
                #     "original": "Оригинальное имя",
                #     "variations": ["вариант1", "вариант2"],
                #     "tracks": {"трек1": "оригинальное название", ...}
                # }
            },
            "artist_aliases": {
                # Быстрый поиск: "моргенштерн" -> "morgenshtern"
            }
        }
    
    def _save_db(self):
        """Сохраняет базу данных"""
        try:
            with open(DB_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.db, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ Ошибка сохранения БД: {e}")
    
    def _normalize_text(self, text: str) -> str:
        """Нормализует текст для сравнения"""
        text = text.lower().strip()
        # Убираем специальные символы, оставляем буквы и пробелы
        text = re.sub(r'[^\w\s]', '', text)
        # Убираем множественные пробелы
        text = re.sub(r'\s+', ' ', text)
        return text
    
    def _split_artist_track(self, query: str) -> Tuple[str, str]:
        """
        Пытается разделить запрос на артиста и трек
        Примеры:
        - "Моргенштерн Cadillac" -> ("Моргенштерн", "Cadillac")
        - "Twenty One Pilots Stressed Out" -> ("Twenty One Pilots", "Stressed Out")
        """
        query = query.strip()
        
        # Стратегия 1: Ищем известного артиста в начале строки
        best_artist_match = self._find_artist_in_text(query)
        if best_artist_match:
            artist_name, artist_len = best_artist_match
            # Оставшаяся часть - потенциальное название трека
            track_part = query[artist_len:].strip()
            return artist_name, track_part
        
        # Стратегия 2: Разбиваем по первому длинному слову (артист = 1-2 слова)
        words = query.split()
        if len(words) >= 2:
            # Пробуем первое слово как артиста
            return words[0], ' '.join(words[1:])
        
        # Стратегия 3: Весь текст - это артист (трек пустой)
        return query, ""
    
    def _find_artist_in_text(self, text: str) -> Optional[Tuple[str, int]]:
        """
        Ищет известного артиста в начале текста
        Возвращает: (имя_артиста, длина_совпадения) или None
        """
        text_norm = self._normalize_text(text)
        
        # Проверяем все известные артисты
        for artist_key, artist_data in self.db["artists"].items():
            original = artist_data["original"]
            variations = artist_data.get("variations", [])
            
            all_variants = [original] + variations
            for variant in all_variants:
                variant_norm = self._normalize_text(variant)
                
                # Проверяем, начинается ли текст с этого артиста
                if text_norm.startswith(variant_norm):
                    # Проверяем, что после имени артиста идет пробел или конец строки
                    artist_len = len(variant_norm)
                    if artist_len == len(text_norm) or text_norm[artist_len] == ' ':
                        return (original, len(variant))
        
        return None
    
    def add_artist(self, artist_name: str, variations: List[str] = None):
        """
        Добавляет артиста в базу данных
        artist_name: Оригинальное имя артиста (как в Spotify)
        variations: Список вариаций имени (русские транскрипции и т.д.)
        """
        artist_key = self._normalize_text(artist_name)
        
        if artist_key not in self.db["artists"]:
            self.db["artists"][artist_key] = {
                "original": artist_name,
                "variations": variations or [],
                "tracks": {}
            }
            
            # Добавляем алиасы для быстрого поиска
            for var in variations or []:
                var_norm = self._normalize_text(var)
                self.db["artist_aliases"][var_norm] = artist_key
            
            self._save_db()
            print(f"✅ Артист '{artist_name}' добавлен в БД")
    
    def add_track(self, artist_name: str, track_name: str, track_variations: List[str] = None):
        """Добавляет трек артиста в базу"""
        artist_key = self._normalize_text(artist_name)
        
        if artist_key not in self.db["artists"]:
            self.add_artist(artist_name)
        
        track_key = self._normalize_text(track_name)
        self.db["artists"][artist_key]["tracks"][track_key] = {
            "original": track_name,
            "variations": track_variations or []
        }
        
        self._save_db()
    
    def fetch_artist_top_tracks(self, artist_name: str, limit: int = 50):
        """
        Загружает топ-треки артиста из Spotify и добавляет в БД
        """
        if not self.sp_manager or not self.sp_manager.sp:
            print("❌ Spotify Manager не инициализирован")
            return False
        
        try:
            # Ищем артиста
            results = self.sp_manager.sp.search(q=f"artist:{artist_name}", type='artist', limit=1)
            if not results['artists']['items']:
                print(f"❌ Артист '{artist_name}' не найден в Spotify")
                return False
            
            artist = results['artists']['items'][0]
            artist_id = artist['id']
            artist_original_name = artist['name']
            
            # Добавляем артиста в БД
            self.add_artist(artist_original_name, variations=[artist_name] if artist_name != artist_original_name else [])
            
            # Загружаем топ-треки артиста
            top_tracks = self.sp_manager.sp.artist_top_tracks(artist_id, country='RU')
            
            for track in top_tracks['tracks'][:limit]:
                track_name = track['name']
                self.add_track(artist_original_name, track_name)
            
            print(f"✅ Загружено {len(top_tracks['tracks'])} треков для '{artist_original_name}'")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка загрузки треков: {e}")
            return False
    
    def smart_search(self, query: str) -> Optional[str]:
        """
        Умный поиск трека с fuzzy matching
        Возвращает: строку запроса для Spotify или None
        """
        query = query.strip()
        if not query:
            return None
        
        print(f"🔍 Умный поиск: '{query}'")
        
        # Шаг 1: Разделяем на артиста и трек
        artist_part, track_part = self._split_artist_track(query)
        print(f"   Разбор: артист='{artist_part}', трек='{track_part}'")
        
        # Шаг 2: Ищем артиста в БД с fuzzy matching
        artist_match = self._fuzzy_find_artist(artist_part)
        
        if not artist_match:
            # Артист не найден - возвращаем оригинальный запрос
            print(f"   ⚠️ Артист не найден в БД, использую оригинальный запрос")
            return query
        
        artist_original = artist_match
        print(f"   ✅ Артист распознан: '{artist_original}'")
        
        # Шаг 3: Если есть часть с треком - ищем его в БД артиста
        if track_part:
            track_match = self._fuzzy_find_track(artist_original, track_part)
            if track_match:
                print(f"   ✅ Трек распознан: '{track_match}'")
                return f"{artist_original} {track_match}"
            else:
                print(f"   ⚠️ Трек не найден в БД, использую '{track_part}'")
                return f"{artist_original} {track_part}"
        
        # Только артист - возвращаем его
        return artist_original
    
    def _fuzzy_find_artist(self, query: str) -> Optional[str]:
        """Ищет артиста в БД с fuzzy matching"""
        query_norm = self._normalize_text(query)
        
        # Собираем все возможные варианты имен артистов
        choices = []
        artist_map = {}  # вариант -> оригинальное имя
        
        for artist_key, artist_data in self.db["artists"].items():
            original = artist_data["original"]
            variations = artist_data.get("variations", [])
            
            # Добавляем оригинал и вариации
            for variant in [original] + variations:
                variant_norm = self._normalize_text(variant)
                choices.append(variant_norm)
                artist_map[variant_norm] = original
        
        if not choices:
            return None
        
        # Fuzzy matching
        match = process.extractOne(
            query_norm, 
            choices, 
            scorer=fuzz.token_sort_ratio
        )
        
        if match and match[1] >= ARTIST_MATCH_THRESHOLD:
            matched_variant = match[0]
            return artist_map[matched_variant]
        
        return None
    
    def _fuzzy_find_track(self, artist_name: str, track_query: str) -> Optional[str]:
        """Ищет трек артиста в БД с fuzzy matching"""
        artist_key = self._normalize_text(artist_name)
        
        if artist_key not in self.db["artists"]:
            return None
        
        artist_data = self.db["artists"][artist_key]
        tracks = artist_data.get("tracks", {})
        
        if not tracks:
            return None
        
        # Собираем все варианты названий треков
        choices = []
        track_map = {}
        
        for track_key, track_data in tracks.items():
            original = track_data["original"]
            variations = track_data.get("variations", [])
            
            for variant in [original] + variations:
                variant_norm = self._normalize_text(variant)
                choices.append(variant_norm)
                track_map[variant_norm] = original
        
        track_query_norm = self._normalize_text(track_query)
        
        # Fuzzy matching
        match = process.extractOne(
            track_query_norm,
            choices,
            scorer=fuzz.token_sort_ratio
        )
        
        if match and match[1] >= TRACK_MATCH_THRESHOLD:
            matched_variant = match[0]
            return track_map[matched_variant]
        
        return None


# Глобальный экземпляр
_smart_search = None

def get_smart_search() -> SpotifySmartSearch:
    """Получить глобальный экземпляр умного поиска"""
    global _smart_search
    if _smart_search is None:
        _smart_search = SpotifySmartSearch()
    return _smart_search
