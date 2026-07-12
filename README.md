# GT7 Telemetry Pro

![GT7 Telemetry Interface](./screenshot.png)

**GT7 Telemetry Pro** es una aplicación de escritorio moderna y multiplataforma (Windows y macOS) diseñada para capturar, descifrar y visualizar la telemetría en tiempo real desde *Gran Turismo 7* (PS4/PS5). 

## Características Principales

*   **Sin Tecnologías Web**: Interfaz nativa desarrollada enteramente para escritorio, optimizada para alto rendimiento a 60 FPS sin utilizar Electron ni navegadores embebidos.
*   **Decodificación Salsa20**: Implementación del cifrado Salsa20 en tiempo real con derivación de Nonce dinámico por paquete.
*   **Arquitectura Productor-Consumidor**: Múltiples hilos (threads) dedicados para asegurar cero pérdida de paquetes y una respuesta inmediata de la interfaz gráfica.
*   **Mapeo Exhaustivo de Memoria**: Soporte completo para leer RPM, velocidad, uso de pedales (acelerador, freno, embrague), actitud del chasis, marchas, y tiempos de vuelta.

## Requisitos del Sistema

*   **Python 3.10** o superior.
*   Windows 10/11 o macOS (Intel/Apple Silicon).
*   Conexión de red en la misma subred que la consola PlayStation (PS4/PS5).

## Cómo Funciona

Gran Turismo 7 no transmite telemetría de forma automática. La aplicación establece un "handshake" y mantiene un canal activo enviando señales de *keep-alive* (Heartbeat) hacia el puerto `33739` de la consola. La consola responde enviando paquetes UDP cifrados a 60Hz al puerto `33740` de la máquina donde se ejecuta este cliente. 

---
*Desarrollado bajo una arquitectura estricta para latencia ultra baja.*
