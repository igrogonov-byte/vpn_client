"""
Утилиты безопасности
"""
import os
import secrets
import hashlib


def secure_clear(data: bytearray) -> None:
    """Безопасная очистка чувствительных данных"""
    for i in range(len(data)):
        data[i] = 0
    # Перезапись случайными данными
    for i in range(len(data)):
        data[i] = secrets.randbelow(256)
    for i in range(len(data)):
        data[i] = 0


def hash_uuid(uuid: str) -> str:
    """Хеширование UUID для безопасного хранения"""
    return hashlib.sha256(uuid.encode()).hexdigest()[:16]


def secure_compare(a: str, b: str) -> bool:
    """Безопасное сравнение строк (защита от timing attack)"""
    return secrets.compare_digest(a, b)


class SecureString:
    """Класс для безопасного хранения чувствительных строк"""
    
    def __init__(self, value: str):
        self._data = bytearray(value.encode('utf-8'))
    
    def get(self) -> str:
        return self._data.decode('utf-8')
    
    def clear(self):
        secure_clear(self._data)
    
    def __del__(self):
        self.clear()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.clear()
