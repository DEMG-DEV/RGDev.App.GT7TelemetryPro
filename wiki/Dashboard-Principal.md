# 🏁 Dashboard Principal

> **Archivo:** `ui/main_window.py` · **Clase:** `TelemetryMainWindow` · **656 líneas**

El Dashboard Principal es la ventana central de GT7 Telemetry Pro. Muestra toda la instrumentación de telemetría en tiempo real mientras conduces en Gran Turismo 7.

![Dashboard Principal](https://raw.githubusercontent.com/DEMG-DEV/RGDev.App.GT7TelemetryPro/master/docs/main_window_running.png)

---

## Dimensiones y Tema

| Propiedad | Valor |
|-----------|-------|
| Resolución base | 1600 × 900 px |
| Tema | Daylight Mode (fondo claro `#FAFAFA`) |
| QSS global | `ui/styles/daylight_theme.qss` |
| Frecuencia de datos | 60 Hz (recepción de paquetes) |
| Frecuencia de renderizado | ~30 Hz (QTimer cada 33ms) |

---

## Layout de 3 Columnas

La ventana se divide en una barra superior (header) y tres columnas principales:

```
┌──────────────────────────────────────────────────────────────────────────┐
│  HEADER: Status │ Record │ IP │ Connect │ Análisis │ Pro │ Export/Import│
├───────────┬─────────────────────────────┬────────────────────────────────┤
│           │                             │                                │
│  IZQUIERDA│        CENTRO               │         DERECHA                │
│  (20%)    │        (40%)                │         (40%)                  │
│           │                             │                                │
│  Info     │  Gráficas Telemetría        │  ┌──────┐ ┌──────┐            │
│  Vuelta   │  (Velocidad/Pedales/RPM)    │  │ VEL  │ │ RPM  │  Gauges   │
│           │                             │  └──────┘ └──────┘            │
│  Mapa     │                             │  ┌──────┐ ┌──────┐            │
│  Pista    │                             │  │TURBO │ │ TEMP │            │
│           │                             │  └──────┘ └──────┘            │
│  G-Force  │  Delta-T                    │  FL ▐▌▐▌ FR  Tyres+Pedals    │
│           │  (150px fijo)               │  RL ▐▌▐▌ RR                   │
│           │                             │  Marcha: 3      Alertas       │
└───────────┴─────────────────────────────┴────────────────────────────────┘
```

### Stretch Ratios
| Columna | Stretch | % Aproximado |
|---------|---------|-------------|
| Izquierda | 2 | ~20% |
| Centro | 4 | ~40% |
| Derecha | 4 | ~40% |

---

## Barra Superior (Header)

La barra de herramientas horizontal contiene todos los controles de la aplicación:

| Elemento | Widget | Descripción |
|----------|--------|-------------|
| **Estado** | `QLabel` | Indicador de conexión: 🔴 Disconnected / 🟡 Searching / 🟢 Connected |
| **Grabar** | `QPushButton` | "⏺ Iniciar Grabación" / "⏹ Detener Grabación" — deshabilitado hasta recibir telemetría |
| **Estado Rec.** | `QLabel` | Texto informativo de grabación activa |
| **IP Consola** | `QLineEdit` | Campo de 200px para IP de PS4/PS5 (auto-detect disponible) |
| **Conectar** | `QPushButton` | "Connect Live" / "Disconnect" — inicia/detiene `GT7LiveClient` |
| **Análisis** | `QPushButton` | "Historial y Análisis" → abre [AdvancedAnalysisDialog](Historial-y-Analisis) |
| **Pro Analysis** | `QPushButton` | "Pro Analysis" (acento azul) → abre [ProfessionalWorkspace](Pro-Analysis-Workspace) |
| **Exportar BD** | `QPushButton` | "📦 Exportar BD" → diálogo de guardar archivo `.gt7db` |
| **Importar BD** | `QPushButton` | "📥 Importar BD" → diálogo de abrir + flujo merge/replace |
| **Sync LAN** | `QPushButton` | "🔄 Sync LAN" → abre [SyncDialog](Sincronizacion-LAN) |

---

## Columna Izquierda — Información y Mapas

### Panel "Información de Vuelta"
Muestra datos de la vuelta actual en tiempo real:

| Dato | Formato | Detalle |
|------|---------|---------|
| Auto | Texto | Nombre del auto (desde `gt7_cars.json`, 800+ IDs) |
| Vuelta | "Lap X/Y" | Vuelta actual / total de vueltas |
| Tiempo | `mm:ss.SSS` | Tiempo de la vuelta actual (monospace 18pt) |
| Combustible est. | Texto | "~X.X vueltas restantes" |
| Barra combustible | `QProgressBar` | Color dinámico: Verde (>30%) → Naranja (10-30%) → Rojo (<10%) |
| Consumo/Vuelta | Texto | "Consumo: X.XX/vuelta" |
| WOT | Indicador | "🟢 WOT" cuando acelerador = 100% |

### Mapa de Pista (stretch=3)
Ver → [Mapa de Pista](Mapa-Pista)

### Diagrama G-Force (stretch=2)
Ver → [Fuerzas G](Fuerzas-G)

---

## Columna Centro — Gráficas y Delta

### Gráficas de Telemetría (stretch=4)
Ver → [Gráficas de Telemetría](Graficas-Telemetria)

### Delta-T (stretch=1, 150px fijo)
Ver → [Delta-T](Delta-T)

---

## Columna Derecha — Instrumentación

### Medidores Circulares (Grid 2×2)
| Posición | Medidor | Rango | Color |
|----------|---------|-------|-------|
| Superior Izq. | Velocidad | 0–350 km/h | Azul |
| Superior Der. | RPM | 0–10,000 (auto-ajusta al máximo) | Naranja |
| Inferior Izq. | Turbo/Boost | 0–2.0 bar | Rojo |
| Inferior Der. | Temp. Agua | 50–130 °C | Verde |

Ver → [Medidores Circulares](Medidores-Circulares)

### Neumáticos + Pedales

```
┌────────┐  ┌────┬────┐  ┌────────┐
│  FL 🌡️  │  │ THR│ BRK│  │  FR 🌡️  │
│  87°   │  │ ▐▌ │ ▐▌ │  │  92°   │
├────────┤  │ 78%│ 0% │  ├────────┤
│  RL 🌡️  │  │    │    │  │  RR 🌡️  │
│  71°   │  └────┴────┘  │  85°   │
└────────┘                └────────┘
```

- **Pedales**: 2 barras verticales (30×180px) — Acelerador (verde) / Freno (rojo) con label de porcentaje
- **Neumáticos**: 4 semicírculos → Ver [Temperatura de Neumáticos](Temperatura-Neumaticos)

### Indicador de Marcha
Texto en monospace 24pt bold: "Marcha: N" / "Marcha: 3" / "Marcha: R"

### Alertas Pit-Wall
Ver → [Alertas Pit-Wall](Alertas-Pit-Wall)

---

## Flujo de Datos

```
GT7LiveClient (3 hilos)
    │
    │ packet_signal @ 60Hz
    ▼
_cache_packet() ──────────────────────────────────────────────┐
    │                                                          │
    ├── MathEngine.process_packet() → fuel, WOT, slip         │
    ├── LapManager.process_packet() → delta-T                 │
    ├── AlertEngine.check_alerts() → pit-wall warnings        │
    ├── map_widget.add_point(x, z, throttle, brake)           │
    ├── gforce_widget.add_point(lateral, longitudinal)        │
    └── graphs_widget.add_data(speed, throttle, brake, rpm)   │
                                                               │
QTimer(33ms) ─── update_dashboard_ui() @ 30Hz ◄───────────────┘
    │
    ├── Actualizar 4 medidores circulares (.set_value)
    ├── Actualizar 4 temperaturas de neumáticos (.set_temp)
    ├── Actualizar barras de pedales (.setValue)
    ├── Actualizar barra de combustible
    ├── Actualizar indicador de marcha
    ├── Actualizar info de vuelta
    ├── map_widget.update_plot()
    ├── gforce_widget.update_plot()
    ├── graphs_widget.update_plot()
    └── delta_widget.update_data()
```

### ¿Por qué 2 frecuencias diferentes?

- **60 Hz** (`_cache_packet`): Recibe cada paquete del juego sin perder ninguno. Alimenta los buffers de datos.
- **30 Hz** (`update_dashboard_ui`): Refresca la interfaz visual. 30 FPS es suficiente para el ojo humano y reduce la carga de CPU en un 50%.

---

## Auto-Actualización

Al arrancar la aplicación, un `UpdateChecker` (QThread) consulta la API de GitHub para detectar nuevas versiones. Si existe una versión más reciente que `APP_VERSION`:

1. Muestra diálogo: "Nueva versión X.X.X disponible. ¿Descargar?"
2. Si acepta → `UpdateDownloader` descarga el ZIP en background con barra de progreso
3. Al completar → extrae y reinicia la aplicación
