#!/usr/bin/env python3
"""
Скрипт для запуска VPN клиента
Запускается в фоне, не занимает терминал
"""
import sys
import os
import subprocess
import time

# Для Windows - скрываем консоль
if sys.platform == "win32":
    import ctypes
    try:
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except Exception:
        pass

def main():
    """Запуск приложения в фоне"""
    # Получаем путь к скрипту
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(script_dir, 'vpn_client', 'main.py')
    
    # Запускаем как отдельный процесс в фоне
    if sys.platform == "win32":
        # Windows - запуск без окна консоли
        subprocess.Popen(
            [sys.executable, main_script],
            creationflags=subprocess.CREATE_NO_WINDOW,
            cwd=script_dir
        )
    else:
        # Linux/macOS - запуск в фоне с перенаправлением вывода
        with open(os.devnull, 'w') as null:
            subprocess.Popen(
                [sys.executable, main_script],
                stdout=null,
                stderr=null,
                stdin=null,
                start_new_session=True,
                cwd=script_dir
            )
    
    # Небольшая задержка чтобы процесс успел запуститься
    time.sleep(0.5)
    
    print("✅ VPN Client запущен в фоне")
    return 0


if __name__ == "__main__":
    sys.exit(main())
