# Устранение ошибки "DLL load failed while importing QtWidgets"
# Ошибка "Не найдена указанная процедура" часто связана с несовместимостью PyQt6/Qt

Write-Host "Проверка и переустановка PyQt6..." -ForegroundColor Cyan

# 1. Удалить старый PyQt6
pip uninstall PyQt6 PyQt6-Qt6 PyQt6-sip -y 2>$null

# 2. Очистить кэш pip
pip cache purge 2>$null

# 3. Установить PyQt6 заново (совместимая версия)
pip install --no-cache-dir PyQt6==6.6.1

Write-Host ""
Write-Host "Проверка импорта..." -ForegroundColor Cyan
python -c "from PyQt6.QtWidgets import QApplication; print('OK: PyQt6 загружен')"
if ($LASTEXITCODE -eq 0) {
    Write-Host "PyQt6 работает. Запустите: python main.py" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Если ошибка осталась:" -ForegroundColor Yellow
    Write-Host "1. Установите Visual C++ Redistributable: https://aka.ms/vs/17/release/vc_redist.x64.exe"
    Write-Host "2. Убедитесь что Python 64-bit: python -c \"import struct; print(struct.calcsize('P')*8, 'bit')\""
    Write-Host "3. Попробуйте другую версию PyQt6: pip install PyQt6==6.5.0"
}
