# 📋 Registro Técnico de Cambios

> Documento generado automáticamente con cada commit realizado en el proyecto.
> Contiene el detalle técnico completo de cada cambio para el equipo de desarrollo.

---

## Feature: Arquitectura Analítica F1 y Persistencia SQLite

| Campo | Detalle |
|-------|---------|
| **Fecha** | 2026-07-12 14:52:00 |
| **Autor** | David Mendez (demg@outlook.com) |
| **Branch** | master |
| **Tipo** | Feature / Refactor |

### Archivos Modificados

| Archivo | Estado | Descripción del Cambio |
|---------|--------|----------------------|
| `core/database.py` | Agregado | Nuevo hilo asíncrono con `sqlite3` y pragma `WAL` para registrar telemetría masiva a 60Hz. |
| `core/lap_manager.py` | Agregado | Lógica de segmentación de vueltas y generación de *Ghost* dinámico para cálculo de Delta en milisegundos. |
| `core/math_channels.py` | Agregado | Motor matemático (`MathEngine`) para derivar *Slip Angle*, consumo delta de combustible y métricas WOT. |
| `core/alert_engine.py` | Agregado | Motor de notificaciones paramétricas para excesos térmicos de motor y neumáticos. |
| `services/live_client.py` | Modificado | Migración del antiguo volcado binario (`.gt7`) a la inyección asíncrona hacia `SessionDatabaseWriter`. |
| `services/replay_player.py` | Modificado | Eliminación de retrocompatibilidad `.gt7` cruda; ahora sólo consume `SELECT` estructurados desde `.sqlite`. |
| `ui/main_window.py` | Modificado | Ensamblado integral de los 4 nuevos motores. Adición de widgets (Delta, Alerts) y etiquetas métricas calculadas. |
| `ui/widgets/map_widget.py` | Modificado | Transformación de mapa de rutas estático a `ScatterPlotItem` dinámico mapeando frenadas (Rojo) y aceleración plena (Verde). |
| `ui/widgets/delta_widget.py` | Agregado | Renderizado lineal +/- de ganancia/pérdida de milisegundos. |
| `ui/widgets/alert_widget.py` | Agregado | Sistema de avisos Pit-Wall con emisión acústica global. |
| `.ai/architecture.md` | Modificado | Inclusión de la nueva capa de motores Core y el hilo DB a la documentación. |
| `README.md` | Modificado | Reescritura como herramienta F1/Le Mans con screenshot actualizado `docs/ui_screenshot.png`. |

### Detalle Técnico

Se ha elevado sustancialmente la aplicación de un simple "Live Viewer" a una **Plataforma Analítica de Telemetría Nivel F1**. Se erradicó el antiguo esquema de guardado opaco en archivos crudos `.gt7`, rediseñándolo sobre bases de datos locales **SQLite** con pragma `journal_mode=WAL`, lo que garantiza latencia cero durante operaciones `executemany` en la capa de persistencia `database.py`.

El `LapManager` ahora almacena vectores relacionales de `[distancia, tiempo]` por vuelta, interpolando mediante búsqueda binaria y geometría lineal el Delta-Time contra la vuelta de referencia del usuario (Ghosting). El `MathEngine` deriva señales virtuales como "Laps Remaning" en base al Delta de consumo cruzando la línea de meta, y el `MapWidget` ahora es térmico, consumiendo más memoria (limitado a 10,000 puntos en buffer circular para pistas enormes como Nordschleife) para delinear las zonas de derrape y agresividad de aceleración.

### Fragmentos de Código Relevantes

```diff
-        # Old _playback_loop in replay_player.py
-        with open(self.filename, 'rb') as f:
-             # raw binary struct parsing
+        # New SQLite streaming
+        with sqlite3.connect(self.filename) as conn:
+            cursor = conn.cursor()
+            cursor.execute("SELECT timestamp, raw_packet FROM telemetry ORDER BY id")
+            for row in cursor:
+                packet_timestamp, payload = row
```

---

## Fix: Rediseño de red UDP y correcciones de estados visuales UI

| Campo | Detalle |
|-------|---------|
| **Fecha** | 2026-07-12 13:06:00 |
| **Autor** | David Mendez (demg@outlook.com) |
| **Branch** | master |
| **Tipo** | Bug Fix / Documentation |

### Archivos Modificados

