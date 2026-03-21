"""
Модуль для показа системных уведомлений
"""
import logging
import subprocess
import sys
from typing import Optional

logger = logging.getLogger(__name__)


def show_notification(title: str, message: str, app_name: str = "VPN Client") -> bool:
    """
    Показать системное уведомление

    Args:
        title: Заголовок уведомления
        message: Текст уведомления
        app_name: Имя приложения

    Returns:
        True если уведомление показано, False если произошла ошибка
    """
    # Linux - используем notify-send
    if sys.platform == "linux":
        try:
            result = subprocess.run(
                ["notify-send", "-a", app_name, title, message],
                timeout=5,
                capture_output=True
            )
            if result.returncode == 0:
                logger.info(f"Показано уведомление (notify-send): {title} - {message}")
                return True
            else:
                logger.error(f"notify-send вернул код {result.returncode}: {result.stderr.decode()}")
                return False
        except FileNotFoundError:
            logger.error("notify-send не найден. Установите libnotify-bin")
            return False
        except subprocess.TimeoutExpired:
            logger.error("notify-send таймаут")
            return False
        except Exception as e:
            logger.error(f"Ошибка при показе уведомления (Linux): {e}")
            return False

    # Windows/macOS - используем plyer
    try:
        from plyer import notification

        notification.notify(
            title=title,
            message=message,
            app_name=app_name,
            app_icon=None,
            timeout=10,
            toast=False
        )
        logger.info(f"Показано уведомление (plyer): {title} - {message}")
        return True

    except ImportError:
        logger.error("plyer не установлен. Выполните: pip install plyer")
        return False

    except Exception as e:
        logger.error(f"Ошибка при показе уведомления: {e}")
        return False
