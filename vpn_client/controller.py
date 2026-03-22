"""
VPN Controller - связующий слой между GUI и ядром
"""
import logging
import time
import threading
from pathlib import Path
from typing import Optional, Dict, Any, Callable

from vpn_client.core.xray_manager import XrayManager
from vpn_client.core.vless_config import create_vless_reality_xhttp, save_config
from vpn_client.core.xray_updater import get_updater, XrayUpdater
from vpn_client.utils.proxy import SystemProxy
from vpn_client.utils.autostart import AutoStart

logger = logging.getLogger(__name__)


class VPNController:
    """Контроллер VPN подключения
    __slots__ для экономии памяти
    """
    __slots__ = [
        'config_dir', 'config_file', 'xray_manager', 'system_proxy',
        'autostart', 'current_config', 'use_system_proxy',
        'on_status_change', 'on_log', 'on_update_available',
        'on_connection_lost',
        'xray_updater', '_update_check_thread'
    ]

    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir) if config_dir else self._get_default_config_dir()
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.config_file = self.config_dir / "config.json"

        self.xray_manager: Optional[XrayManager] = None
        self.system_proxy = SystemProxy()
        self.autostart = AutoStart("VPNClient")
        self.xray_updater: Optional[XrayUpdater] = None

        self.current_config: Optional[Dict[str, Any]] = None
        self.use_system_proxy = True

        # Callbacks
        self.on_status_change: Optional[Callable[[bool], None]] = None
        self.on_log: Optional[Callable[[str], None]] = None
        self.on_update_available: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_connection_lost: Optional[Callable[[], None]] = None

        # Запуск фоновой проверки обновлений
        self._start_update_check()

    def _get_default_config_dir(self) -> Path:
        import sys
        if sys.platform == "win32":
            return Path.home() / "AppData" / "Roaming" / "VPNClient"
        else:
            # Linux
            return Path.home() / ".config" / "vpnclient"

    def connect(self, config_data: Dict[str, Any]) -> bool:
        try:
            if self.on_log:
                self.on_log("Подключение к VPN...")

            try:
                local_port = int(config_data.get("local_port", 10808)) if config_data.get("local_port") else 10808
                port = int(config_data["port"]) if config_data.get("port") else 443
            except (ValueError, TypeError) as e:
                raise Exception(f"Неверный формат порта: {e}")

            if not config_data.get("address"):
                raise Exception("Не указан адрес сервера")
            if not config_data.get("uuid"):
                raise Exception("Не указан UUID")

            xray_config = create_vless_reality_xhttp(
                address=config_data["address"].strip(),
                port=port,
                uuid=config_data["uuid"].strip(),
                server_name=config_data.get("sni", "").strip() or config_data["address"].strip(),
                public_key=config_data.get("public_key", "").strip(),
                short_id=config_data.get("short_id", "").strip(),
                flow=config_data.get("flow", "").strip(),
                local_socks_port=local_port,
                local_http_port=local_port + 1,
                transport=config_data.get("transport", "xhttp").strip() if config_data.get("transport") else "xhttp",
                grpc_service_name=config_data.get("service_name", "grpc").strip() if config_data.get("service_name") else "grpc",
                grpc_multi_mode=config_data.get("mode", "").strip() == "multi"
            )

            if not save_config(xray_config, str(self.config_file)):
                raise Exception("Не удалось сохранить конфигурацию")

            self.current_config = config_data
            self.xray_manager = XrayManager(str(self.config_file))

            self.xray_manager.on_start = self._on_xray_start
            self.xray_manager.on_stop = self._on_xray_stop
            self.xray_manager.on_error = self._on_xray_error
            self.xray_manager.on_log = self._on_xray_log
            self.xray_manager.on_connection_lost = self._on_connection_lost

            if not self.xray_manager.start():
                raise Exception("Не удалось запустить Xray-core")

            time.sleep(2)
            if not self.xray_manager.is_running():
                raise Exception("Xray завершился сразу")

            if self.on_log:
                self.on_log("✅ Xray работает")

            # Проверка реального подключения через HTTP GET к 1.1.1.1:80
            if self.on_log:
                self.on_log("⏳ Проверка подключения к интернету...")

            socks_port = int(config_data.get("local_port", 10808))

            # Используем xray_manager.check_connection() вместо дублирования логики
            latency = self.xray_manager.check_connection(socks_port)
            if latency <= 0:
                error = "Сервер недоступен или нет связи с интернетом"
                if self.on_log:
                    self.on_log(f"❌ {error}")
                self.disconnect()
                raise Exception(error)

            if self.on_log:
                self.on_log("✅ Подключение к интернету успешно")
                self.on_log("✅ VPN подключение установлено")

            if self.use_system_proxy:
                # Преобразование порта в int
                try:
                    proxy_port = int(config_data.get("local_port", 10808))
                except (ValueError, TypeError):
                    proxy_port = 10808
                
                if self.on_log:
                    self.on_log(f"Включаю системный прокси (127.0.0.1:{proxy_port})...")
                result = self.system_proxy.enable("127.0.0.1", proxy_port)
                if self.on_log:
                    if result:
                        self.on_log(f"✅ Системный прокси ВКЛЮЧЁН (порт {proxy_port})")
                    else:
                        self.on_log(f"⚠ Системный прокси НЕ включён!")

            if self.on_log:
                self.on_log("✅ VPN подключение установлено")
            
            return True

        except Exception as e:
            if self.on_log:
                self.on_log(f"❌ Ошибка: {e}")
            # Отключаем только если Xray был запущен и работает
            # (не отключаем если ошибка была до запуска)
            if self.xray_manager is not None and self.xray_manager.is_running():
                self.disconnect()
            return False

    def disconnect(self) -> bool:
        """Отключение от VPN"""
        logger.info("disconnect() вызван")
        
        try:
            if self.on_log:
                self.on_log("Отключение от VPN...")

            if self.use_system_proxy and self.system_proxy.is_enabled:
                logger.info("Отключаем системный прокси")
                self.system_proxy.disable()

            if self.xray_manager:
                logger.info(f"Останавливаем Xray: {self.xray_manager}")
                self.xray_manager.stop()
                self.xray_manager = None
                logger.info("Xray остановлен, xray_manager = None")

            self.current_config = None
            logger.info("current_config очищен")

            if self.on_log:
                self.on_log("VPN отключено")
            
            logger.info("disconnect() завершён успешно")
            return True

        except Exception as e:
            logger.error(f"Ошибка в disconnect(): {e}", exc_info=True)
            if self.on_log:
                self.on_log(f"❌ Ошибка: {e}")
            return False

    def is_connected(self) -> bool:
        if not self.xray_manager:
            return False
        return self.xray_manager.is_running()

    def get_stats(self) -> Dict[str, Any]:
        if self.xray_manager:
            return self.xray_manager.get_stats()
        return {"running": False, "pid": None, "uptime": None}

    def get_connection_info(self) -> Dict[str, Any]:
        """
        Получение информации о подключении из Xray

        Returns:
            Dict с информацией:
            - 'active': bool - активно ли подключение
            - 'error': str - последняя ошибка
            - 'error_count': int - количество ошибок
            - 'connection_count': int - количество подключений
            - 'healthy': bool - здоровье подключения
        """
        if not self.xray_manager:
            return {
                'active': False,
                'error': None,
                'error_count': 0,
                'connection_count': 0,
                'healthy': False
            }

        info = self.xray_manager.get_connection_info()
        info['healthy'] = self.xray_manager.is_connection_healthy()
        return info

    def check_connection(self, socks_port: Optional[int] = None) -> float:
        """
        Проверка соединения через curl к 1.1.1.1:443

        Args:
            socks_port: Порт SOCKS прокси (по умолчанию из текущей конфигурации)

        Returns:
            latency в секундах или 0 при ошибке/таймауте
        """
        if not self.xray_manager:
            return 0
        if socks_port is None:
            socks_port = self.current_config.get("local_port", 10808) if self.current_config else 10808
        return self.xray_manager.check_connection(socks_port)

    def set_system_proxy(self, enabled: bool, port: Optional[int] = None) -> bool:
        self.use_system_proxy = enabled
        if port is None:
            port = self.current_config.get("local_port", 10808) if self.current_config else 10808
        if enabled and self.is_connected():
            self.system_proxy.enable("127.0.0.1", port)
        elif not enabled and self.system_proxy.is_enabled:
            self.system_proxy.disable()
        return True

    def set_autostart(self, enabled: bool) -> bool:
        return self.autostart.enable() if enabled else self.autostart.disable()

    def is_autostart_enabled(self) -> bool:
        return self.autostart.is_enabled()

    def save_config(self, config: Dict[str, Any]) -> bool:
        from vpn_client.utils.settings import SettingsManager
        return SettingsManager(str(self.config_dir)).save_last_config(config)

    def load_saved_config(self) -> Optional[Dict[str, Any]]:
        from vpn_client.utils.settings import SettingsManager
        return SettingsManager(str(self.config_dir)).get_last_config()

    def save_profile(self, name: str, config: Dict[str, Any]) -> bool:
        """Сохранение профиля подключения"""
        from vpn_client.utils.settings import SettingsManager
        return SettingsManager(str(self.config_dir)).save_profile(name, config)

    def load_profile(self, name: str) -> Optional[Dict[str, Any]]:
        """Загрузка профиля подключения"""
        from vpn_client.utils.settings import SettingsManager
        return SettingsManager(str(self.config_dir)).load_profile(name)

    def get_profile_names(self) -> list:
        """Получение списка имен профилей"""
        from vpn_client.utils.settings import SettingsManager
        return SettingsManager(str(self.config_dir)).get_profile_names()

    def delete_profile(self, name: str) -> bool:
        """Удаление профиля"""
        from vpn_client.utils.settings import SettingsManager
        return SettingsManager(str(self.config_dir)).delete_profile(name)

    def _on_xray_start(self):
        if self.on_log:
            self.on_log("Xray запущен")

    def _on_xray_stop(self):
        if self.on_log:
            self.on_log("Xray остановлен")

    def _on_xray_error(self, error: str):
        if self.on_log:
            self.on_log(f"❌ Xray ошибка: {error}")

    def _on_xray_log(self, message: str):
        if self.on_log:
            self.on_log(message)

    def _on_connection_lost(self):
        if self.on_log:
            self.on_log("❌ Потеряно соединение с VPN")

    # Методы обновления Xray-core
    
    def _start_update_check(self):
        """Запустить фоновую проверку обновлений"""
        def check():
            try:
                self.xray_updater = get_updater()
                self.xray_updater.on_update_available = self._on_update_found
                update_info = self.xray_updater.check_for_updates(force=False)
                if update_info and self.on_update_available:
                    # Вызываем callback в главном потоке если возможно
                    self.on_update_available(update_info)
            except Exception as e:
                logger.debug(f"Ошибка проверки обновлений: {e}")
        
        self._update_check_thread = threading.Thread(target=check, daemon=True)
        self._update_check_thread.start()
    
    def _on_update_found(self, update_info: Dict[str, Any]):
        """Вызывается когда найдено обновление"""
        logger.info(f"Доступно обновление Xray: {update_info.get('current_version')} → {update_info.get('latest_version')}")
    
    def check_for_updates(self, force: bool = False) -> Optional[Dict[str, Any]]:
        """
        Проверить наличие обновлений Xray-core
        
        Args:
            force: Принудительная проверка (игнорировать интервал)
        
        Returns:
            Информация об обновлении или None
        """
        if not self.xray_updater:
            self.xray_updater = get_updater()
            self.xray_updater.on_update_available = self._on_update_found
        
        return self.xray_updater.check_for_updates(force=force)
    
    def get_xray_version(self) -> Optional[str]:
        """Получить текущую версию Xray-core"""
        if not self.xray_updater:
            self.xray_updater = get_updater()
        return self.xray_updater.get_current_version() or self.xray_updater.get_binary_version()
    
    def download_update(self, update_info: Dict[str, Any],
                        progress_callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """
        Скачать и установить обновление Xray-core

        Args:
            update_info: Информация об обновлении
            progress_callback: Callback прогресса (downloaded, total)

        Returns:
            True если успешно
        """
        if not self.xray_updater:
            self.xray_updater = get_updater()
        return self.xray_updater.download_update(update_info, progress_callback)
