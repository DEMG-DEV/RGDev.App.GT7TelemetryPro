<div align="center">
  <img src="app_icon.png" width="128" alt="GT7 Telemetry Pro Icon">
  <h1>🏁 GT7 Telemetry Pro: F1 & Le Mans Edition</h1>
  
  <p>
    <b>Convierte tu Gran Turismo 7 en un simulador de telemetría profesional.</b><br>
    <i>Inspirado en los sistemas de muro de boxes de la vida real (MoTeC i2 / Atlas).</i>
  </p>

  <p>
    <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python Version">
    <img src="https://img.shields.io/badge/GUI-PyQt6-green.svg" alt="PyQt6">
    <img src="https://img.shields.io/badge/Version-1.1.3-purple.svg" alt="Version">
    <img src="https://img.shields.io/badge/macOS-Native%20Support-lightgrey.svg" alt="macOS Support">
    <img src="https://img.shields.io/badge/Windows-Native%20Support-lightgrey.svg" alt="Windows Support">
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
  </p>
</div>

![GT7 Telemetry Pro Dashboard](docs/main_window.png)

Una plataforma analítica de código abierto diseñada para extraer y transformar los datos crudos del **Gran Turismo 7** (PS4/PS5) en una consola de ingeniería virtual del más alto nivel. 

> 💡 **Nota de diseño:** La aplicación cuenta con un esquema de colores "Modo Diurno" (Daylight Mode) de alto contraste, diseñado específicamente para ser visible bajo luz natural brillante, típico en muros de boxes y *paddocks* profesionales. Todos los componentes utilizan un sistema de tokens de diseño centralizado (`ui/theme.py`) para garantizar uniformidad visual en cualquier plataforma.

---

## 🌟 Características Principales

| Funcionalidad | Descripción |
| :--- | :--- |
| **Telemetry Dashboard** | Visualiza a 60 FPS la telemetría en tiempo real: pedales, marchas, volante y g-forces sin interrupciones (*Zero-stutter*). |
| **Instrumentación Circular** | Cluster de 4 medidores circulares (Velocidad, RPM, Turbo/Boost, Temp. Agua) dibujados nativamente con QPainter. |
| **Consumo por Vuelta** | Medición automática del consumo de combustible por vuelta con alertas visuales progresivas (Normal → Advertencia → Crítico). |
| **Topografía Automática** | Un motor heurístico cruza tus datos contra **122 pistas oficiales**, detectando automáticamente si estás en *Fuji* o *Le Mans*. |
| **Mapa Termodinámico** | Traza la pista procedimentalmente. **Rojo** = Frenadas fuertes, **Verde** = Acelerador a fondo (*WOT*). |
| **Base de Datos SQLite** | Historial ilimitado en modo `WAL`. Guarda cada sesión y organízala por auto y tiempos de vuelta en un archivo maestro. |
| **Alertas Inteligentes** | Sistema de alertas en tiempo real con tono profesional sintetizado (1800 Hz, estilo MoTeC) para temperaturas peligrosas y eventos críticos. |
| **Auto-Actualización** | Verificación automática de nuevas versiones desde GitHub Releases con descarga y aplicación en caliente. |

---

## 🆕 Novedades en v1.1.2

### 📦 Exportar / Importar Base de Datos
Mueve tus datos de telemetría entre computadoras fácilmente:
- **Exportar:** Genera un archivo `.gt7db` portátil y limpio (sin archivos WAL sueltos) que puedes enviar por USB, correo o nube.
- **Importar:** Dos modos disponibles:
  - **Fusionar:** Agrega sesiones nuevas a tu base de datos existente sin perder nada. Detecta duplicados automáticamente.
  - **Reemplazar:** Sobrescribe la base de datos completa (con backup automático de seguridad).

### 🔄 Sincronización por Red Local (LAN Sync)
Si tienes GT7 Telemetry Pro abierto en **dos o más computadoras** conectadas a la misma red WiFi/LAN:
1. Haz clic en **"🔄 Sync LAN"** en la barra superior.
2. La app detecta automáticamente los otros dispositivos en tu red.
3. Un solo clic sincroniza las sesiones faltantes en **ambas direcciones**.
4. Los datos se transfieren comprimidos para máxima velocidad.

