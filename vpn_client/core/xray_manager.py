"""
Менеджер Xray-core: запуск, остановка, управление процессом
Оптимизировано для работы с памятью
"""
import os
import sys
import subprocess
import threading
import logging
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger('vpn_client.xray_manager')


class XrayManager:
    """Управление Xray-core процессом
    __slots__ для экономии памяти
    """
    __slots__ = [
        'config_path', 'binary_path', 'process', '_lock',
        '_output_thread', '_stop_event',
        'on_start', 'on_stop', 'on_error', 'on_log'
    ]

    def __init__(self, config_path: str, binary_path: Optional[str] = None):
        self.config_path = Path(config_path)
        self.binary_path = binary_path or self._find_binary()
        self.process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._output_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Callbacks
        self.on_start: Optional[Callable] = None
        self.on_stop: Optional[Callable] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_log: Optional[Callable[[str], None]] = None

    def _find_binary(self) -> str:
        """Поиск бинарника Xray"""
        binaries_dir = Path(__file__).parent.parent / "binaries"
        if binaries_dir.exists():
            if sys.platform == "win32":
                binary = binaries_dir / "xray.exe"
            else:
                binary = binaries_dir / "xray"
            if binary.exists():
                return str(binary)

        import shutil
        xray_path = shutil.which("xray")
        if xray_path:
            return xray_path

        raise FileNotFoundError("Xray-core не найден")

    def _read_output(self):
        """Чтение вывода процесса в фоне - оптимизировано"""
        logger = logging.getLogger('vpn_client.xray_read')
        logger.info("_read_output запущен")
        
        if not self.process:
            logger.warning("process = None, выходим")
            return

        # Используем select для неблокирующего чтения на Linux/macOS
        use_select = sys.platform != "win32"
        if use_select:
            import select

        buffer = []
        max_buffer_size = 50  # Уменьшили буфер
        check_interval = 0.05  # 50ms между проверками
        read_count = 0
        
        while not self._stop_event.is_set():
            try:
                read_count += 1
                
                # Проверяем, жив ли процесс
                if self.process.poll() is not None:
                    logger.info(f"Процесс завершился (poll={self.process.poll()}), читаем остаток")
                    # Процесс завершился, читаем остаток
                    try:
                        remaining = self.process.stdout.read()
                        if remaining:
                            for line in remaining.decode('utf-8', errors='replace').splitlines():
                                if self.on_log:
                                    self.on_log(line)
                    except Exception as e:
                        logger.error(f"Ошибка чтения остатка: {e}")
                    break
                
                # Неблокирующее чтение на Linux/macOS
                if use_select:
                    import select
                    ready, _, _ = select.select([self.process.stdout], [], [], check_interval)
                    if not ready:
                        # Логируем каждые 1000 итераций
                        if read_count % 1000 == 0:
                            logger.debug(f"read_count={read_count}, nothing to read")
                        continue
                
                # Читаем одну строку
                line = self.process.stdout.readline()
                if not line:
                    logger.info("Получена пустая строка, выходим")
                    break
                
                decoded = line.decode('utf-8', errors='replace').strip()
                if decoded and self.on_log:
                    # Ограничиваем размер сообщения
                    if len(decoded) > 500:
                        decoded = decoded[:500] + "..."
                    self.on_log(decoded)
                    
                    # Добавляем в буфер
                    buffer.append(decoded)
                    
                    # Очищаем буфер периодически (не каждый цикл!)
                    if len(buffer) > max_buffer_size:
                        buffer.clear()
                        # gc.collect() вызываем редко - это дорогая операция
                    
            except Exception as e:
                logger.error(f"Исключение в цикле чтения: {e}", exc_info=True)
                break
        
        # Финальная очистка
        logger.info(f"_read_output завершён (прочитано {read_count} раз)")
        buffer.clear()

    def start(self) -> bool:
        """Запуск Xray-core"""
        logger.info("start() вызван")
        
        with self._lock:
            logger.debug("Получили lock")
            
            if self.process and self.process.poll() is None:
                logger.warning("Xray уже запущен")
                if self.on_log:
                    self.on_log("Xray уже запущен")
                return True

            if not self.config_path.exists():
                error = f"Конфиг не найден: {self.config_path}"
                logger.error(error)
                if self.on_error:
                    self.on_error(error)
                return False

            try:
                args = [self.binary_path, "run", "-c", str(self.config_path)]
                logger.info(f"Запускаем: {' '.join(args)}")

                self.process = subprocess.Popen(
                    args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )
                logger.info(f"Процесс запущен, PID={self.process.pid}")

                self._stop_event.clear()
                self._output_thread = threading.Thread(target=self._read_output, daemon=True)
                logger.info("Запускаем поток чтения...")
                self._output_thread.start()
                logger.info("Поток чтения запущен")

                if self.on_start:
                    self.on_start()

                if self.on_log:
                    self.on_log("Xray запущен")
                
                logger.info("start() завершён успешно")
                return True

            except Exception as e:
                error = f"Ошибка запуска: {e}"
                logger.error(error, exc_info=True)
                if self.on_error:
                    self.on_error(error)
                return False

    def stop(self, timeout: float = 5.0) -> bool:
        """Остановка Xray-core"""
        logger.info(f"stop() вызван, timeout={timeout}")
        
        with self._lock:
            logger.debug("Получили lock в stop()")
            
            if not self.process:
                logger.debug("process = None, возвращаем True")
                return True

            try:
                if self.on_log:
                    self.on_log("Остановка Xray...")

                # Сигнал остановки
                logger.info("Устанавливаем _stop_event")
                self._stop_event.set()

                # Ждём завершения потока
                if self._output_thread and self._output_thread.is_alive():
                    logger.info("Ждём завершения потока чтения...")
                    self._output_thread.join(timeout=2.0)
                    logger.info(f"Поток завершён, is_alive={self._output_thread.is_alive()}")

                # Принудительно читаем остаток
                try:
                    self.process.stdout.close()
                except Exception as e:
                    logger.warning(f"Не удалось закрыть stdout: {e}")

                # Останавливаем процесс
                logger.info(f"Останавливаем процесс (terminate)...")
                self.process.terminate()
                try:
                    logger.info(f"Ждём завершения процесса (timeout={timeout})...")
                    self.process.wait(timeout=timeout)
                    logger.info(f"Процесс завершён с кодом {self.process.returncode}")
                except subprocess.TimeoutExpired:
                    logger.warning("Таймаут, убиваем процесс")
                    self.process.kill()
                    self.process.wait()

                self.process = None
                logger.info("process = None")

                if self.on_stop:
                    self.on_stop()

                if self.on_log:
                    self.on_log("Xray остановлен")
                
                logger.info("stop() завершён успешно")
                return True

            except Exception as e:
                error = f"Ошибка остановки: {e}"
                logger.error(error, exc_info=True)
                if self.on_error:
                    self.on_error(error)
                return False

    def is_running(self) -> bool:
        """Проверка статуса"""
        if not self.process:
            return False
        return self.process.poll() is None

    def get_stats(self) -> dict:
        """Получение статистики"""
        return {
            "running": self.is_running(),
            "pid": self.process.pid if self.process else None,
            "uptime": None
        }
    
    def __del__(self):
        """Деструктор - гарантированная очистка"""
        try:
            if self.process and self.process.poll() is None:
                self.stop()
        except Exception:
            pass
