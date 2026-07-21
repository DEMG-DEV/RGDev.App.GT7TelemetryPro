# Política de Seguridad — GT7 Telemetry Pro

## Versiones Soportadas

| Versión | Soporte |
|---------|---------|
| 1.2.x   | ✅ Activo |
| 1.1.x   | ⚠️ Solo bugs críticos |
| < 1.0   | ❌ Sin soporte |

## Reportar una Vulnerabilidad

Si descubres una vulnerabilidad de seguridad en GT7 Telemetry Pro, **por favor NO la reportes como un Issue público**.

### Proceso de reporte privado:

1. Envía un correo a **demg@outlook.com** con el asunto: `[SECURITY] GT7 Telemetry Pro`.
2. Incluye:
   - Descripción detallada de la vulnerabilidad
   - Pasos para reproducirla
   - Impacto potencial
   - Sugerencia de corrección (si la tienes)
3. Recibirás una respuesta dentro de **72 horas** confirmando la recepción.
4. Trabajaremos contigo para entender y resolver el problema antes de cualquier divulgación pública.

## Alcance de Seguridad

### Áreas críticas del proyecto:

| Componente | Riesgo | Mitigación |
|------------|--------|------------|
| **Canales Matemáticos** (`core/dynamic_math.py`) | Ejecución de código arbitrario via fórmulas del usuario | `SafeMathVisitor` (AST sandbox) valida expresiones antes de `eval()`. Whitelist estricta de funciones permitidas. |
| **Desencriptación Salsa20** (`services/crypto.py`) | Manipulación de paquetes de red | Validación de magic number `G7S0` post-descifrado. Solo acepta paquetes UDP del puerto 33740. |
| **Sincronización LAN** (`services/sync_service.py`) | Inyección de datos maliciosos via TCP | Mensajes JSON delimitados por longitud con validación de esquema. Compresión zlib. Solo red local. |
| **Auto-Actualización** (`services/updater.py`) | Descarga de binarios comprometidos | Descarga exclusivamente desde GitHub Releases del repositorio oficial (`DEMG-DEV/RGDev.App.GT7TelemetryPro`). |
| **Base de Datos** (`core/database.py`) | SQL injection | Uso exclusivo de queries parametrizadas (`?` placeholders). Nunca se interpolan strings en SQL. |

## Buenas Prácticas Implementadas

- ✅ No se usa `eval()` sin validación AST previa
- ✅ Queries SQL parametrizadas en todo el proyecto
- ✅ Decorador `@safe_slot` para captura de excepciones en slots PyQt6
- ✅ Comunicación de red limitada a red local (no hay servidores externos excepto GitHub API para updates)
- ✅ Sin dependencias con vulnerabilidades conocidas

## Divulgación

Seguimos un proceso de **divulgación responsable**. Una vez corregida la vulnerabilidad, publicaremos un advisory de seguridad con los detalles y créditos correspondientes.
