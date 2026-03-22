"""
Тесты для модуля настроек (SettingsManager)
"""
import pytest
import json
from pathlib import Path
from vpn_client.utils.settings import SettingsManager


class TestSettingsManager:
    """Тесты класса SettingsManager"""
    
    def test_init_default_dir(self, temp_config_dir):
        """Тест инициализации с директорией по умолчанию"""
        manager = SettingsManager(str(temp_config_dir))
        
        assert manager.config_dir == temp_config_dir
        assert manager.settings_file == temp_config_dir / "settings.json"
    
    def test_init_creates_directory(self, temp_config_dir):
        """Тест что директория создаётся при инициализации"""
        new_dir = temp_config_dir / "new_config"
        manager = SettingsManager(str(new_dir))
        
        assert new_dir.exists()
        assert new_dir.is_dir()
    
    def test_save_and_load(self, temp_config_dir):
        """Тест сохранения и загрузки настроек"""
        manager = SettingsManager(str(temp_config_dir))
        
        test_settings = {
            "theme": "dark",
            "language": "ru",
            "auto_start": True
        }
        
        # Сохраняем
        result = manager.save(test_settings)
        assert result == True
        assert manager.settings_file.exists()
        
        # Загружаем
        loaded = manager.load()
        assert loaded == test_settings
    
    def test_load_nonexistent_file(self, temp_config_dir):
        """Тест загрузки из несуществующего файла"""
        manager = SettingsManager(str(temp_config_dir))
        
        loaded = manager.load()
        assert loaded == {}
    
    def test_save_last_config(self, temp_config_dir):
        """Тест сохранения последней конфигурации"""
        manager = SettingsManager(str(temp_config_dir))
        
        config = {
            "address": "example.com",
            "port": 443,
            "uuid": "test-uuid"
        }
        
        result = manager.save_last_config(config)
        assert result == True
        
        # Проверяем что сохранено в settings.json
        with open(manager.settings_file, 'r') as f:
            data = json.load(f)
        
        assert "last_config" in data
        assert data["last_config"]["address"] == "example.com"
    
    def test_get_last_config(self, temp_config_dir):
        """Тест загрузки последней конфигурации"""
        manager = SettingsManager(str(temp_config_dir))
        
        # Сначала сохраняем
        config = {"address": "test.com", "port": 8080}
        manager.save_last_config(config)
        
        # Загружаем
        loaded = manager.get_last_config()
        assert loaded == config
    
    def test_get_last_config_empty(self, temp_config_dir):
        """Тест загрузки когда нет сохранённой конфигурации"""
        manager = SettingsManager(str(temp_config_dir))
        
        loaded = manager.get_last_config()
        assert loaded is None
    
    def test_save_profile(self, temp_config_dir):
        """Тест сохранения профиля"""
        manager = SettingsManager(str(temp_config_dir))
        
        profile = {
            "address": "server1.com",
            "port": 443,
            "uuid": "uuid-1"
        }
        
        result = manager.save_profile("Profile1", profile)
        assert result == True
        
        # Проверяем что профиль сохранён в settings.json
        with open(manager.settings_file, 'r') as f:
            data = json.load(f)
        
        assert "profiles" in data
        assert "Profile1" in data["profiles"]
        assert data["profiles"]["Profile1"]["address"] == "server1.com"
    
    def test_load_profile(self, temp_config_dir):
        """Тест загрузки профиля"""
        manager = SettingsManager(str(temp_config_dir))
        
        # Сохраняем профиль
        profile = {"address": "server1.com", "port": 443}
        manager.save_profile("TestProfile", profile)
        
        # Загружаем
        loaded = manager.load_profile("TestProfile")
        assert loaded == profile
    
    def test_load_nonexistent_profile(self, temp_config_dir):
        """Тест загрузки несуществующего профиля"""
        manager = SettingsManager(str(temp_config_dir))
        
        loaded = manager.load_profile("NonExistent")
        assert loaded is None
    
    def test_get_profile_names(self, temp_config_dir):
        """Тест получения списка профилей"""
        manager = SettingsManager(str(temp_config_dir))
        
        # Создаём несколько профилей
        manager.save_profile("Profile1", {"address": "s1.com"})
        manager.save_profile("Profile2", {"address": "s2.com"})
        manager.save_profile("Profile3", {"address": "s3.com"})
        
        names = manager.get_profile_names()
        
        assert len(names) == 3
        assert "Profile1" in names
        assert "Profile2" in names
        assert "Profile3" in names
    
    def test_get_profile_names_empty(self, temp_config_dir):
        """Тест когда профилей нет"""
        manager = SettingsManager(str(temp_config_dir))
        
        names = manager.get_profile_names()
        assert names == []
    
    def test_delete_profile(self, temp_config_dir):
        """Тест удаления профиля"""
        manager = SettingsManager(str(temp_config_dir))
        
        # Сохраняем профиль
        manager.save_profile("ToDelete", {"address": "test.com"})
        
        # Удаляем
        result = manager.delete_profile("ToDelete")
        assert result == True
        
        # Проверяем что удалён
        profile_file = temp_config_dir / "profiles" / "ToDelete.json"
        assert not profile_file.exists()
    
    def test_delete_nonexistent_profile(self, temp_config_dir):
        """Тест удаления несуществующего профиля"""
        manager = SettingsManager(str(temp_config_dir))
        
        result = manager.delete_profile("NonExistent")
        assert result == False
    
    def test_save_window_geometry(self, temp_config_dir):
        """Тест сохранения геометрии окна"""
        manager = SettingsManager(str(temp_config_dir))
        
        result = manager.save_window_geometry(x=100, y=50, width=800, height=600)
        assert result == True
        
        # Проверяем в settings.json
        with open(manager.settings_file, 'r') as f:
            data = json.load(f)
        
        assert "window_geometry" in data
        assert data["window_geometry"]["width"] == 800
        assert data["window_geometry"]["height"] == 600
    
    def test_get_window_geometry(self, temp_config_dir):
        """Тест загрузки геометрии окна"""
        manager = SettingsManager(str(temp_config_dir))
        
        # Сохраняем
        manager.save_window_geometry(x=0, y=0, width=1024, height=768)
        
        # Загружаем
        loaded = manager.get_window_geometry()
        assert loaded == {"x": 0, "y": 0, "width": 1024, "height": 768}
    
    def test_get_window_geometry_empty(self, temp_config_dir):
        """Тест когда геометрия не сохранена"""
        manager = SettingsManager(str(temp_config_dir))
        
        loaded = manager.get_window_geometry()
        assert loaded is None
    
    def test_multiple_profiles_isolation(self, temp_config_dir):
        """Тест что профили изолированы друг от друга"""
        manager = SettingsManager(str(temp_config_dir))
        
        # Сохраняем два профиля с разными данными
        profile1 = {"address": "server1.com", "uuid": "uuid-1"}
        profile2 = {"address": "server2.com", "uuid": "uuid-2"}
        
        manager.save_profile("Profile1", profile1)
        manager.save_profile("Profile2", profile2)
        
        # Загружаем и проверяем
        loaded1 = manager.load_profile("Profile1")
        loaded2 = manager.load_profile("Profile2")
        
        assert loaded1["address"] == "server1.com"
        assert loaded2["address"] == "server2.com"
        assert loaded1["uuid"] != loaded2["uuid"]
