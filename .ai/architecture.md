# Archivo de Contexto de Arquitectura (IA)
## Proyecto: GT7 Telemetry Pro

Este documento dicta las pautas arquitectónicas y las restricciones del proyecto para futuros desarrollos de Inteligencia Artificial o de agentes.

### Restricciones Principales
1. **No Web-Tech**: Está estrictamente prohibido utilizar tecnologías web (HTML, CSS, JS, Electron, Tauri, WebView, frameworks web de Python como Flask/Django/FastAPI).
2. **Interfaz Gráfica**: La GUI debe basarse en un framework nativo de escritorio (`PyQt6` con `pyqtgraph` para gráficos).
3. **Alto Rendimiento (60 FPS)**: La decodificación criptográfica (`Salsa20`) y el parseo de estructuras son asíncronos para evitar tirones (*stutters*).

### Estructura de Directorios Modular
El proyecto sigue una arquitectura limpia (Clean Architecture):
La arquitectura original era un simple visor en tiempo real. Ahora es una **Herramienta Analítica de Nivel F1**, modularizada de la siguiente manera:

- **`services/`**: Se encarga de la ingestión de datos crudos (UDP, sockets, criptografía y reproducción SQLite).
- **`core/`**: Motores de cálculo de élite (parseo de paquetes, Math Channels, Gestor de Vueltas Delta, Sistema de Alertas, y escritura SQLite con transacciones asíncronas).
- **`ui/`**: Interfaz pura de renderizado y layouts nativos de PyQt6 / PyQtGraph.

### Capas

1. **Capa de Ingestión (Services)**
   - `services/live_client.py`: Socket UDP, descifra, graba en base de datos SQLite y despacha el binario a `parse_telemetry_packet`.
   - `services/replay_player.py`: Reproductor de telemetría, simula la misma tasa de 60Hz leyendo `raw_packet` desde un archivo SQLite.

2. **Capa de UI (PyQt6 + PyQtGraph)**
   - `ui/main_window.py`: Ensambla el layout a tres columnas e integra todos los servicios. Instancia localmente los motores de Core y transfiere los datos a los widgets. Maneja el lanzamiento del análisis post-sesión.
   - `ui/widgets/map_widget.py`: Ahora funciona como un **Heatmap dinámico**. Pinta rojo puro en frenadas duras y verde en aceleraciones 100% WOT. También expone métodos para dibujar un `crosshair` sincronizado con las gráficas de telemetría.
   - `ui/widgets/delta_widget.py`: Gráfica lineal que se mueve en + o - según vayas más rápido o lento que tu "Ghost".
   - `ui/widgets/alert_widget.py`: Panel Pit-Wall anclado a la derecha, muestra notificaciones de colores y emite sonido `Beep` del sistema.
   - `ui/widgets/advanced_analysis_dialog.py`: El corazón del **Análisis Post-Sesión**. Consolidado como la única "Master View" para navegar, bloquear y borrar historiales, integra algoritmos dinámicos para detectar curvas, calcula distancias a 60Hz, y detecta el circuito aplicando un filtro de distancia (Hard Filter 200m) consultando `data/tracks.json`. Presenta un enfoque "Zero-Friction UX" centrado en **Data Grids (Tablas)** que expanden dinámicamente sus columnas al seleccionar múltiples vueltas, superponiendo (Overlay) únicamente la gráfica de Velocidad para comparación, eliminando el ruido visual de gráficas complejas. La vista integra herramientas seguras para eliminación permanente de DB (`VACUUM`) y enclavamiento anti-borrado accidental.

### Manejo de Bases de Datos Dinámicas
- **`data/tracks.json`**: Base de datos completa con más de 122 layouts y pistas oficiales de GT7, extraída de *datamines*, que permite al sistema identificar en qué pista corrió el piloto basado en la distancia total acumulada de la vuelta.
- **`data/gt7_cars.json`**: Diccionario de IDs de coches.

### Arquitectura Multi-Hilo (Red/Live)
1. **`Thread 1 (Network)`**: Lee de `socket.recvfrom` (UDP 33740) con timeout y empuja crudos a una `queue.Queue`.
2. **`Thread 2 (Crypto/Parse)`**: Saca de la cola, descifra con Salsa20, desempaqueta datos binarios y emite una señal `pyqtSignal` hacia la GUI.
3. **`Thread 3 (Heartbeat)`**: Envía latidos (`'C'`) al puerto `33739` simulando a la consola por partida doble (broadcast y unicast).
4. **`Main Thread (GUI)`**: Dibuja la interfaz y actualiza los indicadores (PyQt6 solo permite actualización visual en el hilo principal).

### Consideraciones de Datos
- Las constantes de XOR y la clave Salsa20 son fijas (`gt7-telemetry-spec.md`).
- Todas las señales que viajen desde los hilos de red hacia la GUI en PyQt6 utilizan `pyqtSignal` para asegurar hilo-seguridad (thread-safety).
