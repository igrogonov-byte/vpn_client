#!/usr/bin/env python3
"""
Тест генерации конфигурации VLESS Reality xhttp
"""
import sys
import json
sys.path.insert(0, '/home/arc/VS/2222/vpn_')

from vpn_client.core.vless_config import create_vless_reality_xhttp

# Тестовые данные
config = create_vless_reality_xhttp(
    address="example.com",
    port=443,
    uuid="00000000-0000-0000-0000-000000000000",
    server_name="example.com",
    public_key="test_public_key",
    short_id="abcd1234",
    flow="xtls-rprx-vision",
    local_socks_port=10808,
    local_http_port=10809
)

print(json.dumps(config, indent=2, ensure_ascii=False))
