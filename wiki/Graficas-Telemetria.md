# 📊 Gráficas de Telemetría

> **Archivo:** `ui/widgets/telemetry_graphs.py` · **Clase:** `TelemetryGraphsWidget` · **78 líneas**

Tres gráficas apiladas verticalmente que muestran un historial de 10 segundos de las métricas principales de conducción.

---

## Vista General

```
┌────────────────────────────────────────┐
│  Velocidad (km/h)                      │
│  ~~~~~~~~~~~~~~~~~~~~~~~~~~~ 287       │  ← Línea azul
│                                        │
├────────────────────────────────────────┤
│  Acelerador / Freno (%)                │
│  ███████████████████ 78%               │  ← Verde = Acelerador (relleno)
│  ██████ 23%                            │  ← Rojo = Freno (relleno)
├────────────────────────────────────────┤
│  R.P.M.                               │
│  ~~~~~~~~~~~~~~~~~~~~~~~~~~~ 7,200     │  ← Línea naranja oscuro
│                                        │
└────────────────────────────────────────┘
  -10s                              ahora
```

---

## Configuración de Canales

| Canal | Color | Hex | Relleno | Puntos |
|-------|-------|-----|---------|--------|
| **Velocidad** | Azul | `#0000FF` | No | 600 |
| **Acelerador** | Verde | `#008000` | Sí (semi-transparente) | 600 |
| **Freno** | Rojo | `#FF0000` | Sí (semi-transparente) | 600 |
| **RPM** | Naranja Oscuro | `#FF8C00` | No | 600 |

---

## Detalles Técnicos

| Propiedad | Valor |
|-----------|-------|
| Historial | 600 puntos (~10 segundos a 60Hz) |
| Eje X | Pre-computado: `np.linspace(-10, 0, 600)` |
| Fondo | `#FAFAFA` |
| Layout | `GraphicsLayoutWidget` con 3 rows |
| Actualización de datos | `np.roll()` sobre arrays de numpy |

### Flujo de Datos

```
_cache_packet() @ 60Hz
    │
    └── graphs_widget.add_data(speed, throttle, brake, rpm)
            │
            └── np.roll() en 4 arrays de 600 elementos

update_dashboard_ui() @ 30Hz
    │
    └── graphs_widget.update_plot()
            │
            └── setData() en 4 curvas de pyqtgraph
```

---

## API

```python
widget = TelemetryGraphsWidget()

# Agregar un punto de datos (llamado a 60Hz)
widget.add_data(speed=287.5, throttle=200, brake=0, rpm=7200)

# Actualizar las gráficas visualmente (llamado a 30Hz)
widget.update_plot()

# Limpiar todo
widget.clear()
```
