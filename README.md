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
    <img src="https://img.shields.io/badge/macOS-Native%20Support-lightgrey.svg" alt="macOS Support">
    <img src="https://img.shields.io/badge/Status-Pro%20Analysis%20Ready-orange.svg" alt="Status">
  </p>
</div>

![GT7 Telemetry Pro Dashboard](docs/main_window.png)

Una plataforma analítica de código abierto diseñada para extraer y transformar los datos crudos del **Gran Turismo 7** (PS4/PS5) en una consola de ingeniería virtual del más alto nivel. 

> 💡 **Nota de diseño:** La aplicación cuenta con un esquema de colores "Modo Diurno" (Daylight Mode) de alto contraste, diseñado específicamente para ser visible bajo luz natural brillante, típico en muros de boxes y *paddocks* profesionales.

---

## 🌟 Características Principales

| Funcionalidad | Descripción |
| :--- | :--- |
| **Telemetry Dashboard** | Visualiza a 60 FPS la telemetría en tiempo real: pedales, marchas, volante y g-forces sin interrupciones (*Zero-stutter*). |
| **Topografía Automática** | Un motor heurístico cruza tus datos contra **122 pistas oficiales**, detectando automáticamente si estás en *Fuji* o *Le Mans*. |
| **Mapa Termodinámico** | Traza la pista procedimentalmente. **Rojo** = Frenadas fuertes, **Verde** = Acelerador a fondo (*WOT*). |
| **Base de Datos SQLite** | Historial ilimitado en modo `WAL`. Guarda cada sesión y organízala por auto y tiempos de vuelta en un archivo maestro. |

---

## 📈 Pro Analysis Workspace (Estilo MoTeC)

Accesible desde el menú principal, el **Pro Analysis Workspace** transforma la telemetría en un entorno de ingeniería puro para comparar múltiples vueltas con un nivel de detalle milimétrico.

![Pro Analysis Workspace](docs/pro_analysis.png)

*   **Overlay Milimétrico:** Compara varias vueltas (Multiselección) encimando gráficas de Velocidad y Pedales. Nuestro algoritmo ignora los clásicos errores de "Drift" de red usando el *Delta-T* real para la integración de distancias.
*   **Cursor Sincronizado Multigráfica:** Inspecciona cualquier curva del circuito y mira simultáneamente qué hacían tus pies, tus manos y tu suspensión.
*   **Histogramas Dinámicos de Suspensión:** Analiza la velocidad vertical de los 4 amortiguadores en tiempo real para perfeccionar el *Setup* del auto sobre los pianos.
*   **Data Grids Dinámicos:** Tablas que resumen la telemetría compleja generando columnas codificadas por color automáticamente.

---

## 🧮 Canales Matemáticos (Formula Manager)

Los datos crudos no siempre dicen toda la verdad. GT7 Telemetry Pro integra un **motor seguro de canales matemáticos (Math Channels)** para proteger tu sistema mientras experimentas.

<div align="center">
  <img src="docs/formula_manager.png" alt="Formula Manager" width="800">
</div>

*   **Editor Visual Integrado:** Crea y guarda tus propias fórmulas (ej: *Rueda Delantera Derrape*, *Aerobalance*) sin tocar una sola línea de código fuente.
*   **Parsing Seguro Vectorizado:** Escribe fórmulas complejas usando el arreglo de datos crudos (ej: `speed / 3.6`) y el motor calculará arreglos enteros de miles de puntos instantáneamente mediante NumPy.
*   **Persistencia Local:** Tus canales se guardan automáticamente en tu perfil para sesiones futuras.

---

## 🏁 Análisis Avanzado Post-Sesión

Al terminar de correr o cargar una repetición, GT7 Telemetry Pro despliega su **Módulo de Análisis Avanzado**, optimizado para lectura instantánea sin gráficos abrumadores.

![Advanced Analysis Mode](docs/analysis_mode.png)

*   **Zero-Friction UX:** Navega por el historial de sesiones sin ventanas emergentes. La interfaz principal integra la tabla de historiales, las vueltas y los gráficos.
*   **Gestión Segura de Datos (Lock & Delete):** Protege tus mejores carreras bloqueándolas (`is_locked`). Usa el borrado masivo para purgar bases de datos y recuperar espacio en disco automáticamente (`VACUUM`).

---

## ⚙️ Arquitectura Limpia (Clean Architecture)

El código fuente está modularizado en tres componentes críticos y fuertemente desacoplados, idóneo para escalado o integraciones:

1.  📡 **`services/` (Capa de Ingestión):** Controla el Socket UDP, desencriptación nativa Salsa20 y reproducción de BD.
2.  🧠 **`core/` (Capa de Dominio):** `LapManager`, `MathEngine` analizando matrices numéricas a la velocidad del rayo en hilos asíncronos.
3.  🖥️ **`ui/` (Capa Gráfica):** Implementación robusta en **PyQt6** y gráficos hiperrápidos acelerados mediante **PyQtGraph**.

---

## 🛠️ Instalación y Uso

### Prerrequisitos
- **Python 3.10+** instalado en tu sistema.
- Consola **PS4 o PS5** con Gran Turismo 7 (Debe estar conectado en tu red local WiFi/Ethernet).

### Configuración Rápida
Clona el proyecto, crea tu entorno virtual y arranca el simulador del muro de boxes:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

En la esquina superior derecha del programa, **Introduce la IP local de tu consola PS4/PS5** (Ej: `192.168.1.68`) y presiona **Connect Live**. 

> ⚠️ **Importante:** La telemetría solo se emite cuando estás *físicamente manejando en pista o viendo una repetición*. Los menús y boxes no emiten señal.

### 🍎 Compilación Nativa para macOS (.app)
Si deseas generar una aplicación empaquetada (`GT7TelemetryPro.app`) para ejecutarla con un simple doble clic:

1. Asegúrate de tener las librerías instaladas en tu entorno virtual.
2. Ejecuta nuestro script inteligente (automáticamente encenderá el entorno y empaquetará el código con el icono de alta resolución `.icns`):
   ```bash
   ./build_macos.sh
   ```
3. ¡Listo! Tu app nativa aparecerá en la carpeta `dist/`. Al iniciarla, la aplicación aislará tu base de datos y tus registros en una carpeta segura (`~/Documents/GT7TelemetryPro/`) para proteger el sistema de archivos de tu Mac.
