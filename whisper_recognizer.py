import pyaudio
import numpy as np
from faster_whisper import WhisperModel
import time


class WhisperRecognizer:
    """
    Распознавание речи через Whisper (faster-whisper)
    Оптимизированная версия БЕЗ временных файлов
    """
    
    def __init__(self, model_size="small", device="cpu", compute_type="int8"):
        print(f"🔄 Загрузка Whisper модели '{model_size}'...")
        print(f"   Устройство: {device}, тип вычислений: {compute_type}")
        
        start_time = time.time()
        
        try:
            self.model = WhisperModel(
                model_size_or_path=model_size,
                device=device,
                compute_type=compute_type,
                download_root=None,
                local_files_only=False
            )
            
            load_time = time.time() - start_time
            print(f"✅ Whisper модель загружена за {load_time:.2f} сек")
            
        except Exception as e:
            print(f"❌ Ошибка загрузки Whisper: {e}")
            print("💡 Убедитесь что установлен faster-whisper: pip install faster-whisper")
            raise
        
        # Параметры аудио
        self.sample_rate = 16000
        self.channels = 1
        self.chunk_size = 8000
        
        # VAD параметры
        self.silence_threshold = 500
        self.silence_duration = 1.5
    
    def recognize_command(self, timeout=3, language="ru"):
        """
        Распознаёт голосовую команду с микрофона
        ✅ БЕЗ временных файлов - напрямую в Whisper
        """
        print(f"🎤 Слушаю команду (таймаут: {timeout} сек)...")
        
        try:
            # Записываем аудио в numpy array
            audio_array = self._record_audio_with_vad(timeout)
            
            if audio_array is None or len(audio_array) == 0:
                print("⚠️ Аудио не записано")
                return None
            
            # ✅ ПРЯМАЯ ПЕРЕДАЧА в Whisper (без сохранения в файл)
            result_text = self._transcribe_audio_direct(audio_array, language)
            
            return result_text
            
        except Exception as e:
            print(f"❌ Ошибка распознавания: {e}")
            return None
    
    def _record_audio_with_vad(self, timeout):
        """
        Запись с Voice Activity Detection
        ✅ Возвращает numpy array вместо WAV файла
        """
        audio = pyaudio.PyAudio()
        stream = None
        
        try:
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            print("🔴 Запись... (остановится при тишине)")
            frames = []
            
            silence_chunks_threshold = int(
                (self.silence_duration * self.sample_rate) / self.chunk_size
            )
            consecutive_silence = 0
            max_chunks = int(self.sample_rate / self.chunk_size * timeout)
            
            for i in range(max_chunks):
                data = stream.read(self.chunk_size, exception_on_overflow=False)
                frames.append(data)
                
                # Анализ громкости
                audio_chunk = np.frombuffer(data, dtype=np.int16)
                volume = np.abs(audio_chunk).mean()
                
                if volume < self.silence_threshold:
                    consecutive_silence += 1
                else:
                    consecutive_silence = 0
                
                # Ранний выход при тишине
                if consecutive_silence >= silence_chunks_threshold and len(frames) > 5:
                    print(f"⏹️ Обнаружена тишина ({self.silence_duration} сек)")
                    break
            else:
                print("⏹️ Таймаут достигнут")
            
            # ✅ КОНВЕРТАЦИЯ: bytes → numpy array → float32 (формат Whisper)
            audio_bytes = b''.join(frames)
            audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
            
            # Нормализация: int16 [-32768, 32767] → float32 [-1.0, 1.0]
            audio_float32 = audio_int16.astype(np.float32) / 32768.0
            
            return audio_float32
            
        except Exception as e:
            print(f"❌ Ошибка записи аудио: {e}")
            return None
            
        finally:
            if stream:
                stream.stop_stream()
                stream.close()
            audio.terminate()
    
    def _transcribe_audio_direct(self, audio_array, language):
        """
        ✅ НОВЫЙ МЕТОД: Распознавание из numpy array (без файлов)
        
        Args:
            audio_array (np.ndarray): Аудио в формате float32
            language (str): Код языка или None
        
        Returns:
            str: Распознанный текст
        """
        print("🧠 Обработка через Whisper...")
        
        start_time = time.time()
        
        try:
            # ✅ ПРЯМАЯ ПЕРЕДАЧА numpy array в Whisper
            segments, info = self.model.transcribe(
                audio_array,  # ← Вместо пути к файлу передаём массив!
                language=language,
                task="transcribe",
                
                # Оптимизации для скорости
                beam_size=1,
                best_of=1,
                
                # VAD в Whisper
                vad_filter=True,
                vad_parameters=dict(
                    threshold=0.5,
                    min_speech_duration_ms=250,
                    min_silence_duration_ms=500
                ),
                
                temperature=0.0,
                condition_on_previous_text=False,
                word_timestamps=False
            )
            
            result_text = " ".join([segment.text.strip() for segment in segments])
            
            elapsed_time = time.time() - start_time
            
            if result_text:
                print(f"📝 Распознано за {elapsed_time:.2f} сек: '{result_text}'")
                print(f"   Язык: {info.language} (уверенность: {info.language_probability:.2%})")
            else:
                print(f"⚠️ Ничего не распознано (обработка заняла {elapsed_time:.2f} сек)")
            
            return result_text if result_text else None
            
        except Exception as e:
            print(f"❌ Ошибка транскрибации: {e}")
            return None
    
    def listen_for_text(self, timeout=10):
        """
        Слушает произвольный текст с автоопределением языка (только ru/en)
        ✅ Одиночный проход - быстрее
        """
        print(f"🎤 Жду название трека (макс. {timeout} сек, остановится при тишине)...")
        
        try:
            # Записываем аудио
            audio_array = self._record_audio_with_vad(timeout)
            
            if audio_array is None or len(audio_array) == 0:
                print("⚠️ Аудио не записано")
                return None
            
            # ✅ Распознаём с автоопределением языка
            print("🧠 Обработка через Whisper...")
            start_time = time.time()
            
            segments, info = self.model.transcribe(
                audio_array,
                language=None,  # Автоопределение
                task="transcribe",
                beam_size=1,
                best_of=1,
                vad_filter=True,
                vad_parameters=dict(
                    threshold=0.5,
                    min_speech_duration_ms=250,
                    min_silence_duration_ms=500
                ),
                temperature=0.0,
                condition_on_previous_text=False,
                word_timestamps=False
            )
            
            result_text = " ".join([segment.text.strip() for segment in segments])
            elapsed_time = time.time() - start_time
            
            detected_lang = info.language
            confidence = info.language_probability
            
            # ✅ ПРОВЕРКА: Если язык НЕ ru/en → переспрашиваем
            if detected_lang not in ['ru', 'en']:
                print(f"⚠️ Определён неподдерживаемый язык: {detected_lang} ({confidence:.2%})")
                print(f"   Распознано: '{result_text}'")
                print(f"   Сравниваем уверенность для ru vs en...")
                
                # Распознаём как РУССКИЙ
                segments_ru, info_ru = self.model.transcribe(
                    audio_array,
                    language='ru',
                    task="transcribe",
                    beam_size=1,
                    best_of=1,
                    vad_filter=True,
                    temperature=0.0,
                    condition_on_previous_text=False,
                    word_timestamps=False
                )
                text_ru = " ".join([segment.text.strip() for segment in segments_ru])
                confidence_ru = info_ru.language_probability
                
                # Распознаём как АНГЛИЙСКИЙ
                segments_en, info_en = self.model.transcribe(
                    audio_array,
                    language='en',
                    task="transcribe",
                    beam_size=1,
                    best_of=1,
                    vad_filter=True,
                    temperature=0.0,
                    condition_on_previous_text=False,
                    word_timestamps=False
                )
                text_en = " ".join([segment.text.strip() for segment in segments_en])
                confidence_en = info_en.language_probability
                
                # Выбираем язык с БОЛЬШЕЙ уверенностью
                print(f"   📊 Русский: '{text_ru}' (уверенность: {confidence_ru:.2%})")
                print(f"   📊 Английский: '{text_en}' (уверенность: {confidence_en:.2%})")
                
                if confidence_ru > confidence_en:
                    result_text = text_ru
                    print(f"   ✅ Выбран русский (выше уверенность)")
                else:
                    result_text = text_en
                    print(f"   ✅ Выбран английский (выше уверенность)")
            else:
                # Язык поддерживается
                print(f"📝 Распознано за {elapsed_time:.2f} сек: '{result_text}'")
                print(f"   Язык: {detected_lang} (уверенность: {confidence:.2%})")
            
            return result_text if result_text else None
            
        except Exception as e:
            print(f"❌ Ошибка распознавания: {e}")
            return None



