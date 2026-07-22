# Archivo de Contexto de Arquitectura (IA)
## Proyecto: GT7 Telemetry Pro — v1.4.4

> **Última actualización:** 2026-07-21  
> **Total archivos Python:** 33  
> **Total líneas de código fuente:** ~8,900

Este documento describe la arquitectura completa y las restricciones del proyecto para agentes de IA y desarrolladores futuros.

---

### Restricciones Principales
1. **No Web-Tech**: Está estrictamente prohibido utilizar tecnologías web (HTML, CSS, JS, Electron, Tauri, WebView, frameworks web de Python como Flask/Django/FastAPI).
2. **Interfaz Gráfica**: La GUI se basa exclusivamente en `PyQt6` con `pyqtgraph` para gráficos de alto rendimiento.
3. **Alto Rendimiento (60 FPS)**: La decodificación criptográfica (`Salsa20`), escritura a SQLite, carga masiva de datos y exportación MoTeC son asíncronas para evitar tirones (*stutters*).
4. **Modo Diurno**: Toda la UI opera en tema claro de alto contraste. Prohibidos los temas oscuros y colores neón.

---

### Estructura de Directorios Completa

```
GT7TelemetryPro/
├── main.py                         # Entry point (redefine CWD → AppData)
├── requirements.txt                # pycryptodome, PyQt6, pyqtgraph, numpy
├── GT7TelemetryPro.spec            # PyInstaller spec (macOS .icns + Windows .ico)
├── math_channels.json              # Canales matemáticos del usuario (persistencia)
│
├── core/                           # Capa de Dominio (lógica de negocio)
│   ├── config.py                   # APP_VERSION, GITHUB_REPO
│   ├── models.py                   # GT7TelemetryPacket (dataclass, 63+ campos) + parse_telemetry_packet()
│   ├── database.py                 # SessionDatabaseWriter (WAL, batch async) + get_lap_data_vectorized()
│   ├── db_portability.py           # Export (VACUUM INTO) / Import (merge/replace) / LAN buffer
│   ├── dynamic_math.py             # SafeMathVisitor (AST sandbox) + DynamicMathEngine
│   ├── math_channels.py            # MathEngine (fuel, throttle %, brake %, WOT, slip en tiempo real)
│   ├── lap_manager.py              # LapManager + LapData (delta-T por interpolación de distancia)
│   ├── alert_engine.py             # AlertEngine (tyre temps, fuel, water temp, over-rev + cooldowns)
│   ├── car_database.py             # CarDatabase singleton (gt7_cars.json → nombre de auto)
│   └── utils.py                    # @safe_slot decorator (captura excepciones silenciosas en slots PyQt6)
│
├── services/                       # Capa de Ingestión y Red (I/O)
│   ├── provider.py                 # TelemetryProvider (QObject base abstracta con packet_signal)
│   ├── crypto.py                   # Salsa20 decryption con XOR nonce + fallback multi-constante
│   ├── live_client.py              # GT7LiveClient (3 hilos: network/parse/heartbeat)
│   ├── replay_player.py            # GT7SessionPlayer (reproduce sesiones SQLite respetando timestamps)
│   ├── sync_service.py             # PeerDiscovery (UDP 33741) + SyncServer/SyncClient (TCP 33742)
│   ├── updater.py                  # UpdateChecker + UpdateDownloader (QThread, GitHub Releases)
│   └── motec_exporter.py           # MotecLdWriter (.ld) + MotecLdxWriter (.ldx) + MotecExporter
│
├── ui/                             # Capa Gráfica (PyQt6 + pyqtgraph)
│   ├── theme.py                    # Theme: tokens de diseño centralizados (~40 constantes + helpers)
│   ├── main_window.py              # TelemetryMainWindow (dashboard principal 3 columnas)
│   ├── workspace.py                # ProfessionalWorkspace (análisis post-carrera, QDockWidget)
│   ├── formula_manager.py          # FormulaManagerWidget (CRUD canales matemáticos)
│   ├── sync_dialog.py              # SyncDialog (UI de sincronización LAN)
│   ├── styles/
│   │   ├── daylight_theme.qss      # Estilos globales QSS (producción)
│   │   └── dark_theme.qss          # Plantilla experimental (NO usar en producción)
│   └── widgets/
│       ├── advanced_analysis_dialog.py  # Análisis post-sesión (historial, track detection, VACUUM)
│       ├── live_telemetry_widget.py     # Dashboard compacto (speed, gear, pedals, RPM)
│       ├── tyre_temp_gauge.py           # TyreTempGauge (semicírculo con gradiente 4 zonas)
│       ├── circular_gauge.py            # CircularGaugeWidget (arco 270° para velocidad/RPM/boost/temp)
│       ├── telemetry_graphs.py          # 3 gráficas stacked (velocidad, pedales, RPM)
│       ├── map_widget.py                # Heatmap de pista (rojo=freno, verde=acelerador)
│       ├── alert_widget.py              # Notificaciones pit-wall con QSoundEffect
│       ├── delta_widget.py              # Delta-T rolling graph (verde=faster, rojo=slower)
│       └── gforce_widget.py             # G-force scatter (lateral vs longitudinal, ±2G)
│
├── data/                            # Datos estáticos y activos visuales
│   ├── gt7_cars.json                # 580 autos estandarizados (id → maker/name/thumbnail)
│   ├── car_thumbnails/              # 570 imágenes HD PNG para despliegue 100% offline
│   └── tracks.json                  # 121 layouts oficiales (length_m, elevation_diff_m, num_corners)
│
├── tools/                           # Testing y utilidades de desarrollo
│   ├── test_full_ui_sim.py          # Simulación completa a 60fps con paquetes sintéticos
│   ├── test_tyre_gauges.py          # Test aislado de semicírculos de temperatura
│   └── screenshot_generator.py      # Captura automatizada para documentación
│
├── assets/
│   └── pro_beep.wav                 # Sonido de alerta sintetizado (1800Hz)
│
└── docs/                            # Capturas para README
    ├── main_window.png / _running.png / _hot_tyres.png
    ├── analysis_mode.png
    ├── pro_analysis.png
    └── social_preview.jpg
```

