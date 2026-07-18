# 🎯 Fuerzas G

> **Archivo:** `ui/widgets/gforce_widget.py` · **Clase:** `GForceWidget` · **52 líneas**

El diagrama de Fuerzas G muestra un scatter plot de aceleración lateral (izquierda-derecha) vs longitudinal (aceleración-frenada), conocido como **círculo de tracción** o **traction circle**.

---

## Vista General

```
         Aceleración (+)
              │
              │    ·
         ·    │  · ·
     ─────────┼─────────
    Izquierda │  Derecha
         · ·  │
              │  ·
              │
         Frenada (-)
```

---

## Elementos Visuales

| Elemento | Tamaño | Color | Descripción |
|----------|--------|-------|-------------|
| **Cruz de referencia** | Full span | Gris | Líneas en X=0, Y=0 |
| **Círculo de referencia** | Radio = 1G | Gris | Límite teórico de adherencia |
| **Estela** | 5 px | Naranja | Últimos 100 puntos (historial reciente) |
| **Punto actual** | 10 px | Rojo | Posición G actual |

---

## Configuración

| Propiedad | Valor |
|-----------|-------|
| Rango X | ±2 G |
| Rango Y | ±2 G |
| Aspecto | Bloqueado 1:1 |
| Historial | 100 puntos (`deque(maxlen=100)`) |
| Fondo | `#FAFAFA` |

---

## Interpretación

| Zona del Diagrama | Significado |
|-------------------|-------------|
| Arriba | Aceleración longitudinal fuerte (acelerando fuerte) |
| Abajo | Desaceleración fuerte (frenada) |
| Izquierda | Curva a la izquierda |
| Derecha | Curva a la derecha |
| Diagonal | Combinación de fuerzas (ej: frenada en curva = trail braking) |
| Dentro del círculo de 1G | Dentro del límite de adherencia |
| Fuera del círculo de 1G | Al límite o perdiendo tracción |

### Patrones de Conducción

| Patrón | Indica |
|--------|--------|
| Cluster compacto en el centro | Conducción suave, poca carga |
| Puntos que tocan el círculo | Conducción al límite |
| Distribución simétrica izq-der | Pista balanceada |
| Más puntos abajo que arriba | Más tiempo frenando que acelerando (circuito técnico) |

---

## API

```python
gforce = GForceWidget()

# Agregar punto G (llamado a 60Hz)
gforce.add_point(x=0.8, y=-1.2)  # 0.8G lateral, -1.2G longitudinal (frenada en curva)

# Actualizar visualización
gforce.update_plot()

# Limpiar
gforce.clear()
```
