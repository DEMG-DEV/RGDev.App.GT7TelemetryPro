# 🔄 Sincronización LAN

> **Archivo:** `ui/sync_dialog.py` · **Clase:** `SyncDialog` · **276 líneas**

La sincronización LAN permite transferir sesiones de telemetría entre dos dispositivos conectados a la misma red local, de forma bidireccional y automática.

---

## Vista General

```
┌──────────────────────────────────────────────────┐
│  Dispositivos en tu Red Local                    │
│                                                  │
│  🔍 Buscando...                                  │
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │ 🖥️  MacBook-Pro  (192.168.1.105)          │  │
│  │     — 47 sesiones                          │  │
│  ├────────────────────────────────────────────┤  │
│  │ 🖥️  Gaming-PC  (192.168.1.110)            │  │
│  │     — 23 sesiones                          │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
│  ┌─ Resumen de Sincronización ───────────────┐  │
│  │ → Sesiones a enviar: 12                   │  │
│  │ ← Sesiones a recibir: 8                   │  │
│  └───────────────────────────────────────────┘  │
│                                                  │
│  ████████████████████████░░░░░ 67%               │
│                                                  │
│  ✅ Sincronización completada                    │
│                                                  │
│                    [🔄 Sincronizar]  [Cerrar]    │
└──────────────────────────────────────────────────┘
```

---

## Dimensiones

| Propiedad | Valor |
|-----------|-------|
| Tamaño mínimo | 520 × 480 px |
| Tipo | `QDialog` modal |

---

## Elementos de la Interfaz

| Elemento | Widget | Descripción |
|----------|--------|-------------|
| **Título** | `QLabel` bold 16pt | "Dispositivos en tu Red Local" |
| **Estado búsqueda** | `QLabel` | "🔍 Buscando..." → "✅ X dispositivo(s) encontrado(s)" |
| **Lista de peers** | `QListWidget` | Items con formato: `🖥️ hostname (ip) — N sesiones` |
| **Resumen sync** | `QGroupBox` | Oculto hasta comparar. Muestra envío (azul) y recepción (verde) |
| **Barra progreso** | `QProgressBar` | Oculta hasta iniciar sync. Estilo acento azul. |
| **Estado** | `QLabel` centrado | Mensajes de conexión, transferencia, completado o error |
| **Sincronizar** | `QPushButton` verde | Deshabilitado hasta seleccionar un peer |
| **Cerrar** | `QPushButton` gris | Cierra el diálogo |

---

## Puertos de Red

| Puerto | Protocolo | Dirección | Función |
|--------|-----------|-----------|---------|
| **33741** | UDP | Broadcast bidireccional | Descubrimiento de peers |
| **33742** | TCP | Bidireccional punto a punto | Transferencia de datos |

> ⚠️ Estos puertos están reservados para GT7 Telemetry Pro. No deben reutilizarse.

---

## Servicios de Red (iniciados al abrir el diálogo)

### 1. `PeerDiscovery` (QThread)
- Envía **beacons UDP** broadcast en el puerto 33741
- Escucha beacons de otros dispositivos
- Filtra IPs locales para evitar auto-descubrimiento
- Emite `peer_found(hostname, ip, session_count, port)` y `peer_lost(ip)`

### 2. `SyncServer` (QThread)
- Servidor TCP escuchando en el puerto 33742
- Acepta conexiones entrantes de otros peers
- Atiende solicitudes de comparación y transferencia

### 3. `SyncClient` (QThread)
- Se crea al hacer click en "Sincronizar"
- Conecta al peer seleccionado vía TCP 33742
- Ejecuta el protocolo de sincronización bidireccional

---

## Protocolo de Sincronización

### Fase 1 — Comparación
```
Client                          Server
  │                               │
  │── LIST_SESSIONS ──────────►   │
  │                               │
  │   ◄────── SESSION_LIST ───    │  (lista de (start_time, car_id))
  │                               │
  │── COMPARISON_RESULT ──────►   │  (sesiones faltantes en cada lado)
```

### Fase 2 — Transferencia Bidireccional
```
  │                               │
  │   ◄── SEND_SESSION_DATA ──    │  ← Recibir sesiones del peer
  │       (por cada sesión)       │
  │                               │
  │── SEND_SESSION_DATA ──────►   │  → Enviar sesiones al peer
  │       (por cada sesión)       │
```

### Formato del Mensaje TCP
```
┌──────────────┬──────────────────────────┐
│ 4 bytes      │ N bytes                  │
│ (big-endian) │ (zlib compressed)        │
│ longitud     │ JSON payload             │
└──────────────┴──────────────────────────┘
```

- Los BLOBs de telemetría (`raw_packet`) se serializan como **hex strings** dentro del JSON
- El paquete completo se comprime con `zlib` nivel 6
- Detección de duplicados por clave natural: `(start_time, car_id)`

---

## Reglas de Sincronización

| Regla | Descripción |
|-------|-------------|
| **Bidireccional** | Primero recibe del peer, luego envía |
| **Sin duplicados** | Usa `(start_time, car_id)` como clave natural |
| **Protección de bloqueo** | Sesiones con `is_locked = 1` se sincronizan pero **NUNCA** se sobrescriben |
| **Re-mapeo de IDs** | Los `session_id` autoincrementales se re-mapean al importar |

---

## Señales del SyncClient

| Señal | Datos | UI Update |
|-------|-------|-----------|
| `comparison_ready` | `(to_send, to_receive)` | Muestra resumen de sync |
| `transfer_progress` | `percent (int)` | Actualiza barra de progreso |
| `sync_complete` | `(sent_count, received_count)` | Mensaje de éxito |
| `error_occurred` | `error_message (str)` | Diálogo de error |

---

## Limpieza

Al cerrar el diálogo (`closeEvent`):
1. Detiene `SyncClient` (si existe) + espera 2s
2. Detiene `PeerDiscovery` + espera 2s
3. Detiene `SyncServer` + espera 2s
