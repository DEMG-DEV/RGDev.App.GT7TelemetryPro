# 🔬 Pro Analysis Workspace

> **Archivo:** `ui/workspace.py` · **Clase:** `ProfessionalWorkspace` · **880 líneas**

El Pro Analysis Workspace es la vista de análisis más avanzada de GT7 Telemetry Pro. Emula la interfaz de herramientas profesionales como **MoTeC i2 Pro**, con paneles flotantes/acoplables (`QDockWidget`) y análisis multicapa.

![Pro Analysis](https://raw.githubusercontent.com/DEMG-DEV/RGDev.App.GT7TelemetryPro/master/docs/pro_analysis.png)

---

## Layout General

```
┌──────────────────────────────────────────────────────────────────────┐
│  Toolbar: [Channel ▼] [Add Trace] [Clear Custom] [Restore Panels]  │
├──────────────┬───────────────────────────────────┬───────────────────┤
│              │                                   │                   │
│  DOCKS IZQ.  │      CENTRO (Trace Principal)     │   DOCKS DER.     │
│  (Tabs)      │                                   │                  │
│              │  Speed (km/h)  ─── lap overlay ──  │  X-Y Scatter    │
│  🗺️ Track    │  ═══════════════════════════════   │                  │
│     Map      │                                   │  Suspension      │
│              │  Inputs (%)  ─── THR/BRK ────     │  Histograms     │
│  🎯 G-Force  │  ═══════════════════════════════   │                  │
│              │                                   │  Tyre Temps     │
│  📋 Data     │  Math Channel ─── custom ────     │                  │
│     Manager  │  ═══════════════════════════════   │  Tyre Slip      │
│              │          ┃ crosshair cursor        │  Ratios         │
│              │                                   │                  │
└──────────────┴───────────────────────────────────┴───────────────────┘
```

---

## Panel Central — Gráficas de Traces

### Gráficas Default (3 filas apiladas, X-linked)

| # | Canal | Colores por Vuelta |
|---|-------|--------------------|
| 1 | **Speed (km/h)** | Cyan, Magenta, Yellow, Green, Orange, White, Red, Blue |
| 2 | **Inputs (%)** | Acelerador = sólido, Freno = discontinuo (por vuelta) |
| 3 | **Math Channel** | Canal matemático seleccionado del ComboBox |

Cada gráfica tiene un botón "X" embebido para cerrarla individualmente.

### Crosshair Sincronizado
- Línea vertical amarilla discontinua (`InfiniteLine`) draggable
- Al mover el crosshair: se busca el índice más cercano en el array de distancia
- El punto correspondiente se marca en el **Track Map** como un dot rojo

### Toolbar

| Botón | Acción |
|-------|--------|
| **Channel ComboBox** | Selecciona canal para nueva gráfica (Speed, Throttle, Brake, RPM, Boost, Steer, + math channels) |
| **Add Trace** | Agrega una nueva fila de gráfica X-linked al trace principal |
| **Clear Custom Traces** | Elimina todas las gráficas agregadas por el usuario |
| **Restore Panels** | Resetea todos los docks a su posición default |

---

## Paneles Dock (8 totales)

### Panel Izquierdo — Tabs (Sur)

#### 🗺️ Track Map
- Scatter plot con aspecto bloqueado
- Colorización por velocidad usando colormap `turbo`/`inferno` de pyqtgraph
- Punto cursor (rojo) sincronizado con el crosshair central
- Dibuja todos los laps seleccionados superpuestos

#### 🎯 G-Force Traction Circle
- Scatter de aceleración lateral (sway) vs longitudinal (surge)
- Crosshair de referencia en el origen
- Aspecto bloqueado 1:1

#### 📋 Gestor de Datos y Fórmulas

| Elemento | Función |
|----------|---------|
| **Session ComboBox** | Selecciona sesión a analizar (muestra fecha + auto + vueltas) |
| **Tabla de Vueltas** | Lista checkable de vueltas con tiempo (★ = mejor) |
| **Load Selected Laps** | Carga las vueltas seleccionadas vía `DataLoaderThread` |
| **Formula Manager** | Abre [Gestor de Fórmulas](Gestor-de-Formulas) |
| **Export to MoTeC** | Exporta sesión a `.ld/.ldx` vía `MotecExportThread` |
| **Save Layout** | Guarda posición de los docks en `QSettings` |

---

### Panel Derecho

#### 📈 X-Y Scatter
- Dos ComboBox para seleccionar canales X e Y
- Scatter plot de la correlación entre dos canales cualesquiera
- Útil para análisis como: Speed vs Throttle, RPM vs Boost, etc.

#### 📊 Suspension Velocity Histogram
- Grid 2×2: FL, FR, RL, RR
- Histograma de barras (40 bins, rango ±0.05)
- Muestra la distribución de velocidad de suspensión
- Útil para diagnosticar: suspensión demasiado dura/blanda, bottoming out

#### 🌡️ Tyre Temperatures (°C)
- Grid 2×2: FL, FR, RL, RR
- Línea de temperatura sobre el tiempo/distancia
- Muestra evolución térmica durante la vuelta

#### 🔄 Tyre Slip Ratio
- Grid 2×2: FL, FR, RL, RR
- Slip = `(wheelRPS × radius) - chassis_speed`
- X-linked con la gráfica de velocidad central
- Muestra deslizamiento de cada rueda (positivo = spinning, negativo = locking)

---

## Flujo de Datos

```
ProfessionalWorkspace abierto
    │
    ▼ Usuario selecciona sesión y vueltas
    │
    ▼ Click "Load Selected Laps"
    │
    ▼ DataLoaderThread (QThread)
    │     │
    │     └── get_lap_data_vectorized(session_id, lap_numbers)
    │             │
    │             └── SQLite → numpy arrays por vuelta
    │
    ▼ data_ready signal → on_data_loaded()
    │
    ├── Detectar pista (heurísticas vs tracks.json)
    ├── Refrescar combos de canales
    └── update_plots()
            │
            ├── Calcular distancia con dt REAL: np.diff(timestamps)
            ├── Speed overlay (por vuelta, por color)
            ├── Inputs overlay (throttle sólido, brake discontinuo)
            ├── Math channel evaluation (DynamicMathEngine)
            ├── Track map (colormap de velocidad)
            ├── G-Force scatter
            ├── Suspension histograms
            ├── Tyre temperatures
            └── Tyre slip ratios
```

### Cálculo de Distancia con dt Real

A diferencia del análisis básico, el workspace profesional **NUNCA** asume 60Hz fijo:

```python
dt = np.diff(lap_time)          # Intervalos reales entre paquetes
dt = np.clip(dt, 0, 0.5)       # Clip para evitar gaps de red > 500ms
dt = np.insert(dt, 0, 0.016)   # Primer punto
distance = np.cumsum(speed_ms * dt)  # Integración trapezoidal
```

---

## Exportación MoTeC

| Propiedad | Valor |
|-----------|-------|
| Formato | `.ld` (datos binarios) + `.ldx` (metadatos XML) |
| Empaquetado | ZIP con ambos archivos |
| Tasa de muestreo | 60 Hz fija |
| Hilo | `MotecExportThread` (QThread) |
| Canales exportados | Speed, RPM, Throttle, Brake, Gear, Boost, Steer, G-Lat, G-Long, 4× Tyre Temps, 4× Susp Velocity |

### Compatibilidad
Los archivos generados son compatibles con **MoTeC i2 Pro** y pueden abrirse directamente para análisis avanzado con las herramientas profesionales de MoTeC.

---

## Persistencia del Layout

Los paneles dock pueden:
- **Flotarse** (arrastrar fuera de la ventana)
- **Tabularse** (apilar en tabs)
- **Reposicionarse** (arrastrar a cualquier borde)
- **Guardarse** (`QSettings` → `"RGDev/GT7TelemetryPro_Workspace"`)
- **Restaurarse** (botón "Restore Panels")
