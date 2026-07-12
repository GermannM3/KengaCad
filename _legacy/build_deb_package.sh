#!/bin/bash
# Скрипт для создания DEB пакета KengaCAD

set -e  # Выход при ошибке

echo "Создание DEB пакета для KengaCAD..."

# Проверяем, что исполняемый файл существует
if [ ! -f "dist/KengaCAD.exe" ]; then
    echo "Ошибка: dist/KengaCAD.exe не найден. Сначала создайте исполняемый файл с помощью PyInstaller."
    exit 1
fi

# Создаем структуру DEB пакета
DEB_PACKAGE="installers/deb_package/kengacad-1.0.0"
mkdir -p "$DEB_PACKAGE/DEBIAN"
mkdir -p "$DEB_PACKAGE/opt/kengacad"
mkdir -p "$DEB_PACKAGE/usr/bin"
mkdir -p "$DEB_PACKAGE/usr/share/applications"
mkdir -p "$DEB_PACKAGE/usr/share/icons/hicolor/256x256/apps"

# Копируем исполняемый файл (для Linux будем использовать другой подход)
# Создаем структуру для Linux версии
echo "#!/bin/bash" > "$DEB_PACKAGE/opt/kengacad/kengacad"
echo "# Запуск KengaCAD" >> "$DEB_PACKAGE/opt/kengacad/kengacad"
echo "# В реальной версии будет исполняемый файл для Linux" >> "$DEB_PACKAGE/opt/kengacad/kengacad"
echo "echo 'KengaCAD для Linux'" >> "$DEB_PACKAGE/opt/kengacad/kengacad"
chmod +x "$DEB_PACKAGE/opt/kengacad/kengacad"

# Создаем symlink
ln -sf "/opt/kengacad/kengacad" "$DEB_PACKAGE/usr/bin/kengacad"

# Создаем desktop файл
cat > "$DEB_PACKAGE/usr/share/applications/kengacad.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=KengaCAD
Comment=CAD-программа для настройки траекторий роботов
Exec=/usr/bin/kengacad
Icon=kengacad
Categories=Graphics;Engineering;
Terminal=false
StartupNotify=true
EOF

# Создаем control файл
cat > "$DEB_PACKAGE/DEBIAN/control" << EOF
Package: kengacad
Version: 1.0.0
Section: graphics
Priority: optional
Architecture: amd64
Depends: python3, python3-pyqt6, python3-websockets, python3-ezdxf
Maintainer: KengaCAD Team <info@kengacad.example.com>
Description: CAD-программа для настройки траекторий роботов
 KengaCAD - это CAD-программа, максимально похожая на AutoCAD,
 предназначенная для настройки траекторий роботов нанесения мастики
 на кузов автомобиля с использованием движка Kenga.
EOF

echo "Структура DEB пакета создана в: $DEB_PACKAGE"
echo ""
echo "Для завершения создания пакета выполните в Linux:"
echo "  dpkg-deb --build $DEB_PACKAGE"
echo ""
echo "Результат будет файл: installers/deb_package/kengacad-1.0.0.deb"