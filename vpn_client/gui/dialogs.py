"""
Модуль диалоговых окон для GUI
"""
import customtkinter as ctk
from typing import Optional, Dict, Any
from .styles import COLORS


class DialogBuilder:
    """Базовый класс для создания диалоговых окон"""
    
    @staticmethod
    def _center_dialog(master: ctk.CTk, dialog_w: int, dialog_h: int) -> tuple:
        """Вычислить координаты для центрирования диалога"""
        master.update_idletasks()
        main_x = master.winfo_rootx()
        main_y = master.winfo_rooty()
        main_w = master.winfo_width()
        main_h = master.winfo_height()
        
        x = main_x + (main_w - dialog_w) // 2
        y = main_y + (main_h - dialog_h) // 2
        return x, y
    
    @staticmethod
    def _create_dialog_frame(
        master: ctk.CTk,
        title: str,
        width: int = 400,
        height: int = 180
    ) -> tuple:
        """Создать базовый диалог с фреймом"""
        x, y = DialogBuilder._center_dialog(master, width, height)

        dialog = ctk.CTkToplevel(master)
        dialog.title(title)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        dialog.resizable(False, False)
        dialog.update_idletasks()  # Важно! Обновляем перед grab_set
        dialog.transient(master)
        dialog.grab_set()

        main_frame = ctk.CTkFrame(dialog, fg_color=COLORS["bg_secondary"])
        main_frame.pack(fill="both", expand=True)

        return dialog, main_frame


class MessageDialog(DialogBuilder):
    """Диалог с сообщением (информация, ошибка, предупреждение)"""
    
    @staticmethod
    def show(
        master: ctk.CTk,
        title: str,
        message: str,
        icon: str = "ℹ️",
        button_color: str = COLORS["accent_blue"],
        button_hover: str = COLORS["accent_blue_hover"]
    ) -> None:
        """Показать диалог с сообщением"""
        dialog, main_frame = MessageDialog._create_dialog_frame(
            master, title, width=400, height=180
        )
        
        icon_label = ctk.CTkLabel(
            main_frame,
            text=icon,
            font=ctk.CTkFont(size=40),
            fg_color="transparent"
        )
        icon_label.pack(pady=(15, 10))
        
        message_label = ctk.CTkLabel(
            main_frame,
            text=message,
            font=ctk.CTkFont(size=14),
            fg_color="transparent",
            text_color=COLORS["text_primary"],
            wraplength=340
        )
        message_label.pack(pady=(0, 20))
        
        ok_button = ctk.CTkButton(
            main_frame,
            text="ОК",
            width=120,
            height=35,
            fg_color=button_color,
            hover_color=button_hover,
            text_color="#ffffff",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=dialog.destroy
        )
        ok_button.pack(pady=(0, 15))
        ok_button.focus_set()
        dialog.bind("<Return>", lambda e: dialog.destroy())
        
        dialog.wait_window()


class YesNoDialog(DialogBuilder):
    """Диалог с вопросом Да/Нет"""
    
    @staticmethod
    def show(master: ctk.CTk, title: str, message: str) -> bool:
        """
        Показать диалог с вопросом
        
        Returns:
            True если нажат "Да", False если "Нет"
        """
        result = {'value': False}
        dialog, main_frame = YesNoDialog._create_dialog_frame(
            master, title, width=400, height=180
        )
        
        icon_label = ctk.CTkLabel(
            main_frame,
            text="❓",
            font=ctk.CTkFont(size=40),
            fg_color="transparent"
        )
        icon_label.pack(pady=(15, 10))
        
        message_label = ctk.CTkLabel(
            main_frame,
            text=message,
            font=ctk.CTkFont(size=14),
            fg_color="transparent",
            text_color=COLORS["text_primary"],
            wraplength=340
        )
        message_label.pack(pady=(0, 20))
        
        buttons_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        buttons_frame.pack(pady=(0, 15))
        
        def on_yes():
            result['value'] = True
            dialog.destroy()
        
        def on_no():
            result['value'] = False
            dialog.destroy()
        
        yes_button = ctk.CTkButton(
            buttons_frame,
            text="Да",
            width=100,
            height=35,
            fg_color=COLORS["danger"],
            hover_color="#c0392b",
            text_color="#ffffff",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=on_yes
        )
        yes_button.pack(side="left", padx=(20, 10))
        
        no_button = ctk.CTkButton(
            buttons_frame,
            text="Нет",
            width=100,
            height=35,
            fg_color=COLORS["bg_tertiary"],
            hover_color="#3a4a5d",
            text_color="#ffffff",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=on_no
        )
        no_button.pack(side="left", padx=10)
        
        dialog.bind("<Return>", lambda e: on_yes())
        dialog.bind("<Escape>", lambda e: on_no())
        
        dialog.wait_window()
        return result['value']


class InputDialog(DialogBuilder):
    """Диалог для ввода текста"""
    
    @staticmethod
    def show(
        master: ctk.CTk,
        title: str,
        text: str,
        placeholder: str = ""
    ) -> Optional[str]:
        """
        Показать диалог для ввода текста
        
        Returns:
            Введённый текст или None если отменено
        """
        result = {'value': None}
        dialog, main_frame = InputDialog._create_dialog_frame(
            master, title, width=500, height=200
        )
        
        text_label = ctk.CTkLabel(
            main_frame,
            text=text,
            font=ctk.CTkFont(size=14),
            fg_color="transparent",
            text_color=COLORS["text_primary"]
        )
        text_label.pack(pady=(15, 5))
        
        entry = ctk.CTkEntry(
            main_frame,
            placeholder_text=placeholder,
            width=400,
            height=35,
            fg_color=COLORS["bg_tertiary"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"]
        )
        entry.pack(pady=(5, 15))
        entry.focus_set()
        
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(pady=(0, 15))
        
        def on_ok():
            result['value'] = entry.get()
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        ok_button = ctk.CTkButton(
            button_frame,
            text="ОК",
            width=100,
            height=35,
            fg_color=COLORS["accent_blue"],
            hover_color=COLORS["accent_blue_hover"],
            text_color="#ffffff",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=on_ok
        )
        ok_button.pack(side="left", padx=10)
        
        cancel_button = ctk.CTkButton(
            button_frame,
            text="Отмена",
            width=100,
            height=35,
            fg_color=COLORS["bg_primary"],
            hover_color=COLORS["bg_secondary"],
            text_color=COLORS["text_primary"],
            font=ctk.CTkFont(size=14, weight="bold"),
            command=on_cancel
        )
        cancel_button.pack(side="left", padx=10)
        
        entry.bind("<Return>", lambda e: on_ok())
        dialog.bind("<Escape>", lambda e: on_cancel())
        
        dialog.wait_window()
        return result['value']
