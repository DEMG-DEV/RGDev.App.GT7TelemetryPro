# Reglas Estrictas para Agentes IA en GT7 Telemetry Pro

## Reglas Inquebrantables de Arquitectura

1. **PROHIBIDAS LAS TECNOLOGÍAS WEB**: 
   - No sugieras, no instales, ni escribas código en HTML, CSS, JavaScript, React, Vue, Electron, Tauri, FastAPI, Flask, o Django.
   - Todo el desarrollo de Interfaz Gráfica (GUI) **DEBE** realizarse exclusivamente mediante `PyQt6`.
   - Todas las gráficas **DEBEN** dibujarse usando `pyqtgraph`. No uses `matplotlib` ya que es muy lento para renderizar a 60 FPS.

2. **Rendimiento y Zero-Stutter**:
   - Nunca bloquees el hilo principal (`Main Thread`). Todo el trabajo pesado (desencriptación Salsa20, escritura a SQLite en disco, algoritmos de detección) debe ocurrir en hilos separados usando `threading.Thread` y colas (`queue.Queue`).
   - Usa `pyqtSignal` obligatoriamente para transferir cualquier dato desde los hilos de fondo a la GUI.

3. **Arquitectura SQLite**:
   - Este proyecto utiliza *Write-Ahead Logging* (WAL) y *Autocommit* para optimizar la escritura en ráfagas de alta densidad de datos. 
   - Se utiliza una **Base de Datos Maestra Única** (`telemetry_master.sqlite`) en lugar de múltiples archivos. Esta base de datos agrupa el historial en la tabla `sessions` vinculándola con la telemetría a través de la llave foránea `session_id`.
   - Al ejecutar `VACUUM` u operaciones globales de BD, nunca lo hagas dentro de una transacción `WITH` iniciada por `sqlite3`.
   - El esquema usa una columna `is_locked` en la tabla `sessions` para la protección anti-borrado.

4. **Diseño Visual Fijo (UI)**:
   - Las proporciones de la interfaz de Análisis Avanzado deben permanecer mediante `stretch` layout fijos y no mediante `QSplitter` dinámicos. Esto preserva la intención de "diseño de precisión" sin que el usuario desajuste los márgenes accidentalmente.
