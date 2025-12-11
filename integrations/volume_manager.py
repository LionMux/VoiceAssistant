"""
Управление громкостью системы Windows
Приглушает все активные звуки при wake word
"""

from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

class VolumeManager:
    def __init__(self):
        """Инициализация менеджера громкости"""
        self.saved_volumes = {}  # Сохраненные громкости приложений
        self.ducking_enabled = True  # Флаг включения/отключения
        
    def duck_audio(self, target_volume=0.1):
        """
        Приглушает все активные звуки
        target_volume: 0.1 = 10%, 0.2 = 20%, и т.д.
        """
        if not self.ducking_enabled:
            return
        
        try:
            sessions = AudioUtilities.GetAllSessions()
            
            for session in sessions:
                volume = session.SimpleAudioVolume
                
                if session.Process and volume:
                    # Получаем имя процесса
                    process_name = session.Process.name()
                    
                    # Сохраняем текущую громкость
                    current_volume = volume.GetMasterVolume()
                    
                    # Пропускаем если звук уже на нуле
                    if current_volume > 0.01:
                        self.saved_volumes[process_name] = current_volume
                        
                        # Понижаем до 10%
                        volume.SetMasterVolume(target_volume, None)
                        
        except Exception as e:
            print(f"⚠️  Ошибка приглушения: {e}")
    
    def restore_audio(self):
        """Восстанавливает громкость на исходный уровень"""
        if not self.ducking_enabled:
            return
        
        try:
            sessions = AudioUtilities.GetAllSessions()
            
            for session in sessions:
                volume = session.SimpleAudioVolume
                
                if session.Process and volume:
                    process_name = session.Process.name()
                    
                    # Если есть сохраненная громкость - восстанавливаем
                    if process_name in self.saved_volumes:
                        volume.SetMasterVolume(
                            self.saved_volumes[process_name], 
                            None
                        )
            
            # Очищаем сохраненные громкости
            self.saved_volumes.clear()
            
        except Exception as e:
            print(f"⚠️  Ошибка восстановления: {e}")
    
    def disable(self):
        """Отключить управление громкостью (откат)"""
        self.ducking_enabled = False
    
    def enable(self):
        """Включить управление громкостью"""
        self.ducking_enabled = True


# Глобальный экземпляр
_volume_manager = None

def get_volume_manager():
    """Получить глобальный экземпляр VolumeManager"""
    global _volume_manager
    if _volume_manager is None:
        _volume_manager = VolumeManager()
    return _volume_manager
