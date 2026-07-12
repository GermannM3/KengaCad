#!/usr/bin/env bash
# Portable PyQt bundle for Linux/macOS (configs from KengaCAD Professional).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="${1:-2.1.0}"
TARGET="${2:-linux}"   # linux | macos
OUT_DIR="${3:-$ROOT/installers/Output}"

STAGING="$(mktemp -d)"
trap 'rm -rf "$STAGING"' EXIT

rsync -a --delete "$ROOT/KengaCAD/config/" "$STAGING/config/"
rsync -a \
  --exclude='.venv' --exclude='.venv-build' --exclude='__pycache__' \
  --exclude='build' --exclude='dist' --exclude='*.pyc' \
  "$ROOT/_legacy/" "$STAGING/"

cat > "$STAGING/install.sh" << 'EOF'
#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m venv .venv
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "Готово. Запуск: ./run.sh"
EOF

cat > "$STAGING/run.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
if [[ ! -d .venv ]]; then
  echo "Сначала выполните: chmod +x install.sh && ./install.sh"
  exit 1
fi
source .venv/bin/activate
exec python3 main.py "$@"
EOF

chmod +x "$STAGING/install.sh" "$STAGING/run.sh"

if [[ "$TARGET" == "macos" ]]; then
  cat > "$STAGING/KengaCAD.command" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
[[ -d .venv ]] || ./install.sh
source .venv/bin/activate
exec python3 main.py "$@"
EOF
  chmod +x "$STAGING/KengaCAD.command"
  ARCHIVE="$OUT_DIR/KengaCAD_Professional_${VERSION}_macos_portable.tar.gz"
else
  ARCHIVE="$OUT_DIR/KengaCAD_Professional_${VERSION}_linux-x64_portable.tar.gz"
fi

mkdir -p "$OUT_DIR"
tar -czf "$ARCHIVE" -C "$STAGING" .
echo "Created: $ARCHIVE"
