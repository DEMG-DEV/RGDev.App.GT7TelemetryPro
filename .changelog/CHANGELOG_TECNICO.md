# 📋 Registro Técnico de Cambios

> Documento generado automáticamente con cada commit realizado en el proyecto.
> Contiene el detalle técnico completo de cada cambio para el equipo de desarrollo.

---

## Docs: Actualización de screenshots y especificaciones de IA (Light Mode)

| Campo | Detalle |
|-------|---------|
| **Fecha** | 2026-07-13 08:52:07 |
| **Autor** | David Mendez (demg@outlook.com) |
| **Branch** | master |
| **Tipo** | Docs |

### Archivos Modificados

| Archivo | Estado | Descripción del Cambio |
|---------|--------|----------------------|
| `.agents/AGENTS.md` | Modificado | Inclusión de directriz estricta para forzar diseños "Modo Diurno" en la generación de GUI por agentes. |
| `.ai/architecture.md` | Modificado | Actualización de la documentación de capa UI señalando la implementación de esquemas de alto contraste diurno. |
| `README.md` | Modificado | Adición de nota de diseño sobre el entorno Pit-Wall y regeneración de las miniaturas de documentación. |
| `docs/main_window.png` | Modificado | Captura actualizada del dashboard principal en Modo Claro. |
| `docs/analysis_mode.png` | Modificado | Captura actualizada de la herramienta de Análisis Avanzado exhibiendo el renderizado SQLite en Modo Claro. |

### Detalle Técnico

Se actualizaron los archivos de contexto persistente del repositorio para reflejar la última migración arquitectónica a una interfaz de modo diurno (*Light Mode*). Se inyectaron comandos en `.agents/AGENTS.md` para obligar a los agentes IA a respetar la paleta diurna de colores de aquí en adelante.
Además, se ejecutó un script iterativo usando `QTimer` para instanciar las ventanas PyQt6 de forma asíncrona, conectarse a la BD `telemetry_master.sqlite` para poblar datos y emplear `QWidget.grab()` con el fin de generar las nuevas capturas de pantalla de la interfaz actualizada en el directorio `docs/`.

---

## Refactor: Implementación de tema visual "Daylight" (Light Mode)

| Campo | Detalle |
|-------|---------|
| **Fecha** | 2026-07-13 08:42:18 |
| **Autor** | David Mendez (demg@outlook.com) |
| **Branch** | master |
| **Tipo** | Refactor / Style |

### Archivos Modificados

| Archivo | Estado | Descripción del Cambio |
|---------|--------|----------------------|
| `ui/styles/dark_theme.qss` | Modificado | Reescritura completa del stylesheet general para usar paleta de colores claros. |
| `ui/main_window.py` | Modificado | Sustitución de colores de alto contraste oscuros por colores aptos para fondos blancos (negros, grises oscuros, rojo, azul). |
| `ui/widgets/advanced_analysis_dialog.py` | Modificado | Ajuste de colores en la tabla de sesiones, sliders, y corrección de colores hardcodeados en `setForeground`. |
| `ui/widgets/live_telemetry_widget.py` | Modificado | Adaptación de barras de progreso y corrección de instanciación de etiquetas. |
| `ui/widgets/telemetry_graphs.py` | Modificado | Cambio de `setBackground` a gris claro (`#FAFAFA`) y oscurecimiento de trazos. |
| `ui/widgets/gforce_widget.py` | Modificado | Eliminación de fondo gris oscuro hardcodeado, ajuste de mira a gris claro. |
| `ui/widgets/map_widget.py` | Modificado | Ajuste de punto del auto a negro para contraste en fondo transparente/blanco. |

### Detalle Técnico

Se llevó a cabo una migración de estética para pasar de un entorno nativo oscuro a un esquema "Light Mode" enfocado en uso diurno. Se eliminó el negro de los paneles de fondo priorizando blancos y grises claros (`#F0F0F0`, `#FAFAFA`, `#FFFFFF`) con texto gris oscuro (`#1A1A1A`).
Los gráficos de `pyqtgraph` fueron invertidos:
- Velocidad: Blanco a Azul Puro (`#0000FF`).
- Acelerador/Freno: Degradados convertidos a tonos sólidos oscuros.
Se detectó y solucionó la existencia de colores cian hardcodeados a través de `setForeground()` en las celdas de las tablas de `advanced_analysis_dialog.py` que impedían la correcta lectura.

