# 🏁 GT7 Telemetry Pro — Wiki

> Convierte tu Gran Turismo 7 en un simulador de telemetría profesional de grado ingenieril.

**Versión actual:** 1.2.4 · **Stack:** Python 3.10+ · PyQt6 · pyqtgraph · NumPy · PyCryptodome  
**Plataformas:** macOS 12+ · Windows 10/11 · **Consolas:** PS4 / PS5

---

## 📖 Índice de Vistas

### Dashboard Principal
| Página | Descripción |
|--------|-------------|
| [Dashboard Principal](Dashboard-Principal) | Ventana principal con instrumentación completa en tiempo real |
| [Medidores Circulares](Medidores-Circulares) | Velocidad, RPM, Turbo/Boost y Temperatura de Agua |
| [Temperatura de Neumáticos](Temperatura-Neumaticos) | Semicírculos con gradiente de 4 zonas (FL/FR/RL/RR) |
| [Gráficas de Telemetría](Graficas-Telemetria) | 3 gráficas apiladas: Velocidad, Pedales, RPM |
| [Mapa de Pista](Mapa-Pista) | Trazado termodinámico de la pista en tiempo real |
| [Fuerzas G](Fuerzas-G) | Diagrama de tracción (lateral vs longitudinal) |
| [Delta-T](Delta-T) | Diferencia de tiempo contra mejor vuelta |
| [Alertas Pit-Wall](Alertas-Pit-Wall) | Notificaciones inteligentes con sonido |

### Análisis Post-Carrera
| Página | Descripción |
|--------|-------------|
| [Historial y Análisis](Historial-y-Analisis) | Navegación de sesiones, overlay de vueltas, reproducción |
| [Pro Analysis Workspace](Pro-Analysis-Workspace) | Workspace profesional estilo MoTeC con paneles acoplables |
| [Gestor de Fórmulas](Gestor-de-Formulas) | Creación de canales matemáticos personalizados |

### Conectividad
| Página | Descripción |
|--------|-------------|
| [Sincronización LAN](Sincronizacion-LAN) | Sincronización bidireccional entre dispositivos |

---

## 🏗️ Arquitectura General

```
PS4/PS5 (GT7) ──UDP 33740──► GT7LiveClient ──pyqtSignal──► TelemetryMainWindow
                                   │                              │
                                   ▼                              ▼
                            SessionDatabaseWriter          Dashboard Widgets
                                   │                       (Gauges, Map, Graphs,
                                   ▼                        G-Force, Delta, Alerts)
                         telemetry_master.sqlite
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
            AdvancedAnalysis  ProWorkspace   SyncDialog
            (Playback/Overlay) (MoTeC/Math)  (LAN P2P)
```

---

## 🚀 Inicio Rápido

1. Conecta tu PS4/PS5 a la misma red WiFi/Ethernet que tu computadora
2. Abre GT7 Telemetry Pro
3. Ingresa la IP de tu consola (o deja que el auto-descubrimiento la encuentre)
4. Click **"Connect Live"** — la telemetría comienza a fluir a 60 FPS
5. Click **"⏺ Iniciar Grabación"** para guardar la sesión en la base de datos

---

## 📂 Estructura de Datos

| Archivo | Ubicación | Contenido |
|---------|-----------|-----------|
| `telemetry_master.sqlite` | `~/Library/Application Support/GT7TelemetryPro/` (Mac) | Todas las sesiones y telemetría |
| `math_channels.json` | Mismo directorio | Fórmulas matemáticas del usuario |
| `gt7_telemetry.log` | Mismo directorio | Log de la aplicación |
