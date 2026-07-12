# KengaCAD — Quick Start (Factory Demo)

## Portable Demo (no install)
1. Open `installers/portable/`.
1. Unzip `KengaCAD-<version>-portable.zip`.
1. Run `KengaCAD.exe` (Windows) or `KengaCAD` (Linux).

## Installers
Pick the installer for the OS:
- Windows: `KengaCAD-<version>-windows-<arch>-setup.exe`
- Linux (Debian/Ubuntu): `KengaCAD-<version>-linux-<arch>.deb`
- Linux (Fedora/RHEL): `KengaCAD-<version>-linux-<arch>.rpm`
- Linux (Arch): `KengaCAD-<version>-linux-<arch>.pkg.tar.zst`
- Linux (Universal): `KengaCAD-<version>-linux-<arch>.AppImage`

## First Run (Factory)
1. Start KengaCAD.
1. Engine starts automatically.
1. Create a POINT/LINE/CIRCLE and save a DXF.
1. Load a robot model and run SIMULATE.
1. Use View → Zoom/Snap for navigation.
1. Use Layers dock to switch active layer and toggle visibility.

## Release Bundle (what to hand over)
Provide the entire folder:
`release/<version>/`

It contains:
- Windows installer (`*-windows-*-setup.exe`)
- Windows MSI (`*.msi`)
- Linux DEB/RPM/Arch packages
- Linux AppImage
- Portable ZIP (`*-portable.zip`)
