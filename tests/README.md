# Unit тесты для VPN Client

## Установка зависимостей

```bash
source venv/bin/activate
pip install pytest pytest-cov pytest-mock
```

## Запуск тестов

### Все тесты
```bash
pytest tests/ -v
```

### Конкретный файл
```bash
pytest tests/test_vless_config.py -v
```

### Конкретный тест
```bash
pytest tests/test_vless_config.py::TestCreateVlessRealityXhttp::test_minimal_config -v
```

### С отчётом о покрытии
```bash
pytest --cov=vpn_client --cov-report=html
```

Отчёт будет в `htmlcov/index.html`

## Структура тестов

```
tests/
├── conftest.py              # Фикстуры pytest
├── test_vless_config.py     # Тесты генерации конфигов VLESS
├── test_xray_manager.py     # TODO: Тесты управления Xray
├── test_xray_updater.py     # TODO: Тесты обновлений
├── test_controller.py       # TODO: Тесты контроллера
├── test_proxy.py            # TODO: Тесты прокси
├── test_settings.py         # TODO: Тесты настроек
└── gui/
    ├── test_dialogs.py      # TODO: Тесты диалогов
    └── test_styles.py       # TODO: Тесты стилей
```

## Фикстуры

### `temp_config_dir`
Временная директория для конфигов. Автоматически удаляется после теста.

### `mock_xray_binary`
Создаёт фейковый бинарник Xray во временной директории.

### `sample_vless_config`
Пример конфигурации VLESS для тестов.

### `sample_vless_link`
Пример VLESS ссылки для тестов парсинга.

### `mock_controller`
Mock объект контроллера для тестов GUI.

## Покрытие кода

| Модуль | Статус | Покрытие |
|--------|--------|----------|
| `core/vless_config.py` | ✅ Готово | ~90% |
| `core/xray_manager.py` | ⏳ TODO | - |
| `core/xray_updater.py` | ⏳ TODO | - |
| `controller.py` | ⏳ TODO | - |
| `utils/settings.py` | ⏳ TODO | - |
| `utils/proxy.py` | ⏳ TODO | - |
| `gui/dialogs.py` | ⏳ TODO | - |

## Добавление новых тестов

1. Создайте файл `test_<module>.py` в `tests/`
2. Импортируйте тестируемый модуль
3. Создайте класс `Test<ModuleName>`
4. Добавьте методы `test_<something>()`
5. Используйте фикстуры из `conftest.py`

Пример:
```python
from vpn_client.core.vless_config import create_vless_reality_xhttp

class TestCreateVlessRealityXhttp:
    def test_something(self, sample_vless_config):
        config = create_vless_reality_xhttp(...)
        assert config["log"]["loglevel"] == "warning"
```
