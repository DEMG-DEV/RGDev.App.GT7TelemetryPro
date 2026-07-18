# 🎯 Medidores Circulares

> **Archivo:** `ui/widgets/circular_gauge.py` · **Clase:** `CircularGaugeWidget` · **108 líneas**

Los medidores circulares son indicadores de arco de 270° dibujados con `QPainter`, similares a los relojes de un auto de carreras. Se usan para las 4 métricas principales del dashboard.

---

## Vista General

```
        ╭───────────╮
      ╱   350 km/h    ╲
    ╱                    ╲
   │      ████████        │
   │     ██ 287 ██        │
   │      ████████        │
    ╲     Velocidad      ╱
      ╲    km/h        ╱
        ╰───────────╯
```

---

## Configuración de los 4 Medidores

| Medidor | Rango | Color del Arco | Unidad |
|---------|-------|----------------|--------|
| **Velocidad** | 0 – 350 | Azul (`#2196F3`) | km/h |
| **RPM** | 0 – 10,000 | Naranja (`#FF9800`) | rpm |
| **Turbo/Boost** | 0 – 2.0 | Rojo (`#F44336`) | bar |
| **Temp. Agua** | 50 – 130 | Verde (`#4CAF50`) | °C |

> **Nota:** El medidor de RPM se auto-ajusta dinámicamente al máximo de RPM del auto actual usando `set_max()`.

---

## Anatomía del Widget

| Capa | Descripción | Detalles Técnicos |
|------|-------------|-------------------|
| **Arco de fondo** | Arco gris claro que marca el rango completo | Color `#DCDCDC`, 8px de ancho, caps redondos |
| **Arco de valor** | Arco coloreado proporcional al valor actual | El ángulo se calcula como `(value - min) / (max - min) × 270°` |
| **Texto central** | Valor numérico grande | Monospace bold, 22% del tamaño del widget |
| **Título** | Nombre del medidor (arriba del valor) | 8% del tamaño del widget |
| **Unidad** | Unidad de medida (debajo del valor) | 8% del tamaño del widget |

### Geometría del Arco
- **Ángulo de inicio:** 225° (posición ~7 en punto)
- **Barrido:** -270° (sentido horario, dejando un gap de 90° abajo)
- **Margen:** 10% del ancho total

### Formato del Valor
- Si el rango es ≤ 10 (ej: Turbo 0-2 bar) → 2 decimales: `1.47`
- Si el rango es > 10 (ej: Velocidad 0-350) → 0 decimales: `287`

---

## Tamaño y Responsividad

| Propiedad | Valor |
|-----------|-------|
| Tamaño mínimo | 160 × 160 px |
| Política de tamaño | `Expanding` × `Expanding` |
| Stretch en grid | 3 (mayor que las ruedas y pedales que usan 1) |

El widget se adapta a cualquier tamaño manteniendo las proporciones del arco.

---

## API

```python
gauge = CircularGaugeWidget(
    title="Velocidad",
    min_val=0,
    max_val=350,
    unit="km/h",
    color="#2196F3"
)

gauge.set_value(287.5)   # Actualiza el valor y repinta
gauge.set_max(9500)      # Ajusta el máximo dinámicamente (para RPM)
```
