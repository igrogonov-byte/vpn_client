#!/usr/bin/env python3
"""
VPN Client - VLESS Reality xhttp
GUI на CustomTkinter + pystray (правильная работа в трее)
Поддерживаемые платформы: Windows x86_64, Linux x86_64
"""
import sys
import os
import threading
import signal

# Добавляем корень проекта в path
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, script_dir)

# Для Windows - скрываем консоль
if sys.platform == "win32":
    import ctypes
    try:
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except Exception:
        pass

def main():
    """Точка входа приложения"""
    # Проверка зависимостей
    try:
        import customtkinter as ctk
        import pystray
        from PIL import Image
    except ImportError as e:
        error_file = os.path.join(os.path.dirname(__file__), 'ERROR.txt')
        with open(error_file, 'w', encoding='utf-8') as f:
            f.write(f"Не установлены зависимости: {e}\nВыполните: pip install pystray Pillow\n")
        return 1

    # Импорт компонентов
    from vpn_client.controller import VPNController
    from vpn_client.gui.main_window_ctk import VPNMainWindow

    # Установка темы ДО создания окна
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    # Создание приложения
    app = ctk.CTk()
    app.title("VPN Client - VLESS Reality xhttp")
    app.geometry("840x683")
    app.minsize(630, 525)

    # Создание контроллера
    controller = VPNController()

    # Флаг состояния
    state = {'is_hidden': False}

    # Создание главного окна (передаём ссылку на state для уведомлений)
    window = VPNMainWindow(app, controller, auto_start_proxy=True, app_state=state)
    window.pack(fill="both", expand=True)

    def create_icon():
        """Создание иконки для трея"""
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "icons8-vpn-48.png")
        return Image.open(icon_path)

    def on_show(icon, item):
        """Показать окно"""
        app.after(0, lambda: [app.deiconify(), app.focus_force(), app.lift()])
        state['is_hidden'] = False
        icon.menu = create_menu()

    def on_hide(icon, item):
        """Скрыть окно"""
        app.after(0, lambda: app.withdraw())
        state['is_hidden'] = True
        icon.menu = create_menu()

    def on_toggle(icon, item):
        """Подключить/Отключить"""
        app.after(0, window.toggle_connection)

    def on_exit(icon, item):
        """Выход"""
        controller.disconnect()
        icon.stop()
        app.quit()

    def create_menu():
        """Создание меню с текущим состоянием"""
        return pystray.Menu(
            pystray.MenuItem("Показать", on_show, enabled=state['is_hidden']),
            pystray.MenuItem("Скрыть", on_hide, enabled=not state['is_hidden']),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Подключить/Отключить", on_toggle),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Выход", on_exit)
        )

    # Создание иконки
    icon = pystray.Icon("vpn_client", create_icon(), "VPN Client", create_menu())

    # Запуск иконки в ОТДЕЛЬНОМ daemon потоке
    def run_icon():
        try:
            icon.run()
        except Exception:
            pass
    
    icon_thread = threading.Thread(target=run_icon, daemon=True)
    icon_thread.start()
    
    # Небольшая задержка чтобы иконка успела создаться
    import time
    time.sleep(0.1)

    # Обработка закрытия окна - сворачивание в трей
    def on_close():
        app.withdraw()  # Скрыть окно
        state['is_hidden'] = True
        icon.menu = create_menu()  # Обновить меню
    
    app.protocol("WM_DELETE_WINDOW", on_close)

    # Обработка сигналов завершения
    def signal_handler(sig, frame):
        controller.disconnect()
        icon.stop()
        app.quit()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Запуск основного цикла tkinter
    try:
        app.mainloop()
    finally:
        # Остановка иконки при выходе
        icon.stop()


if __name__ == "__main__":
    sys.exit(main())
