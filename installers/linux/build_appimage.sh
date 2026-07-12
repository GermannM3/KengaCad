#!/usr/bin/env bash
# KengaCAD Cross-Platform (PyQt legacy) — AppImage для Linux x64
# Запускать на Linux (Ubuntu 22.04+). С Windows: WSL2 или CI.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION="${KENGACAD_VERSION:-2.1.0}"
OUT="$ROOT/installers/Output"
BUILD="$OUT/build-appimage"
APPDIR="$BUILD/KengaCAD.AppDir"
LEGACY="$ROOT/_legacy"
STAGING="$BUILD/staging"

echo "[AppImage] KengaCAD $VERSION — Linux x64"

rm -rf "$BUILD"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/applications" "$APPDIR/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$STAGING"

# Синхронизация конфигов из C# ветки (robots, postprocessors, templates)
rsync -a --delete "$ROOT/KengaCAD/config/" "$STAGING/config/"
rsync -a --exclude='.venv*' --exclude='__pycache__' --exclude='build' --exclude='dist' \
  "$LEGACY/" "$STAGING/"

cd "$STAGING"

if [[ ! -d .venv-build ]]; then
  python3 -m venv .venv-build
fi
# shellcheck disable=SC1091
source .venv-build/bin/activate
pip install -q --upgrade pip wheel
pip install -q -r requirements.txt pyinstaller opcua 2>/dev/null || pip install -q -r requirements.txt pyinstaller

# PyInstaller one-folder (linuxdeploy требует каталог)
pyinstaller --noconfirm --clean --windowed --name KengaCAD \
  --add-data "config:config" \
  --add-data "assets:assets" \
  --hidden-import PyQt5 \
  --hidden-import pyqtribbon \
  main.py

PYDIST="$STAGING/dist/KengaCAD"
if [[ ! -d "$PYDIST" ]]; then
  echo "Ошибка: PyInstaller не создал dist/KengaCAD"
  exit 1
fi

cp -a "$PYDIST/." "$APPDIR/usr/bin/"

cat > "$APPDIR/AppRun" << 'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "$0")")"
export LD_LIBRARY_PATH="$HERE/usr/bin:$LD_LIBRARY_PATH"
exec "$HERE/usr/bin/KengaCAD" "$@"
EOF
chmod +x "$APPDIR/AppRun"

cat > "$APPDIR/kengacad.desktop" << EOF
[Desktop Entry]
Type=Application
Name=KengaCAD
Comment=CAD/CAM для промышленных роботов
Exec=KengaCAD
Icon=kengacad
Categories=Engineering;Graphics;
Terminal=false
EOF

cp "$STAGING/assets/logo.png" "$APPDIR/kengacad.png" 2>/dev/null || true
cp "$APPDIR/kengacad.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/kengacad.png" 2>/dev/null || true

LINUXDEPLOY="$BUILD/linuxdeploy-x86_64.AppImage"
APPIMAGETOOL="$BUILD/appimagetool-x86_64.AppImage"

if [[ ! -f "$LINUXDEPLOY" ]]; then
  curl -fsSL -o "$LINUXDEPLOY" \
    "https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage"
  chmod +x "$LINUXDEPLOY"
fi
if [[ ! -f "$APPIMAGETOOL" ]]; then
  curl -fsSL -o "$APPIMAGETOOL" \
    "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
  chmod +x "$APPIMAGETOOL"
fi

export ARCH=x86_64
export VERSION="$VERSION"
export APPIMAGE_EXTRACT_AND_RUN=1

"$LINUXDEPLOY" --appdir "$APPDIR" --desktop-file "$APPDIR/kengacad.desktop" --icon-file "$APPDIR/kengacad.png" \
  --output appimage --plugin qt 2>/dev/null || \
"$APPIMAGETOOL" "$APPDIR" "$OUT/KengaCAD_Professional_${VERSION}_linux-x64.AppImage"

# linuxdeploy может положить AppImage в BUILD
if [[ -f "$BUILD/KengaCAD-"*"-x86_64.AppImage" ]]; then
  mv "$BUILD"/KengaCAD-*-x86_64.AppImage "$OUT/KengaCAD_Professional_${VERSION}_linux-x64.AppImage"
fi

if [[ -f "$OUT/KengaCAD_Professional_${VERSION}_linux-x64.AppImage" ]]; then
  chmod +x "$OUT/KengaCAD_Professional_${VERSION}_linux-x64.AppImage"
  sha256sum "$OUT/KengaCAD_Professional_${VERSION}_linux-x64.AppImage" > "$OUT/KengaCAD_Professional_${VERSION}_linux-x64.AppImage.sha256"
  echo "[AppImage] Готово: $OUT/KengaCAD_Professional_${VERSION}_linux-x64.AppImage"
else
  echo "[AppImage] appimagetool не создал файл — см. лог выше"
  exit 1
fi
