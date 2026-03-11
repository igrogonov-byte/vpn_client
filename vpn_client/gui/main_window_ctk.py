"""
Основное окно GUI на CustomTkinter
Современный строгий дизайн с серо-голубой цветовой схемой
"""
import customtkinter as ctk
from tkinter import messagebox, filedialog, Menu
from datetime import datetime
import json


# Цветовая палитра
COLORS = {
    "bg_primary": "#1a1f2e",       # Основной фон (темно-серый)
    "bg_secondary": "#242b3d",     # Вторичный фон (панели)
    "bg_tertiary": "#2d3548",      # Третичный фон (поля ввода)
    "accent_blue": "#4a9eff",      # Акцент голубой
    "accent_blue_hover": "#3a8eef", # Акцент при наведении
    "success": "#2ecc71",          # Успех
    "success_bg": "#1e4632",       # Фон успеха
    "danger": "#e74c3c",           # Опасность
    "danger_bg": "#4a1f1f",        # Фон опасности
    "warning": "#f39c12",          # Предупреждение
    "text_primary": "#ecf0f1",     # Основной текст
    "text_secondary": "#95a5a6",   # Вторичный текст
    "border": "#3a4255",           # Границы
}


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
        
        # Настройка цветов темы
        self._configure_theme_colors()

        # Создание интерфейса
        self.create_ui()

        # Подключение callback'ов
        self.controller.on_log = self.on_log

        # Загрузка сохранённых настроек
        self.load_settings()

        # Автозапуск прокси если указано
        if self.auto_start_proxy:
            self.master.after(1000, self.auto_enable_proxy)

    def _configure_theme_colors(self):
        """Настройка цветовой темы"""
        ctk.set_default_color_theme("blue")
    
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
        # Настройка основного фона
        self.configure(fg_color=COLORS["bg_primary"])
        
        # Заголовок
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent", height=80)
        self.header_frame.pack(fill="x", padx=30, pady=(25, 15))
        self.header_frame.pack_propagate(False)

        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="🔒 VPN Client",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=COLORS["accent_blue"]
        )
        self.title_label.pack(side="left")

        self.status_indicator = ctk.CTkLabel(
            self.header_frame,
            text="●",
            font=ctk.CTkFont(size=20),
            text_color=COLORS["danger"]
        )
        self.status_indicator.pack(side="right")

        # Статус бар
        self.status_label = ctk.CTkLabel(
            self,
            text="⏸ Статус: Остановлен",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["bg_secondary"],
            text_color=COLORS["text_secondary"],
            corner_radius=8,
            height=45
        )
        self.status_label.pack(fill="x", padx=30, pady=(0, 15))

        # Вкладки
        self.tabview = ctk.CTkTabview(
            self,
            fg_color=COLORS["bg_secondary"],
            border_color=COLORS["border"],
            corner_radius=12,
            border_width=1
        )
        self.tabview.pack(fill="both", expand=True, padx=30, pady=10)
        
        # Настройка цвета текста вкладок
        self.tabview._segmented_button.configure(
            fg_color=COLORS["bg_secondary"],
            selected_color=COLORS["accent_blue"],
            selected_hover_color=COLORS["accent_blue_hover"]
        )

        self.tab_connect = self.tabview.add("Подключение")
        self.tab_settings = self.tabview.add("Настройки")
        self.tab_logs = self.tabview.add("Логи")
        
        # Настройка фона вкладок
        for tab in [self.tab_connect, self.tab_settings, self.tab_logs]:
            tab.configure(fg_color=COLORS["bg_secondary"])

        # Вкладка подключения
        self.create_connect_tab()

        # Вкладка настроек
        self.create_settings_tab()

        # Вкладка логов
        self.create_logs_tab()

        # Кнопки управления
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent", height=60)
        self.btn_frame.pack(fill="x", padx=30, pady=(15, 25))
        self.btn_frame.pack_propagate(False)

        self.btn_connect = ctk.CTkButton(
            self.btn_frame,
            text="▶ Подключить",
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=COLORS["success"],
            hover_color="#27ae60",
            corner_radius=10,
            height=50,
            command=self.toggle_connection
        )
        self.btn_connect.pack(side="left", fill="x", expand=True, padx=(0, 12))

        self.btn_exit = ctk.CTkButton(
            self.btn_frame,
            text="✕ Выход",
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=COLORS["danger"],
            hover_color="#c0392b",
            corner_radius=10,
            height=50,
            command=self.exit_app
        )
        self.btn_exit.pack(side="left", fill="x", expand=True, padx=(12, 0))

    def create_connect_tab(self):
        """Вкладка подключения"""
        # Форма с параметрами
        self.form_frame = ctk.CTkScrollableFrame(
            self.tab_connect,
            fg_color="transparent"
        )
        self.form_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Привязка прокрутки колесом мыши
        self.form_frame.bind('<Enter>', self._bind_to_mousewheel)
        self.form_frame.bind('<Leave>', self._unbind_from_mousewheel)

        # Общий стиль для меток
        label_font = ctk.CTkFont(size=13, weight="bold")
        entry_height = 42
        entry_width = 450
        
        # Адрес сервера
        ctk.CTkLabel(
            self.form_frame, text="Адрес сервера:", font=label_font,
            text_color=COLORS["text_primary"]
        ).grid(row=0, column=0, sticky="w", pady=(15, 8), padx=10)
        self.edit_address = ctk.CTkEntry(
            self.form_frame, placeholder_text="example.com", width=entry_width, height=entry_height,
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"]
        )
        self.edit_address.grid(row=0, column=1, pady=(15, 8), padx=10)
        self._add_context_menu(self.edit_address)

        # Порт
        ctk.CTkLabel(
            self.form_frame, text="Порт:", font=label_font,
            text_color=COLORS["text_primary"]
        ).grid(row=1, column=0, sticky="w", pady=8, padx=10)
        self.spin_port = ctk.CTkEntry(
            self.form_frame, placeholder_text="443", width=entry_width, height=entry_height,
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"]
        )
        self.spin_port.grid(row=1, column=1, pady=8, padx=10)
        self._add_context_menu(self.spin_port)

        # UUID
        ctk.CTkLabel(
            self.form_frame, text="UUID:", font=label_font,
            text_color=COLORS["text_primary"]
        ).grid(row=2, column=0, sticky="w", pady=8, padx=10)
        self.edit_uuid = ctk.CTkEntry(
            self.form_frame, placeholder_text="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            width=entry_width, height=entry_height,
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"]
        )
        self.edit_uuid.grid(row=2, column=1, pady=8, padx=10)
        self._add_context_menu(self.edit_uuid)

        # SNI
        ctk.CTkLabel(
            self.form_frame, text="SNI:", font=label_font,
            text_color=COLORS["text_primary"]
        ).grid(row=3, column=0, sticky="w", pady=8, padx=10)
        self.edit_sni = ctk.CTkEntry(
            self.form_frame, placeholder_text="example.com", width=entry_width, height=entry_height,
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"]
        )
        self.edit_sni.grid(row=3, column=1, pady=8, padx=10)
        self._add_context_menu(self.edit_sni)

        # Public Key
        ctk.CTkLabel(
            self.form_frame, text="Public Key:", font=label_font,
            text_color=COLORS["text_primary"]
        ).grid(row=4, column=0, sticky="w", pady=8, padx=10)
        self.edit_public_key = ctk.CTkEntry(
            self.form_frame, placeholder_text="Публичный ключ Reality",
            width=entry_width, height=entry_height,
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"]
        )
        self.edit_public_key.grid(row=4, column=1, pady=8, padx=10)
        self._add_context_menu(self.edit_public_key)

        # Short ID
        ctk.CTkLabel(
            self.form_frame, text="Short ID:", font=label_font,
            text_color=COLORS["text_primary"]
        ).grid(row=5, column=0, sticky="w", pady=8, padx=10)
        self.edit_short_id = ctk.CTkEntry(
            self.form_frame, placeholder_text="hex строка", width=entry_width, height=entry_height,
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"]
        )
        self.edit_short_id.grid(row=5, column=1, pady=8, padx=10)
        self._add_context_menu(self.edit_short_id)

        # Flow
        ctk.CTkLabel(
            self.form_frame, text="Flow:", font=label_font,
            text_color=COLORS["text_primary"]
        ).grid(row=6, column=0, sticky="w", pady=8, padx=10)
        self.combo_flow = ctk.CTkComboBox(
            self.form_frame, values=["", "xtls-rprx-vision"], width=entry_width, height=entry_height,
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            button_color=COLORS["accent_blue"], button_hover_color=COLORS["accent_blue_hover"]
        )
        self.combo_flow.grid(row=6, column=1, pady=8, padx=10)

        # Транспорт
        ctk.CTkLabel(
            self.form_frame, text="Транспорт:", font=label_font,
            text_color=COLORS["text_primary"]
        ).grid(row=7, column=0, sticky="w", pady=8, padx=10)
        self.combo_transport = ctk.CTkComboBox(
            self.form_frame, values=["xhttp", "grpc", "ws", "tcp"], width=entry_width, height=entry_height,
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            button_color=COLORS["accent_blue"], button_hover_color=COLORS["accent_blue_hover"]
        )
        self.combo_transport.grid(row=7, column=1, pady=8, padx=10)

        # Локальный порт (по умолчанию 10808)
        ctk.CTkLabel(
            self.form_frame, text="Local SOCKS:", font=label_font,
            text_color=COLORS["text_primary"]
        ).grid(row=8, column=0, sticky="w", pady=8, padx=10)
        self.spin_local_port = ctk.CTkEntry(
            self.form_frame, placeholder_text="10808", width=entry_width, height=entry_height,
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"]
        )
        self.spin_local_port.grid(row=8, column=1, pady=8, padx=10)
        self.spin_local_port.insert(0, "10808")
        self._add_context_menu(self.spin_local_port)

        # Кнопка импорта
        self.btn_import = ctk.CTkButton(
            self.form_frame,
            text="📥 Импортировать из VLESS ссылки",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["accent_blue"],
            hover_color=COLORS["accent_blue_hover"],
            corner_radius=10,
            height=44,
            command=self.import_from_link
        )
        self.btn_import.grid(row=9, column=1, pady=(25, 15), sticky="w")

    def _add_context_menu(self, widget):
        """Добавление кастомного контекстного меню (ПКМ) для поля ввода"""
        # Используем список для работы в замыканиях
        context_menu_ref = [None]
        close_menu_id_ref = [None]
        
        def close_menu():
            """Закрыть меню"""
            if context_menu_ref[0]:
                try:
                    context_menu_ref[0].destroy()
                except:
                    pass
                context_menu_ref[0] = None
            # Снимаем привязки с master
            if close_menu_id_ref[0]:
                try:
                    self.master.unbind("<Button-1>", close_menu_id_ref[0])
                    self.master.unbind("<Button-3>", close_menu_id_ref[0])
                except:
                    pass
                close_menu_id_ref[0] = None
        
        def show_menu(event):
            # Закрываем предыдущее меню если есть
            close_menu()
            
            # Создаем кастомное меню
            context_menu_ref[0] = ctk.CTkToplevel(self)
            context_menu_ref[0].overrideredirect(True)  # Без рамки
            context_menu_ref[0].attributes('-topmost', True)
            
            # Позиционируем меню
            menu_x = event.x_root
            menu_y = event.y_root
            
            # Фрейм меню
            menu_frame = ctk.CTkFrame(
                context_menu_ref[0],
                fg_color=COLORS["bg_tertiary"],
                corner_radius=10,
                border_width=1,
                border_color=COLORS["border"]
            )
            menu_frame.pack(fill="both", expand=True, padx=2, pady=2)
            
            # Опции меню
            menu_items = [
                ("📋 Копировать", lambda: widget.event_generate('<<Copy>>')),
                ("📥 Вставить", lambda: widget.event_generate('<<Paste>>')),
                ("✂️ Вырезать", lambda: widget.event_generate('<<Cut>>')),
                ("⎯" * 15, None),  # Разделитель
                ("✅ Выделить всё", lambda: widget.event_generate('<<SelectAll>>')),
            ]
            
            for i, (text, command) in enumerate(menu_items):
                if command is None:
                    # Разделитель
                    sep = ctk.CTkFrame(
                        menu_frame,
                        fg_color=COLORS["border"],
                        height=1
                    )
                    sep.grid(row=i, column=0, sticky="ew", pady=4)
                else:
                    btn = ctk.CTkButton(
                        menu_frame,
                        text=text,
                        font=ctk.CTkFont(size=13),
                        fg_color="transparent",
                        hover_color=COLORS["accent_blue"],
                        text_color=COLORS["text_primary"],
                        anchor="w",
                        height=32,
                        corner_radius=6,
                        width=150
                    )
                    btn.grid(row=i, column=0, sticky="ew", padx=2, pady=1)
                    # Закрываем меню после выбора
                    btn.configure(command=lambda c=command: (c(), close_menu()))
            
            # Позиционируем окно
            context_menu_ref[0].geometry(f"+{menu_x}+{menu_y}")
            
            # Привязка закрытия по клику вне меню
            def do_close(e=None):
                close_menu()
            
            close_menu_id_ref[0] = self.master.bind("<Button-1>", do_close, add='+')
            self.master.bind("<Button-3>", do_close, add='+')
            
            # Закрытие по Escape
            context_menu_ref[0].bind("<Escape>", lambda e: do_close())

        widget.bind('<Button-3>', show_menu)

    def _bind_to_mousewheel(self, event):
        """Привязка прокрутки колесом мыши к скроллируемому фрейму"""
        # Привязываем к самому фрейму - события всплывают
        self.form_frame.bind('<Button-4>', self._on_mousewheel_linux, add='+')
        self.form_frame.bind('<Button-5>', self._on_mousewheel_linux, add='+')

    def _unbind_from_mousewheel(self, event):
        """Отвязка прокрутки колесом мыши"""
        try:
            self.form_frame.unbind('<Button-4>')
            self.form_frame.unbind('<Button-5>')
        except Exception:
            pass

    def _on_mousewheel_linux(self, event):
        """Обработка прокрутки колесом мыши (Linux)"""
        # Button-4 = вверх, Button-5 = вниз
        direction = -1 if event.num == 4 else 1
        # Прокрутка через yview с аргументом scroll
        self.form_frame._parent_canvas.yview("scroll", direction, "units")

    def create_settings_tab(self):
        """Вкладка настроек"""
        self.settings_frame = ctk.CTkScrollableFrame(
            self.tab_settings,
            fg_color="transparent"
        )
        self.settings_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Системный прокси
        self.proxy_frame = ctk.CTkFrame(
            self.settings_frame,
            fg_color=COLORS["bg_tertiary"],
            border_color=COLORS["border"],
            corner_radius=12,
            border_width=1
        )
        self.proxy_frame.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(
            self.proxy_frame,
            text="🌐 Системный прокси",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text_primary"]
        ).pack(pady=(15, 10))

        self.chk_system_proxy = ctk.CTkSwitch(
            self.proxy_frame,
            text="Включить системный прокси",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_primary"],
            fg_color=COLORS["accent_blue"],
            border_color=COLORS["border"],
            command=self.toggle_system_proxy
        )
        self.chk_system_proxy.pack(pady=(0, 15))

    def create_logs_tab(self):
        """Вкладка логов"""
        self.logs_frame = ctk.CTkFrame(
            self.tab_logs,
            fg_color="transparent"
        )
        self.logs_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Текстовое поле для логов
        self.log_text = ctk.CTkTextbox(
            self.logs_frame,
            font=("Consolas", 12),
            fg_color=COLORS["bg_tertiary"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=10,
            border_width=1
        )
        self.log_text.pack(fill="both", expand=True, pady=(0, 15))

        # Кнопки управления логами
        self.btn_log_frame = ctk.CTkFrame(self.logs_frame, fg_color="transparent")
        self.btn_log_frame.pack(fill="x")

        self.btn_clear = ctk.CTkButton(
            self.btn_log_frame,
            text="🗑 Очистить",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=10,
            width=130,
            height=40,
            command=self.clear_logs
        )
        self.btn_clear.pack(side="left", padx=(0, 12))

        self.btn_export = ctk.CTkButton(
            self.btn_log_frame,
            text="💾 Экспорт",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["accent_blue"],
            hover_color=COLORS["accent_blue_hover"],
            corner_radius=10,
            width=130,
            height=40,
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
                fg_color=COLORS["success_bg"],
                text_color=COLORS["success"]
            )
            self.status_indicator.configure(text_color=COLORS["success"])
            self.btn_connect.configure(
                text="⏹ Отключить",
                fg_color=COLORS["danger"],
                hover_color="#c0392b"
            )
        else:
            self.status_label.configure(
                text="⏸ Статус: Остановлен",
                fg_color=COLORS["bg_secondary"],
                text_color=COLORS["text_secondary"]
            )
            self.status_indicator.configure(text_color=COLORS["danger"])
            self.btn_connect.configure(
                text="▶ Подключить",
                fg_color=COLORS["success"],
                hover_color="#27ae60"
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