# ============================================
# Utility функции для тестирования
# ============================================

def test_whisper_basic():
    """Базовый тест распознавания"""
    print("\n" + "="*50)
    print("ТЕСТ: Базовое распознавание")
    print("="*50 + "\n")
    
    recognizer = WhisperRecognizer(model_size="small")
    
    print("\n🎤 Скажите что-нибудь (например: 'привет компьютер')...")
    result = recognizer.recognize_command(timeout=3)
    
    if result:
        print(f"\n✅ УСПЕХ! Распознано: '{result}'")
    else:
        print("\n❌ Не удалось распознать")


def test_whisper_music():
    """Тест распознавания музыкальных названий"""
    print("\n" + "="*50)
    print("ТЕСТ: Распознавание музыкальных треков")
    print("="*50 + "\n")
    
    recognizer = WhisperRecognizer(model_size="small")
    
    print("\n🎤 Скажите название трека на английском (например: 'tveth Paramedic')...")
    result = recognizer.recognize_command(timeout=4, language=None)
    
    if result:
        print(f"\n✅ УСПЕХ! Распознано: '{result}'")
        print(f"   (Проверьте правильность английских слов)")
    else:
        print("\n❌ Не удалось распознать")


if __name__ == "__main__":
    # Базовый тест
    test_whisper_basic()
    
    # Тест музыкальных треков
    # test_whisper_music()
