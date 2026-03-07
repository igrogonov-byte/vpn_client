"""
Управление автозапуском
Кроссплатформенная реализация для Windows, Linux, macOS
"""
import sys
import os
import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class AutoStart:
    """Управление автозапуском приложения
    __slots__ для экономии памяти
    """
    __slots__ = ['app_name', 'app_path']

    def __init__(self, app_name: str = "VPNClient", app_path: Optional[str] = None):
        self.app_name = app_name
        self.app_path = app_path or self._get_app_path()
    
    def _get_app_path(self) -> str:
        """Получение пути к исполняемому файлу"""
        if getattr(sys, 'frozen', False):
            # Запущено как скомпилированное приложение
            return sys.executable
        else:
            # Запущено как скрипт
            return sys.executable
    
    def is_enabled(self) -> bool:
        """Проверка статуса автозапуска"""
        if sys.platform == "win32":
            return self._is_enabled_windows()
        elif sys.platform == "darwin":
            return self._is_enabled_macos()
        else:
            return self._is_enabled_linux()
    
    def enable(self) -> bool:
        """Включение автозапуска"""
        if sys.platform == "win32":
            return self._enable_windows()
        elif sys.platform == "darwin":
            return self._enable_macos()
        else:
            return self._enable_linux()
    
    def disable(self) -> bool:
        """Отключение автозапуска"""
        if sys.platform == "win32":
            return self._disable_windows()
        elif sys.platform == "darwin":
            return self._disable_macos()
        else:
            return self._disable_linux()
    
    # === Windows ===
    
    def _is_enabled_windows(self) -> bool:
        """Проверка автозапуска на Windows"""
        try:
            import winreg
            
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_READ
            )
            
            try:
                value = winreg.QueryValueEx(key, self.app_name)
                winreg.CloseKey(key)
                return value[0] == self.app_path
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False
                
        except Exception as e:
            logger.error(f"Ошибка проверки автозапуска Windows: {e}")
            return False
    
    def _enable_windows(self) -> bool:
        """Включение автозапуска на Windows"""
        try:
            import winreg
            
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(key, self.app_name, 0, winreg.REG_SZ, self.app_path)
            winreg.CloseKey(key)
            
            logger.info(f"Автозапуск включен: {self.app_name}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка включения автозапуска Windows: {e}")
            return False
    
    def _disable_windows(self) -> bool:
        """Отключение автозапуска на Windows"""
        try:
            import winreg
            
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )
            
            try:
                winreg.DeleteValue(key, self.app_name)
            except FileNotFoundError:
                pass
            
            winreg.CloseKey(key)
            
            logger.info("Автозапуск отключен")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отключения автозапуска Windows: {e}")
            return False
    
    # === Linux ===
    
    def _is_enabled_linux(self) -> bool:
        """Проверка автозапуска на Linux"""
        desktop_file = self._get_linux_desktop_path()
        return desktop_file.exists()
    
    def _get_linux_desktop_path(self) -> Path:
        """Получение пути к .desktop файлу"""
        xdg_config = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
        return xdg_config / 'autostart' / f'{self.app_name.lower()}.desktop'
    
    def _enable_linux(self) -> bool:
        """Включение автозапуска на Linux"""
        try:
            desktop_file = self._get_linux_desktop_path()
            desktop_file.parent.mkdir(parents=True, exist_ok=True)
            
            content = f"""[Desktop Entry]
Type=Application
Name={self.app_name}
Exec={self.app_path}
Comment=VPN Client AutoStart
X-GNOME-Autostart-enabled=true
"""
            
            with open(desktop_file, 'w') as f:
                f.write(content)
            
            logger.info(f"Автозапуск включен: {desktop_file}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка включения автозапуска Linux: {e}")
            return False
    
    def _disable_linux(self) -> bool:
        """Отключение автозапуска на Linux"""
        try:
            desktop_file = self._get_linux_desktop_path()
            if desktop_file.exists():
                desktop_file.unlink()
            
            logger.info("Автозапуск отключен")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отключения автозапуска Linux: {e}")
            return False
    
    # === macOS ===
    
    def _is_enabled_macos(self) -> bool:
        """Проверка автозапуска на macOS"""
        plist_file = self._get_macos_plist_path()
        return plist_file.exists()
    
    def _get_macos_plist_path(self) -> Path:
        """Получение пути к .plist файлу"""
        return Path.home() / 'Library' / 'LaunchAgents' / f'{self.app_name}.plist'
    
    def _enable_macos(self) -> bool:
        """Включение автозапуска на macOS"""
        try:
            plist_file = self._get_macos_plist_path()
            plist_file.parent.mkdir(parents=True, exist_ok=True)
            
            content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{self.app_name}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{self.app_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>Hide</key>
    <true/>
</dict>
</plist>
"""
            
            with open(plist_file, 'w') as f:
                f.write(content)
            
            # Загрузка launchd
            subprocess.run(
                ['launchctl', 'load', str(plist_file)],
                check=False,
                capture_output=True
            )
            
            logger.info(f"Автозапуск включен: {plist_file}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка включения автозапуска macOS: {e}")
            return False
    
    def _disable_macos(self) -> bool:
        """Отключение автозапуска на macOS"""
        try:
            plist_file = self._get_macos_plist_path()
            
            # Выгрузка из launchd
            subprocess.run(
                ['launchctl', 'unload', str(plist_file)],
                check=False,
                capture_output=True
            )
            
            if plist_file.exists():
                plist_file.unlink()
            
            logger.info("Автозапуск отключен")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отключения автозапуска macOS: {e}")
            return False


# Импорт для type hints
from typing import Optional
