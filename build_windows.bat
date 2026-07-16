@echo off
echo =======================================================
echo Iniciando compilacion de GT7 Telemetry Pro para Windows
echo =======================================================

:: Intentar activar el entorno virtual automáticamente si existe
if exist ".venv\Scripts\activate.bat" (
    echo Activando entorno virtual ^(.venv^)...
    call ".venv\Scripts\activate.bat"
) else if exist "venv\Scripts\activate.bat" (
    echo Activando entorno virtual ^(venv^)...
    call "venv\Scripts\activate.bat"
) else (
    echo [ADVERTENCIA] No se detecto un entorno virtual. Intentando usar dependencias globales...
)

:: Asegurar que pyinstaller y los requerimientos estan instalados
echo.
echo Instalando/Actualizando dependencias requeridas...
pip install pyinstaller
pip install -r requirements.txt

:: Limpiar compilaciones previas
echo.
echo Limpiando compilaciones anteriores...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

:: Compilar usando el archivo de especificación
echo.
echo Compilando la aplicacion (esto puede tomar varios minutos)...
python -m PyInstaller GT7TelemetryPro.spec --noconfirm

echo.
echo =======================================================
echo ¡Compilacion Exitosa!
echo Tu aplicacion se encuentra en la carpeta 'dist\'
echo =======================================================
pause
