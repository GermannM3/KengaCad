@echo off
REM Скрипт для создания portable версии KengaCAD

echo Создание portable версии KengaCAD...

REM Создаем директорию для portable версии
if not exist "portable_app" mkdir portable_app
cd portable_app

REM Создаем структуру portable приложения
mkdir app
mkdir assets
mkdir config
mkdir examples
mkdir ui
mkdir engine
mkdir robot
mkdir cad

REM Копируем исполняемый файл
copy "..\dist\KengaCAD_Simple_Standalone.exe" "app\KengaCAD.exe" >nul

REM Создаем файл запуска
echo @echo off > run_kengacad.bat
echo REM Запуск KengaCAD portable версии >> run_kengacad.bat
echo echo Проверка наличия движка Kenga... >> run_kengacad.bat
echo where kenga >nul 2>&1 >> run_kengacad.bat
echo if %%errorlevel%% neq 0 ( >> run_kengacad.bat
echo   echo ПРЕДУПРЕЖДЕНИЕ: Движок Kenga не найден в системе. >> run_kengacad.bat
echo   echo Для полной функциональности установите движок Kenga отдельно. >> run_kengacad.bat
echo   echo См. инструкции в INSTALL_ENGINE.md >> run_kengacad.bat
echo ) >> run_kengacad.bat
echo echo. >> run_kengacad.bat
echo echo Запуск KengaCAD... >> run_kengacad.bat
echo start "" "app\KengaCAD.exe" >> run_kengacad.bat
echo echo. >> run_kengacad.bat
echo echo KengaCAD запущен в упрощенном режиме. >> run_kengacad.bat
echo echo Для полной функциональности запустите движок Kenga отдельно. >> run_kengacad.bat
echo pause >> run_kengacad.bat

REM Создаем инструкцию по установке движка
echo УСТАНОВКА ДВИЖКА KENGA > INSTALL_ENGINE.txt
echo ====================== >> INSTALL_ENGINE.txt
echo. >> INSTALL_ENGINE.txt
echo 1. Установите Go (версия 1.22+): >> INSTALL_ENGINE.txt
echo    - Скачайте с https://golang.org/dl/ >> INSTALL_ENGINE.txt
echo    - Установите и убедитесь, что go version работает >> INSTALL_ENGINE.txt
echo. >> INSTALL_ENGINE.txt
echo 2. Скачайте движок Kenga: >> INSTALL_ENGINE.txt
echo    git clone https://github.com/GermannM3/GoEngineKenga.git >> INSTALL_ENGINE.txt
echo. >> INSTALL_ENGINE.txt
echo 3. Соберите движок: >> INSTALL_ENGINE.txt
echo    cd GoEngineKenga >> INSTALL_ENGINE.txt
echo    go build ./cmd/kenga >> INSTALL_ENGINE.txt
echo. >> INSTALL_ENGINE.txt
echo 4. Добавьте путь к kenga.exe в PATH: >> INSTALL_ENGINE.txt
echo    - Нажмите Win+R, введите sysdm.cpl >> INSTALL_ENGINE.txt
echo    - Перейдите на вкладку "Дополнительно" -> "Переменные среды" >> INSTALL_ENGINE.txt
echo    - В "Системные переменные" найдите "Path" и нажмите "Изменить" >> INSTALL_ENGINE.txt
echo    - Добавьте путь к папке с kenga.exe >> INSTALL_ENGINE.txt
echo. >> INSTALL_ENGINE.txt
echo 5. Запустите движок перед использованием KengaCAD: >> INSTALL_ENGINE.txt
echo    kenga run --project . --scene scene.json --ws-port 127.0.0.1:7777 >> INSTALL_ENGINE.txt

REM Создаем README
echo KENGA CAD PORTABLE VERSION > README.txt
echo ========================== >> README.txt
echo. >> README.txt
echo Это portable версия KengaCAD. >> README.txt
echo. >> README.txt
echo СТРУКТУРА: >> README.txt
echo - app\KengaCAD.exe - основное приложение >> README.txt
echo - run_kengacad.bat - скрипт запуска >> README.txt
echo - INSTALL_ENGINE.txt - инструкция по установке движка >> README.txt
echo. >> README.txt
echo ИСПОЛЬЗОВАНИЕ: >> README.txt
echo 1. Запустите run_kengacad.bat >> README.txt
echo 2. Приложение запустится в упрощенном режиме >> README.txt
echo 3. Для полной функциональности установите движок Kenga >> README.txt

REM Возвращаемся в основную директорию
cd ..

REM Создаем ZIP архив
echo Создание ZIP архива portable версии...
powershell Compress-Archive -Force -Path portable_app\* -DestinationPath KengaCAD_Portable.zip

echo.
echo Portable версия KengaCAD создана: KengaCAD_Portable.zip
echo Пользователь может просто распаковать архив и запустить run_kengacad.bat
echo.
pause