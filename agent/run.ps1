# Запуск агента. Токен: $env:HUGGINGFACE_TOKEN или в agent\.env
Set-Location $PSScriptRoot
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match '^\s*HUGGINGFACE_TOKEN=(.+)$') { $env:HUGGINGFACE_TOKEN = $matches[1].Trim() }
    }
}
$goal = $args -join ' '
if (-not $goal) { $goal = 'Нарисовать линию и круг, затем запустить симуляцию траектории.' }
python agent.py $goal
