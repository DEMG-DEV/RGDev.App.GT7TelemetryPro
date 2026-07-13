#!/bin/bash
echo "🏁 Iniciando compilación de GT7 Telemetry Pro para macOS..."

# Intentar activar el entorno virtual automáticamente si existe
if [ -d ".venv" ]; then
    echo "Activando entorno virtual (.venv)..."
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "Activando entorno virtual (venv)..."
    source venv/bin/activate
else
    echo "⚠️ No se detectó un entorno virtual. Intentando usar dependencias globales..."
fi

# Asegurar que pyinstaller está instalado
pip install pyinstaller

# Limpiar compilaciones previas
echo "🧹 Limpiando compilaciones anteriores..."
rm -rf build dist

# Compilar usando el archivo de especificación
echo "🔨 Compilando la aplicación (esto puede tomar un minuto)..."
pyinstaller GT7TelemetryPro.spec --noconfirm

echo "✅ ¡Compilación Exitosa!"
echo "Tu aplicación empaquetada se encuentra en la carpeta 'dist/'."
echo "Puedes abrir la carpeta escribiendo: open dist/"
