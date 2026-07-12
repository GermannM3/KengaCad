@echo off
REM Финальный скрипт для подготовки установщиков KengaCAD к распространению

echo Подготовка установщиков KengaCAD к распространению...

REM Создаем директорию для финальных установщиков
if not exist "final_installers" mkdir final_installers

REM Копируем все установщики в одну директорию
echo Копирование установщиков...

REM Windows установщик (файл-заглушка, т.к. реальный установщик требует Inno Setup)
if exist "installers\kengacad_installer.iss" (
    echo Создание Windows установщика...
    echo Запустите "ISCC installers\kengacad_installer.iss" в Inno Setup Compiler > "final_installers\BUILD_WINDOWS_INSTRUCTIONS.txt"
    echo Установщик будет создан как KengaCAD_Setup.exe > "final_installers\BUILD_WINDOWS_INSTRUCTIONS.txt"
)

REM Linux DEB (файл-заглушка, т.к. реальный пакет создается в Linux)
if exist "installers\deb_package" (
    echo Создание Linux DEB пакета...
    echo Запустите "dpkg-deb --build installers\deb_package\kengacad-1.0.0" в Linux > "final_installers\BUILD_LINUX_DEB_INSTRUCTIONS.txt"
    echo Установщик будет создан как kengacad-1.0.0.deb > "final_installers\BUILD_LINUX_DEB_INSTRUCTIONS.txt"
)

REM Linux RPM (файл-заглушка, т.к. реальный пакет создается в Linux)
if exist "installers\rpm_package" (
    echo Создание Linux RPM пакета...
    echo Запустите "rpmbuild -bb installers\rpm_package\kengacad.spec" в Linux > "final_installers\BUILD_LINUX_RPM_INSTRUCTIONS.txt"
    echo Установщик будет создан в ~/rpmbuild/RPMS/ > "final_installers\BUILD_LINUX_RPM_INSTRUCTIONS.txt"
)

REM Arch Linux (файл-заглушка, т.к. реальный пакет создается в Arch)
if exist "installers\arch_package" (
    echo Создание Arch Linux пакета...
    echo Запустите "makepkg -f" в директории installers\arch_package в Arch Linux > "final_installers\BUILD_ARCH_INSTRUCTIONS.txt"
    echo Установщик будет создан как файл .pkg.tar.zst > "final_installers\BUILD_ARCH_INSTRUCTIONS.txt"
)

REM Копируем все скрипты сборки
if exist "build_scripts" (
    xcopy /E /I /Y "build_scripts" "final_installers\build_scripts" >nul
    echo Скрипты сборки скопированы
)

REM Копируем документацию
copy "INSTALLERS.md" "final_installers\" >nul
copy "INSTALL.md" "final_installers\" >nul
copy "INSTALLER_DEPLOYMENT_REPORT.md" "final_installers\" >nul
copy "PACKAGE_DESCRIPTION.md" "final_installers\" >nul
copy "API_DOCS.md" "final_installers\" >nul
echo Документация скопирована

REM Создаем финальный README
echo. > "final_installers\README.txt"
echo =========================== >> "final_installers\README.txt"
echo УСТАНОВЩИКИ KENGACAD >> "final_installers\README.txt"
echo =========================== >> "final_installers\README.txt"
echo. >> "final_installers\README.txt"
echo Установщики находятся в соответствующих поддиректориях: >> "final_installers\README.txt"
echo. >> "final_installers\README.txt"
echo 1. Windows: >> "final_installers\README.txt"
echo    - Установите Inno Setup Compiler >> "final_installers\README.txt"
echo    - Запустите: ISCC installers\kengacad_installer.iss >> "final_installers\README.txt"
echo    - Результат: KengaCAD_Setup.exe >> "final_installers\README.txt"
echo. >> "final_installers\README.txt"
echo 2. Linux DEB (Ubuntu/Debian): >> "final_installers\README.txt"
echo    - Запустите в Linux: dpkg-deb --build installers/deb_package/kengacad-1.0.0 >> "final_installers\README.txt"
echo    - Результат: kengacad-1.0.0.deb >> "final_installers\README.txt"
echo. >> "final_installers\README.txt"
echo 3. Linux RPM (Fedora/openSUSE): >> "final_installers\README.txt"
echo    - Запустите в Linux: rpmbuild -bb installers/rpm_package/kengacad.spec >> "final_installers\README.txt"
echo    - Результат: ~/rpmbuild/RPMS/x86_64/kengacad-*.rpm >> "final_installers\README.txt"
echo. >> "final_installers\README.txt"
echo 4. Arch Linux: >> "final_installers\README.txt"
echo    - Запустите в Arch: makepkg -f в директории installers/arch_package >> "final_installers\README.txt"
echo    - Результат: kengacad-*.pkg.tar.zst >> "final_installers\README.txt"
echo. >> "final_installers\README.txt"
echo См. также файлы BUILD_*_INSTRUCTIONS.txt для подробных инструкций.

echo.
echo Финальная подготовка завершена!
echo Установщики находятся в директории final_installers/
echo.
echo Для каждой платформы следуйте соответствующим инструкциям в README.txt
pause