| Archivo | Estado | Descripción del Cambio |
|---------|--------|----------------------|
| `services/live_client.py` | Modificado | Implementación de doble heartbeat simultáneo (Broadcast y Unicast) utilizando el mismo socket receptor para aplicar UDP hole-punching natural en el firewall. |
| `ui/main_window.py` | Modificado | Corrección de falsos positivos en el estado de conexión para que indique "Esperando telemetría" hasta recibir la primera trama de datos comprobable, en lugar de simular conexión instantánea. |
| `.ai/architecture.md` | Modificado | Refleja la arquitectura moderna con el patrón de directorios separados (`core/`, `services/`, `ui/`) para futura asimilación de IA. |
| `README.md` | Modificado | Reescritura completa del documento. Estilo moderno, medallas visuales (badges) e instrucciones explícitas de conexión. |

### Detalle Técnico

Se resolvió una ambigüedad engañosa en la interfaz antigua que forzaba visualmente un estado "Connected" tan pronto se presionaba el botón, independientemente de si el tráfico UDP era exitoso. 
En el lado de red, se detectó que GT7 es altamente sensible a la procedencia del *heartbeat*. Se refactorizó `_heartbeat_loop` para deshacerse de sockets dedicados e inyectar el *payload* usando el propio `self.sock` de captura, disparándolo bidireccionalmente: hacia la IP local (si se especificó) y hacia la IP broadcast global (`255.255.255.255`). Esto no solo incrementa radicalmente el éxito de enlace con la consola, sino que entrena a *firewalls* estrictos (macOS) a esperar tráfico entrante en el puerto local 33740 como respuesta legítima de una conexión saliente.


## Refactor: Arquitectura modular, MVC y extracción de componentes UI

| Campo | Detalle |
|-------|---------|
| **Fecha** | 2026-07-12 12:03:00 |
| **Autor** | David Mendez (demg@outlook.com) |
| **Branch** | master |
| **Tipo** | Refactor |

### Archivos Modificados

| Archivo | Estado | Descripción del Cambio |
|---------|--------|----------------------|
| `main.py` | Modificado | Refactorizado de 603 a 19 líneas como puro entry point. |
| `ui/main_window.py` | Agregado | Orquesta la ventana principal aislando el QTimer y el layout. |
| `ui/widgets/*` | Agregado | Separación de UI en `map_widget.py`, `gforce_widget.py`, `telemetry_graphs.py`. |
| `ui/styles/dark_theme.qss` | Agregado | Extracción del estilo bruto. |
| `core/models.py` | Renombrado | Trasladado desde la raíz hacia el core. |
| `core/car_database.py` | Agregado | Lógica Singleton para inyectar los autos, aislandola de `main.py`. |
| `services/live_client.py` | Renombrado | `client.py` heredando ahora de `TelemetryProvider`. |
| `services/replay_player.py` | Renombrado | `player.py` heredando ahora de `TelemetryProvider`. |
| `services/crypto.py` | Renombrado | Decodificación Salsa20 reubicada. |

### Detalle Técnico

Se llevó a cabo una refactorización masiva y profunda eliminando el síndrome de "Archivo Monolítico". El proyecto abandonó su estructura de script para tomar forma de sistema modular con patrón MVC/Servicios. Se introdujo polimorfismo con una clase base abstracta `TelemetryProvider` de la que ahora heredan los emisores de red y reproductores de grabaciones, estandarizando la emisión del paquete procesado en la misma señal de PyQt. Los componentes del Dashboard pasaron de estar amontonados a ser Widgets completamente autónomos, responsables únicamente de su propia representación, mejorando la escalabilidad del sistema y su testabilidad de cara al futuro.


## Refactorización UI asíncrona, fix de telemetría y nombres de autos

| Campo | Detalle |
|-------|---------|
| **Fecha** | 2026-07-12 11:46:00 |
| **Autor** | David Mendez (demg@outlook.com) |
| **Branch** | master |
| **Tipo** | Refactor / Bug Fix / Feature |

### Archivos Modificados

| Archivo | Estado | Descripción del Cambio |
|---------|--------|----------------------|
| `main.py` | Modificado | Refactor asíncrono con QTimer (30 FPS), nueva interfaz apilada (GT7 native), y consumo de DB de autos. |
| `models.py` | Modificado | Corrección de empaquetado de memoria (Flags uint16) que causaba desfasaje de 2 bytes en marchas y pedales. |
| `client.py` | Modificado | Solucionado crash silencioso en hilo de grabación al faltar `import struct`. |
| `player.py` | Agregado | Lógica de reproducción de sesiones `.gt7` guardadas con simulación de tiempo real. |
| `gt7_cars.json` | Agregado | Base de datos de 575 autos para traducir el `car_code` a nombres reales. |
| `download_cars.py` | Agregado | Script automatizado para descargar y consolidar DB de GT7 desde fuentes comunitarias. |
| `capture_ui.py` | Agregado | Script headless con QTimer para capturar pantalla. |
| `screenshot.png` | Agregado | Captura visual de la UI. |
| `README.md` | Modificado | Agregada captura de pantalla en la cabecera. |

