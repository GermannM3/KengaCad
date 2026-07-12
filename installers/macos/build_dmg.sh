#!/usr/bin/env bash
# KengaCAD Cross-Platform — DMG для macOS (x64/arm64)
# Запускать на macOS с Xcode Command Line Tools.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION="${KENGACAD_VERSION:-2.1.0}"
OUT="$ROOT/installers/Output"
BUILD="$OUT/build-macos"
APP="$BUILD/KengaCAD.app"
LEGACY="$ROOT/_legacy"
STAGING="$BUILD/staging"

echo "[DMG] KengaCAD $VERSION — macOS"

rm -rf "$BUILD"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources" "$STAGING"

rsync -a --delete "$ROOT/KengaCAD/config/" "$STAGING/config/"
rsync -a --exclude='.venv*' --exclude='__pycache__' --exclude='build' --exclude='dist' \
  "$LEGACY/" "$STAGING/"

cd "$STAGING"
python3 -m venv .venv-build
# shellcheck disable=SC1091
source .venv-build/bin/activate
pip install -q --upgrade pip wheel
pip install -q -r requirements.txt pyinstaller py2app 2>/dev/null || pip install -q -r requirements.txt pyinstaller

pyinstaller --noconfirm --clean --windowed --name KengaCAD \
  --add-data "config:config" \
  --add-data "assets:assets" \
  main.py

PYDIST="$STAGING/dist/KengaCAD.app"
if [[ -d "$PYDIST" ]]; then
  cp -a "$PYDIST/." "$APP/"
else
  cp -a "$STAGING/dist/KengaCAD/." "$APP/Contents/MacOS/"
  cat > "$APP/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleExecutable</key><string>KengaCAD</string>
  <key>CFBundleIdentifier</key><string>com.kengacad.professional</string>
  <key>CFBundleName</key><string>KengaCAD</string>
  <key>CFBundleVersion</key><string>${VERSION}</string>
  <key>CFBundleShortVersionString</key><string>${VERSION}</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
EOF
fi

if [[ -f "$STAGING/assets/logo.png" ]]; then
  cp "$STAGING/assets/logo.png" "$APP/Contents/Resources/logo.png"
fi

DMG="$OUT/KengaCAD_Professional_${VERSION}_macos.dmg"
rm -f "$DMG"
hdiutil create -volname "KengaCAD Professional" -srcfolder "$APP" -ov -format UDZO "$DMG"

shasum -a 256 "$DMG" > "$DMG.sha256"
echo "[DMG] Готово: $DMG"
