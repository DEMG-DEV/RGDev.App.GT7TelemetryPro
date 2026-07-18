# 📂 Historial y Análisis

> **Archivo:** `ui/widgets/advanced_analysis_dialog.py` · **Clase:** `AdvancedAnalysisDialog` · **777 líneas**

La vista de Historial y Análisis es un diálogo a pantalla completa que permite navegar sesiones grabadas, reproducirlas, comparar múltiples vueltas en overlay y analizar el rendimiento post-carrera.

![Análisis](https://raw.githubusercontent.com/DEMG-DEV/RGDev.App.GT7TelemetryPro/master/docs/analysis_mode.png)

---

## Layout de 3 Columnas (25:50:25)

```
┌───────────────┬─────────────────────────────────┬───────────────┐
│  IZQUIERDA    │          CENTRO                 │   DERECHA     │
│  (25%)        │          (50%)                  │   (25%)       │
│               │                                 │               │
│  Sesiones     │   Gráfica de Velocidad          │  Mapa         │
│  (tabla)      │   (overlay multi-vuelta)        │  Interactivo  │
│               │                                 │               │
│  ▶ Playback   │   ───────── crosshair ─────     │  (con         │
│  ⏸ Pausa      │                                 │   crosshair)  │
│  ━━━━ slider  │   Resumen de Vueltas            │               │
│               │   (tabla comparativa)           │  Dashboard    │
│  Vueltas      │                                 │  Compacto     │
│  ☑ Lap 1      │                                 │  (velocidad,  │
│  ☑ Lap 2 ★    │                                 │   marcha,     │
│  ☐ Lap 3      │                                 │   pedales,    │
│               │                                 │   RPM)        │
└───────────────┴─────────────────────────────────┴───────────────┘
```

---

## Panel Izquierdo — Sesiones y Vueltas

### Tabla de Sesiones (stretch=6)

| Columna | Contenido |
|---------|-----------|
| ID | Número de sesión |
| Fecha | Timestamp de inicio |
| Auto | Nombre del auto |
| Vueltas | Total de vueltas completadas |
| Mejor Vuelta | Mejor tiempo de la sesión |

**Acciones por sesión:**

| Botón | Función | Restricciones |
|-------|---------|---------------|
| 🔒 Bloquear | Activa `is_locked = 1` en la BD | Protege contra borrado accidental |
| 🔓 Desbloquear | Desactiva `is_locked = 0` | — |
| 🗑️ Eliminar | Borra sesión + telemetría + VACUUM | Deshabilitado si la sesión está bloqueada |

### Controles de Playback

| Control | Función |
|---------|---------|
| ▶ / ⏸ | Reproducir / Pausar la sesión seleccionada |
| Slider horizontal | Navegar temporalmente por la sesión |
| Label de tiempo | Muestra el timestamp actual de reproducción |
| Label mejor vuelta | Muestra el mejor tiempo de la sesión |

**Atajos de teclado:**

| Tecla | Acción |
|-------|--------|
| `Espacio` | Play / Pausa |
| `←` Flecha izq. | Retroceder 1 segundo |
| `→` Flecha der. | Avanzar 1 segundo |

### Lista de Vueltas (stretch=4)

- Título: "Vueltas (Multiselección)"
- Cada vuelta es un item checkable en `QListWidget`
- La mejor vuelta se marca con ★ y se pre-selecciona
- Seleccionar/deseleccionar vueltas actualiza la gráfica de overlay

---

## Panel Centro — Gráfica y Resumen

### Gráfica de Velocidad (overlay multi-vuelta)

- **Eje X:** Distancia recorrida (metros) — calculada por integración `speed × dt`
- **Eje Y:** Velocidad (km/h)
- **Overlay:** Cada vuelta seleccionada se dibuja con un color diferente + leyenda
- **Crosshair vertical:** Línea que sigue el cursor del mouse y se sincroniza con el mapa

### Interacción del Mouse

Al mover el cursor sobre la gráfica de velocidad:
1. La línea vertical del crosshair sigue la posición X
2. Se calcula el punto más cercano en la distancia
3. El crosshair del mapa se mueve a la posición XZ correspondiente en la pista

La sincronización se implementa con `SignalProxy` de pyqtgraph para limitar a 60 actualizaciones/segundo.

### Tabla Resumen de Vueltas

Tabla dinámica que muestra métricas por cada vuelta seleccionada:

| Métrica | Descripción |
|---------|-------------|
| Velocidad Máxima | km/h máximo alcanzado en la vuelta |
| Vel. Mínima en Curva | km/h mínimo (punto más lento de la vuelta) |
| % Full Throttle | Porcentaje del tiempo con acelerador al 100% |
| % Braking | Porcentaje del tiempo aplicando freno |

Cada fila se colorea con el mismo color de la curva en el overlay.

---

## Panel Derecho — Mapa y Dashboard

### Mapa Interactivo (stretch=6)
- Misma clase `MapWidget` que el dashboard en vivo
- Muestra el trazado de la vuelta seleccionada con heatmap (freno/acelerador)
- **Crosshair rojo** sincronizado con el cursor del centro

### Dashboard Compacto (stretch=4)
Widget `LiveTelemetryWidget` que muestra durante el playback:

```
┌──────────────────────────────────┐
│  287        3        THR ▐▌ BRK │
│  km/h     GEAR       78%    0%  │
│                                  │
│  ████████████████ 7200 RPM       │
└──────────────────────────────────┘
```

| Elemento | Tamaño | Color |
|----------|--------|-------|
| Velocidad | 36px bold | Azul |
| Marcha | 42px bold | Naranja |
| Pedales THR | Barra vertical | Verde gradiente |
| Pedales BRK | Barra vertical | Rojo gradiente |
| RPM | Barra horizontal | Gradiente azul→naranja→rojo |

---

## Detección Automática de Pista

Al cargar una sesión, el sistema identifica automáticamente el circuito usando heurísticas:

1. **Calcula la mediana de distancia** de las vueltas completas (excluyendo out-lap/in-lap)
2. **Compara contra `tracks.json`** (122+ pistas) usando:
   - Distancia del trazado (tolerancia del 15%)
   - Diferencia de elevación
   - Número de curvas
3. **Muestra el resultado** en la UI si hay match

---

## Procesamiento de Datos

### Carga de Sesión
```
SQLite (raw_packet BLOB)
    │
    ▼ parse_telemetry_packet()
    │
    ▼ GT7TelemetryPacket (por cada fila)
    │
    ▼ Agrupar por lap_count
    │
    ▼ Por cada vuelta:
        ├── Distancia = Σ(speed × dt)  
        ├── Arrays numpy: speed, throttle, brake, rpm, steer, pos_x, pos_z
        └── Filtrar out-lap/in-lap (vueltas con < 50% de la mediana de distancia)
```

### Filtrado de Vueltas
- **Out-lap**: Primera vuelta (generalmente incompleta, desde pit lane)
- **In-lap**: Última vuelta si el piloto entró a pits
- **Criterio**: Vueltas con distancia < 50% de la mediana se excluyen automáticamente
