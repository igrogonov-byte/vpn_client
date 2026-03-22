"""
Основное окно GUI на CustomTkinter
Современный строгий дизайн с серо-голубой цветовой схемой
"""
import customtkinter as ctk
from datetime import datetime
import threading
import subprocess

from .styles import COLORS
from .dialogs import MessageDialog, YesNoDialog, InputDialog


class VPNMainWindow(ctk.CTkFrame):
    """Основное окно VPN клиента"""

    def __init__(self, master, controller, auto_start_proxy=False, app_state=None):
        super().__init__(master)
        self.master = master
        self.controller = controller
        self.is_connected = False
        self.auto_start_proxy = auto_start_proxy
        self.app_state = app_state or {'is_hidden': False}
        
        # Блокировка для потокобезопасного доступа к общим переменным
        self._lock = threading.Lock()
        self._connection_failures = 0
        self._max_failures = 3

        # Настройка стиля
        ctk.set_appearance_mode("dark")

        # Создание интерфейса
        self.create_ui()

        # Подключение callback'ов
        self.controller.on_log = self.on_log
        self.controller.on_update_available = self.on_update_available_auto
        self.controller.on_connection_lost = self.on_connection_lost

        # Автозапуск прокси если указано
        if self.auto_start_proxy:
            self.master.after(1000, self.auto_enable_proxy)

        # Загрузка версии Xray
        self.master.after(500, self.load_xray_version)
    
    def on_update_available_auto(self, update_info):
        """Автоматическое уведомление о доступном обновлении (фоновая проверка)"""
        def notify():
            current = update_info.get('current_version', '?')
            latest = update_info.get('latest_version', '?')
            self.version_label.configure(
                text=f"Версия: {current} → Доступна {latest}",
                text_color=COLORS["danger"]
            )
            self.btn_install_update.configure(state="normal")
            self._pending_update = update_info
            self.append_log(f"🔄 Доступно обновление Xray: {current} → {latest}")
        # Выполняем в главном потоке
        self.master.after(0, notify)

    def on_connection_lost(self):
        """Обработчик потери соединения (вызывается из мониторинга)"""
        def handle():
            # 1. Запись в лог
            self.append_log("❌ Потеряно соединение с VPN")

            # 2. Проверяем состояние окна
            is_hidden = self.app_state.get('is_hidden', False)
            self.append_log(f"[DEBUG] Окно скрыто в трей: {is_hidden}")

            # 3. Если окно скрыто в трей - показываем системное уведомление
            if is_hidden:
                from vpn_client.utils.notify import show_notification
                self.append_log("[DEBUG] Вызываем show_notification...")
                result = show_notification(
                    title="VPN упал",
                    message="Соединение с VPN потеряно. Требуется реконнект.",
                    app_name="VPN Client"
                )
                self.append_log(f"[DEBUG] Результат уведомления: {result}")
            else:
                # 4. Если окно видно - показываем диалог
                self.show_warning_dialog("Внимание", "Соединение с VPN потеряно. Требуется реконнект")

            # 5. Выполняем отключение
            self.disconnect()

        # Выполняем в главном потоке
        self.master.after(0, handle)

    def load_xray_version(self):
        """Загрузка информации о текущей версии Xray"""
        try:
            version = self.controller.get_xray_version()
            if version:
                self.version_label.configure(text=f"Версия: {version}")
            else:
                self.version_label.configure(text="Версия: не определена")
        except Exception as e:
            self.version_label.configure(text="Версия: неизвестно")

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
        self.status_frame = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_secondary"],
            corner_radius=8,
            height=45
        )
        self.status_frame.pack(fill="x", padx=30, pady=(0, 15))
        self.status_frame.pack_propagate(False)

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="⏸ Статус: Остановлен",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="transparent",
            text_color=COLORS["text_secondary"]
        )
        self.status_label.pack(side="left", padx=15, pady=0)

        self.session_timer_label = ctk.CTkLabel(
            self.status_frame,
            text="",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="transparent",
            text_color=COLORS["accent_blue"]
        )
        self.session_timer_label.pack(side="right", padx=(5, 15), pady=0)

        self.latency_label = ctk.CTkLabel(
            self.status_frame,
            text="",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="transparent",
            text_color=COLORS["text_secondary"]
        )
        self.latency_label.pack(side="right", padx=(5, 15), pady=0)

        self.session_timer_id = None
        self.latency_timer_id = None
        self.local_port = 10808  # Порт прокси для измерения latency

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

        # Инициализация видимости Service Name
        self._on_transport_change()

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
            command=self.on_btn_connect_click
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
            command=self.on_btn_exit_click
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

        # Настройка grid для form_frame
        self.form_frame.grid_columnconfigure(0, weight=0)  # Label колонка
        self.form_frame.grid_columnconfigure(1, weight=0)  # Поля ввода

        # Привязка прокрутки колесом мыши
        self.form_frame.bind('<Enter>', self._bind_to_mousewheel)
        self.form_frame.bind('<Leave>', self._unbind_from_mousewheel)

        # Секция управления профилями
        self.profile_frame = ctk.CTkFrame(
            self.form_frame,
            fg_color=COLORS["bg_tertiary"],
            corner_radius=10,
            border_width=1,
            border_color=COLORS["border"]
        )
        self.profile_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 15))
        self.profile_frame.grid_columnconfigure(0, weight=1)

        # Выбор профиля
        ctk.CTkLabel(
            self.profile_frame, text="📁 Профиль:", font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_primary"]
        ).grid(row=0, column=0, sticky="w", pady=10, padx=10)

        self.combo_profiles = ctk.CTkComboBox(
            self.profile_frame,
            values=[],
            width=300,
            height=36,
            fg_color=COLORS["bg_tertiary"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            button_color=COLORS["accent_blue"],
            button_hover_color=COLORS["accent_blue_hover"],
            command=self.on_profile_selected
        )
        self.combo_profiles.grid(row=0, column=1, sticky="w", pady=10, padx=10)

        # Кнопки управления профилями
        self.btn_save_profile = ctk.CTkButton(
            self.profile_frame,
            text="💾 Сохранить",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["success"],
            hover_color="#27ae60",
            corner_radius=8,
            height=36,
            width=110,
            command=self.save_profile_dialog
        )
        self.btn_save_profile.grid(row=0, column=2, sticky="w", pady=10, padx=10)

        self.btn_delete_profile = ctk.CTkButton(
            self.profile_frame,
            text="🗑 Удалить",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["danger"],
            hover_color="#c0392b",
            corner_radius=8,
            height=36,
            width=100,
            command=self.delete_profile_dialog
        )
        self.btn_delete_profile.grid(row=0, column=3, sticky="w", pady=10, padx=10)

        # Загрузка списка профилей
        self.refresh_profiles()

        # Кнопка импорта (под профилем)
        # Выровнена по левому краю profile_frame (padx=10)
        self.btn_import_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        self.btn_import_frame.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 15), padx=10)

        self.btn_import = ctk.CTkButton(
            self.btn_import_frame,
            text="📥 Импортировать из VLESS",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent_blue"],
            hover_color=COLORS["accent_blue_hover"],
            corner_radius=10,
            width=200,
            height=35,
            command=self.import_from_link
        )
        self.btn_import.pack(side="left", padx=(0, 15))

        # Метка текущего профиля
        ctk.CTkLabel(
            self.btn_import_frame,
            text="Текущий профиль:",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"]
        ).pack(side="left")

        self.current_profile_label = ctk.CTkLabel(
            self.btn_import_frame,
            text="—",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        self.current_profile_label.pack(side="left", padx=(5, 10))

        # Общий стиль для меток
        label_font = ctk.CTkFont(size=13, weight="bold")
        entry_height = 42
        entry_width = 450

        # Адрес сервера
        ctk.CTkLabel(
            self.form_frame, text="Адрес сервера:", font=label_font,
            text_color=COLORS["text_primary"]
        ).grid(row=2, column=0, sticky="w", pady=(15, 8), padx=10)
        self.edit_address = ctk.CTkEntry(
            self.form_frame, placeholder_text="example.com", width=entry_width, height=entry_height,
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"]
        )
        self.edit_address.grid(row=2, column=1, pady=(15, 8), padx=10)
        self._add_context_menu(self.edit_address)

        # Порт
        ctk.CTkLabel(
            self.form_frame, text="Порт:", font=label_font,
            text_color=COLORS["text_primary"]
        ).grid(row=3, column=0, sticky="w", pady=8, padx=10)
        self.spin_port = ctk.CTkEntry(
            self.form_frame, placeholder_text="443", width=entry_width, height=entry_height,
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"]
        )
        self.spin_port.grid(row=3, column=1, pady=8, padx=10)
        self._add_context_menu(self.spin_port)

        # UUID
        ctk.CTkLabel(
            self.form_frame, text="UUID:", font=label_font,
            text_color=COLORS["text_primary"]
        ).grid(row=4, column=0, sticky="w", pady=8, padx=10)
        self.edit_uuid = ctk.CTkEntry(
            self.form_frame, placeholder_text="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            width=entry_width, height=entry_height,
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"]
        )
        self.edit_uuid.grid(row=4, column=1, pady=8, padx=10)
        self._add_context_menu(self.edit_uuid)

        # SNI
        ctk.CTkLabel(
            self.form_frame, text="SNI:", font=label_font,
            text_color=COLORS["text_primary"]
        ).grid(row=5, column=0, sticky="w", pady=8, padx=10)
        self.edit_sni = ctk.CTkEntry(
            self.form_frame, placeholder_text="example.com", width=entry_width, height=entry_height,
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"]
        )
        self.edit_sni.grid(row=5, column=1, pady=8, padx=10)
        self._add_context_menu(self.edit_sni)

        # Public Key
        ctk.CTkLabel(
            self.form_frame, text="Public Key:", font=label_font,
            text_color=COLORS["text_primary"]
        ).grid(row=6, column=0, sticky="w", pady=8, padx=10)
        self.edit_public_key = ctk.CTkEntry(
            self.form_frame, placeholder_text="Публичный ключ Reality",
            width=entry_width, height=entry_height,
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"]
        )
        self.edit_public_key.grid(row=6, column=1, pady=8, padx=10)
        self._add_context_menu(self.edit_public_key)

        # Short ID
        ctk.CTkLabel(
            self.form_frame, text="Short ID:", font=label_font,
            text_color=COLORS["text_primary"]
        ).grid(row=7, column=0, sticky="w", pady=8, padx=10)
        self.edit_short_id = ctk.CTkEntry(
            self.form_frame, placeholder_text="hex строка", width=entry_width, height=entry_height,
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"]
        )
        self.edit_short_id.grid(row=7, column=1, pady=8, padx=10)
        self._add_context_menu(self.edit_short_id)

        # Flow
        ctk.CTkLabel(
            self.form_frame, text="Flow:", font=label_font,
            text_color=COLORS["text_primary"]
        ).grid(row=8, column=0, sticky="w", pady=8, padx=10)
        self.combo_flow = ctk.CTkComboBox(
            self.form_frame, values=["", "xtls-rprx-vision"], width=entry_width, height=entry_height,
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            button_color=COLORS["accent_blue"], button_hover_color=COLORS["accent_blue_hover"]
        )
        self.combo_flow.grid(row=8, column=1, pady=8, padx=10)

        # Транспорт
        ctk.CTkLabel(
            self.form_frame, text="Транспорт:", font=label_font,
            text_color=COLORS["text_primary"]
        ).grid(row=9, column=0, sticky="w", pady=8, padx=10)
        self.combo_transport = ctk.CTkComboBox(
            self.form_frame, values=["xhttp", "grpc", "tcp"], width=entry_width, height=entry_height,
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            button_color=COLORS["accent_blue"], button_hover_color=COLORS["accent_blue_hover"],
            command=self._on_transport_change
        )
        self.combo_transport.grid(row=9, column=1, pady=8, padx=10)

        # Service Name (только для GRPC)
        ctk.CTkLabel(
            self.form_frame, text="Service Name:", font=label_font,
            text_color=COLORS["text_primary"]
        ).grid(row=10, column=0, sticky="w", pady=8, padx=10)
        self.edit_service_name = ctk.CTkEntry(
            self.form_frame, placeholder_text="grpc", width=entry_width, height=entry_height,
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"]
        )
        self.edit_service_name.grid(row=10, column=1, pady=8, padx=10)
        self.edit_service_name.insert(0, "grpc")
        self._add_context_menu(self.edit_service_name)

        # Локальный порт (по умолчанию 10808)
        ctk.CTkLabel(
            self.form_frame, text="Local SOCKS:", font=label_font,
            text_color=COLORS["text_primary"]
        ).grid(row=11, column=0, sticky="w", pady=8, padx=10)
        self.spin_local_port = ctk.CTkEntry(
            self.form_frame, placeholder_text="10808", width=entry_width, height=entry_height,
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"]
        )
        self.spin_local_port.grid(row=11, column=1, pady=8, padx=10)
        self.spin_local_port.insert(0, "10808")
        self._add_context_menu(self.spin_local_port)

    def _on_transport_change(self, transport=None):
        """Обработка смены транспорта - показ/скрытие Service Name"""
        if self.combo_transport.get() == "grpc":
            self.edit_service_name.grid()
        else:
            self.edit_service_name.grid_remove()

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
        self.form_frame.unbind('<Button-4>')
        self.form_frame.unbind('<Button-5>')

    def _on_mousewheel_linux(self, event):
        """Обработка прокрутки колесом мыши (Linux)"""
        # Button-4 = вверх, Button-5 = вниз
        direction = -1 if event.num == 4 else 1
        # Прокрутка через yview с аргументом scroll
        self.form_frame._parent_canvas.yview("scroll", direction, "units")

    def _get_form_config(self):
        """Получение данных из формы"""
        return {
            "address": self.edit_address.get(),
            "port": self.spin_port.get(),
            "uuid": self.edit_uuid.get(),
            "sni": self.edit_sni.get(),
            "public_key": self.edit_public_key.get(),
            "short_id": self.edit_short_id.get(),
            "flow": self.combo_flow.get(),
            "transport": self.combo_transport.get(),
            "local_port": self.spin_local_port.get(),
            "mode": getattr(self, '_imported_mode', 'gun'),
            "service_name": self.edit_service_name.get(),
        }

    def _fill_form_from_config(self, config):
        """Заполнение формы данными из конфигурации"""
        self.edit_address.delete(0, 'end')
        self.edit_address.insert(0, config.get("address", ""))
        self.spin_port.delete(0, 'end')
        self.spin_port.insert(0, str(config.get("port", "443")))
        self.edit_uuid.delete(0, 'end')
        self.edit_uuid.insert(0, config.get("uuid", ""))
        self.edit_sni.delete(0, 'end')
        self.edit_sni.insert(0, config.get("sni", ""))
        self.edit_public_key.delete(0, 'end')
        self.edit_public_key.insert(0, config.get("public_key", ""))
        self.edit_short_id.delete(0, 'end')
        self.edit_short_id.insert(0, config.get("short_id", ""))
        self.combo_flow.set(config.get("flow", ""))
        self.combo_transport.set(config.get("transport", "xhttp"))
        self.edit_service_name.delete(0, 'end')
        self.edit_service_name.insert(0, config.get("service_name", "grpc"))
        self.spin_local_port.delete(0, 'end')
        self.spin_local_port.insert(0, str(config.get("local_port", "10808")))
        # Обновить видимость Service Name
        self._on_transport_change()

    def refresh_profiles(self):
        """Обновление списка профилей в ComboBox"""
        profile_names = self.controller.get_profile_names()
        self.combo_profiles.configure(values=profile_names)
        # При инициализации показываем "..."
        self.combo_profiles.set("...")
        # Сбрасываем метку текущего профиля
        if hasattr(self, 'current_profile_label'):
            self.current_profile_label.configure(text="—")

    def on_profile_selected(self, profile_name):
        """Обработка выбора профиля"""
        if profile_name == "Новый профиль..." or not profile_name:
            return

        profile = self.controller.load_profile(profile_name)
        if profile:
            self._fill_form_from_config(profile)
            self.append_log(f"✅ Профиль '{profile_name}' загружен")
            # Обновляем метку текущего профиля
            if hasattr(self, 'current_profile_label'):
                self.current_profile_label.configure(text=profile_name)

    def save_profile_dialog(self):
        """Диалог сохранения профиля"""
        profile_name = self._create_text_input_dialog(
            title="Сохранение профиля",
            text="Введите имя профиля:",
            placeholder="Мой профиль"
        )

        if profile_name:
            profile_name = profile_name.strip()
            if not profile_name:
                self.show_error_dialog("Ошибка", "Имя профиля не может быть пустым")
                return

            # Получаем текущие настройки из полей
            config = self._get_form_config()

            # Сохраняем профиль
            if self.controller.save_profile(profile_name, config):
                self.append_log(f"✅ Профиль '{profile_name}' сохранен")
                self.refresh_profiles()
                self.combo_profiles.set(profile_name)
                # Обновляем метку текущего профиля
                if hasattr(self, 'current_profile_label'):
                    self.current_profile_label.configure(text=profile_name)
            else:
                self.show_error_dialog("Ошибка", "Не удалось сохранить профиль")

    def delete_profile_dialog(self):
        """Диалог удаления профиля"""
        profile_name = self.combo_profiles.get()

        if not profile_name or profile_name == "...":
            self.show_info_dialog("Информация", "Выберите профиль для удаления")
            return

        if self.show_yesno_dialog("Удаление профиля", f"Удалить профиль '{profile_name}'?"):
            if self.controller.delete_profile(profile_name):
                self.append_log(f"🗑 Профиль '{profile_name}' удален")
                self.refresh_profiles()
                # Сбрасываем метку текущего профиля
                if hasattr(self, 'current_profile_label'):
                    self.current_profile_label.configure(text="—")
            else:
                self.show_error_dialog("Ошибка", "Не удалось удалить профиль")

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

        # Обновление Xray-core
        self.update_frame = ctk.CTkFrame(
            self.settings_frame,
            fg_color=COLORS["bg_tertiary"],
            border_color=COLORS["border"],
            corner_radius=12,
            border_width=1
        )
        self.update_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            self.update_frame,
            text="🔄 Обновление Xray-core",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_primary"]
        ).pack(pady=(8, 4))

        # Информация о версии
        self.version_info_frame = ctk.CTkFrame(self.update_frame, fg_color="transparent")
        self.version_info_frame.pack(fill="x", padx=20, pady=(0, 4))

        self.version_label = ctk.CTkLabel(
            self.version_info_frame,
            text="Версия: загрузка...",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_secondary"]
        )
        self.version_label.pack(side="left")

        # Кнопки
        self.btn_update_frame = ctk.CTkFrame(self.update_frame, fg_color="transparent")
        self.btn_update_frame.pack(fill="x", padx=20, pady=(0, 8))

        self.btn_check_update = ctk.CTkButton(
            self.btn_update_frame,
            text="📥 Проверить обновления",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=COLORS["accent_blue"],
            hover_color=COLORS["accent_blue_hover"],
            corner_radius=8,
            width=150,
            height=28,
            command=self.check_for_updates
        )
        self.btn_check_update.pack(side="left", padx=(0, 10))

        self.btn_install_update = ctk.CTkButton(
            self.btn_update_frame,
            text="⬇️ Установить",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=COLORS["success"],
            hover_color="#27ae60",
            corner_radius=8,
            width=120,
            height=28,
            command=self.install_update,
            state="disabled"
        )
        self.btn_install_update.pack(side="left")

        # Прогресс бар
        self.update_progress = ctk.CTkProgressBar(
            self.update_frame,
            mode="determinate",
            fg_color=COLORS["bg_secondary"],
            progress_color=COLORS["accent_blue"]
        )
        self.update_progress.pack(fill="x", padx=20, pady=(0, 6))
        self.update_progress.set(0)

        self.update_status_label = ctk.CTkLabel(
            self.update_frame,
            text="",
            font=ctk.CTkFont(size=9),
            text_color=COLORS["text_secondary"]
        )
        self.update_status_label.pack(pady=(0, 4))

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
            font=("Consolas", 11),
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
        self.btn_clear.pack(side="left")

    def on_btn_connect_click(self):
        """Обработчик клика на кнопку Подключить/Отключить"""
        self.toggle_connection()

    def on_btn_exit_click(self):
        """Обработчик клика на кнопку Выход"""
        self.exit_app()

    def toggle_connection(self):
        """Переключение подключения"""
        if self.is_connected:
            self.disconnect()
        else:
            self.connect()

    def connect(self):
        """Подключение"""
        # Сбор данных из формы
        config_data = self._get_form_config()

        # Сохранение порта для измерения latency
        try:
            self.local_port = int(self.spin_local_port.get())
        except ValueError:
            self.local_port = 10808

        # Блокировка кнопки
        self.btn_connect.configure(state="disabled", text="⏳ Подключение...")

        try:
            result = self.controller.connect(config_data)
            if result:
                with self._lock:
                    self._connection_failures = 0  # Сброс счётчика при успешном подключении
                self.update_ui_connected(True)
                self.append_log("✅ Подключение успешно")
                self.save_settings()
            else:
                raise Exception("Не удалось подключиться")
        except Exception as e:
            error_msg = str(e)
            # Если ошибка о недоступности сервера — показываем понятное сообщение
            if "Сервер недоступен" in error_msg or "нет связи с интернетом" in error_msg:
                self.show_connection_error_dialog("Сервер недоступен или нет связи с интернетом")
            elif "Не удалось подключиться" in error_msg:
                self.show_connection_error_dialog("Сервер недоступен или нет связи с интернетом")
            else:
                self.show_connection_error_dialog(error_msg)
            self.append_log(f"❌ Ошибка: {e}")
        finally:
            self.btn_connect.configure(state="normal")

    def show_connection_error_dialog(self, message: str):
        """Показ диалога ошибки подключения в стиле GUI"""
        # Вычисляем позицию центра ДО создания окна
        self.master.update_idletasks()
        main_x = self.master.winfo_rootx()
        main_y = self.master.winfo_rooty()
        main_w = self.master.winfo_width()
        main_h = self.master.winfo_height()
        
        dialog_w = 450
        dialog_h = 200
        x = main_x + (main_w - dialog_w) // 2
        y = main_y + (main_h - dialog_h) // 2

        dialog = ctk.CTkToplevel(self.master)
        dialog.title("❌ Ошибка подключения")
        dialog.geometry(f"{dialog_w}x{dialog_h}+{x}+{y}")
        dialog.resizable(False, False)

        # Делаем диалог модальным
        dialog.transient(self.master)
        dialog.grab_set()

        # Основной фрейм
        main_frame = ctk.CTkFrame(dialog, fg_color=COLORS["bg_secondary"])
        main_frame.pack(fill="both", expand=True)

        # Иконка ошибки
        icon_label = ctk.CTkLabel(
            main_frame,
            text="❌",
            font=ctk.CTkFont(size=40),
            fg_color="transparent"
        )
        icon_label.pack(pady=(15, 10))

        # Текст сообщения
        message_label = ctk.CTkLabel(
            main_frame,
            text=message,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="transparent",
            text_color=COLORS["text_primary"],
            wraplength=380
        )
        message_label.pack(pady=(0, 20))

        # Кнопка ОК
        ok_button = ctk.CTkButton(
            main_frame,
            text="ОК",
            width=120,
            height=35,
            fg_color=COLORS["danger"],
            hover_color="#c0392b",
            text_color="#ffffff",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=dialog.destroy
        )
        ok_button.pack(pady=(0, 15))

        # Фокус на кнопке
        ok_button.focus_set()

        # Закрытие по Enter
        dialog.bind("<Return>", lambda e: dialog.destroy())

    def show_error_dialog(self, title: str, message: str):
        """Показ диалога ошибки"""
        MessageDialog.show(
            self.master, title, message,
            icon="❌",
            button_color=COLORS["danger"],
            button_hover="#c0392b"
        )

    def show_info_dialog(self, title: str, message: str):
        """Показ информационного диалога"""
        MessageDialog.show(
            self.master, title, message,
            icon="ℹ️",
            button_color=COLORS["accent_blue"]
        )

    def show_warning_dialog(self, title: str, message: str):
        """Показ диалога предупреждения"""
        MessageDialog.show(
            self.master, title, message,
            icon="⚠️",
            button_color=COLORS["warning"],
            button_hover="#e67e22"
        )

    def show_yesno_dialog(self, title: str, message: str) -> bool:
        """Показ диалога с вопросом Да/Нет. Возвращает True если Да."""
        return YesNoDialog.show(self.master, title, message)

    def disconnect(self):
        """Отключение"""
        self.controller.disconnect()
        with self._lock:
            self._connection_failures = 0  # Сброс счётчика при отключении
        self.update_ui_connected(False)
        self.append_log("Отключено")

    def clear_connection_form(self):
        """Очистка формы подключения при выходе"""
        # Очищаем все поля ввода
        self.edit_address.delete(0, 'end')
        self.spin_port.delete(0, 'end')
        self.edit_uuid.delete(0, 'end')
        self.edit_sni.delete(0, 'end')
        self.edit_public_key.delete(0, 'end')
        self.edit_short_id.delete(0, 'end')
        self.combo_flow.set("")
        self.combo_transport.set("xhttp")
        self.edit_service_name.delete(0, 'end')
        self.edit_service_name.insert(0, "grpc")
        self.spin_local_port.delete(0, 'end')
        self.spin_local_port.insert(0, "10808")
        
        # Сбрасываем профиль
        if hasattr(self, 'current_profile_label'):
            self.current_profile_label.configure(text="—")
        self.combo_profiles.set("...")
        
        # Отключаем VPN если подключено
        if self.is_connected:
            self.disconnect()

    def update_ui_connected(self, connected: bool):
        """Обновление UI при подключении"""
        self.is_connected = connected

        if connected:
            self.status_label.configure(
                text="✅ Статус: Подключено",
                text_color=COLORS["success"]
            )
            self.status_indicator.configure(text_color=COLORS["success"])
            self.btn_connect.configure(
                text="⏹ Отключить",
                fg_color=COLORS["danger"],
                hover_color="#c0392b"
            )
            self.session_timer_label.configure(text="⏱ 00:00:00")
            self.start_session_timer()
            self.start_latency_timer()
        else:
            self.status_label.configure(
                text="⏸ Статус: Остановлен",
                text_color=COLORS["text_secondary"]
            )
            self.status_indicator.configure(text_color=COLORS["danger"])
            self.btn_connect.configure(
                text="▶ Подключить",
                fg_color=COLORS["success"],
                hover_color="#27ae60"
            )
            self.stop_session_timer()
            self.stop_latency_timer()

    def start_session_timer(self):
        """Запуск таймера сеанса"""
        self.session_start_time = datetime.now()
        self.update_session_timer()

    def stop_session_timer(self):
        """Остановка таймера сеанса"""
        if self.session_timer_id:
            self.master.after_cancel(self.session_timer_id)
            self.session_timer_id = None
        self.session_timer_label.configure(text="")

    def update_session_timer(self):
        """Обновление таймера сеанса"""
        if self.is_connected and self.session_start_time:
            elapsed = datetime.now() - self.session_start_time
            self.session_timer_label.configure(text=f"⏱ {self.format_session_time(elapsed)}")
            self.session_timer_id = self.master.after(1000, self.update_session_timer)

    def format_session_time(self, delta):
        """Форматирование времени сеанса"""
        total_seconds = int(delta.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def start_latency_timer(self):
        """Запуск периодического измерения latency"""
        self.measure_latency()
        self.schedule_next_latency_measurement()

    def stop_latency_timer(self):
        """Остановка измерения latency"""
        if self.latency_timer_id:
            self.master.after_cancel(self.latency_timer_id)
            self.latency_timer_id = None
        with self._lock:
            self._connection_failures = 0  # Сброс счётчика
        self.latency_label.configure(text="")

    def schedule_next_latency_measurement(self):
        """Планирование следующего измерения latency (каждые 10 секунд)"""
        if self.is_connected:
            self.latency_timer_id = self.master.after(10000, self.measure_latency_and_schedule)

    def measure_latency_and_schedule(self):
        """Измерение latency и планирование следующего"""
        self.measure_latency()
        self.schedule_next_latency_measurement()

    def measure_latency(self):
        """Измерение задержки через VPN прокси + мониторинг соединения (в отдельном потоке)"""
        def _measure():
            try:
                # Используем controller.check_connection() — один запрос для latency и мониторинга
                latency = self.controller.check_connection(self.local_port)

                if latency > 0:
                    # Успех — сбрасываем счётчик неудач
                    with self._lock:
                        self._connection_failures = 0
                    latency_ms = latency * 1000
                    self.master.after(0, lambda: self.latency_label.configure(text=f"📶 {latency_ms:.0f} мс"))
                else:
                    # Неудача — инкремент счётчика
                    with self._lock:
                        self._connection_failures += 1
                        failures = self._connection_failures
                    self.master.after(0, lambda: self.latency_label.configure(text="📶 --"))

                    # 3 неудачи подряд = потеря соединения
                    if failures >= self._max_failures:
                        self.master.after(0, self.on_connection_lost)

            except Exception:
                with self._lock:
                    self._connection_failures += 1
                    failures = self._connection_failures
                self.master.after(0, lambda: self.latency_label.configure(text="📶 --"))

                if failures >= self._max_failures:
                    self.master.after(0, self.on_connection_lost)

        threading.Thread(target=_measure, daemon=True).start()

    def _create_text_input_dialog(self, title: str, text: str, placeholder: str = "") -> str:
        """Создание диалога для ввода текста. Возвращает введённое значение."""
        return InputDialog.show(self.master, title, text, placeholder)

    def import_from_link(self):
        """Импорт из VLESS ссылки"""
        link = self._create_text_input_dialog(
            title="Импорт из VLESS ссылки",
            text="Вставьте VLESS ссылку:",
            placeholder="vless://uuid@address:port?..."
        )

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
                    self.edit_service_name.delete(0, 'end')
                    self.edit_service_name.insert(0, params.get("serviceName", "grpc"))
                    # Сохраняем mode для controller
                    self._imported_mode = params.get("mode", "gun")
                    self.append_log("✅ Конфигурация импортирована из ссылки")
                    self.save_settings()
                    # Обновить видимость Service Name
                    self._on_transport_change()
                else:
                    self.show_import_error_dialog(
                        "Не удалось распарсить VLESS ссылку.",
                        "Проверьте правильность формата ссылки:\nvless://uuid@address:port?security=reality&type=xhttp&..."
                    )
            except Exception as e:
                self.show_import_error_dialog(
                    "Невозможно применить настройки из ссылки:",
                    str(e)
                )

    def show_import_error_dialog(self, title: str, message: str):
        """Показ диалога ошибки импорта в стиле GUI"""
        # Центрирование
        self.master.update_idletasks()
        main_x = self.master.winfo_rootx()
        main_y = self.master.winfo_rooty()
        main_w = self.master.winfo_width()
        main_h = self.master.winfo_height()
        dialog_w = 450
        dialog_h = 200
        dialog_x = main_x + (main_w - dialog_w) // 2
        dialog_y = main_y + (main_h - dialog_h) // 2

        # Диалоговое окно
        dialog = ctk.CTkToplevel(self.master)
        dialog.title("")
        dialog.geometry(f"{dialog_w}x{dialog_h}+{dialog_x}+{dialog_y}")
        dialog.resizable(False, False)
        dialog.attributes('-topmost', True)
        dialog.configure(fg_color=COLORS["bg_primary"])

        # Контейнер
        container = ctk.CTkFrame(dialog, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=25, pady=20)

        # Верхняя часть с иконкой и заголовком
        top_frame = ctk.CTkFrame(container, fg_color="transparent")
        top_frame.pack(fill="x", pady=(5, 15))

        ctk.CTkLabel(
            top_frame,
            text="❌",
            font=ctk.CTkFont(size=26),
            width=40
        ).pack(side="left")

        ctk.CTkLabel(
            top_frame,
            text="Ошибка импорта",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["danger"],
            justify="left"
        ).pack(side="left", pady=8, padx=(5, 0))

        # Текст ошибки
        ctk.CTkLabel(
            container,
            text=f"{title}\n{message}",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_primary"],
            justify="left",
            wraplength=380
        ).pack(fill="x", pady=(0, 15), padx=10)

        # Кнопка OK
        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(side="bottom", fill="x")

        ctk.CTkButton(
            btn_frame,
            text="OK",
            command=dialog.destroy,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["accent_blue"],
            hover_color=COLORS["accent_blue_hover"],
            corner_radius=8,
            width=110,
            height=38
        ).pack(side="right")

    def toggle_system_proxy(self):
        """Переключение системного прокси"""
        enabled = self.chk_system_proxy.get() == 1
        self.controller.set_system_proxy(enabled)
        self.append_log(f"Системный прокси {'включен' if enabled else 'отключен'}")

    def check_for_updates(self):
        """Проверка обновлений Xray-core"""
        self.btn_check_update.configure(state="disabled", text="⏳ Проверка...")
        self.update_status_label.configure(text="")
        
        def check_thread():
            try:
                update_info = self.controller.check_for_updates(force=True)
                
                # Обновляем UI в главном потоке
                self.master.after(0, lambda: self.btn_check_update.configure(
                    state="normal", text="📥 Проверить обновления"
                ))
                
                if update_info:
                    current = update_info.get('current_version', '?')
                    latest = update_info.get('latest_version', '?')
                    self.version_label.configure(
                        text=f"Версия: {current} → Доступна {latest}",
                        text_color=COLORS["warning"] if 'warning' in COLORS else COLORS["danger"]
                    )
                    self.update_status_label.configure(
                        text=f"Доступно обновление: {current} → {latest}"
                    )
                    self.btn_install_update.configure(state="normal")
                    self._pending_update = update_info
                    self.append_log(f"🔄 Доступно обновление Xray: {current} → {latest}")
                else:
                    self.version_label.configure(text="Версия: актуальна")
                    self.update_status_label.configure(text="Установлена последняя версия")
                    self.btn_install_update.configure(state="disabled")
                    self._pending_update = None
                    self.append_log("✅ Версия Xray актуальна")
                    
            except Exception as e:
                self.master.after(0, lambda: (
                    self.btn_check_update.configure(state="normal", text="📥 Проверить обновления"),
                    self.update_status_label.configure(text=f"Ошибка: {e}")
                ))
                self.append_log(f"❌ Ошибка проверки обновлений: {e}")
        
        thread = threading.Thread(target=check_thread, daemon=True)
        thread.start()
    
    def install_update(self):
        """Установка обновления Xray-core"""
        if not hasattr(self, '_pending_update') or not self._pending_update:
            self.show_warning_dialog("Обновление", "Сначала проверьте обновления")
            return

        if not self.show_yesno_dialog(
            "Подтверждение",
            f"Установить обновление Xray-core?\n\n"
            f"Текущая версия: {self._pending_update.get('current_version', '?')}\n"
            f"Новая версия: {self._pending_update.get('latest_version', '?')}\n\n"
            "Приложение будет перезапущено после установки."
        ):
            return

        self.btn_install_update.configure(state="disabled", text="⏳ Загрузка...")
        self.btn_check_update.configure(state="disabled")
        self.update_progress.set(0)

        def progress_callback(downloaded, total):
            """Обновление прогресса"""
            if total > 0:
                percent = (downloaded / total) * 100
                mb_downloaded = downloaded / (1024 * 1024)
                mb_total = total / (1024 * 1024)
                self.master.after(0, lambda: (
                    self.update_progress.set(percent / 100),
                    self.update_status_label.configure(
                        text=f"Загрузка: {mb_downloaded:.1f} / {mb_total:.1f} MB ({percent:.0f}%)"
                    )
                ))

        def install_thread():
            try:
                success = self.controller.download_update(self._pending_update, progress_callback)

                self.master.after(0, lambda: (
                    self.btn_install_update.configure(state="normal", text="⬇️ Установить"),
                    self.btn_check_update.configure(state="normal")
                ))

                if success:
                    self.update_status_label.configure(text="✅ Обновление установлено!")
                    self.version_label.configure(text="Версия: обновлена")
                    self.btn_install_update.configure(state="disabled")
                    self._pending_update = None
                    self.append_log("✅ Xray-core обновлён")

                    # Предложение перезапуска
                    if self.show_yesno_dialog("Обновление установлено",
                        "Xray-core обновлён. Перезапустить приложение?"):
                        self.master.after(500, self.master.quit)
                else:
                    self.update_status_label.configure(text="❌ Ошибка установки")
                    self.append_log("❌ Ошибка установки обновления")
                    
            except Exception as e:
                self.master.after(0, lambda: (
                    self.btn_install_update.configure(state="normal", text="⬇️ Установить"),
                    self.btn_check_update.configure(state="normal"),
                    self.update_status_label.configure(text=f"❌ Ошибка: {e}")
                ))
                self.append_log(f"❌ Ошибка установки: {e}")
        
        thread = threading.Thread(target=install_thread, daemon=True)
        thread.start()

    def append_log(self, message: str, max_lines: int = 500):
        """Добавление сообщения в лог с ротацией

        Args:
            message: Сообщение для добавления
            max_lines: Максимальное количество строк в логе (по умолчанию 500)
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")

        # Ротация: удаление старых строк при превышении лимита
        lines = int(self.log_text.index("end-1c").split(".")[0])
        if lines > max_lines:
            # Удаляем старые строки (с начала)
            self.log_text.delete("1.0", f"{lines - max_lines}.0")

        # Автоскролл к последней строке
        self.log_text.see("end")

    def clear_logs(self):
        """Очистка логов"""
        self.log_text.delete("1.0", "end")

    def on_log(self, message: str):
        """Обработка лога от Xray"""
        self.append_log(f"Xray: {message}")

    def save_settings(self):
        """Сохранение настроек"""
        config = self._get_form_config()
        self.controller.save_config(config)

    def load_settings(self):
        """Загрузка сохранённых настроек"""
        saved = self.controller.load_saved_config()
        if saved:
            self._fill_form_from_config(saved)
            self.append_log("✅ Настройки загружены")

    def exit_app(self):
        """Выход из приложения с отключением прокси"""
        if self.is_connected:
            self.show_exit_confirm_dialog()
        else:
            self.master.quit()

    def show_exit_confirm_dialog(self):
        """Показ кастомного диалога подтверждения выхода в стиле GUI"""
        # Центрирование
        self.master.update_idletasks()
        main_x = self.master.winfo_rootx()
        main_y = self.master.winfo_rooty()
        main_w = self.master.winfo_width()
        main_h = self.master.winfo_height()
        dialog_w = 420
        dialog_h = 180
        dialog_x = main_x + (main_w - dialog_w) // 2
        dialog_y = main_y + (main_h - dialog_h) // 2

        # Диалоговое окно
        dialog = ctk.CTkToplevel(self.master)
        dialog.title("")
        dialog.geometry(f"{dialog_w}x{dialog_h}+{dialog_x}+{dialog_y}")
        dialog.resizable(False, False)
        dialog.attributes('-topmost', True)
        dialog.configure(fg_color=COLORS["bg_primary"])

        # Контейнер
        container = ctk.CTkFrame(dialog, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=25, pady=20)

        # Верхняя часть с иконкой и текстом
        top_frame = ctk.CTkFrame(container, fg_color="transparent")
        top_frame.pack(fill="x", pady=(5, 15))

        ctk.CTkLabel(
            top_frame,
            text="⚠️",
            font=ctk.CTkFont(size=26),
            width=40
        ).pack(side="left")

        ctk.CTkLabel(
            top_frame,
            text="VPN подключение активно\nОтключиться и выйти?",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_primary"],
            justify="left"
        ).pack(side="left", pady=8, padx=(5, 0))

        # Кнопки
        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(side="bottom", fill="x")

        def on_cancel():
            dialog.destroy()

        def on_confirm():
            try:
                self.controller.disconnect()
            except Exception:
                pass
            dialog.destroy()
            self.master.quit()

        ctk.CTkButton(
            btn_frame,
            text="Отмена",
            command=on_cancel,
            font=ctk.CTkFont(size=13),
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=8,
            width=110,
            height=38
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            btn_frame,
            text="Выйти",
            command=on_confirm,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["danger"],
            hover_color="#c0392b",
            corner_radius=8,
            width=110,
            height=38
        ).pack(side="right")