---

### Esquema de Base de Datos (telemetry_master.sqlite)

```sql
-- Modo WAL, cache 64MB, NORMAL sync
PRAGMA journal_mode = WAL;
PRAGMA cache_size = -65536;
PRAGMA synchronous = NORMAL;

CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time TEXT,
    end_time TEXT,
    car_id INTEGER,
    car_name TEXT,
    total_laps INTEGER,
    best_laptime INTEGER,
    is_locked INTEGER DEFAULT 0
);

CREATE TABLE telemetry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES sessions(id),
    timestamp REAL,
    lap_count INTEGER,
    speed_kmh REAL,
    engine_rpm REAL,
    throttle INTEGER,
    brake INTEGER,
    current_gear INTEGER,
    raw_packet BLOB
);
```

---

### Puertos de Red

| Puerto | Protocolo | Dirección | Propósito |
|--------|-----------|-----------|-----------|
| 33739 | UDP | Salida → Consola | Heartbeat ('C') cada 1.5s |
| 33740 | UDP | Entrada ← Consola | Telemetría encriptada (Salsa20) |
| 33741 | UDP | Broadcast bidireccional | Descubrimiento de peers LAN |
| 33742 | TCP | Bidireccional entre peers | Transferencia de datos de sync |

---

### Modelo de Hilos

| Hilo | Ubicación | Propósito |
|------|-----------|-----------|
| **Main (GUI)** | `main.py` / QApplication | Evento loop PyQt6, renderizado de widgets |
| **Network** | `live_client._network_capture_loop` | `socket.recvfrom()` UDP 33740 con timeout 1s |
| **Crypto/Parse** | `live_client._parser_loop` | Salsa20 decrypt → struct unpack → `packet_signal.emit()` |
| **Heartbeat** | `live_client._heartbeat_loop` | Envía 'C' cada 1.5s a UDP 33739 |
| **DB Writer** | `database.SessionDatabaseWriter._worker_loop` | Batch inserts de 60 filas por commit |
| **Peer Discovery** | `sync_service.PeerDiscovery` (QThread) | UDP broadcast beacons en 33741 |
| **Sync Server** | `sync_service.SyncServer` (QThread) | TCP listener en 33742 |
| **Sync Client** | `sync_service.SyncClient` (QThread) | TCP conexión a peer |
| **Update Check** | `updater.UpdateChecker` (QThread) | Consulta API GitHub |
| **Update Download** | `updater.UpdateDownloader` (QThread) | Descarga + extracción ZIP |
| **Data Loader** | `workspace.DataLoaderThread` (QThread) | Carga masiva SQLite para análisis |
| **MoTeC Export** | `workspace.MotecExportThread` (QThread) | Generación de archivos .ld/.ldx |

---

### Flujo de Datos (Telemetría en Vivo)

```
PS4/PS5 Console (GT7)
    │ UDP 33740 (paquetes encriptados Salsa20, ~350 bytes)
    ▼
┌──────────────────────────────────────────────────────────┐
│ GT7LiveClient (services/live_client.py)                   │
│                                                           │
│  Thread 1 (Network)     Thread 2 (Crypto/Parse)           │
│  ┌─────────────────┐    ┌────────────────────────────┐    │
│  │ sock.recvfrom() │───►│ queue → decrypt_telemetry()│    │
│  │ (UDP 33740)     │    │ → parse_telemetry_packet() │    │
│  └─────────────────┘    │ → DB Writer (si graba)     │    │
│                         │ → packet_signal.emit()     │    │
│  Thread 3 (Heartbeat)   └────────────────────────────┘    │
│  ┌──────────────────┐                                     │
│  │ sendto 'C' cada  │                                     │
│  │ 1.5s (port 33739)│                                     │
│  └──────────────────┘                                     │
└──────────────────────────────────────────────────────────┘
           │ pyqtSignal(GT7TelemetryPacket) @ 60Hz
           ▼
┌──────────────────────────────────────────────────────────┐
│ TelemetryMainWindow (ui/main_window.py)                   │
│                                                           │
│  _cache_packet() @ 60Hz:                                  │
│  ├── MathEngine.process_packet() → fuel, WOT, slip       │
│  ├── LapManager.process_packet() → delta-T               │
│  ├── AlertEngine.check_alerts() → pit-wall warnings      │
│  └── Feed widgets: Map, G-Force, Graphs                  │
│                                                           │
│  QTimer(33ms) → update_dashboard_ui() @ 30Hz:             │
│  └── Updates: gauges, tyre temps, fuel bar, gear, delta   │
└──────────────────────────────────────────────────────────┘
```

