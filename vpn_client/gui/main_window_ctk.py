"""
Основное окно GUI на CustomTkinter
Современный дизайн без проблем с видеодрайверами
"""
import customtkinter as ctk
from tkinter import messagebox, filedialog, Menu
from datetime import datetime
import json


class VPNMainWindow(ctk.CTkFrame):
    """Основное окно VPN клиента"""

    def __init__(self, master, controller, auto_start_proxy=False):
        super().__init__(master)
        self.master = master
        self.controller = controller
        self.is_connected = False
        self.auto_start_proxy = auto_start_proxy

        # Настройка стиля
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Создание интерфейса
        self.create_ui()

        # Подключение callback'ов
        self.controller.on_log = self.on_log

        # Загрузка сохранённых настроек
        self.load_settings()
        
        # Автозапуск прокси если указано
        if self.auto_start_proxy:
            self.master.after(1000, self.auto_enable_proxy)
    
    def auto_enable_proxy(self):
        """Автоматическое включение системного прокси"""
        try:
            self.chk_system_proxy.select()  # Включить переключатель
            self.controller.set_system_proxy(True)  # Включить прокси
            self.append_log("✅ Системный прокси включён автоматически")
        except Exception as e:
            self.append_log(f"⚠ Не удалось включить прокси: {e}")

    def create_ui(self):
        """Создание интерфейса"""
        # Заголовок
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=20, pady=(20, 10))

        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="🔒 VPN Client",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#4299e1"
        )
        self.title_label.pack(side="left")

        self.status_indicator = ctk.CTkLabel(
            self.header_frame,
            text="●",
            font=ctk.CTkFont(size=24),
            text_color="#f56565"
        )
        self.status_indicator.pack(side="right")

        # Статус бар
        self.status_label = ctk.CTkLabel(
            self,
            text="⏸ Статус: Остановлен",
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#2d3548",
            corner_radius=10,
            pady=14
        )
        self.status_label.pack(fill="x", padx=20, pady=10)

        # Вкладки
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=10)

        self.tab_connect = self.tabview.add("Подключение")
        self.tab_settings = self.tabview.add("Настройки")
        self.tab_logs = self.tabview.add("Логи")

        # Вкладка подключения
        self.create_connect_tab()

        # Вкладка настроек
        self.create_settings_tab()

        # Вкладка логов
        self.create_logs_tab()

        # Кнопки управления
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(fill="x", padx=20, pady=(0, 20))

        self.btn_connect = ctk.CTkButton(
            self.btn_frame,
            text="▶ Подключить",
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#48bb78",
            hover_color="#68d391",
            height=50,
            command=self.toggle_connection
        )
        self.btn_connect.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_exit = ctk.CTkButton(
            self.btn_frame,
            text="✕ Выход",
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#f56565",
            hover_color="#fc8181",
            height=50,
            command=self.exit_app
        )
        self.btn_exit.pack(side="left", fill="x", expand=True, padx=(10, 0))

    def create_connect_tab(self):
        """Вкладка подключения"""
        # Форма с параметрами
        self.form_frame = ctk.CTkScrollableFrame(self.tab_connect, fg_color="transparent")
        self.form_frame.pack(fill="both", expand=True)

        # Адрес сервера
        ctk.CTkLabel(self.form_frame, text="Адрес:").grid(row=0, column=0, sticky="w", pady=8, padx=5)
        self.edit_address = ctk.CTkEntry(self.form_frame, placeholder_text="example.com", width=400, height=40)
        self.edit_address.grid(row=0, column=1, pady=8, padx=5)
        self._add_context_menu(self.edit_address)

        # Порт
        ctk.CTkLabel(self.form_frame, text="Порт:").grid(row=1, column=0, sticky="w", pady=8, padx=5)
        self.spin_port = ctk.CTkEntry(self.form_frame, placeholder_text="443", width=400, height=40)
        self.spin_port.grid(row=1, column=1, pady=8, padx=5)
        self._add_context_menu(self.spin_port)

        # UUID
        ctk.CTkLabel(self.form_frame, text="UUID:").grid(row=2, column=0, sticky="w", pady=8, padx=5)
        self.edit_uuid = ctk.CTkEntry(self.form_frame, placeholder_text="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx", width=400, height=40)
        self.edit_uuid.grid(row=2, column=1, pady=8, padx=5)
        self._add_context_menu(self.edit_uuid)

        # SNI
        ctk.CTkLabel(self.form_frame, text="SNI:").grid(row=3, column=0, sticky="w", pady=8, padx=5)
        self.edit_sni = ctk.CTkEntry(self.form_frame, placeholder_text="example.com", width=400, height=40)
        self.edit_sni.grid(row=3, column=1, pady=8, padx=5)
        self._add_context_menu(self.edit_sni)

        # Public Key
        ctk.CTkLabel(self.form_frame, text="Public Key:").grid(row=4, column=0, sticky="w", pady=8, padx=5)
        self.edit_public_key = ctk.CTkEntry(self.form_frame, placeholder_text="Публичный ключ Reality", width=400, height=40)
        self.edit_public_key.grid(row=4, column=1, pady=8, padx=5)
        self._add_context_menu(self.edit_public_key)

        # Short ID
        ctk.CTkLabel(self.form_frame, text="Short ID:").grid(row=5, column=0, sticky="w", pady=8, padx=5)
        self.edit_short_id = ctk.CTkEntry(self.form_frame, placeholder_text="hex строка", width=400, height=40)
        self.edit_short_id.grid(row=5, column=1, pady=8, padx=5)
        self._add_context_menu(self.edit_short_id)

        # Flow
        ctk.CTkLabel(self.form_frame, text="Flow:").grid(row=6, column=0, sticky="w", pady=8, padx=5)
        self.combo_flow = ctk.CTkComboBox(self.form_frame, values=["", "xtls-rprx-vision"], width=400, height=40)
        self.combo_flow.grid(row=6, column=1, pady=8, padx=5)

        # Транспорт
        ctk.CTkLabel(self.form_frame, text="Транспорт:").grid(row=7, column=0, sticky="w", pady=8, padx=5)
        self.combo_transport = ctk.CTkComboBox(self.form_frame, values=["xhttp", "grpc", "ws", "tcp"], width=400, height=40)
        self.combo_transport.grid(row=7, column=1, pady=8, padx=5)

        # Локальный порт (по умолчанию 10808)
        ctk.CTkLabel(self.form_frame, text="Local SOCKS:").grid(row=8, column=0, sticky="w", pady=8, padx=5)
        self.spin_local_port = ctk.CTkEntry(self.form_frame, placeholder_text="10808", width=400, height=40)
        self.spin_local_port.grid(row=8, column=1, pady=8, padx=5)
        self.spin_local_port.insert(0, "10808")  # Порт по умолчанию
        self._add_context_menu(self.spin_local_port)

        # Кнопка импорта
        self.btn_import = ctk.CTkButton(
            self.form_frame,
            text="📥 Импортировать из VLESS ссылки",
            height=40,
            command=self.import_from_link
        )
        self.btn_import.grid(row=9, column=1, pady=20, sticky="w")

    def _add_context_menu(self, widget):
        """Добавление контекстного меню (ПКМ) для поля ввода"""
        menu = Menu(widget, tearoff=0)
        menu.add_command(label="Копировать", command=lambda: widget.event_generate('<<Copy>>'))
        menu.add_command(label="Вставить", command=lambda: widget.event_generate('<<Paste>>'))
        menu.add_command(label="Вырезать", command=lambda: widget.event_generate('<<Cut>>'))
        menu.add_separator()
        menu.add_command(label="Выделить всё", command=lambda: widget.event_generate('<<SelectAll>>'))
        
        def show_menu(event):
            menu.tk_popup(event.x_root, event.y_root)
        
        widget.bind('<Button-3>', show_menu)

    def create_settings_tab(self):
        """Вкладка настроек"""
        self.settings_frame = ctk.CTkScrollableFrame(self.tab_settings, fg_color="transparent")
        self.settings_frame.pack(fill="both", expand=True)

        # Системный прокси
        self.proxy_frame = ctk.CTkFrame(self.settings_frame, corner_radius=10)
        self.proxy_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            self.proxy_frame,
            text="🌐 Системный прокси",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)

        self.chk_system_proxy = ctk.CTkSwitch(
            self.proxy_frame,
            text="Включить системный прокси",
            font=ctk.CTkFont(size=14),
            command=self.toggle_system_proxy
        )
        self.chk_system_proxy.pack(pady=10)

        # Автозапуск
        self.autostart_frame = ctk.CTkFrame(self.settings_frame, corner_radius=10)
        self.autostart_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            self.autostart_frame,
            text="🚀 Автозапуск",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)

        self.chk_autostart = ctk.CTkSwitch(
            self.autostart_frame,
            text="Добавить в автозапуск",
            font=ctk.CTkFont(size=14),
            command=self.toggle_autostart
        )
        self.chk_autostart.pack(pady=10)

    def create_logs_tab(self):
        """Вкладка логов"""
        self.logs_frame = ctk.CTkFrame(self.tab_logs, fg_color="transparent")
        self.logs_frame.pack(fill="both", expand=True)

        # Текстовое поле для логов
        self.log_text = ctk.CTkTextbox(self.logs_frame, font=("Consolas", 12))
        self.log_text.pack(fill="both", expand=True, pady=10)

        # Кнопки управления логами
        self.btn_log_frame = ctk.CTkFrame(self.logs_frame, fg_color="transparent")
        self.btn_log_frame.pack(fill="x", pady=10)

        self.btn_clear = ctk.CTkButton(
            self.btn_log_frame,
            text="🗑 Очистить",
            width=120,
            command=self.clear_logs
        )
        self.btn_clear.pack(side="left", padx=(0, 10))

        self.btn_export = ctk.CTkButton(
            self.btn_log_frame,
            text="💾 Экспорт",
            width=120,
            command=self.export_logs
        )
        self.btn_export.pack(side="left")

    def toggle_connection(self):
        """Переключение подключения"""
        if self.is_connected:
            self.disconnect()
        else:
            self.connect()

    def connect(self):
        """Подключение"""
        # Сбор данных из формы
        config_data = {
            "address": self.edit_address.get(),
            "port": self.spin_port.get(),
            "uuid": self.edit_uuid.get(),
            "sni": self.edit_sni.get(),
            "public_key": self.edit_public_key.get(),
            "short_id": self.edit_short_id.get(),
            "flow": self.combo_flow.get(),
            "transport": self.combo_transport.get(),
            "local_port": self.spin_local_port.get(),
        }

        # Блокировка кнопки
        self.btn_connect.configure(state="disabled", text="⏳ Подключение...")

        try:
            result = self.controller.connect(config_data)
            if result:
                self.update_ui_connected(True)
                self.append_log("✅ Подключение успешно")
                self.save_settings()
            else:
                raise Exception("Не удалось подключиться")
        except Exception as e:
            messagebox.showerror("Ошибка подключения", str(e))
            self.append_log(f"❌ Ошибка: {e}")
        finally:
            self.btn_connect.configure(state="normal")

    def disconnect(self):
        """Отключение"""
        self.controller.disconnect()
        self.update_ui_connected(False)
        self.append_log("Отключено")

    def update_ui_connected(self, connected: bool):
        """Обновление UI при подключении"""
        self.is_connected = connected

        if connected:
            self.status_label.configure(
                text="✅ Статус: Подключено",
                fg_color="#276749",
                text_color="#c6f6d5"
            )
            self.status_indicator.configure(text_color="#48bb78")
            self.btn_connect.configure(
                text="⏹ Отключить",
                fg_color="#f56565",
                hover_color="#fc8181"
            )
        else:
            self.status_label.configure(
                text="⏸ Статус: Остановлен",
                fg_color="#2d3548",
                text_color="#a0aec0"
            )
            self.status_indicator.configure(text_color="#f56565")
            self.btn_connect.configure(
                text="▶ Подключить",
                fg_color="#48bb78",
                hover_color="#68d391"
            )

    def import_from_link(self):
        """Импорт из VLESS ссылки"""
        dialog = ctk.CTkInputDialog(
            title="Импорт",
            text="Вставьте VLESS ссылку:"
        )
        link = dialog.get_input()

        if link:
            try:
                from vpn_client.core.vless_config import parse_vless_link
                params = parse_vless_link(link)
                if params:
                    self.edit_address.delete(0, 'end')
                    self.edit_address.insert(0, params.get("address", ""))
                    self.spin_port.delete(0, 'end')
                    self.spin_port.insert(0, str(params.get("port", "443")))
                    self.edit_uuid.delete(0, 'end')
                    self.edit_uuid.insert(0, params.get("uuid", ""))
                    self.edit_sni.delete(0, 'end')
                    self.edit_sni.insert(0, params.get("sni", ""))
                    self.edit_public_key.delete(0, 'end')
                    self.edit_public_key.insert(0, params.get("pbk", ""))
                    self.edit_short_id.delete(0, 'end')
                    self.edit_short_id.insert(0, params.get("sid", ""))
                    self.combo_flow.set(params.get("flow", ""))
                    self.combo_transport.set(params.get("type", "xhttp"))
                    self.append_log("✅ Конфигурация импортирована из ссылки")
                    self.save_settings()
                else:
                    messagebox.showwarning("Ошибка", "Неверный формат ссылки")
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

    def toggle_system_proxy(self):
        """Переключение системного прокси"""
        enabled = self.chk_system_proxy.get() == 1
        self.controller.set_system_proxy(enabled)
        self.append_log(f"Системный прокси {'включен' if enabled else 'отключен'}")

    def toggle_autostart(self):
        """Переключение автозапуска"""
        enabled = self.chk_autostart.get() == 1
        self.controller.set_autostart(enabled)
        self.append_log(f"Автозапуск {'включен' if enabled else 'отключен'}")

    def append_log(self, message: str):
        """Добавление сообщения в лог"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")

    def clear_logs(self):
        """Очистка логов"""
        self.log_text.delete("1.0", "end")

    def export_logs(self):
        """Экспорт логов"""
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Текстовые файлы", "*.txt")]
        )
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.get("1.0", "end"))
                messagebox.showinfo("Успех", f"Логи сохранены в {path}")
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

    def on_log(self, message: str):
        """Обработка лога от Xray"""
        self.append_log(f"Xray: {message}")

    def save_settings(self):
        """Сохранение настроек"""
        config = {
            "address": self.edit_address.get(),
            "port": self.spin_port.get(),
            "uuid": self.edit_uuid.get(),
            "sni": self.edit_sni.get(),
            "public_key": self.edit_public_key.get(),
            "short_id": self.edit_short_id.get(),
            "flow": self.combo_flow.get(),
            "transport": self.combo_transport.get(),
            "local_port": self.spin_local_port.get(),
        }
        self.controller.save_config(config)

    def load_settings(self):
        """Загрузка сохранённых настроек"""
        saved = self.controller.load_saved_config()
        if saved:
            self.edit_address.delete(0, 'end')
            self.edit_address.insert(0, saved.get("address", ""))
            self.spin_port.delete(0, 'end')
            self.spin_port.insert(0, str(saved.get("port", "443")))
            self.edit_uuid.delete(0, 'end')
            self.edit_uuid.insert(0, saved.get("uuid", ""))
            self.edit_sni.delete(0, 'end')
            self.edit_sni.insert(0, saved.get("sni", ""))
            self.edit_public_key.delete(0, 'end')
            self.edit_public_key.insert(0, saved.get("public_key", ""))
            self.edit_short_id.delete(0, 'end')
            self.edit_short_id.insert(0, saved.get("short_id", ""))
            self.combo_flow.set(saved.get("flow", ""))
            self.combo_transport.set(saved.get("transport", "xhttp"))
            self.spin_local_port.delete(0, 'end')
            self.spin_local_port.insert(0, str(saved.get("local_port", "10808")))
            self.append_log("✅ Настройки загружены")

    def exit_app(self):
        """Выход из приложения с отключением прокси"""
        if self.is_connected:
            if messagebox.askyesno("Выход", "VPN подключен. Отключиться и выйти?"):
                self.controller.disconnect()
                self.master.quit()
        else:
            self.master.quit()