> 🔒 Las sesiones marcadas como protegidas (`is_locked`) nunca se sobrescriben durante la sincronización.

---

## 📈 Pro Analysis Workspace (Estilo MoTeC)

Accesible desde el menú principal, el **Pro Analysis Workspace** transforma la telemetría en un entorno de ingeniería puro para comparar múltiples vueltas con un nivel de detalle milimétrico.

![Pro Analysis Workspace](docs/pro_analysis.png)

*   **Layout de 3 Columnas:** Diseñado para pantallas anchas (widescreen). Track Map, Gráficas Centrales y paneles de Análisis se distribuyen equitativamente.
*   **Overlay Milimétrico:** Compara varias vueltas (Multiselección) encimando gráficas de Velocidad y Pedales. Nuestro algoritmo ignora los clásicos errores de "Drift" de red usando el *Delta-T* real para la integración de distancias.
*   **Cursor Sincronizado Multigráfica:** Inspecciona cualquier curva del circuito y mira simultáneamente qué hacían tus pies, tus manos y tu suspensión.
*   **Histogramas Dinámicos de Suspensión:** Analiza la velocidad vertical de los 4 amortiguadores en tiempo real para perfeccionar el *Setup* del auto sobre los pianos.
*   **Data Grids Dinámicos:** Tablas que resumen la telemetría compleja generando columnas codificadas por color automáticamente.

---

## 🧮 Canales Matemáticos (Gestor de Fórmulas)

Los datos crudos no siempre dicen toda la verdad. GT7 Telemetry Pro integra un **motor seguro de canales matemáticos (Math Channels)** para proteger tu sistema mientras experimentas.

*   **Editor Visual Integrado:** Crea y guarda tus propias fórmulas (ej: *Rueda Delantera Derrape*, *Aerobalance*) sin tocar una sola línea de código fuente.
*   **Parsing Seguro Vectorizado:** Escribe fórmulas complejas usando el arreglo de datos crudos (ej: `speed / 3.6`) y el motor calculará arreglos enteros de miles de puntos instantáneamente mediante NumPy.
*   **Persistencia Local:** Tus canales se guardan automáticamente en tu perfil para sesiones futuras.

---

## 🏁 Análisis Avanzado de Sesión

Al terminar de correr o cargar una repetición, GT7 Telemetry Pro despliega su **Módulo de Análisis Avanzado**, optimizado para lectura instantánea sin gráficos abrumadores.

![Análisis Avanzado de Sesión](docs/analysis_mode.png)

*   **Zero-Friction UX:** Navega por el historial de sesiones sin ventanas emergentes. La interfaz principal integra la tabla de historiales, las vueltas y los gráficos.
*   **Gestión Segura de Datos (Lock & Delete):** Protege tus mejores carreras bloqueándolas (`is_locked`). Usa el borrado masivo para purgar bases de datos y recuperar espacio en disco automáticamente (`VACUUM`).
*   **Exportador MoTeC i2:** Exporta sesiones completas al formato binario `.ld` de MoTeC para análisis en software profesional de terceros.

---

## ⚙️ Arquitectura Limpia (Clean Architecture)

El código fuente (~6,200 líneas) está modularizado en cuatro componentes desacoplados:

