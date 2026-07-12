"""Скрипт для генерации компонентов WiX из собранного приложения"""
import os
import uuid
from pathlib import Path

def generate_wix_components():
    """Генерация компонентов WiX для всех файлов в dist"""
    dist_dir = Path("dist") / "KengaCAD"
    
    if not dist_dir.exists():
        print("Папка dist/KengaCAD не найдена. Запустите сборку PyInstaller.")
        print("Выполните: python build_scripts/build_windows.py")
        return
    
    # Проверяем, существует ли Product.wxs
    product_wxs_path = Path("Product.wxs")
    if not product_wxs_path.exists():
        print("Файл Product.wxs не найден.")
        return
    
    with open(product_wxs_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Начинаем генерировать компоненты
    components_xml = []
    
    # Обходим все файлы и папки в dist/KengaCAD
    for root, dirs, files in os.walk(dist_dir):
        rel_root = Path(root).relative_to(dist_dir)
        
        for file in files:
            file_path = rel_root / file
            # Создаем уникальный ID для файла
            file_id = f"File_{str(file_path).replace(os.sep, '_').replace('.', '_').replace(' ', '_')}"
            src_path = f"dist\\\\KengaCAD\\\\{file_path}".replace(os.sep, "\\\\")
            
            comp_guid = str(uuid.uuid4()).upper()
            components_xml.append(f"""      <Component Id="{file_id}Comp" Guid="{{{comp_guid}}}" Win64="yes">
        <File Id="{file_id}" Source="{src_path}" KeyPath="yes" />
      </Component>""")
    
    # Создаем ComponentGroup с компонентами
    group_xml = """  <Fragment>
    <ComponentGroup Id="ProductComponents" Directory="INSTALLFOLDER">"""
    
    for comp_line in components_xml:
        indented_comp = "      " + "\n      ".join(comp_line.split("\n"))
        group_xml += "\n" + indented_comp
    
    group_xml += "\n    </ComponentGroup>\n  </Fragment>"
    
    # Заменяем секцию ComponentGroup в Product.wxs
    # Находим начало и конец секции
    start_marker = '  <Fragment>\n    <ComponentGroup Id="ProductComponents" Directory="INSTALLFOLDER">'
    end_marker = '    </ComponentGroup>\n  </Fragment>'
    
    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker, start_idx)
    
    if start_idx != -1 and end_idx != -1:
        end_idx += len(end_marker)
        new_content = content[:start_idx] + group_xml + content[end_idx:]
        
        with open(product_wxs_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"Компоненты WiX добавлены в {product_wxs_path}")
        print(f"Добавлено компонентов: {len(components_xml)}")
        print("Теперь можно выполнить компиляцию: candle.exe Product.wxs -out Product.wixobj")
        print("И линковку: light.exe Product.wixobj -ext WixUIExtension -ext WixUtilExtension -out KengaCAD.msi")
    else:
        print("Не найдена секция ComponentGroup в Product.wxs для замены")
        # Если не найдена, выводим инструкции
        print("Добавьте вручную следующую секцию в Product.wxs:")
        print(group_xml)

if __name__ == "__main__":
    generate_wix_components()