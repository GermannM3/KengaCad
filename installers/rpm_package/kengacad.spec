Name: kengacad
Version: 1.0.0
Release: 1
Summary: CAD-программа для настройки траекторий роботов
License: MIT
Group: Applications/Graphics
URL: https://github.com/GermannM3/KengaCAD
BuildArch: x86_64

Requires: python3, PyQt5, python3-websockets, python3-ezdxf

%description
KengaCAD - это CAD-программа, максимально похожая на AutoCAD,
предназначенная для настройки траекторий роботов нанесения мастики
на кузов автомобиля с использованием движка Kenga.

%files
/opt/kengacad/*
/usr/bin/kengacad
/usr/share/applications/kengacad.desktop
/usr/share/icons/kengacad.png

%prep
# Подготовка не требуется для бинарного пакета

%build
# Сборка не требуется для бинарного пакета

%install
mkdir -p %{buildroot}/opt/kengacad
mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}/usr/share/applications
mkdir -p %{buildroot}/usr/share/icons

# Копируем файлы приложения
cp -r dist/KengaCAD/* %{buildroot}/opt/kengacad/

# Создаем скрипт запуска
echo '#!/bin/bash' > %{buildroot}/usr/bin/kengacad
echo 'exec python3 /opt/kengacad/KengaCAD "$@"' >> %{buildroot}/usr/bin/kengacad

# Создаем desktop файл
cat > %{buildroot}/usr/share/applications/kengacad.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=KengaCAD
Comment=CAD-программа для настройки траекторий роботов
Exec=/usr/bin/kengacad
Icon=kengacad
Categories=Graphics;
Terminal=false
EOF

# Делаем скрипт исполняемым
chmod +x %{buildroot}/usr/bin/kengcad

%changelog
* Mon Jan 28 2026 KengaCAD Team <info@kengacad.example.com> - 1.0.0-1
- Initial package
