#!/bin/bash
# Скрипт для подготовки RPM пакета KengaCAD

set -e  # Выход при ошибке

echo "Подготовка RPM пакета для KengaCAD..."

# Создаем структуру RPM пакета
RPM_DIR="installers/rpm_package"
mkdir -p "$RPM_DIR/BUILD"
mkdir -p "$RPM_DIR/SOURCES"
mkdir -p "$RPM_DIR/SPECS"
mkdir -p "$RPM_DIR/RPMS"
mkdir -p "$RPM_DIR/SRPMS"

# Создаем SPEC файл
SPEC_FILE="$RPM_DIR/SPECS/kengacad.spec"
cat > "$SPEC_FILE" << 'EOF'
Name: kengacad
Version: 1.0.0
Release: 1
Summary: CAD-программа для настройки траекторий роботов
License: MIT
Group: Applications/Graphics
URL: https://github.com/GermannM3/KengaCAD
BuildArch: x86_64

Requires: python3, PyQt6, python3-websockets, python3-ezdxf

%description
KengaCAD - это CAD-программа, максимально похожая на AutoCAD,
предназначенная для настройки траекторий роботов нанесения мастики
на кузов автомобиля с использованием движка Kenga через WebSocket API.

%prep
# Подготовка не требуется для бинарного пакета

%build
# Сборка не требуется для бинарного пакета

%install
mkdir -p %{buildroot}/opt/kengacad
mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}/usr/share/applications

# Создаем скрипт запуска
cat > %{buildroot}/opt/kengacad/kengacad << 'SCRIPT_EOF'
#!/bin/bash
# Запуск KengaCAD
echo "KengaCAD для Linux"
SCRIPT_EOF

chmod +x %{buildroot}/opt/kengacad/kengacad

# Создаем symlink
ln -sf /opt/kengacad/kengacad %{buildroot}/usr/bin/kengacad

# Создаем desktop файл
cat > %{buildroot}/usr/share/applications/kengacad.desktop << 'DESKTOP_EOF'
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
DESKTOP_EOF

%files
/opt/kengacad/*
/usr/bin/kengacad
/usr/share/applications/kengacad.desktop

%changelog
* Mon Jan 28 2026 KengaCAD Team <info@kengacad.example.com> - 1.0.0-1
- Initial package
EOF

echo "SPEC файл создан: $SPEC_FILE"
echo ""
echo "Для завершения создания пакета выполните в Linux с установленным rpm-build:"
echo "  rpmbuild -bb --define '_topdir $(pwd)/installers/rpm_package' $SPEC_FILE"
echo ""
echo "Результат будет в: ~/rpmbuild/RPMS/x86_64/ или installers/rpm_package/RPMS/"