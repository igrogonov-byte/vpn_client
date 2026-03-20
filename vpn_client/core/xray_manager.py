"""
Менеджер Xray-core: запуск, остановка, управление процессом
Оптимизированная версия с queue, poll, batch-обработкой и контекстным менеджером
"""
import os
import sys
import subprocess
import threading
import logging
import select
import time
from pathlib import Path
from queue import Queue, Empty
from typing import Optional, Callable, List

logger = logging.getLogger('vpn_client.xray_manager')

# Кэш пути к бинарнику на уровне модуля
_binary_cache: Optional[str] = None


class XrayManager:
    """Управление Xray-core процессом
    
    Оптимизации:
    - __slots__ для экономии памяти
    - queue.Queue для потокобезопасной передачи логов
    - select.poll вместо select на Linux
    - batch-обработка логов
    - rate limiting для защиты от flood
    - контекстный менеджер для автоматической очистки
    """
    __slots__ = [
        'config_path', 'binary_path', 'process', '_lock',
        '_output_thread', '_stop_event', '_log_queue', '_log_worker',
        'on_start', 'on_stop', 'on_error', 'on_log',
        '_last_log_time', '_log_rate_limit', '_pending_logs',
        '_connection_count', '_error_count', '_last_error', '_connection_active',
        '_monitor_thread', '_monitor_stop_event', '_consecutive_failures', '_socks_port',
        'on_connection_lost'
    ]

    # Константы
    LOG_RATE_LIMIT = 0.05  # Мин. интервал между логами (50ms ~ 20 логов/сек)
    LOG_BATCH_SIZE = 5     # Размер пачки для batch-отправки
    LOG_QUEUE_TIMEOUT = 0.1  # Таймаут ожидания логов из очереди
    MONITOR_INTERVAL = 10  # Интервал мониторинга (секунды)
    MONITOR_TIMEOUT = 5  # Таймаут одной проверки (секунды)
    MAX_CONSECUTIVE_FAILURES = 3  # Провалов подряд для детектирования потери

    # Паттерны ошибок подключения Xray
    CONNECTION_ERROR_PATTERNS = [
        "failed to dial",
        "context deadline exceeded",
        "connection refused",
        "no route to host",
        "connection timed out",
        "i/o timeout",
        "eof",
        "reset by peer",
        "temporary failure in name resolution",
        "server misbehaving",
        "unable to dial",
        "dial tcp",
        "xray: connection failed",
        "read: connection reset",
        "write: broken pipe",
        "proxy: failed to connect",
        "remote error: tls",
        "invalid argument",
        "connection aborted",
        "flow read error",
        "socks: connection closed",
    ]

    # Паттерны успешного подключения
    CONNECTION_SUCCESS_PATTERNS = [
        "accepted",  # Xray принял соединение
        "started",   # Сервис запущен
        "listening", # Ожидание подключений
    ]

    def __init__(
        self,
        config_path: str,
        binary_path: Optional[str] = None,
        log_rate_limit: float = LOG_RATE_LIMIT
    ):
        self.config_path = Path(config_path)
        self.binary_path = binary_path or self._find_binary_cached()
        self.process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._output_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Очередь для потокобезопасной передачи логов
        self._log_queue: Queue = Queue(maxsize=1000)
        self._log_worker: Optional[threading.Thread] = None
        
        # Rate limiting для логов
        self._last_log_time: float = 0
        self._log_rate_limit: float = log_rate_limit
        self._pending_logs: List[str] = []

        # Мониторинг соединения
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitor_stop_event = threading.Event()
        self._consecutive_failures: int = 0
        self._socks_port: int = 10808

        # Callbacks
        self.on_start: Optional[Callable[[], None]] = None
        self.on_stop: Optional[Callable[[], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_log: Optional[Callable[[str], None]] = None
        self.on_connection_lost: Optional[Callable[[], None]] = None

        # Статистика подключений
        self._connection_count: int = 0
        self._error_count: int = 0
        self._last_error: Optional[str] = None
        self._connection_active: bool = False

    @classmethod
    def _find_binary_cached(cls) -> str:
        """Поиск бинарника Xray с кэшированием"""
        global _binary_cache
        if _binary_cache:
            return _binary_cache

        binaries_dir = Path(__file__).parent.parent / "binaries"
        if binaries_dir.exists():
            if sys.platform == "win32":
                binary = binaries_dir / "xray.exe"
            else:
                binary = binaries_dir / "xray"
            if binary.exists():
                _binary_cache = str(binary)
                return _binary_cache

        import shutil
        xray_path = shutil.which("xray")
        if xray_path:
            _binary_cache = xray_path
            return _binary_cache

        raise FileNotFoundError("Xray-core не найден")

    def _find_binary(self) -> str:
        """Поиск бинарника Xray (без кэша, для совместимости)"""
        return self._find_binary_cached()

    def _get_process_safe(self) -> Optional[subprocess.Popen]:
        """Безопасное получение процесса с блокировкой"""
        with self._lock:
            return self.process

    def _start_log_worker(self):
        """Запуск воркера для обработки логов из очереди"""
        self._log_worker = threading.Thread(target=self._process_log_queue, daemon=True)
        self._log_worker.start()

    def _process_log_queue(self):
        """Обработка очереди логов - вывод в реальном времени (без batch)"""
        log = logging.getLogger('vpn_client.xray_log_worker')

        while not self._stop_event.is_set():
            try:
                # Ждём лог из очереди
                try:
                    message = self._log_queue.get(timeout=self.LOG_QUEUE_TIMEOUT)
                except Empty:
                    continue

                # Логирование для отладки
                log.info(f"Получено из очереди: {message[:100]}...")

                # Отправляем лог сразу (без batch)
                if self.on_log:
                    log.info(f"Вызываем on_log callback")
                    self._flush_batch([message])
                else:
                    log.warning("on_log callback не установлен!")

            except Exception as e:
                log.error(f"Ошибка в log worker: {e}", exc_info=True)
                break

    def _flush_batch(self, batch: List[str]):
        """Отправка пачки логов с rate limiting"""
        current_time = time.monotonic()

        # Открываем файл для логирования (временно для отладки)
        # Путь в папке проекта
        try:
            import os
            log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'log_x.txt')
            log_file = open(log_path, 'a', encoding='utf-8')
        except Exception:
            log_file = None

        for message in batch:
            # Rate limiting (ВРЕМЕННО ОТКЛЮЧЕН для полного вывода)
            # elapsed = current_time - self._last_log_time
            # if elapsed < self._log_rate_limit:
            #     time.sleep(self._log_rate_limit - elapsed)
            #     current_time = time.monotonic()

            # Парсим лог для статистики подключений
            self._parse_log_for_stats(message)

            # Вызываем callback (отправка в GUI)
            self.on_log(message)
            # self._last_log_time = current_time

            # Пишем в файл лог
            if log_file:
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                log_file.write(f"[{timestamp}] {message}\n")
                log_file.flush()

        if log_file:
            log_file.close()

    def _parse_log_for_stats(self, message: str):
        """
        Парсинг лога для обновления статистики подключений

        Args:
            message: Сообщение лога для парсинга
        """
        message_lower = message.lower()

        # Проверка на успешное подключение
        for pattern in self.CONNECTION_SUCCESS_PATTERNS:
            if pattern in message_lower:
                # Xray принял соединение
                if "accepted" in message_lower and "socks" in message_lower:
                    self._connection_count += 1
                    self._connection_active = True
                    self._last_error = None  # Сбрасываем ошибку при успешном подключении
                break

        # Проверка на ошибку подключения
        for pattern in self.CONNECTION_ERROR_PATTERNS:
            if pattern in message_lower:
                self._error_count += 1
                self._last_error = f"Ошибка Xray: {message.strip()}"
                self._connection_active = False
                logger.warning(f"Обнаружена ошибка подключения: {message.strip()}")
                break

    # ========== Мониторинг соединения ==========

    def start_monitoring(self, socks_port: int = 10808):
        """Запуск мониторинга соединения"""
        self._socks_port = socks_port
        self._monitor_stop_event.clear()
        self._consecutive_failures = 0
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info(f"Мониторинг соединения запущен (порт {socks_port})")

    def stop_monitoring(self):
        """Остановка мониторинга соединения"""
        self._monitor_stop_event.set()
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2)
        logger.info("Мониторинг соединения остановлен")

    def _monitor_loop(self):
        """Фоновый мониторинг соединения"""
        logger.info("Мониторинг: цикл запущен")

        while not self._monitor_stop_event.is_set():
            # Ждём интервал
            if self._monitor_stop_event.wait(timeout=self.MONITOR_INTERVAL):
                break

            # Измеряем latency
            latency = self._measure_latency()

            if latency > 0:
                self._consecutive_failures = 0
                logger.debug(f"Мониторинг: соединение активно (latency={latency:.0f}мс)")
            else:
                self._consecutive_failures += 1
                logger.warning(f"Мониторинг: провал #{self._consecutive_failures}")

                # 3 провала подряд = потеря соединения
                if self._consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
                    self._connection_active = False
                    self._last_error = f"Потеря соединения ({self._consecutive_failures} провала подряд)"

                    # Уведомляем GUI
                    if self.on_connection_lost:
                        try:
                            self.on_connection_lost()
                        except Exception as e:
                            logger.error(f"Ошибка callback on_connection_lost: {e}")

                    logger.warning("Мониторинг: потеря соединения с VPN")
                    break  # Выход из цикла мониторинга

    def _measure_latency(self) -> float:
        """
        Измерение latency через curl к 1.1.1.1:443

        Returns:
            latency в секундах или 0 при ошибке/таймауте
        """
        try:
            result = subprocess.run(
                ['curl', '-x', f'socks5h://127.0.0.1:{self._socks_port}',
                 '-w', '%{time_appconnect}', '-o', '/dev/null',
                 '-s', '--connect-timeout', '3',
                 'https://1.1.1.1/cdn-cgi/trace'],
                capture_output=True, text=True, timeout=self.MONITOR_TIMEOUT
            )
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
            return 0
        except subprocess.TimeoutExpired:
            # Таймаут 5 секунд
            return 0
        except Exception:
            return 0

    # ============================================

    def _read_output(self):
        """Чтение вывода процесса в фоне с отправкой в очередь"""
        log = logging.getLogger('vpn_client.xray_read')
        log.info("_read_output запущен")

        # Получаем процесс один раз в начале
        process = self._get_process_safe()
        if not process or process.stdout is None:
            log.warning("process или stdout = None, выходим")
            return

        # Используем poll для эффективного ожидания на Linux/macOS
        use_poll = sys.platform != "win32"
        poller = None
        if use_poll:
            poller = select.poll()
            poller.register(process.stdout, select.POLLIN)

        check_interval = 50  # 50ms для poll

        while not self._stop_event.is_set():
            try:
                # Проверяем, жив ли процесс
                exit_code = process.poll()
                if exit_code is not None:
                    log.info(f"Процесс завершился (код={exit_code}), читаем остаток")
                    try:
                        remaining = process.stdout.read()
                        if remaining:
                            for line in remaining.decode('utf-8', errors='replace').splitlines():
                                self._log_queue.put(line)
                    except Exception as e:
                        log.error(f"Ошибка чтения остатка: {e}")
                    break

                # Ожидание данных через poll (Linux/macOS)
                if use_poll and poller:
                    try:
                        events = poller.poll(check_interval)
                    except (ValueError, OSError):
                        # stdout закрыт
                        break
                    if not events:
                        continue

                # Читаем доступные данные
                try:
                    line = process.stdout.readline()
                except (BrokenPipeError, OSError) as e:
                    log.warning(f"Ошибка чтения stdout: {e}")
                    break

                if not line:
                    log.info("Получена пустая строка, выходим")
                    break

                decoded = line.decode('utf-8', errors='replace').strip()
                if decoded:
                    # Логирование для отладки - пишем в системный лог
                    log.info(f"Прочитано из stdout: {decoded[:200]}")
                    
                    # Также пишем сразу в файл для отладки
                    try:
                        import os
                        debug_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'debug_stdout.txt')
                        with open(debug_path, 'a') as f:
                            from datetime import datetime
                            f.write(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] STDOUT: {decoded}\n")
                    except Exception:
                        pass
                    
                    # Ограничиваем размер сообщения (ВРЕМЕННО ОТКЛЮЧЕНО для полного вывода)
                    # if len(decoded) > 500:
                    #     decoded = decoded[:500] + "..."
                    # Отправляем в очередь
                    try:
                        self._log_queue.put_nowait(decoded)
                        log.info(f"Отправлено в очередь: {len(decoded)} байт")
                    except Exception as e:
                        # Очередь переполнена, пропускаем лог
                        log.warning(f"Очередь переполнена: {e}")

            except Exception as e:
                log.error(f"Исключение в цикле чтения: {e}", exc_info=True)
                break

        log.info("_read_output завершён")

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
                
                # Запускаем воркер логов
                self._start_log_worker()
                
                # Запускаем поток чтения вывода
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

            process = self.process

            try:
                if self.on_log:
                    self.on_log("Остановка Xray...")

                # Сигнал остановки всем потокам
                logger.info("Устанавливаем _stop_event")
                self._stop_event.set()

                # Ждём завершения потока чтения
                if self._output_thread and self._output_thread.is_alive():
                    logger.info("Ждём завершения потока чтения...")
                    self._output_thread.join(timeout=2.0)
                    logger.info(f"Поток чтения завершён, is_alive={self._output_thread.is_alive()}")

                # Ждём завершения log worker
                if self._log_worker and self._log_worker.is_alive():
                    logger.info("Ждём завершения log worker...")
                    self._log_worker.join(timeout=1.0)
                    logger.info(f"Log worker завершён, is_alive={self._log_worker.is_alive()}")

                # Останавливаем мониторинг соединения
                self.stop_monitoring()

                # Закрываем stdout если открыт
                try:
                    if process.stdout:
                        process.stdout.close()
                except Exception as e:
                    logger.warning(f"Не удалось закрыть stdout: {e}")

                # Останавливаем процесс
                logger.info(f"Останавливаем процесс (terminate)...")
                try:
                    process.terminate()
                except OSError:
                    # Процесс уже завершён
                    pass

                try:
                    logger.info(f"Ждём завершения процесса (timeout={timeout})...")
                    process.wait(timeout=timeout)
                    logger.info(f"Процесс завершён с кодом {process.returncode}")
                except subprocess.TimeoutExpired:
                    logger.warning("Таймаут, убиваем процесс")
                    try:
                        process.kill()
                        process.wait()
                    except OSError:
                        pass

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
        process = self._get_process_safe()
        if not process:
            return False
        return process.poll() is None

    def get_stats(self) -> dict:
        """Получение статистики"""
        process = self._get_process_safe()
        return {
            "running": self.is_running(),
            "pid": process.pid if process else None,
            "uptime": None,
            "connection_count": self._connection_count,
            "error_count": self._error_count,
            "last_error": self._last_error,
            "connection_active": self._connection_active
        }

    def get_connection_info(self) -> dict:
        """
        Получение информации о подключении из логов Xray

        Returns:
            Dict с информацией о подключении:
            - 'active': bool - активно ли подключение
            - 'error': str - последняя ошибка или None
            - 'error_count': int - количество ошибок
            - 'connection_count': int - количество подключений
        """
        return {
            "active": self._connection_active,
            "error": self._last_error,
            "error_count": self._error_count,
            "connection_count": self._connection_count
        }

    def is_connection_healthy(self) -> bool:
        """
        Проверка здоровья подключения

        Returns:
            True если подключение активно и нет ошибок
        """
        return self._connection_active and self._last_error is None

    # Контекстный менеджер
    def __enter__(self):
        """Вход в контекстный менеджер"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Выход из контекстного менеджера - автоматическая остановка"""
        self.stop()
        return False  # Не подавляем исключения

    def __del__(self):
        """Деструктор - гарантированная очистка"""
        try:
            if hasattr(self, 'process') and self.process and self.process.poll() is None:
                self.stop()
        except Exception:
            pass