### Detalle Técnico

- **Arquitectura UI Asíncrona:** Se desacopló la recepción de red de la renderización UI en `main.py`. El hilo de red ahora deposita el paquete en memoria caché (`_cache_packet`), y un `QTimer` independiente se encarga de refrescar los widgets y gráficas estrictamente a 30 Hz. Esto erradica los cuelgues (freezes) al cargar replays pesados.
- **Bug Fix de Desfasaje de Memoria:** La documentación técnica indicaba que la variable `flags` era `uint32` (4 bytes). Mediante volcados hexagonales de las tramas se comprobó que es `uint16` (2 bytes). Esto causaba que `gears`, `throttle` y `brake` estuvieran desalineados leyendo basura de los floats subsiguientes. Se corrigió el string de empaquetado `format_A` encajando todo a exactamente 296 bytes.
- **Auto-Guardado:** Se resolvió un error en `client.py` que dejaba los archivos binarios en 0 bytes debido a la falta de `import struct`. Se redirigieron todos los volcados binarios al directorio `/Sessions`.
- **Integración Base de Datos de Autos:** Se incorporó el mapeo JSON `gt7_cars.json` cargado al inicio de la aplicación en un diccionario para traducir `packet.car_code` en cadenas de texto en tiempo real con una penalización `O(1)`.

### Fragmentos de Código Relevantes

```diff
-    format_A = '<i9ff3f2fI7f4fi2h3i5hI4B4f12f8f4f8fi'
+    format_A = '<i9ff3f2fI7f4fi2h3i5hH4B4f12f8f4f8fi'
```
```diff
-        self.packet_signal.connect(self.update_dashboard)
+        self.ui_timer = QTimer()
+        self.ui_timer.timeout.connect(self.update_dashboard_ui)
+        self.ui_timer.start(33) # ~30 FPS UI refresh
+        self.packet_signal.connect(self._cache_packet)
```

---

## Initial commit: Implement GT7 Telemetry Pro desktop application

| Campo | Detalle |
|-------|---------|
| **Fecha** | 2026-07-12 09:33:10 |
| **Autor** | David Mendez (demg@outlook.com) |
| **Branch** | master |
| **Tipo** | Feature |

### Archivos Modificados

| Archivo | Estado | Descripción del Cambio |
|---------|--------|----------------------|
| `models.py` | Agregado | Implementación de las estructuras de datos y dataclass para deserializar el paquete de telemetría (paquetes A, B, ~, C) de GT7. |
| `crypto.py` | Agregado | Implementación del pipeline de descifrado Salsa20 y generación del Nonce dinámico basado en las constantes XOR de Gran Turismo. |
| `client.py` | Agregado | Cliente UDP asíncrono y multihilo. Contiene la lógica de auto-descubrimiento mediante broadcast IP y el ciclo de latidos (heartbeat). |
| `main.py` | Agregado | Punto de entrada principal con la interfaz gráfica usando PyQt6 y `pyqtgraph`. Renderizado nativo a 60 FPS sin usar tecnologías web. |
| `requirements.txt` | Agregado | Definición de las dependencias (`pycryptodome`, `PyQt6`, `pyqtgraph`, `numpy`). |
| `.ai/architecture.md` | Agregado | Reglas de contexto y arquitectura para IA en el proyecto. |
| `.gitignore` | Agregado | Ignora los entornos virtuales y archivos temporales de Python. |
| `README.md` | Modificado | Documentación detallada con características de la aplicación y modo de uso. |

### Detalle Técnico

Se ha desarrollado la versión inicial completa de **GT7 Telemetry Pro**. La aplicación lee el flujo de telemetría de Gran Turismo 7 interceptando los paquetes UDP por el puerto 33740. Se implementó una arquitectura Productor-Consumidor usando tres hilos separados para evitar la pérdida de paquetes (Packet Drop) y cuellos de botella en la renderización gráfica. El cliente descifra los datos utilizando `Salsa20`, decodifica la estructura binaria en formato *Little-Endian*, y expone un objeto `GT7TelemetryPacket`. 

El frontend se construyó exclusivamente en **PyQt6** como se requirió, evitando cualquier tipo de motor web. Las gráficas (velocidad, acelerador, freno, RPM) se renderizan en tiempo real mediante `pyqtgraph`.

### Fragmentos de Código Relevantes

```python
# Ejemplo de uso de auto-descubrimiento en client.py
if not self.console_ip:
    self.console_ip = addr[0]
    if self.on_connection_established:
        self.on_connection_established(self.console_ip)
```

---
