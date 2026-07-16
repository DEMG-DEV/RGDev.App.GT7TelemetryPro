Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "Iniciando compilacion de GT7 Telemetry Pro para Windows" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan

# Intentar activar el entorno virtual automáticamente si existe
if (Test-Path ".venv\Scripts\activate.ps1") {
    Write-Host "Activando entorno virtual (.venv)..." -ForegroundColor Yellow
    & ".venv\Scripts\activate.ps1"
} elseif (Test-Path "venv\Scripts\activate.ps1") {
    Write-Host "Activando entorno virtual (venv)..." -ForegroundColor Yellow
    & "venv\Scripts\activate.ps1"
} else {
    Write-Host "[ADVERTENCIA] No se detecto un entorno virtual. Intentando usar dependencias globales..." -ForegroundColor Red
}

# Asegurar que pyinstaller y los requerimientos están instalados
Write-Host "`nInstalando/Actualizando dependencias requeridas..."
pip install pyinstaller
pip install -r requirements.txt

# Limpiar compilaciones previas
Write-Host "`nLimpiando compilaciones anteriores..." -ForegroundColor Yellow
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }

# Compilar usando el archivo de especificación
Write-Host "`nCompilando la aplicacion (esto puede tomar varios minutos)..." -ForegroundColor Yellow
python -m PyInstaller GT7TelemetryPro.spec --noconfirm

Write-Host "`n=======================================================" -ForegroundColor Green
Write-Host "¡Compilacion Exitosa!" -ForegroundColor Green
Write-Host "Tu aplicacion se encuentra en la carpeta 'dist\'" -ForegroundColor Green
Write-Host "=======================================================" -ForegroundColor Green
