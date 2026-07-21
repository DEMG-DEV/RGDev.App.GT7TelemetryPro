# Reglas Estrictas para Agentes IA en GT7 Telemetry Pro

> **Versión de referencia:** 1.2.4  
> **Última actualización:** 2026-07-21

## Reglas Inquebrantables de Arquitectura

1. **PROHIBIDAS LAS TECNOLOGÍAS WEB**: 
   - No sugieras, no instales, ni escribas código en HTML, CSS, JavaScript, React, Vue, Electron, Tauri, FastAPI, Flask, o Django.
   - Todo el desarrollo de Interfaz Gráfica (GUI) **DEBE** realizarse exclusivamente mediante `PyQt6`.
   - Todas las gráficas **DEBEN** dibujarse usando `pyqtgraph`. No uses `matplotlib` ya que es muy lento para renderizar a 60 FPS.

2. **Rendimiento y Zero-Stutter**:
   - Nunca bloquees el hilo principal (`Main Thread`). Todo el trabajo pesado (desencriptación Salsa20, escritura a SQLite en disco, algoritmos de detección, carga masiva de datos, exportación MoTeC) debe ocurrir en hilos separados usando `threading.Thread`, `QThread` y colas (`queue.Queue`).
   - Usa `pyqtSignal` obligatoriamente para transferir cualquier dato desde los hilos de fondo a la GUI.

3. **Arquitectura SQLite**:
   - Este proyecto utiliza *Write-Ahead Logging* (WAL) y *Autocommit* para optimizar la escritura en ráfagas de alta densidad de datos. 
   - Se utiliza una **Base de Datos Maestra Única** (`telemetry_master.sqlite`) en lugar de múltiples archivos. Esta base de datos agrupa el historial en la tabla `sessions` vinculándola con la telemetría a través de la llave foránea `session_id`.
   - **Rutas de Base de Datos:** El archivo maestro `telemetry_master.sqlite` SIEMPRE debe buscarse y escribirse en el directorio de trabajo de la aplicación (CWD). Nota: `main.py` redefine el CWD al arrancar hacia la ruta de datos del sistema (`~/Library/Application Support/GT7TelemetryPro` en Mac, `%APPDATA%\GT7TelemetryPro` en Windows). **JAMÁS** crees subcarpetas adicionales como `Sessions/`.
   - **Identidad del Auto Dinámica**: El sistema de escritura de la base de datos de sesión (`SessionDatabaseWriter`) NUNCA debe confiar ciegamente en el ID del primer paquete recibido, dado que GT7 en la parrilla de salida emite telemetría de los oponentes IA. Debe monitorear las frecuencias del ID durante toda la carrera y reescribir la fila de la sesión con el ID más prevalente al detenerse.
   - Al ejecutar `VACUUM` u operaciones globales de BD, nunca lo hagas dentro de una transacción `WITH` iniciada por `sqlite3`.
   - El esquema usa una columna `is_locked` en la tabla `sessions` para la protección anti-borrado.
   - **Esquema de la BD:**
     ```sql
     sessions (id, start_time, end_time, car_id, car_name, total_laps, best_laptime, is_locked)
     telemetry (id, session_id FK, timestamp, lap_count, speed_kmh, engine_rpm, throttle, brake, current_gear, raw_packet BLOB)
     ```

4. **Diseño Visual Fijo y Modo Diurno (Light Mode)**:
   - Las proporciones de la interfaz de Análisis Avanzado deben permanecer mediante `stretch` layout fijos y no mediante `QSplitter` dinámicos. Esto preserva la intención de "diseño de precisión" sin que el usuario desajuste los márgenes accidentalmente.
   - **Estricta Política de Tema Diurno**: Todo desarrollo de interfaz gráfica debe apuntar al modo diurno (Daylight Mode). Está prohibido el uso de colores neón o temas oscuros. Usa grises claros (`#F0F0F0`, `#FAFAFA`, `#FFFFFF`) para fondos y textos oscuros (`#1A1A1A`) para máximo contraste simulando ambientes de ingeniería con luz natural.

5. **Procesamiento de Datos Vectoriales y Gráficos**:
   - Todo cálculo masivo sobre la telemetría extraída de SQLite DEBE convertirse a matrices de `numpy` puras (`np.array`) de forma temprana (ej: en `get_lap_data_vectorized`).
   - Evita iterar sobre listas nativas de Python (`for row in data`) para procesar 100,000+ puntos antes de graficar. Usa operaciones vectorizadas (Ej: `lap_speed / 3.6 * dt`).

