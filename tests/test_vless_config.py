"""
Тесты для модуля генерации конфигурации VLESS
"""
import pytest
import json
from pathlib import Path
from vpn_client.core.vless_config import (
    create_vless_reality_xhttp,
    parse_vless_link,
    save_config,
    load_config
)


class TestCreateVlessRealityXhttp:
    """Тесты функции create_vless_reality_xhttp"""
    
    def test_minimal_config(self, sample_vless_config):
        """Тест минимальной конфигурации"""
        config = create_vless_reality_xhttp(
            address=sample_vless_config["address"],
            port=sample_vless_config["port"],
            uuid=sample_vless_config["uuid"],
            server_name=sample_vless_config["sni"],
            public_key=sample_vless_config["public_key"],
            short_id=sample_vless_config["short_id"]
        )
        
        # Проверка структуры
        assert "log" in config
        assert "api" in config
        assert "inbounds" in config
        assert "outbounds" in config
        assert "routing" in config
        
        # Проверка логирования
        assert config["log"]["loglevel"] == "warning"
        
        # Проверка основного outbound
        assert config["outbounds"][0]["protocol"] == "vless"
        
        # Проверка inbound SOCKS
        socks_inbound = next(i for i in config["inbounds"] if i["tag"] == "socks")
        assert socks_inbound["protocol"] == "socks"
        assert socks_inbound["port"] == 10808
    
    def test_grpc_transport(self, sample_vless_config):
        """Тест транспорта GRPC"""
        config = create_vless_reality_xhttp(
            address=sample_vless_config["address"],
            port=sample_vless_config["port"],
            uuid=sample_vless_config["uuid"],
            server_name=sample_vless_config["sni"],
            public_key=sample_vless_config["public_key"],
            short_id=sample_vless_config["short_id"],
            transport="grpc",
            grpc_service_name="atom",
            grpc_multi_mode=True
        )
        
        stream_settings = config["outbounds"][0]["streamSettings"]
        assert stream_settings["network"] == "grpc"
        assert "grpcSettings" in stream_settings
        assert stream_settings["grpcSettings"]["serviceName"] == "atom"
        assert stream_settings["grpcSettings"]["multiMode"] == True
    
    def test_xhttp_transport(self, sample_vless_config):
        """Тест транспорта XHTTP"""
        config = create_vless_reality_xhttp(
            address=sample_vless_config["address"],
            port=sample_vless_config["port"],
            uuid=sample_vless_config["uuid"],
            server_name=sample_vless_config["sni"],
            public_key=sample_vless_config["public_key"],
            short_id=sample_vless_config["short_id"],
            transport="xhttp"
        )
        
        stream_settings = config["outbounds"][0]["streamSettings"]
        assert stream_settings["network"] == "xhttp"
        assert "xhttpSettings" in stream_settings
    
    def test_tcp_transport(self, sample_vless_config):
        """Тест транспорта TCP"""
        config = create_vless_reality_xhttp(
            address=sample_vless_config["address"],
            port=sample_vless_config["port"],
            uuid=sample_vless_config["uuid"],
            server_name=sample_vless_config["sni"],
            public_key=sample_vless_config["public_key"],
            short_id=sample_vless_config["short_id"],
            transport="tcp"
        )
        
        stream_settings = config["outbounds"][0]["streamSettings"]
        assert stream_settings["network"] == "tcp"
        # Для TCP нет дополнительных настроек
        assert "xhttpSettings" not in stream_settings
        assert "grpcSettings" not in stream_settings
    
    def test_custom_ports(self, sample_vless_config):
        """Тест кастомных портов"""
        config = create_vless_reality_xhttp(
            address=sample_vless_config["address"],
            port=sample_vless_config["port"],
            uuid=sample_vless_config["uuid"],
            server_name=sample_vless_config["sni"],
            public_key=sample_vless_config["public_key"],
            short_id=sample_vless_config["short_id"],
            local_socks_port=20808,
            local_http_port=20809
        )
        
        socks_inbound = next(i for i in config["inbounds"] if i["tag"] == "socks")
        http_inbound = next(i for i in config["inbounds"] if i["tag"] == "http")
        
        assert socks_inbound["port"] == 20808
        assert http_inbound["port"] == 20809
    
    def test_empty_short_id(self, sample_vless_config):
        """Тест с пустым short_id"""
        config = create_vless_reality_xhttp(
            address=sample_vless_config["address"],
            port=sample_vless_config["port"],
            uuid=sample_vless_config["uuid"],
            server_name=sample_vless_config["sni"],
            public_key=sample_vless_config["public_key"],
            short_id=""
        )
        
        reality_settings = config["outbounds"][0]["streamSettings"]["realitySettings"]
        assert reality_settings["shortId"] == ""
    
    def test_short_id_normalization(self, sample_vless_config):
        """Тест нормализации short_id"""
        config = create_vless_reality_xhttp(
            address=sample_vless_config["address"],
            port=sample_vless_config["port"],
            uuid=sample_vless_config["uuid"],
            server_name=sample_vless_config["sni"],
            public_key=sample_vless_config["public_key"],
            short_id="ab cd-12 34"  # С пробелами и дефисами
        )
        
        reality_settings = config["outbounds"][0]["streamSettings"]["realitySettings"]
        assert reality_settings["shortId"] == "abcd1234"
    
    def test_dns_servers(self, sample_vless_config):
        """Тест DNS серверов"""
        config = create_vless_reality_xhttp(
            address=sample_vless_config["address"],
            port=sample_vless_config["port"],
            uuid=sample_vless_config["uuid"],
            server_name=sample_vless_config["sni"],
            public_key=sample_vless_config["public_key"],
            short_id=sample_vless_config["short_id"]
        )
        
        assert "dns" in config
        assert "1.1.1.1" in config["dns"]["servers"]
        assert "8.8.8.8" in config["dns"]["servers"]


