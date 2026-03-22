"""
Фикстуры для pytest
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import shutil


@pytest.fixture
def temp_config_dir():
    """
    Временная директория для конфигов
    
    Usage:
        def test_something(temp_config_dir):
            # temp_config_dir - Path к временной директории
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="vpnclient_test_"))
    yield temp_dir
    # Очистка после теста
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_xray_binary(temp_config_dir):
    """
    Создать фейковый бинарник Xray
    
    Usage:
        def test_with_xray(mock_xray_binary):
            # mock_xray_binary - Path к фейковому бинарнику
    """
    binaries_dir = temp_config_dir / "binaries"
    binaries_dir.mkdir()
    
    binary = binaries_dir / "xray"
    binary.write_text("#!/bin/bash\necho 'Xray 1.0.0'")
    binary.chmod(0o755)
    
    return binary


@pytest.fixture
def sample_vless_config():
    """
    Пример конфигурации VLESS для тестов
    
    Usage:
        def test_config(sample_vless_config):
            # sample_vless_config - dict с тестовыми данными
    """
    return {
        "address": "example.com",
        "port": 443,
        "uuid": "00000000-0000-0000-0000-000000000000",
        "sni": "example.com",
        "public_key": "test_public_key",
        "short_id": "abcd1234",
        "transport": "xhttp",
        "local_port": 10808
    }


@pytest.fixture
def sample_vless_link():
    """
    Пример VLESS ссылки для тестов парсинга
    
    Usage:
        def test_parse(sample_vless_link):
            # sample_vless_link - строка vless://...
    """
    return "vless://00000000-0000-0000-0000-000000000000@example.com:443?type=grpc&security=reality&pbk=test_key&sid=abcd1234&serviceName=grpc&mode=gun"


@pytest.fixture
def mock_controller():
    """
    Mock контроллера для тестов GUI
    
    Usage:
        def test_gui(mock_controller):
            # mock_controller - Mock объект контроллера
    """
    controller = Mock()
    controller.connect = Mock(return_value=True)
    controller.disconnect = Mock()
    controller.is_connected = Mock(return_value=False)
    controller.get_xray_version = Mock(return_value="1.0.0")
    controller.save_profile = Mock(return_value=True)
    controller.load_profile = Mock(return_value=None)
    controller.delete_profile = Mock(return_value=True)
    controller.get_profile_names = Mock(return_value=[])
    controller.check_connection = Mock(return_value=0.05)
    return controller
