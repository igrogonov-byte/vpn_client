"""
Модуль автоматического обновления Xray-core
Проверяет последнюю версию на GitHub и загружает бинарник
"""
import os
import sys
import json
import hashlib
import logging
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta

try:
    import urllib.request
    import urllib.error
    HAS_URLLIB = True
except ImportError:
    HAS_URLLIB = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

logger = logging.getLogger('vpn_client.xray_updater')

# GitHub API для релизов Xray-core
GITHUB_API_URL = "https://api.github.com/repos/XTLS/Xray-core/releases/latest"
GITHUB_RELEASES_URL = "https://github.com/XTLS/Xray-core/releases"

# Пути
BINARIES_DIR = Path(__file__).parent.parent / "binaries"
VERSION_FILE = BINARIES_DIR / "xray.version"
BINARY_FILE = BINARIES_DIR / "xray"
BINARY_FILE_WIN = BINARIES_DIR / "xray.exe"

# Интервал проверки (7 дней)
CHECK_INTERVAL_DAYS = 7


class XrayUpdater:
    """Менеджер обновлений Xray-core"""
    
    __slots__ = [
        'binaries_dir', 'version_file', 'binary_file',
        'on_update_available', 'on_update_downloaded', 'on_update_error',
        '_last_check_file', '_http_session'
    ]
    
    def __init__(self, binaries_dir: Optional[Path] = None):
        self.binaries_dir = binaries_dir or BINARIES_DIR
        self.version_file = self.binaries_dir / "xray.version"
        self.binary_file = self._get_binary_path()
        self._last_check_file = self.binaries_dir / ".last_check"
        self._http_session = None
        
        # Callbacks
        self.on_update_available = None  # Вызывается когда есть обновление
        self.on_update_downloaded = None  # Вызывается после успешной загрузки
        self.on_update_error = None  # Вызывается при ошибке
    
    def _get_binary_path(self) -> Path:
        """Получить путь к бинарнику для текущей ОС"""
        if sys.platform == "win32":
            return self.binaries_dir / "xray.exe"
        return self.binaries_dir / "xray"
    
    def _http_get(self, url: str, timeout: int = 10) -> Optional[bytes]:
        """HTTP GET запрос с поддержкой requests или urllib"""
        try:
            if HAS_REQUESTS:
                import requests
                response = requests.get(url, timeout=timeout)
                response.raise_for_status()
                return response.content
            elif HAS_URLLIB:
                req = urllib.request.Request(url, headers={'User-Agent': 'VPNClient/1.0'})
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    return response.read()
            else:
                logger.error("Нет доступного HTTP клиента (requests или urllib)")
                return None
        except Exception as e:
            logger.error(f"HTTP ошибка при запросе {url}: {e}")
            return None
    
    def get_current_version(self) -> Optional[str]:
        """Получить текущую версию из файла версии"""
        if self.version_file.exists():
            try:
                return self.version_file.read_text().strip()
            except Exception as e:
                logger.error(f"Ошибка чтения файла версии: {e}")
        return None
    
    def get_binary_version(self) -> Optional[str]:
        """Получить версию установленного бинарника через команду version"""
        if not self.binary_file.exists():
            return None
        
        try:
            # Запускаем xray version
            result = subprocess.run(
                [str(self.binary_file), "version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Парсим вывод, например: "Xray 25.3.15 (Xray, Apache-2.0 license)"
                output = result.stdout.strip()
                if output:
                    # Извлекаем версию из первой строки
                    first_line = output.split('\n')[0]
                    parts = first_line.split()
                    if len(parts) >= 2:
                        return parts[1]  # "25.3.15"
        except Exception as e:
            logger.error(f"Ошибка получения версии бинарника: {e}")
        
        return None
    
    def _get_platform_asset(self) -> Optional[str]:
        """Получить название архива для текущей платформы"""
        platform_map = {
            ('linux', 'x86_64'): 'xray-linux-64.zip',
            ('linux', 'amd64'): 'xray-linux-64.zip',
            ('linux', 'aarch64'): 'xray-linux-arm64-v8a.zip',
            ('linux', 'arm64'): 'xray-linux-arm64-v8a.zip',
            ('darwin', 'x86_64'): 'xray-macos-64.zip',
            ('darwin', 'arm64'): 'xray-macos-arm64-v8a.zip',
            ('win32', 'x86_64'): 'xray-windows-64.zip',
            ('win32', 'AMD64'): 'xray-windows-64.zip',
            ('win32', 'arm64'): 'xray-windows-arm64-v8a.zip',
        }
        
        import platform
        system = platform.system().lower()
        machine = platform.machine()
        
        # Пробуем точное совпадение
        key = (system, machine)
        if key in platform_map:
            return platform_map[key]
        
        # Fallback для Linux
        if system == 'linux':
            return 'xray-linux-64.zip'
        elif system == 'darwin':
            return 'xray-macos-64.zip'
        elif system == 'windows':
            return 'xray-windows-64.zip'
        
        return None
    
    def check_for_updates(self, force: bool = False) -> Optional[Dict[str, Any]]:
        """
        Проверить наличие обновлений на GitHub
        
        Args:
            force: Принудительная проверка (игнорировать интервал)
        
        Returns:
            Dict с информацией об обновлении или None если обновлений нет
        """
        # Проверяем, не слишком ли давно проверяли
        if not force and not self._should_check():
            logger.debug("Пропуск проверки обновлений (слишком рано)")
            return None
        
        # Получаем последнюю версию с GitHub
        response_data = self._http_get(GITHUB_API_URL)
        if not response_data:
            logger.warning("Не удалось получить данные от GitHub API")
            self._save_last_check_time()
            return None
        
        try:
            release_info = json.loads(response_data)
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON от GitHub: {e}")
            self._save_last_check_time()
            return None
        
        latest_version = release_info.get('tag_name', '').lstrip('v')
        if not latest_version:
            logger.warning("Не удалось получить версию из GitHub API")
            self._save_last_check_time()
            return None
        
        # Получаем текущую версию
        current_version = self.get_current_version() or self.get_binary_version()
        
        logger.info(f"Текущая версия: {current_version}, последняя: {latest_version}")
        
        # Сравниваем версии
        if current_version and self._compare_versions(current_version, latest_version) >= 0:
            logger.info("Версия актуальна")
            self._save_last_check_time()
            return None
        
        # Есть обновление - собираем информацию
        asset_name = self._get_platform_asset()
        if not asset_name:
            logger.error("Не удалось определить архив для текущей платформы")
            self._save_last_check_time()
            return None
        
        # Ищем нужный asset в релизе
        download_url = None
        for asset in release_info.get('assets', []):
            if asset.get('name') == asset_name:
                download_url = asset.get('browser_download_url')
                break
        
        if not download_url:
            logger.warning(f"Asset {asset_name} не найден в релизе")
            self._save_last_check_time()
            return None
        
        update_info = {
            'current_version': current_version,
            'latest_version': latest_version,
            'asset_name': asset_name,
            'download_url': download_url,
            'release_url': release_info.get('html_url', GITHUB_RELEASES_URL),
            'release_notes': release_info.get('body', ''),
        }
        
        logger.info(f"Доступно обновление: {current_version} → {latest_version}")
        
        # Вызываем callback если есть
        if self.on_update_available:
            self.on_update_available(update_info)
        
        self._save_last_check_time()
        return update_info
    
    def _should_check(self) -> bool:
        """Проверить, пора ли проверять обновления"""
        if not self._last_check_file.exists():
            return True
        
        try:
            last_check_str = self._last_check_file.read_text().strip()
            last_check = datetime.fromisoformat(last_check_str)
            return datetime.now() - last_check >= timedelta(days=CHECK_INTERVAL_DAYS)
        except Exception as e:
            logger.error(f"Ошибка чтения времени последней проверки: {e}")
            return True
    
    def _save_last_check_time(self):
        """Сохранить время последней проверки"""
        try:
            self._last_check_file.write_text(datetime.now().isoformat())
        except Exception as e:
            logger.error(f"Ошибка сохранения времени проверки: {e}")
    
    def _compare_versions(self, v1: str, v2: str) -> int:
        """
        Сравнить две версии
        Returns: -1 если v1 < v2, 0 если равны, 1 если v1 > v2
        """
        def parse_version(v: str):
            parts = []
            for part in v.split('.'):
                try:
                    parts.append(int(part))
                except ValueError:
                    parts.append(0)
            return parts
        
        v1_parts = parse_version(v1)
        v2_parts = parse_version(v2)
        
        # Дополняем до одинаковой длины
        max_len = max(len(v1_parts), len(v2_parts))
        v1_parts.extend([0] * (max_len - len(v1_parts)))
        v2_parts.extend([0] * (max_len - len(v2_parts)))
        
        for p1, p2 in zip(v1_parts, v2_parts):
            if p1 < p2:
                return -1
            elif p1 > p2:
                return 1
        
        return 0
    
    def download_update(self, update_info: Dict[str, Any], 
                        progress_callback: Optional[callable] = None) -> bool:
        """
        Скачать обновление
        
        Args:
            update_info: Информация об обновлении из check_for_updates
            progress_callback: Callback для отображения прогресса (current, total)
        
        Returns:
            True если успешно
        """
        download_url = update_info.get('download_url')
        asset_name = update_info.get('asset_name')
        
        if not download_url or not asset_name:
            logger.error("Нет URL или имени файла для загрузки")
            if self.on_update_error:
                self.on_update_error("Нет URL для загрузки")
            return False
        
        logger.info(f"Загрузка {asset_name}...")
        
        try:
            # Создаем временный файл
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
                tmp_path = Path(tmp_file.name)
            
            # Загружаем файл
            if HAS_REQUESTS:
                import requests
                response = requests.get(download_url, stream=True, timeout=60)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                with open(tmp_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback and total_size:
                                progress_callback(downloaded, total_size)
            elif HAS_URLLIB:
                req = urllib.request.Request(download_url, headers={'User-Agent': 'VPNClient/1.0'})
                with urllib.request.urlopen(req, timeout=60) as response:
                    total_size = response.headers.get('Content-Length')
                    total_size = int(total_size) if total_size else 0
                    
                    downloaded = 0
                    with open(tmp_path, 'wb') as f:
                        while True:
                            chunk = response.read(8192)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback and total_size:
                                progress_callback(downloaded, total_size)
            else:
                logger.error("Нет доступного HTTP клиента")
                if self.on_update_error:
                    self.on_update_error("Нет HTTP клиента для загрузки")
                return False
            
            logger.info(f"Загрузка завершена: {tmp_path}")
            
            # Распаковываем архив
            if not self._extract_binary(tmp_path):
                return False
            
            # Сохраняем версию
            version = update_info.get('latest_version')
            if version:
                self.version_file.write_text(version)
                logger.info(f"Версия обновлена до {version}")
            
            if self.on_update_downloaded:
                self.on_update_downloaded(update_info)
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка загрузки: {e}", exc_info=True)
            if self.on_update_error:
                self.on_update_error(str(e))
            return False
        finally:
            # Удаляем временный файл
            if 'tmp_path' in locals() and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except:
                    pass
    
    def _extract_binary(self, archive_path: Path) -> bool:
        """Извлечь бинарник из архива"""
        import zipfile
        
        try:
            with zipfile.ZipFile(archive_path, 'r') as zf:
                # Находим бинарник в архиве
                binary_name = 'xray.exe' if sys.platform == 'win32' else 'xray'
                
                for member in zf.namelist():
                    if member.endswith(binary_name) and '/' not in member[:-len(binary_name)]:
                        # Извлекаем бинарник
                        with zf.open(member) as source:
                            # Создаем временный файл для нового бинарника
                            new_binary = self.binary_file.with_suffix('.new')
                            with open(new_binary, 'wb') as target:
                                shutil.copyfileobj(source, target)
                        
                        # Делаем исполняемым (Unix)
                        if sys.platform != 'win32':
                            os.chmod(new_binary, 0o755)
                        
                        # Заменяем старый бинарник новым
                        # Сначала переименовываем старый в .old
                        if self.binary_file.exists():
                            old_backup = self.binary_file.with_suffix('.old')
                            self.binary_file.rename(old_backup)
                        
                        # Переименовываем новый
                        new_binary.rename(self.binary_file)
                        
                        # Удаляем backup
                        if old_backup.exists():
                            old_backup.unlink()
                        
                        logger.info(f"Бинарник обновлен: {self.binary_file}")
                        return True
                
                logger.error(f"Бинарник {binary_name} не найден в архиве")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка распаковки: {e}", exc_info=True)
            return False
    
    def install_update(self, update_info: Dict[str, Any],
                       progress_callback: Optional[callable] = None) -> bool:
        """
        Скачать и установить обновление
        
        Args:
            update_info: Информация об обновлении
            progress_callback: Callback прогресса
        
        Returns:
            True если успешно
        """
        logger.info("Начало установки обновления...")
        return self.download_update(update_info, progress_callback)


# Глобальный экземпляр для удобства
_default_updater: Optional[XrayUpdater] = None


def get_updater() -> XrayUpdater:
    """Получить глобальный экземпляр XrayUpdater"""
    global _default_updater
    if _default_updater is None:
        _default_updater = XrayUpdater()
    return _default_updater


def check_updates(force: bool = False) -> Optional[Dict[str, Any]]:
    """Проверить обновления (удобная функция)"""
    return get_updater().check_for_updates(force)


def get_current_version() -> Optional[str]:
    """Получить текущую версию xray"""
    return get_updater().get_current_version() or get_updater().get_binary_version()
