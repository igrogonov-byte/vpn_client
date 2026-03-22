# VPN Client - VLESS Reality xhttp

Кроссплатформенный VPN клиент для протокола **VLESS Reality** с транспортом **xhttp**.

## Возможности

- ✅ VLESS Reality с xhttp транспортом
- ✅ Импорт конфигурации из VLESS ссылок
- ✅ Системный прокси (Windows/Linux)
- ✅ Автозапуск
- ✅ Системный трей
- ✅ Логи подключения
- ✅ Кроссплатформенность (Windows, Linux x86_64)

## Требования

- Python 3.9+
- Xray-core бинарник

## Установка

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Установка Xray-core

Скачайте бинарник Xray-core для вашей платформы:

- **Windows**: https://github.com/XTLS/Xray-core/releases (xray-windows-64.zip)
- **Linux**: https://github.com/XTLS/Xray-core/releases (xray-linux-64.zip)

Разархивируйте и поместите бинарник в:
```
vpn_client/binaries/xray.exe    # Windows
vpn_client/binaries/xray        # Linux
```

Или установите системно:
```bash
# Linux
sudo apt install xray-core
```

## Запуск

### Из исходников

```bash
# Из корня проекта
python run.py

# Или через модуль
python -m vpn_client.main
```

### Сборка в исполняемый файл

```bash
python vpn_client/build.py
```

Исполняемый файл появится в `dist/VPNClient/`

## Использование

### Подключение через форму

1. Введите параметры сервера:
   - Адрес сервера
   - Порт
   - UUID
   - SNI (домен сервера)
   - Public Key ( Reality публичный ключ)
   - Short ID
2. Нажмите "Подключить"

### Импорт из VLESS ссылки

1. Нажмите "Импортировать из VLESS ссылки"
2. Вставьте ссылку вида:
   ```
   vless://uuid@address:port?security=reality&type=xhttp&sni=example.com&pbk=public_key&sid=short_id
   ```
3. Параметры заполнятся автоматически

### Системный прокси

Вкладка "Настройки" → "Системный прокси" → Включить

После включения весь системный трафик будет идти через VPN.

### Автозапуск

Вкладка "Настройки" → "Автозапуск" → Добавить в автозапуск

## Структура проекта

```
vpn_client/
├── main.py              # Точка входа (CustomTkinter + pystray)
├── controller.py        # Связующий слой
├── core/
│   ├── xray_manager.py  # Управление Xray-core
│   └── vless_config.py  # Генерация конфигов VLESS
├── gui/
│   └── main_window_ctk.py   # Основное окно (CustomTkinter)
├── utils/
│   ├── proxy.py         # Системный прокси
│   └── autostart.py     # Автозапуск
├── binaries/            # Xray-core бинарники
└── assets/              # Иконки и ресурсы
```

## Пример конфигурации

```json
{
  "address": "example.com",
  "port": 443,
  "uuid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "sni": "example.com",
  "public_key": "abcdef123456...",
  "short_id": "a1b2c3d4",
  "flow": ""
}
```

## Troubleshooting

### "Xray-core не найден"
- Убедитесь, что бинарник xray находится в `vpn_client/binaries/`
- Или установите xray системно и добавьте в PATH

### "Ошибка подключения"
- Проверьте правильность параметров (UUID, public key, short_id)
- Убедитесь, что сервер доступен
- Проверьте логи во вкладке "Логи"

### "Не работает системный прокси"
- **Linux**: Требуется GNOME (gsettings)
- **Windows**: Требуется доступ к реестру

## Лицензия

MIT
