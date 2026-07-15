# Linux на заводе: Astra Linux и Ред ОС

На кузовном цеху у вас **не Windows**, а отечественный Linux — это нормально.  
Основной продукт для такого ноутбука — **portable PyQt** из Releases (не WPF Setup.exe).

## Что скачать

С [Releases](https://github.com/GermannM3/KengaCad/releases/latest):

```
KengaCAD_Professional_*_linux-x64_portable.tar.gz
```

AppImage на Astra/Ред часто ломается из‑за FUSE и политик — **берите tar.gz**.

## Установка на Astra / Ред ОС

```bash
tar xzf KengaCAD_Professional_2.4.0_linux-x64_portable.tar.gz
cd распакованная_папка   # или создайте каталог и распакуйте туда
chmod +x install.sh run.sh
./install.sh
./run.sh
```

### Если `install.sh` ругается на пакеты

**Astra Linux (ординарный/смоленск, типовой набор):**

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip \
  libxkbcommon-x11-0 libxcb-cursor0 libgl1 libglib2.0-0
```

**Ред ОС (RED OS):**

```bash
sudo dnf install -y python3 python3-pip python3-virtualenv \
  libxkbcommon libxcb libglvnd-glx 2>/dev/null \
  || sudo yum install -y python3 python3-pip
```

Потом снова `./install.sh`.

Сеть: исходящий **TCP 21** (FTP на шкаф) и при необходимости **29999** (UR) не должны резаться локальным firewall.

## Как работать в цехе с Linux-ноутбука

1. Ноутбук в **той же LAN**, что и шкаф робота (KUKA/ABB/Fanuc…).
2. В KengaCAD слева док **«Цех (Linux)»**.
3. IP контроллера → **Проверить**.
4. Нарисуйте траекторию (полилиния) / точки.
5. **Впрыск ВКЛ** → участок шва → **Впрыск ВЫКЛ** (или только ВКЛ — ВЫКЛ поставится в конце).
6. **Экспорт+** → файл `.src` / `.mod` / `.ls`.
7. **Залить FTP** на контроллер.
8. Пуск — с пульта / безопасности ячейки.

Подробнее: [SHOP_FLOOR.md](SHOP_FLOOR.md).

## Чего нет на Linux (пока)

- Полный WPF-клиент Windows (лента Professional 1:1) — только на Windows.
- Нативная Avalonia‑сборка — в планах; сейчас PyQt `_legacy` — рабочий заводской клиент.

Windows Setup по-прежнему удобен для офиса/домашней подготовки. На линии — **portable Linux**.
