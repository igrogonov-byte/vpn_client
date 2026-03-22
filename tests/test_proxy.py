"""
Тесты для модуля системного прокси (SystemProxy)
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import subprocess
from vpn_client.utils.proxy import SystemProxy


class TestSystemProxyInit:
    """Тесты инициализации SystemProxy"""
    
    def test_init(self):
        """Тест создания экземпляра"""
        proxy = SystemProxy()
        
        assert proxy.is_enabled == False
        assert proxy.original_settings is None


class TestSystemProxyEnable:
    """Тесты включения прокси"""
    
    @patch('sys.platform', 'linux')
    @patch('subprocess.run')
    def test_enable_linux_success(self, mock_run):
        """Тест успешного включения прокси на Linux"""
        mock_run.return_value = MagicMock(returncode=0, stdout='none')
        
        proxy = SystemProxy()
        result = proxy.enable("127.0.0.1", 10808)
        
        assert result == True
        assert proxy.is_enabled == True
        # Проверяем что gsettings вызывался
        assert mock_run.call_count >= 1
    
    @patch('sys.platform', 'linux')
    @patch('subprocess.run')
    def test_enable_linux_gsettings_fails(self, mock_run):
        """Тест когда gsettings возвращает ошибку"""
        mock_run.return_value = MagicMock(returncode=1, stderr="Error")
        
        proxy = SystemProxy()
        result = proxy.enable("127.0.0.1", 10808)
        
        # Должно вернуть False при ошибке
        assert result == False
    
    @patch('sys.platform', 'win32')
    @patch('winreg.OpenKey')
    @patch('winreg.SetValueEx')
    @patch('winreg.CloseKey')
    def test_enable_windows_success(self, mock_close, mock_set, mock_open):
        """Тест успешного включения прокси на Windows"""
        mock_key = Mock()
        mock_open.return_value = mock_key
        
        proxy = SystemProxy()
        result = proxy.enable("127.0.0.1", 10808)
        
        assert result == True
        assert proxy.is_enabled == True
        # Проверяем что реестр модифицировался
        mock_set.assert_called()
    
    @patch('sys.platform', 'win32')
    @patch('winreg.OpenKey')
    @patch('winreg.SetValueEx')
    def test_enable_windows_exception(self, mock_set, mock_open):
        """Тест исключения при включении на Windows"""
        mock_open.side_effect = Exception("Registry error")
        
        proxy = SystemProxy()
        result = proxy.enable("127.0.0.1", 10808)
        
        assert result == False


class TestSystemProxyDisable:
    """Тесты отключения прокси"""
    
    @patch('sys.platform', 'linux')
    @patch('subprocess.run')
    def test_disable_linux_success(self, mock_run):
        """Тест успешного отключения прокси на Linux"""
        mock_run.return_value = MagicMock(returncode=0)
        
        proxy = SystemProxy()
        proxy.is_enabled = True  # Имитируем что прокси был включён
        
        result = proxy.disable()
        
        assert result == True
        assert proxy.is_enabled == False
    
    @patch('sys.platform', 'linux')
    @patch('subprocess.run')
    def test_disable_linux_restore_original(self, mock_run):
        """Тест восстановления оригинальных настроек"""
        mock_run.return_value = MagicMock(returncode=0)
        
        proxy = SystemProxy()
        proxy.is_enabled = True
        proxy.original_settings = {"mode": "none"}  # Сохранённые настройки
        
        result = proxy.disable()
        
        assert result == True
        # Должен восстановить оригинальные настройки
        assert mock_run.call_count >= 1
    
    @patch('sys.platform', 'win32')
    @patch('winreg.OpenKey')
    @patch('winreg.SetValueEx')
    @patch('winreg.CloseKey')
    def test_disable_windows_success(self, mock_close, mock_set, mock_open):
        """Тест успешного отключения прокси на Windows"""
        mock_key = Mock()
        mock_open.return_value = mock_key
        
        proxy = SystemProxy()
        proxy.is_enabled = True
        
        result = proxy.disable()
        
        assert result == True
        assert proxy.is_enabled == False


class TestSystemProxyIntegration:
    """Интеграционные тесты"""
    
    @patch('sys.platform', 'linux')
    @patch('subprocess.run')
    def test_enable_then_disable(self, mock_run):
        """Тест включения и последующего отключения"""
        mock_run.return_value = MagicMock(returncode=0)
        
        proxy = SystemProxy()
        
        # Включаем
        enable_result = proxy.enable("127.0.0.1", 10808)
        assert enable_result == True
        assert proxy.is_enabled == True
        
        # Отключаем
        disable_result = proxy.disable()
        assert disable_result == True
        assert proxy.is_enabled == False
    
    @patch('sys.platform', 'linux')
    @patch('subprocess.run')
    def test_double_enable(self, mock_run):
        """Тест повторного включения"""
        mock_run.return_value = MagicMock(returncode=0)
        
        proxy = SystemProxy()
        
        # Включаем первый раз
        result1 = proxy.enable("127.0.0.1", 10808)
        assert result1 == True
        
        # Включаем второй раз (должно сохранить оригинальные настройки)
        result2 = proxy.enable("127.0.0.1", 10809)
        assert result2 == True
    
    @patch('sys.platform', 'linux')
    @patch('subprocess.run')
    def test_disable_without_enable(self, mock_run):
        """Тест отключения без предварительного включения"""
        mock_run.return_value = MagicMock(returncode=0)
        
        proxy = SystemProxy()
        assert proxy.is_enabled == False
        
        # Отключаем (ничего не должно произойти)
        result = proxy.disable()
        
        # Должно вернуть True (ничего не делали)
        assert result == True


class TestSystemProxyEdgeCases:
    """Тесты граничных случаев"""
    
    @patch('sys.platform', 'linux')
    @patch('subprocess.run')
    def test_enable_with_different_ports(self, mock_run):
        """Тест включения с разными портами"""
        mock_run.return_value = MagicMock(returncode=0)
        
        proxy = SystemProxy()
        
        ports = [1080, 8080, 3128, 9999]
        
        for port in ports:
            result = proxy.enable("127.0.0.1", port)
            assert result == True
    
    @patch('sys.platform', 'linux')
    @patch('subprocess.run')
    def test_enable_with_localhost_variants(self, mock_run):
        """Тест включения с разными вариантами localhost"""
        mock_run.return_value = MagicMock(returncode=0)
        
        proxy = SystemProxy()
        
        hosts = ["127.0.0.1", "localhost", "0.0.0.0"]
        
        for host in hosts:
            result = proxy.enable(host, 10808)
            assert result == True
