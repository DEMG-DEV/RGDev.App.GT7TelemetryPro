# 🚨 Alertas Pit-Wall

> **Archivo:** `ui/widgets/alert_widget.py` · **Clase:** `AlertWidget` · **96 líneas**

El sistema de alertas Pit-Wall simula las comunicaciones de un equipo de carreras profesional, notificando al piloto sobre eventos críticos durante la sesión.

---

## Vista General

```
┌──────────────────────────────────────┐
│  Pit-Wall Alerts                     │
│                                      │
│  ┌─ 🔴 CRITICAL ─────────────────┐  │
│  │ ⚠️ OVERHEATING                 │  │
│  │ Rear Left tyre > 110°C        │  │
│  └────────────────────────────────┘  │
│                                      │
│  ┌─ 🟡 WARNING ──────────────────┐  │
│  │ ⛽ LOW FUEL                    │  │
│  │ ~3 laps remaining             │  │
│  └────────────────────────────────┘  │
│                                      │
│  ┌─ 🔵 INFO ─────────────────────┐  │
│  │ 🏁 NEW BEST LAP               │  │
│  │ 1:42.387                      │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

---

## Niveles de Severidad

| Nivel | Color Fondo | Color Texto | Borde | Duración | Sonido |
|-------|-------------|-------------|-------|----------|--------|
| **INFO** | Azul (`#2E86C1`) | Blanco | — | 5 segundos | No |
| **WARNING** | Naranja (`#F39C12`) | Negro | — | 5 segundos | ✅ Beep |
| **CRITICAL** | Rojo (`#C0392B`) | Blanco | Amarillo 2px | 10 segundos | ✅ Beep |

---

## Tipos de Alertas (generadas por `AlertEngine`)

| Alerta | Nivel | Condición |
|--------|-------|-----------|
| Sobrecalentamiento neumático | CRITICAL | Temp > umbral por X segundos |
| Combustible bajo | WARNING | Quedan < 3 vueltas estimadas |
| Combustible crítico | CRITICAL | Queda < 1 vuelta estimada |
| Temperatura de agua alta | WARNING | Temp agua > umbral |
| Over-rev (sobrerrevolución) | WARNING | RPM cerca del corte |
| Nueva mejor vuelta | INFO | Vuelta actual < mejor vuelta previa |

### Sistema de Cooldown

Cada tipo de alerta tiene un **cooldown** configurable para evitar spam. Si una alerta se disparó recientemente, no se mostrará de nuevo hasta que pase el periodo de enfriamiento.

---

## Sonido de Alerta

El sonido se genera automáticamente si no existe el archivo `pro_beep.wav`:

| Propiedad | Valor |
|-----------|-------|
| Frecuencia | 1800 Hz |
| Duración | 250 ms |
| Forma de onda | Seno con envolvente |
| Formato | WAV, 44100 Hz, mono |

Se reproduce vía `QSoundEffect` de PyQt6 Multimedia.

---

## Comportamiento

| Propiedad | Valor |
|-----------|-------|
| Máximo visible | 3 alertas simultáneas |
| Overflow | La alerta más antigua se elimina automáticamente |
| Auto-dismiss | Timer individual por alerta (5s o 10s según severidad) |
| Posición | Panel inferior derecho del dashboard |

---

## API

```python
alerts = AlertWidget()

# Empujar una alerta
alerts.push_alert(
    severity="CRITICAL",    # "INFO", "WARNING", "CRITICAL"
    title="⚠️ OVERHEATING",
    message="Rear Left tyre > 110°C"
)
```
