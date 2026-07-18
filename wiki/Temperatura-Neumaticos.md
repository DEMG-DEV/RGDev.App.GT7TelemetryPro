# 🌡️ Temperatura de Neumáticos

> **Archivo:** `ui/widgets/tyre_temp_gauge.py` · **Clase:** `TyreTempGauge` · **136 líneas**

Los indicadores de temperatura de neumáticos son semicírculos (180°) dibujados con `QPainter.drawArc()` que muestran la temperatura de cada rueda con un gradiente de color dinámico calibrado para Gran Turismo 7.

---

## Vista General

```
    FL              FR
  ╭─────╮        ╭─────╮
  │ 87° │        │ 92° │
  ╰─────╯        ╰─────╯
                        
    RL              RR
  ╭─────╮        ╭─────╮
  │ 71° │        │ 85° │
  ╰─────╯        ╰─────╯
```

---

## Zonas de Color (Calibradas para GT7)

El color del arco se interpola suavemente entre 4 zonas usando interpolación lineal (`_lerp_color`):

| Zona | Rango | Color | Hex | Significado en GT7 |
|------|-------|-------|-----|-------------------|
| 🔵 **Frío** | < 50°C | Azul | `#4285F4` | Sin agarre. Neumático no activado. Calentar antes de atacar. |
| 🟢 **Óptimo** | 50–80°C | Verde | `#2ECC71` | Ventana de operación ideal. Máximo grip mecánico. |
| 🟠 **Caliente** | 80–100°C | Naranja | `#F39C12` | Al límite. Buen grip pero riesgo de degradación acelerada. |
| 🔴 **Sobrecalentamiento** | > 100°C | Rojo | `#E74C3C` | Degradación activa. Reducir agresividad o ajustar presiones. |

### Interpolación de Color

La transición entre zonas es continua, no escalonada. Por ejemplo, a 65°C el color será un verde-azulado intermedio:

```
20°C ───── 50°C ───── 80°C ───── 100°C ───── 140°C
  🔵          🟢          🟠           🔴
  Azul   →  Verde   →  Naranja  →   Rojo
```

---

## Anatomía del Widget

| Capa | Descripción |
|------|-------------|
| **Arco de fondo** | Semicírculo gris claro (`#DCDCDC`), de 0° a 180° |
| **Arco de temperatura** | Semicírculo coloreado, longitud proporcional a la temperatura |
| **Texto de temperatura** | Valor en °C, monospace bold, centrado dentro del semicírculo |
| **Label de posición** | "FL" / "FR" / "RL" / "RR" debajo del semicírculo en gris |

### Rango del Gauge
| Propiedad | Valor |
|-----------|-------|
| Mínimo | 20°C |
| Máximo | 140°C |
| Tamaño mínimo | 60 × 45 px |
| Política de tamaño | `Expanding` × `Expanding` |

---

## Disposición en el Dashboard

Los 4 indicadores se organizan alrededor de las barras de pedales:

```
┌──────────┐  ┌──────────┐  ┌──────────┐
│    FL    │  │ THR  BRK │  │    FR    │
│  ╭───╮   │  │ ▐▌   ▐▌  │  │  ╭───╮   │
│  │87°│   │  │ 78%  0%  │  │  │92°│   │
│  ╰───╯   │  │          │  │  ╰───╯   │
├──────────┤  │          │  ├──────────┤
│    RL    │  │          │  │    RR    │
│  ╭───╮   │  │          │  │  ╭───╮   │
│  │71°│   │  │          │  │  │85°│   │
│  ╰───╯   │  │          │  │  ╰───╯   │
└──────────┘  └──────────┘  └──────────┘
```

### Nomenclatura F1
| Código | Posición | Significado |
|--------|----------|-------------|
| **FL** | Front Left | Delantera Izquierda |
| **FR** | Front Right | Delantera Derecha |
| **RL** | Rear Left | Trasera Izquierda |
| **RR** | Rear Right | Trasera Derecha |

---

## API

```python
gauge = TyreTempGauge(label="FL")  # "FL", "FR", "RL", "RR"
gauge.set_temp(87.3)               # Actualiza temperatura y repinta
```

---

## Guía de Conducción con Temperaturas

| Escenario | Qué hacer |
|-----------|-----------|
| 4 ruedas en 🔵 azul | Calentar neumáticos con zig-zag antes de atacar |
| Frontales en 🟢, traseros en 🔵 | Normal en tracción delantera. Los traseros calentarán con frenadas |
| 1 rueda en 🔴 | Posible bloqueo de rueda o presión incorrecta. Revisar setup |
| 4 ruedas en 🟠/🔴 | Conducción muy agresiva. Reducir ritmo o pit para neumáticos frescos |
| Frontales en 🔴, traseros en 🟢 | Subviraje. Reducir ángulo de dirección o ablandar suspensión delantera |
