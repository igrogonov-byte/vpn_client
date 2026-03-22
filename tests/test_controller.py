"""
Тесты для VPNController
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path


class TestControllerInit:
    """Тесты инициализации контроллера"""
    
    def test_init(self):
        """Тест создания контроллера"""
        from vpn_client.controller import VPNController
        
        controller = VPNController()
        
        assert controller.xray_manager is None
        assert controller.system_proxy is not None
        assert controller.autostart is not None
        assert controller.current_config is None


class TestControllerConnect:
    """Тесты подключения к VPN"""
    
    @patch('vpn_client.controller.XrayManager')
    @patch('vpn_client.controller.save_config')
    @patch('vpn_client.controller.create_vless_reality_xhttp')
    def test_connect_success(self, mock_create_config, mock_save, mock_xray_mgr):
        """Тест успешного подключения"""
        from vpn_client.controller import VPNController
        
        # Настраиваем моки
        mock_create_config.return_value = {"outbounds": [{}]}
        mock_save.return_value = True
        
        mock_xray_instance = Mock()
        mock_xray_instance.start.return_value = True
        mock_xray_mgr.return_value = mock_xray_instance
        
        controller = VPNController()
        
        config_data = {
            "address": "example.com",
            "port": "443",
            "uuid": "00000000-0000-0000-0000-000000000000",
            "sni": "example.com",
            "public_key": "test_key",
            "short_id": "abcd1234"
        }
        
        result = controller.connect(config_data)
        
        assert result == True
        mock_create_config.assert_called_once()
        mock_save.assert_called_once()
        mock_xray_instance.start.assert_called_once()
    
    def test_connect_no_address(self):
        """Тест подключения без адреса"""
        from vpn_client.controller import VPNController
        
        controller = VPNController()
        
        config_data = {
            "port": "443",
            "uuid": "test-uuid"
        }
        
        with pytest.raises(Exception, match="Не указан адрес"):
            controller.connect(config_data)
    
    def test_connect_no_uuid(self):
        """Тест подключения без UUID"""
        from vpn_client.controller import VPNController
        
        controller = VPNController()
        
        config_data = {
            "address": "example.com",
            "port": "443"
        }
        
        with pytest.raises(Exception, match="Не указан UUID"):
            controller.connect(config_data)
    
    def test_connect_invalid_port(self):
        """Тест подключения с невалидным портом"""
        from vpn_client.controller import VPNController
        
        controller = VPNController()
        
        config_data = {
            "address": "example.com",
            "port": "invalid",
            "uuid": "test"
        }
        
        with pytest.raises(Exception, match="Неверный формат порта"):
            controller.connect(config_data)
    
    @patch('vpn_client.controller.XrayManager')
    @patch('vpn_client.controller.save_config')
    @patch('vpn_client.controller.create_vless_reality_xhttp')
    def test_connect_xray_fails(self, mock_create_config, mock_save, mock_xray_mgr):
        """Тест когда Xray не запускается"""
        from vpn_client.controller import VPNController
        
        mock_create_config.return_value = {"outbounds": [{}]}
        mock_save.return_value = True
        
        mock_xray_instance = Mock()
        mock_xray_instance.start.return_value = False
        mock_xray_mgr.return_value = mock_xray_instance
        
        controller = VPNController()
        
        config_data = {
            "address": "example.com",
            "port": "443",
            "uuid": "test-uuid"
        }
        
        with pytest.raises(Exception, match="Не удалось запустить"):
            controller.connect(config_data)


class TestControllerDisconnect:
    """Тесты отключения от VPN"""
    
    @patch('vpn_client.controller.XrayManager')
    def test_disconnect(self, mock_xray_mgr):
        """Тест отключения"""
        from vpn_client.controller import VPNController
        
        mock_xray_instance = Mock()
        mock_xray_mgr.return_value = mock_xray_instance
        
        controller = VPNController()
        controller.xray_manager = mock_xray_instance
        controller.system_proxy = Mock()
        
        result = controller.disconnect()
        
        assert result == True
        mock_xray_instance.stop.assert_called_once()
        controller.system_proxy.disable.assert_called_once()
    
    def test_disconnect_when_not_connected(self):
        """Тест отключения когда не подключено"""
        from vpn_client.controller import VPNController
        
        controller = VPNController()
        controller.xray_manager = None
        
        result = controller.disconnect()
        
        assert result == True


class TestControllerConnectionCheck:
    """Тесты проверки подключения"""
    
    @patch('vpn_client.controller.XrayManager')
    def test_check_connection(self, mock_xray_mgr):
        """Тест проверки соединения"""
        from vpn_client.controller import VPNController
        
        mock_xray_instance = Mock()
        mock_xray_instance.check_connection.return_value = 0.05
        mock_xray_mgr.return_value = mock_xray_instance
        
        controller = VPNController()
        controller.xray_manager = mock_xray_instance
        
        latency = controller.check_connection(10808)
        
        assert latency == 0.05
        mock_xray_instance.check_connection.assert_called_once_with(10808)
    
    def test_check_connection_no_manager(self):
        """Тест проверки без XrayManager"""
        from vpn_client.controller import VPNController
        
        controller = VPNController()
        controller.xray_manager = None
        
        latency = controller.check_connection(10808)
        
        assert latency == 0


class TestControllerProfiles:
    """Тесты управления профилями"""
    
    @patch('vpn_client.controller.SettingsManager')
    def test_save_profile(self, mock_settings_mgr):
        """Тест сохранения профиля"""
        from vpn_client.controller import VPNController
        
        mock_settings = Mock()
        mock_settings.save_profile.return_value = True
        mock_settings_mgr.return_value = mock_settings
        
        controller = VPNController()
        
        config = {"address": "example.com", "port": 443}
        result = controller.save_profile("TestProfile", config)
        
        assert result == True
        mock_settings.save_profile.assert_called_once_with("TestProfile", config)
    
    @patch('vpn_client.controller.SettingsManager')
    def test_load_profile(self, mock_settings_mgr):
        """Тест загрузки профиля"""
        from vpn_client.controller import VPNController
        
        mock_settings = Mock()
        mock_settings.load_profile.return_value = {"address": "example.com"}
        mock_settings_mgr.return_value = mock_settings
        
        controller = VPNController()
        
        result = controller.load_profile("TestProfile")
        
        assert result == {"address": "example.com"}
        mock_settings.load_profile.assert_called_once_with("TestProfile")
    
    @patch('vpn_client.controller.SettingsManager')
    def test_get_profile_names(self, mock_settings_mgr):
        """Тест получения списка профилей"""
        from vpn_client.controller import VPNController
        
        mock_settings = Mock()
        mock_settings.get_profile_names.return_value = ["Profile1", "Profile2"]
        mock_settings_mgr.return_value = mock_settings
        
        controller = VPNController()
        
        result = controller.get_profile_names()
        
        assert result == ["Profile1", "Profile2"]
        mock_settings.get_profile_names.assert_called_once()
    
    @patch('vpn_client.controller.SettingsManager')
    def test_delete_profile(self, mock_settings_mgr):
        """Тест удаления профиля"""
        from vpn_client.controller import VPNController
        
        mock_settings = Mock()
        mock_settings.delete_profile.return_value = True
        mock_settings_mgr.return_value = mock_settings
        
        controller = VPNController()
        
        result = controller.delete_profile("TestProfile")
        
        assert result == True
        mock_settings.delete_profile.assert_called_once_with("TestProfile")


class TestControllerProxy:
    """Тесты системного прокси"""
    
    def test_set_system_proxy_enable(self):
        """Тест включения системного прокси"""
        from vpn_client.controller import VPNController
        
        controller = VPNController()
        controller.system_proxy = Mock()
        controller.current_config = {"local_port": "10808"}
        controller.is_connected = Mock(return_value=True)
        
        result = controller.set_system_proxy(True)
        
        assert result == True
        controller.system_proxy.enable.assert_called_once()
    
    def test_set_system_proxy_disable(self):
        """Тест отключения системного прокси"""
        from vpn_client.controller import VPNController
        
        controller = VPNController()
        controller.system_proxy = Mock()
        controller.system_proxy.is_enabled = True
        
        result = controller.set_system_proxy(False)
        
        assert result == True
        controller.system_proxy.disable.assert_called_once()


class TestControllerAutostart:
    """Тесты автозапуска"""
    
    def test_set_autostart_enable(self):
        """Тест включения автозапуска"""
        from vpn_client.controller import VPNController
        
        controller = VPNController()
        controller.autostart = Mock()
        controller.autostart.enable.return_value = True
        
        result = controller.set_autostart(True)
        
        assert result == True
        controller.autostart.enable.assert_called_once()
    
    def test_set_autostart_disable(self):
        """Тест отключения автозапуска"""
        from vpn_client.controller import VPNController
        
        controller = VPNController()
        controller.autostart = Mock()
        controller.autostart.disable.return_value = True
        
        result = controller.set_autostart(False)
        
        assert result == True
        controller.autostart.disable.assert_called_once()
    
    def test_is_autostart_enabled(self):
        """Тест проверки статуса автозапуска"""
        from vpn_client.controller import VPNController
        
        controller = VPNController()
        controller.autostart = Mock()
        controller.autostart.is_enabled.return_value = True
        
        result = controller.is_autostart_enabled()
        
        assert result == True
        controller.autostart.is_enabled.assert_called_once()