### Flujo de Datos (Análisis Post-Sesión)

```
telemetry_master.sqlite
    │
    ├──► AdvancedAnalysisDialog
    │    - Navega sesiones (tabla + lock/delete/VACUUM)
    │    - Detecta pista automáticamente (tracks.json)
    │    - Overlay de múltiples vueltas (velocidad vs distancia)
    │    - Playback con slider + keyboard (Space, ←/→)
    │
    └──► ProfessionalWorkspace (QDockWidget panels)
         - DataLoaderThread → get_lap_data_vectorized() → numpy
         - Gráficas: velocidad, pedales, RPM, suspensión
         - Track map con crosshair sincronizado multigráfica
         - DynamicMathEngine → canales matemáticos del usuario
         - FormulaManagerWidget → CRUD de fórmulas
         - MotecExportThread → exporta a .ld/.ldx
```

---

### Grafo de Dependencias

```
main.py
  └── ui.main_window.TelemetryMainWindow
        ├── core.config (APP_VERSION)
        ├── core.models (GT7TelemetryPacket, parse_telemetry_packet)
        ├── core.car_database (CarDatabase singleton)
        ├── core.math_channels (MathEngine)
        ├── core.lap_manager (LapManager)
        ├── core.alert_engine (AlertEngine)
        ├── core.db_portability (export/import/merge/replace)
        ├── services.live_client (GT7LiveClient)
        │     ├── services.provider (TelemetryProvider base)
        │     ├── services.crypto (decrypt_telemetry / Salsa20)
        │     └── core.database (SessionDatabaseWriter)
        ├── services.updater (UpdateChecker / UpdateDownloader)
        ├── ui.theme (Theme tokens)
        ├── ui.workspace (ProfessionalWorkspace)
        │     ├── core.database (get_lap_data_vectorized)
        │     ├── core.dynamic_math (DynamicMathEngine / SafeMathVisitor)
        │     ├── ui.formula_manager (FormulaManagerWidget)
        │     └── services.motec_exporter (MotecExporter)
        ├── ui.sync_dialog (SyncDialog)
        │     └── services.sync_service (PeerDiscovery / SyncServer / SyncClient)
        │           └── core.db_portability
        └── ui.widgets.*
              ├── advanced_analysis_dialog (AdvancedAnalysisDialog)
              │     ├── map_widget (MapWidget)
              │     └── live_telemetry_widget (LiveTelemetryWidget)
              ├── map_widget (MapWidget)
              ├── gforce_widget (GForceWidget)
              ├── telemetry_graphs (TelemetryGraphsWidget)
              ├── delta_widget (DeltaWidget)
              ├── alert_widget (AlertWidget)
              ├── circular_gauge (CircularGaugeWidget)
              └── tyre_temp_gauge (TyreTempGauge ×4)
```

---

### Patrones de Diseño

| Patrón | Implementación |
|--------|----------------|
| **Clean Architecture** | `services/` (I/O) → `core/` (lógica) → `ui/` (renderizado) |
| **Signal-Slot** | Toda comunicación cross-thread via `pyqtSignal` |
| **Singleton** | `CarDatabase` (lookup compartido de nombres de autos) |
| **Provider Pattern** | `TelemetryProvider` base → `GT7LiveClient` / `GT7SessionPlayer` |
| **AST Sandbox** | `SafeMathVisitor` para validación de fórmulas del usuario |
| **Batch Processing** | DB writer acumula 60 paquetes antes de cada commit |
| **Design Token System** | `Theme` class (~40 constantes + 4 helpers de estilo) |
| **Decorator Pattern** | `@safe_slot` para captura de excepciones en slots |

### Dependencias (requirements.txt)

| Paquete | Versión | Propósito |
|---------|---------|-----------|
| `pycryptodome` | ≥3.15.0 | Desencriptación Salsa20 de paquetes UDP GT7 |
| `PyQt6` | ≥6.5.0 | Framework GUI (widgets, señales, multimedia) |
| `pyqtgraph` | ≥0.13.0 | Gráficos de alto rendimiento a 60fps |
| `numpy` | ≥1.24.0 | Procesamiento vectorizado de telemetría |
