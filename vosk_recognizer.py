import pyaudio
import json
import vosk
import os
import config

class VoskRecognizer:
    
    def __init__(self):
        print("Загрузка модели Vosk")
        model_path = config.VOSK_MODEL_PATH
        
        if not os.path.exists(model_path):
            print(f"❌ Модель Vosk не найдена: {model_path}")
        
        vosk.SetLogLevel(-1)
        self.model = vosk.Model(model_path)
        self.sample_rate = 16000
        
    def recognize_command(self, timeout=2):
        print("🎤 Слушаю команду...")
        
        recognizer = vosk.KaldiRecognizer(self.model, self.sample_rate)
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=8000
        )
        
        result_text = ""
        
        try:
            import time
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                data = stream.read(4000, exception_on_overflow=False)
                
                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    if result.get("text"):
                        result_text = result["text"]
                        print(f"📝 Распознано: '{result_text}'")
            
            if not result_text:
                partial = json.loads(recognizer.FinalResult())
                result_text = partial.get("text", "")
                if result_text:
                    print(f"📝 Финальный результат: '{result_text}'")
        
        except Exception as e:
            print(f"❌ Ошибка распознавания: {e}")
        
        finally:
            stream.stop_stream()
            stream.close()
            audio.terminate()
        
        return result_text if result_text else None
    
    def listen_for_text(self, timeout=10):
        """
        НОВЫЙ МЕТОД: Слушает произвольный текст
        Используется для получения названия трека
        """
        import time
        
        print("🎤 Жду название трека...")
        recognizer = vosk.KaldiRecognizer(self.model, self.sample_rate)
        audio = pyaudio.PyAudio()
        
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=8000
        )
        stream.start_stream()
        
        result_text = ""
        start_time = time.time()
        
        try:
            while time.time() - start_time < timeout:
                data = stream.read(4000, exception_on_overflow=False)
                
                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    if result.get("text"):
                        result_text = result["text"]
                        print(f"📝 Услышал: '{result_text}'")
                        break
            
            if not result_text:
                partial = json.loads(recognizer.FinalResult())
                result_text = partial.get("text", "")
                
        finally:
            stream.stop_stream()
            stream.close()
            audio.terminate()
        
        return result_text if result_text else None
