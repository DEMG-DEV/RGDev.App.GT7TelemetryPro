# Archivo de Contexto de Arquitectura (IA)
## Proyecto: GT7 Telemetry Pro

Este documento dicta las pautas arquitectónicas y las restricciones del proyecto para futuros desarrollos de Inteligencia Artificial o de agentes.

### Restricciones Principales
1. **No Web-Tech**: Está estrictamente prohibido utilizar tecnologías web (HTML, CSS, JS, Electron, Tauri, WebView, frameworks web de Python como Flask/Django/FastAPI).
2. **Interfaz Gráfica**: La GUI debe basarse en un framework nativo de escritorio (`PyQt6` con `pyqtgraph` para gráficos).
3. **Alto Rendimiento (60 FPS)**: La decodificación criptográfica (`Salsa20`) y el parseo de estructuras son asíncronos para evitar tirones (*stutters*).

### Estructura de Directorios Modular
El proyecto sigue una arquitectura limpia (Clean Architecture):
- `core/`: Lógica central, modelos de datos (`models.py`) independientes de la red o la UI.
- `services/`: Servicios de infraestructura y obtención de datos (`live_client.py`, `replay_player.py`, `crypto.py`, `provider.py`). Proveen la abstracción base.
- `ui/`: Componentes de interfaz gráfica en PyQt6 separados por responsabilidad (`main_window.py` y `widgets/`).

### Arquitectura Multi-Hilo (Red/Live)
1. **`Thread 1 (Network)`**: Lee de `socket.recvfrom` (UDP 33740) con timeout y empuja crudos a una `queue.Queue`.
2. **`Thread 2 (Crypto/Parse)`**: Saca de la cola, descifra con Salsa20, desempaqueta datos binarios y emite una señal `pyqtSignal` hacia la GUI.
3. **`Thread 3 (Heartbeat)`**: Envía latidos (`'C'`) al puerto `33739` simulando a la consola por partida doble (broadcast y unicast).
4. **`Main Thread (GUI)`**: Dibuja la interfaz y actualiza los indicadores (PyQt6 solo permite actualización visual en el hilo principal).

### Consideraciones de Datos
- Las constantes de XOR y la clave Salsa20 son fijas (`gt7-telemetry-spec.md`).
- Todas las señales que viajen desde los hilos de red hacia la GUI en PyQt6 utilizan `pyqtSignal` para asegurar hilo-seguridad (thread-safety).