6. **Heurísticas Espaciales e Integración de Tiempo**:
   - **Nunca asumas un Frame Rate fijo (60Hz / 0.016s)** al calcular distancias, ya que el *jitter* de red acumula errores kilométricos a lo largo de una vuelta. Siempre debes calcular el `dt` real iterando sobre el arreglo de `timestamps` (`dt = np.diff(lap_time)` en segundos).
   - Para evitar envenenar los promedios heurísticos, **DEBES excluir siempre las vueltas incompletas** (Out-lap y In-lap) al procesar métricas como la Mediana de Distancia para la detección automática de pistas contra `tracks.json`.

7. **Empaquetado y Compatibilidad macOS/Windows (App Bundles)**:
   - Al compilar mediante PyInstaller o cx_Freeze, **NUNCA** asumas que `os.getcwd()` es el directorio de la aplicación. 
   - Siempre cambia el directorio de trabajo dinámicamente a una ubicación de datos del sistema estándar (Ej: `~/Library/Application Support/GT7TelemetryPro` en Mac, o `%APPDATA%\\GT7TelemetryPro` en Windows) en la primera línea de `main.py` antes de inicializar bases de datos SQLite o sistemas de *Logging*.
   - Los iconos en `BUNDLE` de macOS exigen formato Apple Icon Image `.icns`. No usar `.png` directo en la definición de la especificación de PyInstaller.
   - Para resolver rutas de archivos bundled (JSON, assets), usa siempre `core/car_database.py:resource_path()` que detecta automáticamente si se ejecuta dentro de un bundle PyInstaller (`sys._MEIPASS`) o en modo desarrollo.

8. **Estilos de Botones (Cirugía PyQt6 en macOS)**:
   - Cuando se sobrescribe el color de fondo de un `QPushButton` mediante `setStyleSheet` en macOS, el motor de dibujado nativo de Apple se rompe y el botón se vuelve un cuadrado plano obsoleto.
   - Todo botón personalizado **DEBE** incluir forzosamente `border-radius: 6px;`, bordes explícitos (ej. `border: 1px solid #CCCCCC;`) y un `padding` holgado (ej. `padding: 8px 16px;`) para recuperar una apariencia moderna (Pill Button).

9. **Sistema Centralizado de Tokens de Diseño (UI Theme)**:
   - Está prohibido hardcodear colores (ej. `#FFFFFF`), tamaños de fuente o bordes directamente con strings mágicos en las clases de UI.
   - Todos los estilos deben construirse obligatoriamente importando la clase `Theme` desde `ui.theme`. Usa constantes como `Theme.BG_PANEL`, `Theme.TEXT_PRIMARY`, o helpers como `Theme.btn_style()` y `Theme.table_style()` para inyectar estilos seguros y uniformes a lo largo de todo el proyecto.

10. **Tipografía Monoespaciada Segura**:
    - Para fuentes monoespaciadas (`QFont`), **nunca asumas** que `Consolas` está disponible, ya que romperá el log de consola en macOS.
    - Utiliza exclusivamente `Theme.FONT_MONO` (el cual resuelve a `Menlo` o `Courier New` como fallback multiplataforma seguro).

11. **Portabilidad de Base de Datos (Exportar/Importar)**:
    - La exportación de la BD **SIEMPRE** debe usar `VACUUM INTO` (nunca `shutil.copy`) para producir un archivo SQLite atómico sin archivos `-wal` ni `-shm` huérfanos.
    - La importación en modo "fusionar" **DEBE** usar la clave natural `(start_time, car_id)` para detectar duplicados y re-mapear los `session_id` autoincrementales. **JAMÁS** confíes en los IDs del archivo importado.
    - El modo "reemplazar" **DEBE** generar un backup automático con timestamp antes de sobrescribir (`_backup_YYYYMMDD_HHMMSS.sqlite`).
    - Toda la lógica de portabilidad vive en `core/db_portability.py`. No mezcles esta responsabilidad con `core/database.py` (que es exclusivamente para escritura de sesiones activas).

