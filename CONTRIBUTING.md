# Guía de Contribución — GT7 Telemetry Pro

¡Gracias por tu interés en contribuir a GT7 Telemetry Pro! 🏁

## Cómo Contribuir

### Reportar Bugs

1. Verifica que el bug no haya sido reportado previamente en [Issues](https://github.com/DEMG-DEV/RGDev.App.GT7TelemetryPro/issues).
2. Crea un nuevo Issue usando la plantilla de **Bug Report**.
3. Incluye:
   - Sistema operativo (macOS / Windows) y versión
   - Versión de GT7 Telemetry Pro
   - Pasos para reproducir el error
   - Comportamiento esperado vs. comportamiento actual
   - Capturas de pantalla o logs si es posible (`gt7_telemetry.log`)

### Sugerir Mejoras

1. Crea un nuevo Issue usando la plantilla de **Feature Request**.
2. Describe claramente la funcionalidad deseada y por qué sería útil.

### Contribuir Código

1. **Fork** el repositorio.
2. Crea una rama descriptiva: `git checkout -b feature/nombre-de-la-mejora`
3. Haz tus cambios siguiendo las reglas de arquitectura (ver abajo).
4. Verifica tu código con el simulador: `python tools/test_full_ui_sim.py`
5. Haz commit con mensajes descriptivos en español.
6. Abre un **Pull Request** contra la rama `master`.

## Reglas de Arquitectura Obligatorias

> ⚠️ **Estas reglas son inquebrantables.** Los PRs que las violen serán rechazados.

### Stack Tecnológico
- **GUI:** Solo `PyQt6`. Prohibidas las tecnologías web (HTML, CSS, JS, Electron, etc.).
- **Gráficas:** Solo `pyqtgraph`. Prohibido `matplotlib` (demasiado lento para 60 FPS).
- **Datos:** `numpy` para procesamiento vectorizado. Prohibido iterar con `for` sobre 100K+ puntos.

### Rendimiento
- **NUNCA** bloquees el hilo principal (Main Thread).
- Todo trabajo pesado debe ocurrir en hilos separados (`threading.Thread` o `QThread`).
- Usa `pyqtSignal` para comunicación entre hilos y la GUI.

### Estilo Visual
- **Solo Modo Diurno** (Daylight Mode). Prohibidos los temas oscuros y colores neón.
- Usa tokens de `ui/theme.py` (`Theme.BG_PANEL`, `Theme.TEXT_PRIMARY`, etc.). Prohibido hardcodear colores.
- Botones en macOS deben incluir `border-radius: 6px`, bordes explícitos y padding.

### Base de Datos
- Archivo maestro único: `telemetry_master.sqlite` (WAL mode).
- Exportación usa `VACUUM INTO`. Importación usa clave natural `(start_time, car_id)`.
- Nunca crear subcarpetas como `Sessions/`.

### Seguridad
- Las fórmulas del usuario se validan con `SafeMathVisitor` (AST) antes de evaluar.
- Slots cross-thread deben usar el decorador `@safe_slot`.

## Estructura del Proyecto

```
core/       → Lógica de negocio (modelos, BD, alertas, delta-T, math channels)
services/   → I/O (UDP, criptografía, sync LAN, auto-update, MoTeC export)
ui/         → Interfaz gráfica (PyQt6 + pyqtgraph)
data/       → Datos estáticos (autos, pistas)
tools/      → Scripts de testing y simulación
```

Para más detalles, consulta `.agents/AGENTS.md` y `.ai/architecture.md`.

## Entorno de Desarrollo

```bash
git clone https://github.com/DEMG-DEV/RGDev.App.GT7TelemetryPro.git
cd RGDev.App.GT7TelemetryPro
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
python main.py
```

### Verificar cambios visuales sin consola PS4/PS5:
```bash
python tools/test_full_ui_sim.py
```

## Licencia

Al contribuir, aceptas que tus contribuciones serán licenciadas bajo la [Licencia MIT](LICENSE) del proyecto.