### Fragmentos de Código Relevantes

```diff
-        self.plot_stack = pg.GraphicsLayoutWidget()
-        self.plot_stack.setBackground('#000000')
+        self.plot_stack = pg.GraphicsLayoutWidget()
+        self.plot_stack.setBackground('#FAFAFA')
```
```diff
-                id_item.setForeground(QColor('#66fcf1') if not is_locked else QColor('#f44336'))
+                id_item.setForeground(QColor('#0000FF') if not is_locked else QColor('#CC0000'))
```

---

## feat: Grabación manual de sesiones y auto-corrección dinámica del ID del vehículo

| Campo | Detalle |
|-------|---------|
| **Fecha** | 2026-07-12 23:02:20 |
| **Autor** | Antigravity AI |
| **Branch** | master |
| **Tipo** | Feature / Bug Fix |

### Archivos Modificados

| Archivo | Estado | Descripción del Cambio |
|---------|--------|----------------------|
| `ui/main_window.py` | Modificado | Se reemplazó el inicio automático de grabación por un sistema manual con botón conmutador de Iniciar/Detener. |
| `core/database.py` | Modificado | Se implementó un algoritmo dinámico que registra la frecuencia de `car_id` durante toda la sesión y sobreescribe la metadata final de la sesión al detenerse. |
| `.agents/AGENTS.md` | Modificado | Se añadió la regla de arquitectura sobre "Identidad del Auto Dinámica". |
| `README.md` | Modificado | Se documentaron los nuevos controles de grabación manual y el algoritmo dinámico de identificación de vehículos. |

### Detalle Técnico

Anteriormente, la aplicación bloqueaba el nombre y el ID del vehículo de la sesión basado enteramente en el **primer** paquete de telemetría recibido (`packet.car_code`). Esto generaba un bug severo durante el Campeonato del Café (o cualquier carrera con IA), dado que durante la cinemática de la parrilla de salida, GT7 transmite la telemetría de los oponentes si la cámara los enfoca, corrompiendo la metadata de la sesión (ej. registrando un Honda S800 cuando el jugador conducía un Corvette C7).

Para solucionarlo, se desacopló el auto-guardado:
- Se eliminó el flujo asíncrono pasivo en favor de un sistema *Event-Driven* manual (`toggle_recording`).
- En `SessionDatabaseWriter`, se implementó un tracking pasivo `self.car_id_counts` que cuenta estadísticamente la incidencia de todos los IDs recibidos por UDP.
- En la función `stop()`, la BD ejecuta un `UPDATE` inteligente utilizando `max(self.car_id_counts, key=self.car_id_counts.get)` para consolidar el vehículo definitivo de la sesión.

### Fragmentos de Código Relevantes

```diff
-        # Cerrar la sesión
-        end_time = datetime.datetime.now().isoformat()
-        with sqlite3.connect(self.db_path) as conn:
-            conn.execute(
-                "UPDATE sessions SET end_time = ?, total_laps = ?, best_laptime = ? WHERE id = ?",
-                (end_time, self.total_laps, self.best_laptime, self.session_id)
-            )
+        # Cerrar la sesión
+        final_car_id = max(self.car_id_counts, key=self.car_id_counts.get) if self.car_id_counts else None
+        end_time = datetime.datetime.now().isoformat()
+        with sqlite3.connect(self.db_path) as conn:
+            if final_car_id is not None:
+                # ... (get car_name)
+                conn.execute(
+                    "UPDATE sessions SET end_time = ?, total_laps = ?, best_laptime = ?, car_id = ?, car_name = ? WHERE id = ?",
+                    (end_time, self.total_laps, self.best_laptime, final_car_id, final_car_name, self.session_id)
+                )
```

---

## CI/CD: Pipeline de compilación multiplataforma (Release v1.0.0)