12. **Sincronización por Red Local (LAN Sync)**:
    - El descubrimiento de peers usa **UDP broadcast** en el puerto `33741`. La transferencia de datos usa **TCP** en el puerto `33742`. Estos puertos están reservados y no deben reutilizarse.
    - Los beacons UDP deben filtrar las IPs locales del propio dispositivo para evitar auto-descubrimiento.
    - El protocolo TCP usa mensajes JSON delimitados por longitud (4 bytes big-endian + payload). Los BLOBs de telemetría se serializan como hex strings dentro del JSON y el paquete completo se comprime con `zlib` nivel 6.
    - La sincronización es **bidireccional**: primero se reciben las sesiones faltantes del peer, luego se envían las que el peer necesita.
    - Las sesiones con `is_locked = 1` se sincronizan pero **NUNCA** se sobrescriben si ya existen en el destino.
    - La UI de sincronización vive en `ui/sync_dialog.py` (`SyncDialog`). Los servicios de red viven en `services/sync_service.py` (`PeerDiscovery`, `SyncServer`, `SyncClient`).

13. **Canales Matemáticos y Evaluación Segura (AST Sandbox)**:
    - El módulo `core/dynamic_math.py` implementa un evaluador basado en `ast.NodeVisitor` (`SafeMathVisitor`) que valida que las expresiones del usuario sean exclusivamente matemáticas puras antes de ejecutarlas.
    - El flujo de evaluación es: **validación AST → `compile()` → `eval()` en globals restringidos** (solo `np` + 6 builtins). Se permite `compile()` + `eval()` **ÚNICAMENTE** tras pasar la validación completa del `SafeMathVisitor`. Jamás ejecutes `eval()` sin validación AST previa.
    - Solo se permiten funciones built-in de la whitelist: `max`, `min`, `abs`, `round`, `sum`, `len`, y funciones de `numpy` accedidas exclusivamente como `np.xxx`.
    - Toda asignación de variables (`=`), importación (`import`), o llamada a atributos no-numpy está terminantemente prohibida y debe lanzar `MathSecurityError`.
    - La persistencia de canales definidos por el usuario se almacena en `math_channels.json` (raíz del proyecto).

14. **Visualización de Temperatura de Neumáticos (Semicírculos)**:
    - Las temperaturas de los 4 neumáticos se visualizan con widgets `TyreTempGauge` (semicírculos dibujados con `QPainter.drawArc`), **NUNCA** con labels de texto plano.
    - El color del arco **DEBE** interpolarse dinámicamente entre 4 zonas calibradas para GT7: Azul (<50°C, frío), Verde (50-80°C, óptimo), Naranja (80-100°C, caliente), Rojo (>100°C, sobrecalentamiento).
    - El rango del gauge es 20°C–140°C. Los labels usan la nomenclatura de Fórmula 1: **FL** (Front Left), **FR** (Front Right), **RL** (Rear Left), **RR** (Rear Right).
    - La disposición en el dashboard es: columna izquierda (FL + RL), centro (pedales Acelerador/Freno), columna derecha (FR + RR).

15. **Testing Visual con Simulación (tools/)**:
    - Todo cambio visual en el dashboard **DEBE** poder verificarse sin una consola PS4/PS5 real mediante el script `tools/test_full_ui_sim.py`, que inyecta paquetes `GT7TelemetryPacket` sintéticos a 60fps directamente a `win.latest_packet` y a los sub-widgets (`map_widget.add_point`, `graphs_widget.add_data`, etc.).
    - El timer de UI del `TelemetryMainWindow` (`ui_timer`, 33ms) se encarga de leer `latest_packet` y actualizar los widgets visuales. **NUNCA** llames a `update_dashboard_ui()` directamente desde el inyector.
    - El script `tools/screenshot_generator.py` genera capturas automatizadas para la documentación del README. Usa `tools/test_tyre_gauges.py` para pruebas aisladas de los semicírculos de temperatura.

16. **Exportación MoTeC i2 (.ld/.ldx)**:
    - El módulo `services/motec_exporter.py` genera archivos binarios `.ld` (datos) y `.ldx` (metadatos XML) compatibles con MoTeC i2 Pro.
    - La tasa de muestreo es fija a **60Hz**. Los nombres de canales y unidades deben respetar las convenciones MoTeC (ASCII, 32 caracteres máximo por nombre, 16 máximo por unidad).
    - El exportador se compone de tres clases: `MotecLdWriter` (binario .ld), `MotecLdxWriter` (XML .ldx) y `MotecExporter` (orquestador que carga datos de SQLite).
    - La exportación **SIEMPRE** debe ejecutarse en un `MotecExportThread` (QThread) para no bloquear la GUI.