```
GT7TelemetryPro/
├── core/               # Capa de Dominio
│   ├── models.py       # GT7TelemetryPacket (dataclass con 50+ campos de telemetría)
│   ├── database.py     # SessionDatabaseWriter (WAL, batch inserts asíncronos)
│   ├── db_portability.py # Exportar/Importar/Sincronizar bases de datos
│   ├── math_channels.py  # Motor de métricas F1 (consumo, WOT, laps restantes)
│   ├── dynamic_math.py   # Evaluador seguro de fórmulas (AST sandbox, sin eval())
│   ├── lap_manager.py    # Detección de vueltas y cálculo de deltas
│   ├── alert_engine.py   # Motor de alertas (temperaturas, RPM, combustible)
│   └── car_database.py   # Mapeo de 2,500+ IDs de autos → nombres
│
├── services/           # Capa de Ingestión y Red
│   ├── crypto.py       # Desencriptación Salsa20 (PS4/PS5 compatible)
│   ├── live_client.py  # Socket UDP con heartbeat, autodescubrimiento de consola
│   ├── sync_service.py # Sincronización LAN (UDP discovery + TCP transfer)
│   ├── updater.py      # Auto-actualización desde GitHub Releases
│   ├── motec_exporter.py # Exportador al formato binario MoTeC .ld
│   └── replay_player.py  # Reproductor de sesiones desde SQLite
│
├── ui/                 # Capa Gráfica (PyQt6 + PyQtGraph)
│   ├── main_window.py  # Ventana principal con dashboard de instrumentación
│   ├── workspace.py    # Pro Analysis Workspace (3 columnas, docks)
│   ├── sync_dialog.py  # Diálogo de sincronización LAN
│   ├── formula_manager.py # Editor visual de canales matemáticos
│   ├── theme.py        # Sistema centralizado de tokens de diseño
│   └── widgets/        # Componentes reutilizables (gauges, mapas, gráficas)
│
├── data/               # Datos estáticos
│   ├── gt7_cars.json   # Base de datos de 2,500+ autos de GT7
│   └── tracks.json     # 122 pistas con heurísticas de distancia
│
└── main.py             # Entry point con aislamiento de datos por plataforma
```

---

## 🛠️ Instalación y Uso

### Prerrequisitos
- **Python 3.10+** instalado en tu sistema.
- Consola **PS4 o PS5** con Gran Turismo 7 (Debe estar conectado en tu red local WiFi/Ethernet).

### Configuración Rápida

<details>
<summary><strong>🍎 macOS / 🐧 Linux</strong></summary>

```bash
git clone https://github.com/DEMG-DEV/RGDev.App.GT7TelemetryPro.git
cd RGDev.App.GT7TelemetryPro
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```
</details>

<details>
<summary><strong>🪟 Windows (PowerShell)</strong></summary>

```powershell
git clone https://github.com/DEMG-DEV/RGDev.App.GT7TelemetryPro.git
cd RGDev.App.GT7TelemetryPro
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```
</details>

En la barra superior del programa, **Introduce la IP local de tu consola PS4/PS5** (Ej: `192.168.1.68`) y presiona **Connect Live**. 

> ⚠️ **Importante:** La telemetría solo se emite cuando estás *físicamente manejando en pista o viendo una repetición*. Los menús y boxes no emiten señal.

---

### 📦 Compilación de Ejecutables Nativos

#### 🍎 macOS → `GT7TelemetryPro.app`

Ejecuta nuestro script inteligente (activa el entorno virtual automáticamente y empaqueta con el ícono `.icns`):
```bash
./build_macos.sh
```
El bundle `.app` aparecerá en `dist/GT7TelemetryPro.app`. Puedes arrastrarlo a tu carpeta de Aplicaciones.

#### 🪟 Windows → `GT7TelemetryPro.exe`

1. Asegúrate de tener PyInstaller instalado dentro de tu entorno virtual:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   pip install pyinstaller
   ```

2. Limpia compilaciones anteriores y ejecuta PyInstaller con el archivo de especificación:
   ```powershell
   Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
   pyinstaller GT7TelemetryPro.spec --noconfirm
   ```

3. ¡Listo! Tu ejecutable portátil se encuentra en:
   ```
   dist\GT7TelemetryPro\GT7TelemetryPro.exe
   ```
   Puedes comprimir toda la carpeta `dist\GT7TelemetryPro\` en un `.zip` para distribuirla.

> 💡 **Nota:** El archivo `GT7TelemetryPro.spec` ya contiene la configuración completa para ambas plataformas (ícono `.ico` para Windows, `.icns` para macOS, datos de pistas y autos incluidos). No necesitas modificarlo.

#### 📂 Rutas de datos de la aplicación

Al ejecutarse como aplicación empaquetada, GT7 Telemetry Pro aísla automáticamente sus bases de datos, logs y configuraciones en las rutas estándar del sistema operativo:

| Plataforma | Ruta de datos |
|------------|---------------|
| **macOS** | `~/Library/Application Support/GT7TelemetryPro/` |
| **Windows** | `%APPDATA%\GT7TelemetryPro\` |
| **Linux** | `~/.local/share/GT7TelemetryPro/` |

---

## 📄 Licencia

Este proyecto está bajo la licencia [MIT](LICENSE).

