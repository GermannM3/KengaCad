# Запуск агента из корня репозитория. Токен: $env:HUGGINGFACE_TOKEN или agent\.env
$agentDir = Join-Path $PSScriptRoot "agent"
if (-not (Test-Path $agentDir)) { Write-Error "Папка agent не найдена: $agentDir"; exit 1 }
& (Join-Path $agentDir "run.ps1") @args
