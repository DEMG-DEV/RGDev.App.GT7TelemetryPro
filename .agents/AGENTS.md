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
   - **Identidad del Auto Dinámica**: El sistema de escritura de la base de datos de sesión (`SessionDatabaseWriter`) NUNCA debe confiar ciegamente en el ID del primer paquete recibido, dado que GT7 en la parrilla de salida emite telemetría de los oponentes IA. Debe monitorear las frecuencias del ID durante toda la carrera y reescribir la fila de la sesión con el ID más prevalente al detenerse.
   - Al ejecutar `VACUUM` u operaciones globales de BD, nunca lo hagas dentro de una transacción `WITH` iniciada por `sqlite3`.
   - El esquema usa una columna `is_locked` en la tabla `sessions` para la protección anti-borrado.

4. **Diseño Visual Fijo y Modo Diurno (Light Mode)**:
   - Las proporciones de la interfaz de Análisis Avanzado deben permanecer mediante `stretch` layout fijos y no mediante `QSplitter` dinámicos. Esto preserva la intención de "diseño de precisión" sin que el usuario desajuste los márgenes accidentalmente.
   - **Estricta Política de Tema Diurno**: Todo desarrollo de interfaz gráfica debe apuntar al modo diurno (Daylight Mode). Está prohibido el uso de colores neón o temas oscuros. Usa grises claros (`#F0F0F0`, `#FAFAFA`, `#FFFFFF`) para fondos y textos oscuros (`#1A1A1A`) para máximo contraste simulando ambientes de ingeniería con luz natural.

5. **Procesamiento de Datos Vectoriales y Gráficos**:
   - Todo cálculo masivo sobre la telemetría extraída de SQLite DEBE convertirse a matrices de `numpy` puras (`np.array`) de forma temprana (ej: en `get_lap_data_vectorized`).
   - Evita iterar sobre listas nativas de Python (`for row in data`) para procesar 100,000+ puntos antes de graficar. Usa operaciones vectorizadas (Ej: `lap_speed / 3.6 * dt`).

6. **Motores Matemáticos y Seguridad**:
   - **Prohibido el uso de `eval()` o `exec()` nativos** para evaluar las fórmulas matemáticas definidas por el usuario (Math Channels). Usa siempre la librería `asteval` para crear un sandbox seguro que evite la ejecución de código arbitrario.

7. **Heurísticas Espaciales e Integración de Tiempo**:
   - **Nunca asumas un Frame Rate fijo (60Hz / 0.016s)** al calcular distancias, ya que el *jitter* de red acumula errores kilométricos a lo largo de una vuelta. Siempre debes calcular el `dt` real iterando sobre el arreglo de `timestamps` (`dt = np.diff(lap_time)` en segundos).
   - Para evitar envenenar los promedios heurísticos, **DEBES excluir siempre las vueltas incompletas** (Out-lap y In-lap) al procesar métricas como la Mediana de Distancia para la detección automática de pistas contra `tracks.json`.
