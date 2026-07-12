#!/bin/bash
# Скрипт для подготовки структуры DEB пакета KengaCAD

# Создаем корневую директорию пакета
PKG_ROOT="kengacad-1.0.0"
mkdir -p "$PKG_ROOT/usr/bin"
mkdir -p "$PKG_ROOT/usr/share/applications"
mkdir -p "$PKG_ROOT/usr/share/icons"
mkdir -p "$PKG_ROOT/opt/kengacad"
mkdir -p "$PKG_ROOT/opt/kengacad/ui"
mkdir -p "$PKG_ROOT/opt/kengacad/engine"
mkdir -p "$PKG_ROOT/opt/kengacad/robot"
mkdir -p "$PKG_ROOT/opt/kengacad/cad"
mkdir -p "$PKG_ROOT/opt/kengacad/config"
mkdir -p "$PKG_ROOT/opt/kengacad/examples"
mkdir -p "$PKG_ROOT/opt/kengacad/assets"

# Копируем файлы приложения
cp -r ui/* "$PKG_ROOT/opt/kengacad/ui/"
cp -r engine/* "$PKG_ROOT/opt/kengacad/engine/"
cp -r robot/* "$PKG_ROOT/opt/kengacad/robot/"
cp -r cad/* "$PKG_ROOT/opt/kengacad/cad/"
cp -r config/* "$PKG_ROOT/opt/kengacad/config/"
cp -r examples/* "$PKG_ROOT/opt/kengacad/examples/"
cp main.py kengacad_app.py "$PKG_ROOT/opt/kengacad/"

# Копируем ресурсы
cp assets/logo.png "$PKG_ROOT/opt/kengacad/assets/"

# Создаем исполняемый скрипт
cat > "$PKG_ROOT/usr/bin/kengacad" << 'EOF'
#!/bin/bash
cd /opt/kengacad
python3 main.py "$@"
EOF

chmod +x "$PKG_ROOT/usr/bin/kengacad"

# Создаем desktop файл
cat > "$PKG_ROOT/usr/share/applications/kengacad.desktop" << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=KengaCAD
Comment=CAD-программа для настройки траекторий роботов
Exec=/usr/bin/kengacad
Icon=/opt/kengacad/assets/logo.png
Categories=Graphics;Engineering;
Terminal=false
StartupNotify=true
EOF

# Создаем DEBIAN директорию и control файл
mkdir -p "$PKG_ROOT/DEBIAN"

cat > "$PKG_ROOT/DEBIAN/control" << EOF
Package: kengacad
Version: 1.0.0
Section: graphics
Priority: optional
Architecture: amd64
Depends: python3, python3-pyqt5, python3-websockets, python3-ezdxf, python3-numpy
Maintainer: KengaCAD Team <info@kengacad.example.com>
Description: CAD-программа для настройки траекторий роботов
 KengaCAD - это CAD-программа, максимально похожая на AutoCAD,
 предназначенная для настройки траекторий роботов нанесения мастики
 на кузов автомобиля с использованием движка Kenga.
EOF

echo "Структура DEB пакета создана в директории $PKG_ROOT"
echo "Для создания пакета выполните: dpkg-deb --build $PKG_ROOT"