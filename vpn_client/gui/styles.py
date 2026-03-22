"""
Цветовая схема и стили для GUI
"""
from typing import Dict

# Цветовая палитра
COLORS: Dict[str, str] = {
    "bg_primary": "#1a1f2e",       # Основной фон (темно-серый)
    "bg_secondary": "#242b3d",     # Вторичный фон (панели)
    "bg_tertiary": "#2d3548",      # Третичный фон (поля ввода)
    "accent_blue": "#4a9eff",      # Акцент голубой
    "accent_blue_hover": "#3a8eef", # Акцент при наведении
    "success": "#2ecc71",          # Успех
    "danger": "#e74c3c",           # Опасность
    "warning": "#f39c12",          # Предупреждение
    "text_primary": "#ecf0f1",     # Основной текст
    "text_secondary": "#95a5a6",   # Вторичный текст
    "border": "#3a4255",           # Границы
}

# Размеры элементов
SIZES = {
    "window_width": 840,
    "window_height": 683,
    "min_width": 630,
    "min_height": 525,
    "entry_width": 450,
    "entry_height": 42,
    "button_height": 35,
    "label_font_size": 13,
    "title_font_size": 28,
}

# Отступы
PADDING = {
    "form_padx": 10,
    "form_pady": 8,
    "frame_padx": 30,
    "frame_pady": 20,
}
