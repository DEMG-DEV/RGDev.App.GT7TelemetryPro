# 🗺️ Mapa de Pista

> **Archivo:** `ui/widgets/map_widget.py` · **Clase:** `MapWidget` · **70 líneas**

El mapa de pista dibuja el trazado del circuito en tiempo real usando las coordenadas XZ del auto, coloreando cada punto según la acción del piloto (aceleración, frenada o inercia).

---

## Vista General

El mapa muestra un scatter plot con aspecto bloqueado (1:1) sobre fondo `#FAFAFA`, sin ejes visibles. Cada punto del trazado se colorea dinámicamente:

| Acción | Color | Condición |
|--------|-------|-----------|
| **Frenada** | 🔴 Rojo (intensidad variable) | `brake > 0` — intensidad proporcional al valor |
| **Aceleración** | 🟢 Verde (intensidad variable) | `throttle > 0` y `brake == 0` — intensidad proporcional |
| **Inercia** | ⚪ Gris claro | Ni acelerador ni freno aplicados |

### Elementos Visuales

| Elemento | Tamaño | Color | Descripción |
|----------|--------|-------|-------------|
| **Puntos del trazado** | 4 px | Variable (heatmap) | Historial de posiciones coloreadas |
| **Punto del auto** | 10 px | Negro | Posición actual del vehículo |
| **Crosshair** | 15 px | Rojo '+' | Cursor de análisis (modo playback) |

---

## Buffer de Datos

| Propiedad | Valor |
|-----------|-------|
| Tipo | `collections.deque` |
| Capacidad máxima | 10,000 puntos |
| Suficiente para | Nürburgring Nordschleife (~20 km) |

Se almacenan 4 deques sincronizados: posición X, posición Z, colores de borde y colores de relleno.

---

## Cálculo de Color

```python
if brake > 0:
    intensity = brake / 255  # 0.0 → 1.0
    color = (255 * intensity, 0, 0)  # Rojo gradual
elif throttle > 0:
    intensity = throttle / 255
    color = (0, 255 * intensity, 0)  # Verde gradual
else:
    color = (200, 200, 200)  # Gris (coasting)
```

---

## API

```python
map_widget = MapWidget()

# Agregar punto (llamado a 60Hz)
map_widget.add_point(x=1234.5, z=-567.8, throttle=200, brake=0)

# Actualizar visualización (llamado a 30Hz)
map_widget.update_plot()

# Mover crosshair (modo análisis)
map_widget.set_crosshair(x=1234.5, z=-567.8)

# Limpiar todo
map_widget.clear()
```
