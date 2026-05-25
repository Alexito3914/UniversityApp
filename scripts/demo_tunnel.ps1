# Arranca UCJC Horarios con túnel público (demo temporal)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "Preparando base de datos demo..." -ForegroundColor Cyan
& ".\.venv\Scripts\python.exe" manage.py migrate --noinput
& ".\.venv\Scripts\python.exe" manage.py collectstatic --noinput 2>$null
& ".\.venv\Scripts\python.exe" manage.py seed_demo

$env:DJANGO_DEBUG = "True"
$env:DJANGO_ALLOW_ALL_HOSTS = "True"
$env:DJANGO_SECURE_COOKIES = "False"

$port = 8765
Write-Host "Arrancando servidor en puerto $port..." -ForegroundColor Cyan
$server = Start-Process -FilePath ".\.venv\Scripts\python.exe" `
    -ArgumentList "manage.py", "runserver", "0.0.0.0:$port" `
    -PassThru -WindowStyle Hidden

Start-Sleep -Seconds 4

Write-Host "Abriendo túnel publico (localtunnel)..." -ForegroundColor Cyan
Write-Host "La URL aparecera abajo en unos segundos." -ForegroundColor Yellow
Write-Host ""
Write-Host "Credenciales decano: decano / ucjc1234" -ForegroundColor Green
Write-Host "Mantén esta ventana abierta mientras el decano use la app." -ForegroundColor Yellow
Write-Host ""

try {
    npx --yes localtunnel --port $port
} finally {
    if ($server -and !$server.HasExited) {
        Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
    }
}
