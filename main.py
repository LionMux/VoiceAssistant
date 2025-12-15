import pyaudio
import struct
import pvporcupine
import config
import commands
import actions
import threading

#from telegram_bot import TelegramBotService
from integrations.async_sound import play_sound
from vosk_recognizer import VoskRecognizer
from whisper_recognizer import WhisperRecognizer
from pathlib import Path
from integrations.volume_manager import get_volume_manager
#from playsound3 import playsound

class VoiceAssistant:
    
    def __init__(self):
        print("pvporcupine.create")
        self._init_porcupine()
        self._init_audio()
        self._init_recognizers()
        self.volume_manager = get_volume_manager()
        self.whisper_loading = True
        self.whisper_thread = threading.Thread(target=self._preload_whisper_async, daemon=True)
        self.whisper_thread.start()
        print("Ассистент готов!")
    
    
    def _init_porcupine(self):
        
        try:
            keyword_path = Path(config.KEYWORD_PATH_NEW)
            if not keyword_path.exists():
                print(f"Файл wake word не найден: {keyword_path}")
                print("Создайте папку 'keywords' и положите туда .ppn файл")
                exit(1)
                
            self.porcupine = pvporcupine.create(access_key=config.PORCUPINE_ACCESS_KEY_NEW,
                                           keyword_paths=[str(keyword_path)],
                                           sensitivities =[config.PORCUPINE_SENSITIVITY])
        except Exception as e:
            print(f"Ошибка инициализации Porcupine: {e}")

    def _init_audio(self):
        self.audio = pyaudio.PyAudio()
        mic_index = config.MICROPHONE_INDEX
        try:                
            self.audio_stream = self.audio.open(
                rate = self.porcupine.sample_rate,
                channels=1,
                input_device_index=mic_index,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self.porcupine.frame_length
            )
            print("Аудио поток создан")
        except Exception as e:
            print(f"ошибка {e}")
            exit(1)

    def _preload_whisper(self):
        """
        ✅ НОВЫЙ МЕТОД: Предзагрузка Whisper при старте
        Загружается в фоне, пока пользователь не начал пользоваться
        """
        try:
            print("   🔄 Загрузка Whisper модели 'small'...")
            print("   (это может занять ~2 секунды при первом запуске)")
            
            self.whisper = WhisperRecognizer(
                model_size="small",
                device="cpu",
                compute_type="int8"
            )
            
            print("   ✅ Whisper предзагружен и готов к использованию")
            
        except Exception as e:
            print(f"   ⚠️ Не удалось предзагрузить Whisper: {e}")
            print("   (Будет загружен при первом запросе музыки)")
            self.whisper = None
    
    def _preload_whisper_async(self):
        """Асинхронная загрузка Whisper в фоновом потоке"""
        try:
            print("   🔄 [Фон] Загрузка Whisper модели 'small'...")
            
            self.whisper = WhisperRecognizer(
                model_size="small",
                device="cpu",
                compute_type="int8"
            )
            
            self.whisper_loading = False
            print("   ✅ [Фон] Whisper загружен и готов!")
            
        except Exception as e:
            print(f"   ⚠️ [Фон] Ошибка загрузки Whisper: {e}")
            self.whisper = None
            self.whisper_loading = False
    
    def _init_recognizers(self):
        """
        ✅ НОВЫЙ МЕТОД: Инициализация обоих распознавателей
        """
        # Vosk для быстрых команд
        try:
            print("🚀 Инициализация Vosk (быстрые команды)...")
            self.vosk = VoskRecognizer()
            print("✅ Vosk готов")
        except Exception as e:
            print(f"❌ Vosk не инициализирован: {e}")
            self.vosk = None
        
        # Whisper для музыкальных треков (ленивая загрузка)
        self.whisper = None  # Загрузим при первом использовании
        print("⏳ Whisper будет загружен при первом поиске музыки")
    
    def get_whisper(self):
        """Получить Whisper (ждём если ещё грузится)"""
        if self.whisper_loading:
            print("⏳ Whisper ещё загружается, ожидание...")
            self.whisper_thread.join()  # Ждём завершения загрузки
            print("✅ Whisper загружен!")
        
        if self.whisper is None:
            print("⚠️ Whisper не загружен, загружаю синхронно...")
            try:
                self.whisper = WhisperRecognizer(
                    model_size="small",
                    device="cpu",
                    compute_type="int8"
                )
            except Exception as e:
                print(f"❌ Не удалось загрузить Whisper: {e}")
                return None
        
        return self.whisper
    
    def _init_vosk(self):
        try:
            self.vosk = VoskRecognizer()
        except Exception as e:
            print(f"Vosk не инициализирован:{e}")
            self.vosk = None
    
    def listen_for_wake_word(self):
        
        try:
            pcm = self.audio_stream.read(
                self.porcupine.frame_length,
                exception_on_overflow = False
            )
            pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)
            keyword_index = self.porcupine.process(pcm)
            if keyword_index >= 0:
                print("wake word обнаружен!")
                self.volume_manager.duck_audio()
                return True
            return False
        except Exception as e:
            print(f"Ошибка: {e}")
            return False
    
    def play_sound(self, sound_path):
        if self.audio_stream.is_active():
            self.audio_stream.stop_stream()
        
        try:
            path = Path(sound_path)
            if not path.exists():
                print(f"Файл не найден: {sound_path}")
                return
            
            print(f"Воспроизведение: {path.name}")
            play_sound(str(path))
        
        except Exception as e:
            print(f"Ошибка воспроизведения: {e}")
        
        finally:
            if not self.audio_stream.is_active():
                self.audio_stream.start_stream()
    
    def play_response_sound(self):
        self.play_sound(config.SOUNDS_PATH)
                
    def process_command(self, command_text):
        if not command_text:
            print("команда пустая")
            self.play_sound(commands.ERROR_RESPONSE)
            self.volume_manager.restore_audio()
            return
        
        matched = commands.find_command(command_text)
        
        if matched:
            self.play_sound(matched["response"])
            if matched.get("action"):
                action_name = matched["action"]
                if action_name in actions.ACTIONS:
                    action_func = actions.ACTIONS[action_name]
                    if action_name == "spotify_play_track":
                        action_func(self.get_whisper())
                    else:
                        action_func()
                else:
                    print(f"Действие '{action_name}' не найдено")
        else:
            print("команда не распознана")
            self.play_sound(commands.ERROR_RESPONSE)
        self.volume_manager.restore_audio()
    
    def run(self):
        print("Голосовой ассистент V=0.3 (Hybrid: Vosk + Whisper) запущен")
        print(f"Произнесите: '{config.KEYWORD_NAME_NEW}'")
        
        try:
            while True:
                if self.listen_for_wake_word():
                    self.play_response_sound()
                    
                    # ✅ ИСПОЛЬЗУЕМ VOSK для обычных команд (быстро!)
                    if self.vosk:
                        command_text = self.vosk.recognize_command(config.COMMAND_TIMEOUT)
                        
                        if command_text:
                            self.process_command(command_text)
                        else:
                            print("Таймаут: команда не распознана")
                            self.play_sound(commands.ERROR_RESPONSE)
                            self.volume_manager.restore_audio()
                    else:
                        print("❌ Vosk не инициализирован")
                        self.play_sound(commands.ERROR_RESPONSE)
                        self.volume_manager.restore_audio()
                        
        except KeyboardInterrupt:
            print("\nЗавершение работы...")
        finally:
            self.cleanup()
    
    def cleanup(self):
        
        if hasattr(self, 'audio_stream') and self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()

        if hasattr(self, 'audio') and self.audio:
            self.audio.terminate()
        
        if hasattr(self, 'porcupine') and self.porcupine:
            self.porcupine.delete()
        
        print("✅ Ресурсы освобождены")

if __name__ == "__main__":
    # Создаем объект VoiceAssistant
    # При создании автоматически вызывается __init__
    assistant = VoiceAssistant()
    
    # Запускаем главный цикл
    assistant.run()