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
            elif sys.platform == "darwin":
                self.config_dir = Path.home() / "Library" / "Application Support" / "VPNClient"
            else:
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
