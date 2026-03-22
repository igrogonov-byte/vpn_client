"""
Управление системным прокси
Кроссплатформенная реализация для Windows, Linux
"""
import sys
import subprocess
import logging
from typing import Optional

logger = logging.getLogger('vpn_client.proxy')


class SystemProxy:
    """Управление системным прокси
    __slots__ для экономии памяти
    """
    __slots__ = ['original_settings', 'is_enabled']

    def __init__(self):
        self.original_settings = None
        self.is_enabled = False
    
    def enable(self, host: str = "127.0.0.1", port: int = 10808) -> bool:
        """
        Включение системного прокси

        Args:
            host: Хост прокси (обычно 127.0.0.1)
            port: Порт прокси
        """
        if sys.platform == "win32":
            return self._enable_windows(host, port)
        else:
            return self._enable_linux(host, port)

    def disable(self) -> bool:
        """Отключение системного прокси"""
        if sys.platform == "win32":
            return self._disable_windows()
        else:
            return self._disable_linux()
    
    # === Windows ===
    
    def _enable_windows(self, host: str, port: int) -> bool:
        """Включение прокси на Windows"""
        try:
            import winreg
            
            # Сохраняем оригинальные настройки
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                    0,
                    winreg.KEY_READ
                )
                self.original_settings = {
                    "ProxyEnable": winreg.QueryValueEx(key, "ProxyEnable")[0],
                    "ProxyServer": winreg.QueryValueEx(key, "ProxyServer")[0] if winreg.QueryValueEx(key, "ProxyServer")[0] else ""
                }
                winreg.CloseKey(key)
            except FileNotFoundError:
                self.original_settings = {"ProxyEnable": 0, "ProxyServer": ""}
            
            # Включаем прокси
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                0,
                winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, f"{host}:{port}")
            winreg.CloseKey(key)
            
            logger.info(f"Системный прокси включен: {host}:{port}")
            self.is_enabled = True
            return True
            
        except Exception as e:
            logger.error(f"Ошибка включения прокси Windows: {e}")
            return False
    
    def _disable_windows(self) -> bool:
        """Отключение прокси на Windows"""
        try:
            import winreg
            
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                0,
                winreg.KEY_SET_VALUE
            )
            
            if self.original_settings:
                winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 
                                 self.original_settings.get("ProxyEnable", 0))
                winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ,
                                 self.original_settings.get("ProxyServer", ""))
            else:
                winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
                winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, "")
            
            winreg.CloseKey(key)
            
            logger.info("Системный прокси отключен")
            self.is_enabled = False
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отключения прокси Windows: {e}")
            return False
    
    # === Linux ===

    def _enable_linux(self, host: str, port: int) -> bool:
        """Включение прокси на Linux"""
        logger.info(f"_enable_linux вызван: host={host}, port={port}")

        # Проверка параметров
        if not host or not port:
            logger.error(f"Неверные параметры: host={host}, port={port}")
            return False

        try:
            # Сначала выключаем прокси (сброс)
            logger.info("Сбрасываем прокси в none...")
            subprocess.run(
                ["gsettings", "set", "org.gnome.system.proxy", "mode", "none"],
                capture_output=True, timeout=3
            )
            logger.info("Прокси сброшен")

            # Небольшая задержка
            import time
            logger.info("Задержка 0.5 сек...")
            time.sleep(0.5)

            # Метод 1: gsettings (GNOME) - включаем прокси
            logger.info("Выполняем команды gsettings...")
            commands = [
                ["gsettings", "set", "org.gnome.system.proxy", "mode", "manual"],
                ["gsettings", "set", "org.gnome.system.proxy.http", "host", str(host)],
                ["gsettings", "set", "org.gnome.system.proxy.http", "port", str(port)],
                ["gsettings", "set", "org.gnome.system.proxy.https", "host", str(host)],
                ["gsettings", "set", "org.gnome.system.proxy.https", "port", str(port)],
                ["gsettings", "set", "org.gnome.system.proxy.socks", "host", str(host)],
                ["gsettings", "set", "org.gnome.system.proxy.socks", "port", str(port)],
            ]

            for i, cmd in enumerate(commands):
                logger.debug(f"Команда {i+1}: {' '.join(cmd)}")
                result = subprocess.run(cmd, check=False, capture_output=True, timeout=5)
                if result.returncode != 0:
                    logger.warning(f"gsettings command {i+1} failed: {result.stderr.decode()}")
                else:
                    logger.debug(f"Команда {i+1} выполнена успешно")

            # Задержка для применения настроек
            logger.info("Задержка 0.5 сек после команд...")
            time.sleep(0.5)

            # Проверка что прокси включился
            logger.info("Проверяем режим прокси...")
            result = subprocess.run(
                ["gsettings", "get", "org.gnome.system.proxy", "mode"],
                capture_output=True, text=True, timeout=5
            )
            
            mode = result.stdout.strip().strip("'")
            logger.info(f"Текущий режим: {mode}")
            
            if mode != "manual":
                logger.error(f"Прокси не включился! Режим: {mode}, пробуем ещё раз...")
                subprocess.run(
                    ["gsettings", "set", "org.gnome.system.proxy", "mode", "manual"],
                    capture_output=True, timeout=3
                )
                time.sleep(0.5)

            # Метод 2: Экспорт в текущую сессию (для приложений)
            logger.info("Экспорт переменных окружения...")
            import os
            os.environ["http_proxy"] = f"http://{host}:{port}"
            os.environ["https_proxy"] = f"http://{host}:{port}"
            os.environ["socks_proxy"] = f"socks5://{host}:{port}"
            os.environ["HTTP_PROXY"] = f"http://{host}:{port}"
            os.environ["HTTPS_PROXY"] = f"http://{host}:{port}"
            os.environ["SOCKS_PROXY"] = f"socks5://{host}:{port}"
            logger.info("Переменные окружения установлены")

            logger.info(f"Системный прокси включен: {host}:{port}")
            self.is_enabled = True
            
            # Финальная проверка
            logger.info("Финальная проверка режима...")
            result = subprocess.run(
                ["gsettings", "get", "org.gnome.system.proxy", "mode"],
                capture_output=True, text=True, timeout=5
            )
            final_mode = result.stdout.strip().strip("'")
            logger.info(f"Финальный режим прокси: {final_mode}")
            
            return final_mode == "manual"

        except Exception as e:
            logger.error(f"Ошибка включения прокси Linux: {e}", exc_info=True)
            # Пробуем хотя бы экспорт переменных
            import os
            os.environ["http_proxy"] = f"http://{host}:{port}"
            os.environ["https_proxy"] = f"http://{host}:{port}"
            os.environ["socks_proxy"] = f"socks5://{host}:{port}"
            self.is_enabled = True
            return True

    def _disable_linux(self) -> bool:
        """Отключение прокси на Linux"""
        logger.info("_disable_linux вызван")
        try:
            logger.info("Переключаем прокси в режим 'none'...")
            result = subprocess.run(
                ["gsettings", "set", "org.gnome.system.proxy", "mode", "none"],
                check=False,
                capture_output=True,
                timeout=5
            )
            logger.info(f"Результат: returncode={result.returncode}, stdout={result.stdout}, stderr={result.stderr}")
            
            # Проверка режима
            check_result = subprocess.run(
                ["gsettings", "get", "org.gnome.system.proxy", "mode"],
                capture_output=True, text=True, timeout=5
            )
            mode = check_result.stdout.strip().strip("'")
            logger.info(f"Текущий режим прокси: {mode}")

            # Очистка переменных окружения
            logger.info("Очистка переменных окружения...")
            import os
            for var in ["http_proxy", "https_proxy", "socks_proxy",
                       "HTTP_PROXY", "HTTPS_PROXY", "SOCKS_PROXY"]:
                os.environ.pop(var, None)

            logger.info("✅ Системный прокси отключен")
            self.is_enabled = False
            return mode == "none"

        except Exception as e:
            logger.error(f"Ошибка отключения прокси Linux: {e}", exc_info=True)
            return False