17. **Auto-Actualización desde GitHub Releases**:
    - El sistema de auto-actualización vive en `services/updater.py` y se compone de dos QThreads: `UpdateChecker` (consulta API de GitHub) y `UpdateDownloader` (descarga + extracción del ZIP).
    - La verificación de versión se ejecuta automáticamente al arrancar la app comparando `core/config.APP_VERSION` contra el tag más reciente de GitHub (`GITHUB_REPO`).
    - **JAMÁS** bloquees el hilo principal durante la verificación o descarga. Todo debe ser asíncrono vía `QThread` con señales `pyqtSignal` para reportar progreso.
    - El flujo es: detectar nueva versión → preguntar al usuario → descargar ZIP → extraer → reiniciar aplicación.

18. **Pro Analysis Workspace (Análisis Profesional)**:
    - El workspace profesional (`ui/workspace.py`, `ProfessionalWorkspace`) es la vista de análisis post-carrera más completa. Usa paneles `QDockWidget` flotantes/acoplables, **NO** ventanas modales ni `QDialog`.
    - Los datos se cargan en un `DataLoaderThread` (QThread) dedicado usando `get_lap_data_vectorized()` para no bloquear la UI.
    - Integra: gráficas de velocidad/pedales/RPM/suspensión, track map con crosshair sincronizado, histogramas de suspensión, data grids con codificación de color, y el gestor de fórmulas matemáticas.
    - La exportación MoTeC se lanza desde este workspace via `MotecExportThread`.

19. **Replay Player (Reproductor de Sesiones)**:
    - El `GT7SessionPlayer` (`services/replay_player.py`) reproduce sesiones almacenadas en SQLite respetando los timestamps originales del paquete para simular la misma cadencia temporal de la grabación real.
    - Hereda de `TelemetryProvider` (base abstracta en `services/provider.py`) para ser **intercambiable** con `GT7LiveClient`. Ambos emiten `packet_signal(GT7TelemetryPacket)`.
    - La reproducción corre en un hilo daemon separado. Emite `playback_finished` al terminar.

20. **QSS y Estilos Globales**:
    - El archivo `ui/styles/daylight_theme.qss` define los estilos base de la aplicación (QGroupBox, QLabel, scrollbars, etc.) y se carga al inicializar `TelemetryMainWindow` obligatoriamente mediante `core/car_database.py:resource_path('ui/styles/daylight_theme.qss')`.
    - **Empaquetado PyInstaller:** El archivo `GT7TelemetryPro.spec` DEBE incluir `('ui/styles/*.qss', 'ui/styles')` y `('data/car_thumbnails', 'data/car_thumbnails')` en el arreglo `datas` para garantizar que los estilos y activos visuales no se pierdan en producción.
    - Existe un `ui/styles/dark_theme.qss` como **plantilla experimental solamente**. Está prohibido activarlo en producción — toda la app debe funcionar exclusivamente en Modo Diurno.
    - Los estilos QSS complementan (no reemplazan) los tokens de `Theme`. QSS maneja estilos globales de widgets; `Theme` maneja estilos específicos inyectados por código.

21. **Decorador de Seguridad para Slots (@safe_slot)**:
    - Todos los slots PyQt6 conectados a señales que provienen de hilos secundarios **DEBEN** usar el decorador `@safe_slot` de `core/utils.py` para capturar excepciones silenciosas.
    - Este decorador envuelve la función en try/except y registra el error via `logging.error` con traceback completo. Sin él, PyQt6 traga las excepciones sin aviso alguno.

22. **Gestor de Fórmulas (Formula Manager UI)**:
    - El diálogo `FormulaManagerWidget` en `ui/formula_manager.py` es la interfaz CRUD para crear, editar y eliminar canales matemáticos definidos por el usuario.
    - Toda validación de fórmulas **DEBE** pasar por `DynamicMathEngine.validate_expression()` (que internamente ejecuta `SafeMathVisitor`) antes de guardarse en `math_channels.json`.
    - El widget incluye un botón de "dry-run" que permite al usuario probar la fórmula contra datos reales antes de confirmar.

23. **Auto-Detección y Caché de Thumbnails de Vehículos**:
    - El panel de información detecta el código de vehículo (`car_code`) en vivo a través del paquete de telemetría y renderiza su imagen correspondiente ubicada en `data/car_thumbnails/`.
    - Para mantener el estándar Zero-Stutter a 60 FPS, la UI DEBE almacenar el `_current_car_code` en memoria y **únicamente recargar y escalar el `QPixmap` cuando el código cambie**, evitando operaciones I/O de disco repetitivas en cada fotograma del `ui_timer`.
