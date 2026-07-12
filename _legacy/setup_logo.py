"""
Скрипт для установки настоящего логотипа KengaCAD
"""
import os
import shutil
from pathlib import Path


def setup_logo():
    """Установка настоящего логотипа"""
    print("Установка логотипа KengaCAD...")
    
    # Путь к папке с ресурсами
    assets_dir = Path("assets")
    assets_dir.mkdir(exist_ok=True)
    
    # Путь к файлу логотипа
    logo_path = assets_dir / "logo.png"
    
    print(f"Для установки настоящего логотипа:")
    print(f"1. Подготовьте файл логотипа в формате PNG")
    print(f"2. Убедитесь, что он имеет размер 256x256 или 512x512 пикселей")
    print(f"3. Переименуйте его в 'logo.png'")
    print(f"4. Скопируйте в папку: {assets_dir.absolute()}")
    print(f"5. Замените существующий placeholder файл")
    
    if logo_path.exists():
        print(f"\nТекущий файл логотипа: {logo_path}")
        print(f"Размер файла: {logo_path.stat().st_size} байт")
    
    print(f"\nПосле замены placeholder файла, логотип будет отображаться:")
    print("- При запуске приложения KengaCAD")
    print("- В установщике Windows (если используется MSI с логотипом)")
    print("- Как значок приложения в меню 'Пуск' и на рабочем столе")


if __name__ == "__main__":
    setup_logo()