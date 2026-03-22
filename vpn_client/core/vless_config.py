"""
Генератор конфигурации VLESS Reality с транспортом xhttp
"""
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def create_vless_reality_xhttp(
    address: str,
    port: int,
    uuid: str,
    server_name: str,
    public_key: str,
    short_id: str,
    spider_x: str = "/",
    local_socks_port: int = 10808,
    local_http_port: int = 10809,
    flow: str = "",
    transport: str = "xhttp",
    grpc_service_name: str = "grpc",
    grpc_multi_mode: bool = False
) -> dict:
    """
    Создание конфигурации VLESS Reality

    Args:
        address: Адрес сервера
        port: Порт сервера
        uuid: UUID пользователя
        server_name: SNI (домен сервера)
        public_key: Публичный ключ Reality
        short_id: Short ID для Reality
        spider_x: Путь для spider-remix
        local_socks_port: Локальный SOCKS порт
        local_http_port: Локальный HTTP порт
        flow: Поток (xtls-rprx-vision или пустой)
        transport: Транспорт (xhttp, grpc, tcp)
        grpc_service_name: Имя сервиса GRPC
        grpc_multi_mode: Включить multiMode для GRPC
    """
    
    # Нормализация short_id (должен быть hex)
    if short_id:
        short_id = short_id.replace(" ", "").replace("-", "")
    
    # Reality настройки
    reality_settings = {
        "fingerprint": "chrome",
        "serverName": server_name,
        "publicKey": public_key,
        "shortId": short_id,
        "spiderX": spider_x
    }
    
    # Настройки транспорта
    stream_settings = {
        "network": transport,
        "security": "reality",
        "realitySettings": reality_settings
    }
    
    # Добавляем настройки транспорта
    if transport in ("xhttp", "http"):
        stream_settings["xhttpSettings"] = {
            "mode": "auto",
            "host": server_name,
            "path": "/"
        }
    elif transport == "grpc":
        stream_settings["grpcSettings"] = {
            "serviceName": grpc_service_name if grpc_service_name else "grpc",
            "multiMode": grpc_multi_mode
        }

    # Outbound (исходящее подключение)
    outbound = {
        "protocol": "vless",
        "settings": {
            "vnext": [
                {
                    "address": address,
                    "port": port,
                    "users": [
                        {
                            "id": uuid,
                            "flow": flow,
                            "encryption": "none",
                            "level": 8
                        }
                    ]
                }
            ]
        },
        "streamSettings": stream_settings,
        "tag": "proxy"
    }
    
    # Полная конфигурация
    full_config = {
        "log": {
            "loglevel": "warning",
            "access": "",
            "error": ""
        },
        "api": {
            "tag": "api",
            "services": [
                "HandlerService",
                "StatsService"
            ]
        },
        "stats": {},  # Включить статистику
        "dns": {
            "servers": [
                "1.1.1.1",
                "8.8.8.8"
            ]
        },
        "inbounds": [
            {
                "tag": "socks",
                "port": local_socks_port,
                "listen": "127.0.0.1",
                "protocol": "socks",
                "settings": {
                    "auth": "noauth",
                    "udp": True,
                    "address": "127.0.0.1"
                },
                "sniffing": {
                    "enabled": True,
                    "destOverride": ["http", "tls", "quic"],
                    "routeOnly": True
                }
            },
            {
                "tag": "http",
                "port": local_http_port,
                "listen": "127.0.0.1",
                "protocol": "http",
                "settings": {
                    "allowTransparent": False
                }
            },
            {
                "tag": "api",
                "port": 18888,
                "listen": "127.0.0.1",
                "protocol": "dokodemo-door",
                "settings": {
                    "address": "127.0.0.1"
                }
            }
        ],
        "outbounds": [
            outbound,
            {
                "protocol": "freedom",
                "tag": "direct"
            },
            {
                "protocol": "blackhole",
                "tag": "block"
            },
            {
                "protocol": "blackhole",
                "tag": "api"
            }
        ],
        "routing": {
            "domainStrategy": "AsIs",
            "rules": [
                {
                    "type": "field",
                    "inboundTag": ["api"],
                    "outboundTag": "api"
                },
                {
                    "type": "field",
                    "ip": ["geoip:private"],
                    "outboundTag": "direct"
                },
                {
                    "type": "field",
                    "network": "tcp,udp",
                    "outboundTag": "proxy"
                }
            ]
        }
    }
    
    return full_config


def save_config(config: dict, path: str) -> bool:
    """Сохранение конфигурации в файл"""
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        logger.info(f"Конфигурация сохранена: {path}")
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения конфигурации: {e}")
        return False


def load_config(path: str) -> Optional[dict]:
    """Загрузка конфигурации из файла"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки конфигурации: {e}")
        return None


def parse_vless_link(link: str) -> Optional[Dict[str, Any]]:
    """
    Парсинг VLESS ссылки

    Формат: vless://uuid@address:port?params
    """
    from urllib.parse import urlparse, parse_qs

    try:
        if not link.startswith("vless://"):
            return None

        parsed = urlparse(link)

        uuid = parsed.username or parsed.netloc.split('@')[0]
        netloc = parsed.netloc.split('@')[-1] if '@' in parsed.netloc else parsed.netloc
        address_port = netloc.split('?')[0]
        address, port = address_port.rsplit(':', 1)

        params = parse_qs(parsed.query)

        # Определение транспорта
        transport_type = params.get("type", ["tcp"])[0]
        
        result = {
            "uuid": uuid,
            "address": address,
            "port": int(port),
            "type": transport_type,
            "security": params.get("security", ["reality"])[0],
            "sni": params.get("sni", [""])[0],
            "fp": params.get("fp", ["chrome"])[0],
            "pbk": params.get("pbk", [""])[0],
            "sid": params.get("sid", [""])[0],
            "flow": params.get("flow", [""])[0],
            "path": params.get("path", ["/"])[0],
            "host": params.get("host", [""])[0],
            "serviceName": params.get("serviceName", ["grpc"])[0],
            "mode": params.get("mode", ["gun"])[0],  # gun или multi
        }

        return result

    except Exception as e:
        logger.error(f"Ошибка парсинга VLESS ссылки: {e}")
        return None
