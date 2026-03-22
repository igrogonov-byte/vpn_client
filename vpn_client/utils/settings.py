"""
Менеджер настроек приложения
Сохранение и загрузка конфигурации
"""
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class SettingsManager:
    """Менеджер настроек приложения"""
    
    def __init__(self, config_dir: Optional[str] = None):
        from pathlib import Path
        import sys

        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            # Директория конфигурации по умолчанию
            if sys.platform == "win32":
                self.config_dir = Path.home() / "AppData" / "Roaming" / "VPNClient"
            else:
                # Linux
                self.config_dir = Path.home() / ".config" / "vpnclient"

        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.settings_file = self.config_dir / "settings.json"
    
    def save(self, settings: Dict[str, Any]) -> bool:
        """Сохранение настроек"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            logger.info(f"Настройки сохранены: {self.settings_file}")
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения настроек: {e}")
            return False
    
    def load(self) -> Dict[str, Any]:
        """Загрузка настроек"""
        if not self.settings_file.exists():
            return {}
        
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки настроек: {e}")
            return {}
    
    def save_last_config(self, config: Dict[str, Any]) -> bool:
        """Сохранение последней конфигурации подключения"""
        settings = self.load()
        settings['last_config'] = config
        return self.save(settings)
    
    def get_last_config(self) -> Optional[Dict[str, Any]]:
        """Получение последней конфигурации"""
        settings = self.load()
        return settings.get('last_config')
    
    def save_window_geometry(self, x: int, y: int, width: int, height: int) -> bool:
        """Сохранение положения и размера окна"""
        settings = self.load()
        settings['window_geometry'] = {
            'x': x,
            'y': y,
            'width': width,
            'height': height
        }
        return self.save(settings)
    
    def get_window_geometry(self) -> Optional[Dict[str, int]]:
        """Получение положения и размера окна"""
        settings = self.load()
        return settings.get('window_geometry')

    def save_profile(self, name: str, config: Dict[str, Any]) -> bool:
        """Сохранение профиля подключения"""
        settings = self.load()
        if 'profiles' not in settings:
            settings['profiles'] = {}
        settings['profiles'][name] = config
        return self.save(settings)

    def load_profile(self, name: str) -> Optional[Dict[str, Any]]:
        """Загрузка профиля подключения"""
        settings = self.load()
        profiles = settings.get('profiles', {})
        return profiles.get(name)

    def get_profiles(self) -> Dict[str, Any]:
        """Получение списка всех профилей"""
        settings = self.load()
        return settings.get('profiles', {})

    def get_profile_names(self) -> list:
        """Получение списка имен профилей"""
        return list(self.get_profiles().keys())

    def delete_profile(self, name: str) -> bool:
        """Удаление профиля"""
        settings = self.load()
        if 'profiles' in settings and name in settings['profiles']:
            del settings['profiles'][name]
            return self.save(settings)
        return False