| Campo | Detalle |
|-------|---------|
| **Fecha** | 2026-07-12 14:56:00 |
| **Autor** | David Mendez (demg@outlook.com) |
| **Branch** | master |
| **Tipo** | Configuration / CI-CD |

### Archivos Modificados

| Archivo | Estado | Descripción del Cambio |
|---------|--------|----------------------|
| `core/car_database.py` | Modificado | Inyección del helper `resource_path` utilizando `sys._MEIPASS` para mapear el empaquetado interno de recursos JSON generados por PyInstaller. |
| `GT7TelemetryPro.spec` | Agregado | Declaración formal de empaquetado para PyInstaller (`--windowed`), añadiendo la persistencia de `gt7_cars.json` al binario compilado. |
| `.github/workflows/release.yml` | Agregado | Pipeline de GitHub Actions basado en matriz de OS (`ubuntu-latest`, `windows-latest`, `macos-latest`) para compilar automáticamente en cada Release creada en GitHub. |

### Detalle Técnico

Se configuró la infraestructura *DevOps* necesaria para distribución pública en binarios nativos sin requerir intérprete Python por parte del cliente.
Dado que PyInstaller desempaca los recursos dependientes (`gt7_cars.json`) en una carpeta temporal generada por el sistema operativo, se alteró la clase Singleton `CarDatabase` para interceptar dinámicamente `sys._MEIPASS` y rutear adecuadamente el origen del archivo JSON sin romper el entorno de desarrollo local.
El pipeline `.github/workflows/release.yml` se engancha al evento `release`, inicializa 3 instancias virtuales paralelas (Windows, Linux, macOS), instala dependencias, ejecuta `pyinstaller` con el archivo `.spec` previamente creado, renombra o comprime (`.zip` para Mac) los binarios y los anexa automáticamente a los Assets de GitHub utilizando `softprops/action-gh-release`.

---

## Docs: Actualización de Documentación (Readme & AGENTS)

| Campo | Detalle |
|-------|---------|
| **Fecha** | 2026-07-12 22:25:00 |
| **Autor** | David Mendez (demg@outlook.com) |
| **Branch** | master |
| **Tipo** | Docs |

### Archivos Modificados

| Archivo | Estado | Descripción del Cambio |
|---------|--------|----------------------|
| `README.md` | Modificado | Se actualizaron las secciones sobre SQLite para reflejar la DB Maestra, y se documentó el nuevo componente `Live Telemetry Dashboard`. |
| `.agents/AGENTS.md` | Modificado | Se actualizó la regla inquebrantable de la base de datos para referenciar al nuevo esquema SQLite de tabla unificada y llave foránea. |

### Detalle Técnico

Se actualizó la documentación estática y las directrices IA (reglas inquebrantables) para alinear el comportamiento del sistema con la reciente refactorización arquitectónica, garantizando que el agente IA mantenga el contexto en futuras sesiones de codificación.

---

## Bug Fix: Freeze during Replay session load

| Campo | Detalle |
|-------|---------|
| **Fecha** | 2026-07-12 22:21:00 |
| **Autor** | David Mendez (demg@outlook.com) |
| **Branch** | master |
| **Tipo** | Bug Fix |

### Archivos Modificados

| Archivo | Estado | Descripción del Cambio |
|---------|--------|----------------------|
| `ui/widgets/advanced_analysis_dialog.py` | Modificado | Se eliminaron referencias obsoletas a `table_corners`. |

### Detalle Técnico

Tras reemplazar `table_corners` con `LiveTelemetryWidget` en el layout, el método `_load_data` todavía intentaba invocar `self.table_corners.setColumnCount(1)`. Dado que esta llamada se encontraba fuera del bloque `try-except`, se lanzaba un `AttributeError` sin control que congelaba el flujo de carga antes de renderizar la UI de repetición. Se limpiaron las referencias a dicho objeto para restaurar el flujo.

---

## Feature: Dashboard de Telemetría en Vivo (Análisis Avanzado)

