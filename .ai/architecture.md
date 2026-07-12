# Archivo de Contexto de Arquitectura (IA)
## Proyecto: GT7 Telemetry Pro

Este documento dicta las pautas arquitectónicas y las restricciones del proyecto para futuros desarrollos de Inteligencia Artificial o de agentes.

### Restricciones Principales
1. **No Web-Tech**: Está estrictamente prohibido utilizar tecnologías web (HTML, CSS, JS, Electron, Tauri, WebView, frameworks web de Python como Flask/Django/FastAPI).
2. **Interfaz Gráfica**: La GUI debe basarse en un framework nativo de escritorio (recomendado `PyQt6` con `pyqtgraph` para gráficos).
3. **Alto Rendimiento (60 FPS)**: La decodificación criptográfica (`Salsa20`) y el parseo de estructuras deben ser asíncronos o ejecutados en un hilo separado al de la interfaz para evitar tirones (*stutters*).
4. **Arquitectura Multi-Hilo**:
   - `Thread 1 (Network)`: Lee de `socket.recvfrom` (UDP 33740) y empuja crudos a la cola.
   - `Thread 2 (Crypto/Parse)`: Saca de la cola, descifra con Salsa20, desempaqueta datos binarios (Little-Endian) y emite un objeto a la GUI.
   - `Thread 3 (Heartbeat)`: Envía el latido al puerto `33739` de la consola cada 1.5s.
   - `Main Thread (GUI)`: Dibuja la interfaz, actualiza indicadores.

### Consideraciones de Datos
- Las constantes mágicas de XOR y la clave Salsa20 son fijas de acuerdo con la especificación `gt7-telemetry-spec.md`.
- No alterar las operaciones bit a bit para la lectura de los "Flags" y las marchas (Offset `0x8E` y `0x92`).
