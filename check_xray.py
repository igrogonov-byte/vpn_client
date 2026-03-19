#!/usr/bin/env python3
"""
Проверка версии Xray-core
"""
import subprocess
import sys
from pathlib import Path

# Добавляем корень проекта в path
script_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(script_dir))

from vpn_client.core.xray_manager import XrayManager

binaries_dir = script_dir / 'vpn_client' / 'binaries'
xray_path = binaries_dir / 'xray'

if xray_path.exists():
    try:
        result = subprocess.run([str(xray_path), 'version'], capture_output=True, text=True, timeout=5)
        print("Xray версия:")
        print(result.stdout)
        print(result.stderr)
    except Exception as e:
        print(f"Ошибка: {e}")
else:
    print(f"Xray не найден: {xray_path}")