class TestParseVlessLink:
    """Тесты функции parse_vless_link"""
    
    def test_parse_grpc_link(self, sample_vless_link):
        """Тест парсинга GRPC ссылки"""
        result = parse_vless_link(sample_vless_link)
        
        assert result is not None
        assert result["uuid"] == "00000000-0000-0000-0000-000000000000"
        assert result["address"] == "example.com"
        assert result["port"] == 443
        assert result["type"] == "grpc"
        assert result["security"] == "reality"
        assert result["pbk"] == "test_key"
        assert result["sid"] == "abcd1234"
        assert result["serviceName"] == "grpc"
        assert result["mode"] == "gun"
    
    def test_parse_with_multi_mode(self):
        """Тест парсинга ссылки с mode=multi"""
        link = "vless://uuid@host:443?type=grpc&mode=multi&serviceName=atom"
        result = parse_vless_link(link)
        
        assert result["mode"] == "multi"
        assert result["serviceName"] == "atom"
    
    def test_parse_with_empty_service_name(self):
        """Тест парсинга ссылки с пустым serviceName"""
        link = "vless://uuid@host:443?type=grpc&serviceName="
        result = parse_vless_link(link)
        
        # Пустой serviceName заменяется на "grpc" по умолчанию
        assert result["serviceName"] == "grpc"
    
    def test_invalid_link_format(self):
        """Тест невалидного формата ссылки"""
        result = parse_vless_link("not-a-vless-link")
        assert result is None
    
    def test_non_vless_scheme(self):
        """Тест схемы отличной от vless://"""
        result = parse_vless_link("http://example.com")
        assert result is None
    
    def test_parse_with_flow(self):
        """Тест парсинга ссылки с flow"""
        link = "vless://uuid@host:443?flow=xtls-rprx-vision"
        result = parse_vless_link(link)
        
        assert result["flow"] == "xtls-rprx-vision"


class TestSaveLoadConfig:
    """Тесты сохранения и загрузки конфигурации"""
    
    def test_save_config(self, sample_vless_config, temp_config_dir):
        """Тест сохранения конфигурации"""
        config_path = temp_config_dir / "config.json"
        
        result = save_config(sample_vless_config, str(config_path))
        
        assert result == True
        assert config_path.exists()
        
        # Проверка содержимого
        with open(config_path, 'r') as f:
            saved = json.load(f)
        
        assert saved["address"] == sample_vless_config["address"]
        assert saved["port"] == sample_vless_config["port"]
    
    def test_load_config(self, sample_vless_config, temp_config_dir):
        """Тест загрузки конфигурации"""
        config_path = temp_config_dir / "config.json"
        
        # Сначала сохраняем
        save_config(sample_vless_config, str(config_path))
        
        # Затем загружаем
        loaded = load_config(str(config_path))
        
        assert loaded is not None
        assert loaded["address"] == sample_vless_config["address"]
        assert loaded["uuid"] == sample_vless_config["uuid"]
    
    def test_load_nonexistent_file(self, temp_config_dir):
        """Тест загрузки несуществующего файла"""
        config_path = temp_config_dir / "nonexistent.json"
        
        result = load_config(str(config_path))
        
        assert result is None
    
    def test_save_invalid_path(self, sample_vless_config):
        """Тест сохранения в недопустимый путь"""
        result = save_config(sample_vless_config, "/nonexistent/path/config.json")
        
        assert result == False
