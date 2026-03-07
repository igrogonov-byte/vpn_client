#!/usr/bin/env python3
"""
Скрипт для сборки приложения в исполняемый файл
Использование: python build.py
"""
import os
import sys
import subprocess
from pathlib import Path

def build():
    """Сборка приложения"""
    print("=== Сборка VPN Client ===\n")
    
    # Проверка зависимостей
    print("Проверка зависимостей...")
    try:
        import PyInstaller
    except ImportError:
        print("Установка PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    
    # Определение платформы
    platform = sys.platform
    print(f"Платформа: {platform}")
    
    # Пути
    root_dir = Path(__file__).parent
    spec_dir = root_dir / "build"
    dist_dir = root_dir / "dist"
    
    # Создание директорий
    spec_dir.mkdir(exist_ok=True)
    dist_dir.mkdir(exist_ok=True)
    
    # Команда для сборки
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "VPNClient",
        "--onefile",
        "--windowed",
        "--clean",
        "--distpath", str(dist_dir),
        "--workpath", str(spec_dir / "build"),
        "--specpath", str(spec_dir),
    ]
    
    # Иконка (если есть)
    icon_path = root_dir / "assets" / "icon.ico" if platform == "win32" else root_dir / "assets" / "icon.png"
    if icon_path.exists():
        cmd.extend(["--icon", str(icon_path)])

    # Добавление данных (binaries)
    binaries_dir = root_dir / "vpn_client" / "binaries"
    if binaries_dir.exists() and any(binaries_dir.iterdir()):
        cmd.extend(["--add-data", f"{binaries_dir}{os.pathsep}vpn_client/binaries"])
    
    # Точка входа
    cmd.append(str(root_dir / "vpn_client" / "main.py"))
    
    print(f"Команда: {' '.join(cmd)}\n")
    print("Запуск сборки...")
    
    try:
        subprocess.run(cmd, check=True)
        print("\n=== Сборка завершена! ===")
        print(f"Исполняемый файл: {dist_dir / 'VPNClient' / ('VPNClient.exe' if platform == 'win32' else 'VPNClient')}")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"\n=== Ошибка сборки: {e} ===")
        return 1


if __name__ == "__main__":
    sys.exit(build())
