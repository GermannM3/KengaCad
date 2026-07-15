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
# KengaCAD portable — Astra Linux / Ред ОС / Ubuntu / Debian
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Нужен python3. Astra: sudo apt-get install -y python3 python3-venv python3-pip"
  echo "Ред ОС:  sudo dnf install -y python3 python3-pip"
  exit 1
fi

python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo ""
echo "Готово для Linux (Astra / Ред ОС тоже)."
echo "Запуск: ./run.sh"
echo "В программе откройте док «Цех (Linux)» — IP робота, впрыск, FTP."
EOF

cat > "$STAGING/run.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
if [[ ! -d .venv ]]; then
  echo "Сначала: chmod +x install.sh && ./install.sh"
  exit 1
fi
# shellcheck disable=SC1091
source .venv/bin/activate
exec python3 main.py "$@"
EOF

# Краткая памятка для заводского Linux
cat > "$STAGING/ASTRA_REDOS.txt" << 'EOF'
KengaCAD на Astra Linux / Ред ОС
================================
1) ./install.sh
2) ./run.sh
3) Док слева «Цех (Linux)»: IP контроллера → Проверить → Экспорт+ → Залить FTP
4) Если Qt/pip ошибки — см. docs/LINUX.md в репозитории GitHub
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