| Campo | Detalle |
|-------|---------|
| **Fecha** | 2026-07-12 22:15:00 |
| **Autor** | David Mendez (demg@outlook.com) |
| **Branch** | master |
| **Tipo** | Feature / UI |

### Archivos Modificados

| Archivo | Estado | Descripción del Cambio |
|---------|--------|----------------------|
| `ui/widgets/live_telemetry_widget.py` | Agregado | Se creó el componente `LiveTelemetryWidget` heredando de QFrame, con barras de progreso estilizadas mediante QSS (gradientes) para simular medidores de freno, acelerador y RPM. |
| `ui/widgets/advanced_analysis_dialog.py` | Modificado | Se reemplazó la antigua tabla `table_corners` por el nuevo widget de telemetría y se conectó el flujo de datos inyectando los paquetes durante la reproducción (`update_playback_ui`). |

### Detalle Técnico

Se implementó un panel de instrumentos que proporciona retroalimentación instantánea sobre el estado físico del vehículo (telemetría cruda) sincronizada con el mapa interactivo durante la repetición.
- **Rendimiento:** Se evitó el uso de gráficos pesados para estos indicadores, usando en su lugar componentes nativos (`QProgressBar`, `QLabel`) que se pueden actualizar a 60 FPS sin penalización en el hilo principal de la GUI (Zero-stutter).
- **Diseño:** Se implementó QSS para lograr un acabado "Premium" con esquinas redondeadas y colores dinámicos (e.g., bordes rojos en *Shift Light* o cortes de inyección).

---

## Chore: Remove GitHub Actions workflow

| Campo | Detalle |
|-------|---------|
| **Fecha** | 2026-07-12 15:58:00 |
| **Autor** | David Mendez (demg@outlook.com) |
| **Branch** | master |
| **Tipo** | Configuration |

### Archivos Modificados

| Archivo | Estado | Descripción del Cambio |
|---------|--------|----------------------|
| `.github/workflows/release.yml` | Eliminado | Se eliminó el flujo de CI/CD para evitar problemas de permisos de OAuth al hacer git push. |

### Detalle Técnico

Se retiró por completo la integración con GitHub Actions debido a conflictos de permisos de alcance (`workflow` scope) que impedían realizar push al repositorio a través del cliente de git con OAuth.

---

## Feature: Base de Datos Maestra y Seguimiento de Sesiones

| Campo | Detalle |
|-------|---------|
| **Fecha** | 2026-07-12 15:52:00 |
| **Autor** | David Mendez (demg@outlook.com) |
| **Branch** | master |
| **Tipo** | Feature / Refactor |

### Archivos Modificados

| Archivo | Estado | Descripción del Cambio |
|---------|--------|----------------------|
| `core/database.py` | Modificado | Se rediseñó el esquema creando tabla `sessions`. Se añadió lógica de trackeo de sesión (start/end) y metadatos (vueltas, mejor tiempo). |
| `services/live_client.py` | Modificado | Se modificó `start_recording` para recibir datos del vehículo e instanciar la sesión en la base maestra. |
| `ui/main_window.py` | Modificado | Se cambió el auto-save para usar un archivo único y se implementó `QInputDialog` para seleccionar qué sesión reproducir del histórico. |
| `services/replay_player.py` | Modificado | Ahora filtra los queries SQL basándose en `session_id`. |

### Detalle Técnico

Se eliminó el comportamiento de crear un archivo `.sqlite` individual por cada sesión grabada. Ahora se emplea una base de datos maestra `telemetry_master.sqlite` donde se agrupan las sesiones utilizando una tabla relacional `sessions`. 
- **Base de datos:** Se creó un modelo de llaves foráneas (`session_id`) en la tabla de `telemetry`.
- **UI:** El reproductor ya no requiere buscar archivos manualmente; detecta el DB maestro y expone un menú interactivo con el resumen de la sesión (fecha, coche, total de vueltas y mejor tiempo).

### Fragmentos de Código Relevantes

```diff
-        self.db_writer = SessionDatabaseWriter(filename)
-        self.db_writer.start()
+        self.db_writer = SessionDatabaseWriter(filename)
+        self.db_writer.start(car_id, car_name)
```

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
