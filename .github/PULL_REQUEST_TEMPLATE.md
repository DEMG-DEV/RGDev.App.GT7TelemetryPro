## Descripción

<!-- Describe brevemente qué cambia este PR y por qué -->

## Tipo de Cambio

- [ ] 🐛 Bug fix
- [ ] ✨ Nueva funcionalidad (Feature)
- [ ] ♻️ Refactoring (sin cambio de comportamiento)
- [ ] 📝 Documentación
- [ ] ⚙️ Configuración / CI-CD
- [ ] 🎨 Estilo / UI

## Cambios Realizados

<!-- Lista los cambios principales -->

- 
- 
- 

## Archivos Modificados

<!-- Lista los archivos principales que fueron modificados -->

| Archivo | Cambio |
|---------|--------|
|  |  |

## Checklist de Arquitectura

> ⚠️ Todos los items deben cumplirse para que el PR sea aprobado.

- [ ] No se usan tecnologías web (HTML, CSS, JS, Electron, etc.)
- [ ] GUI exclusivamente en `PyQt6`, gráficas en `pyqtgraph`
- [ ] No se bloquea el hilo principal (trabajo pesado en hilos separados)
- [ ] Se usa `pyqtSignal` para comunicación entre hilos y GUI
- [ ] Estilos usan tokens de `ui/theme.py` (no colores hardcodeados)
- [ ] Solo Modo Diurno (Daylight Mode), sin temas oscuros
- [ ] Slots cross-thread usan `@safe_slot`
- [ ] Datos vectorizados con `numpy` (no iteración `for` sobre 100K+ puntos)

## Testing

- [ ] Verificado con `tools/test_full_ui_sim.py` (simulación sin consola)
- [ ] No se rompen funcionalidades existentes

## Capturas de Pantalla

<!-- Si hay cambios visuales, agrega capturas antes/después -->
