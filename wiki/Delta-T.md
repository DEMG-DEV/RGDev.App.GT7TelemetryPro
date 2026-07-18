# ⏱️ Delta-T

> **Archivo:** `ui/widgets/delta_widget.py` · **Clase:** `DeltaWidget` · **54 líneas**

El widget Delta-T muestra la diferencia de tiempo entre la vuelta actual y tu mejor vuelta de la sesión, actualizado en tiempo real.

---

## Vista General

```
┌────────────────────────────────────────┐
│  Delta (Current vs Best)               │
│                                        │
│         ──────────── 0.0s ────         │  ← Línea base
│  ████████                              │  ← Verde = más rápido
│                        ████████████    │  ← Rojo = más lento
│                                        │
└────────────────────────────────────────┘
  -10s                              ahora
```

---

## Color Dinámico

| Condición | Color | Significado |
|-----------|-------|-------------|
| `delta < 0` | 🟢 Verde | Vas **más rápido** que tu mejor vuelta |
| `delta > 0` | 🔴 Rojo | Vas **más lento** que tu mejor vuelta |
| `delta = 0` | — | En la línea base |

La línea cambia de color completamente en cada frame según el último valor de delta.

---

## Configuración

| Propiedad | Valor |
|-----------|-------|
| Historial | 600 puntos (~10 segundos) |
| Eje Y | "Delta (s)" con grid activado |
| Fondo | `#FAFAFA` |
| Altura | 150 px (fija) |
| Grosor de línea | 2 px |

---

## Datos de Entrada

El delta proviene de `LapManager.process_packet()` que calcula la diferencia interpolando por distancia recorrida:

```
Delta(d) = Tiempo_actual(d) - Tiempo_mejor(d)
```

Donde `d` es la distancia recorrida en la vuelta actual. Esto permite comparar puntos equivalentes del circuito aunque la velocidad varíe.

---

## API

```python
delta = DeltaWidget()

# Actualizar con delta en milisegundos (llamado a 30Hz)
delta.update_data(delta_ms=-350)  # -350ms = 0.35 segundos más rápido → verde
delta.update_data(delta_ms=120)   # +120ms = 0.12 segundos más lento → rojo
```
