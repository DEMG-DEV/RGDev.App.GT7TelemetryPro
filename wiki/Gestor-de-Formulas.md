# 🧮 Gestor de Fórmulas

> **Archivo:** `ui/formula_manager.py` · **Clase:** `FormulaManagerWidget` · **196 líneas**

El Gestor de Fórmulas permite crear, editar y eliminar canales matemáticos personalizados que se evalúan sobre los datos de telemetría. Las fórmulas se ejecutan en un sandbox seguro basado en AST (Abstract Syntax Tree).

---

## Vista General

```
┌──────────────────────┬────────────────────────────────────────────────┐
│  Canales Guardados:  │  Nombre: [g_total_________________]           │
│                      │  Grupo:  [Chassis ▼]  Color: [#FF6600]       │
│  ┌────────────────┐  │  Descripción: [Fuerza G total combinada]     │
│  │ g_total        │  │                                               │
│  │ slip_angle_f   │  │  Expresión Matemática (NumPy vía 'np.'):     │
│  │ aero_balance   │  │  ┌─────────────────────────────────────────┐ │
│  │ brake_bias     │  │  │ np.sqrt(lateral_g**2 + longitudinal_g   │ │
│  │                │  │  │ **2)                                    │ │
│  └────────────────┘  │  └─────────────────────────────────────────┘ │
│                      │                                               │
│  [Nuevo Canal]       │  [Prueba (Dry Run)]    [Guardar Canal]       │
│  [Eliminar]          │                                               │
│                      │  ✅ Validación exitosa: shape=(3847,),       │
│                      │     min=0.023, max=2.341                      │
└──────────────────────┴────────────────────────────────────────────────┘
```

---

## Layout (Splitter Horizontal 250:550)

### Panel Izquierdo — Lista de Canales

| Elemento | Descripción |
|----------|-------------|
| `QListWidget` | Lista de canales existentes guardados en `math_channels.json` |
| **Nuevo Canal** | Limpia el editor para crear un canal nuevo |
| **Eliminar** | Borra el canal seleccionado (con diálogo de confirmación) |

### Panel Derecho — Editor de Canal

| Campo | Widget | Descripción |
|-------|--------|-------------|
| **Nombre** | `QLineEdit` | Identificador único del canal. Solo lectura al editar existente. |
| **Grupo** | `QComboBox` editable | Engine / Suspension / Tyres / Driver / Chassis / Custom |
| **Color** | `QLineEdit` (80px) | Color hex para la gráfica (ej: `#FF6600`) |
| **Descripción** | `QLineEdit` | Descripción legible del canal |
| **Expresión** | `QTextEdit` (monospace) | Fórmula matemática usando variables de telemetría y NumPy |

---

## Variables Disponibles

Las siguientes variables están disponibles en las expresiones como arrays NumPy:

| Variable | Tipo | Descripción |
|----------|------|-------------|
| `speed` | `np.array` | Velocidad en km/h |
| `rpm` | `np.array` | Revoluciones por minuto |
| `throttle` | `np.array` | Acelerador (0-255) |
| `brake` | `np.array` | Freno (0-255) |
| `boost` | `np.array` | Presión de turbo (bar) |
| `steer` | `np.array` | Ángulo de dirección |
| `lateral_g` | `np.array` | Aceleración lateral (G) |
| `longitudinal_g` | `np.array` | Aceleración longitudinal (G) |
| `susp_fl`, `susp_fr`, `susp_rl`, `susp_rr` | `np.array` | Velocidad de suspensión por rueda |
| `tyre_fl`, `tyre_fr`, `tyre_rl`, `tyre_rr` | `np.array` | Temperatura de neumáticos (°C) |
| `gear` | `np.array` | Marcha actual |
| `timestamp` | `np.array` | Tiempo en segundos |

---

## Ejemplos de Fórmulas

| Canal | Expresión | Descripción |
|-------|-----------|-------------|
| `g_total` | `np.sqrt(lateral_g**2 + longitudinal_g**2)` | Fuerza G total combinada |
| `speed_mph` | `speed * 0.621371` | Velocidad en millas por hora |
| `brake_pct` | `brake / 255 * 100` | Freno como porcentaje 0-100% |
| `throttle_pct` | `throttle / 255 * 100` | Acelerador como porcentaje |
| `tyre_spread` | `np.max([tyre_fl, tyre_fr, tyre_rl, tyre_rr], axis=0) - np.min([tyre_fl, tyre_fr, tyre_rl, tyre_rr], axis=0)` | Diferencia máxima entre neumáticos |
| `susp_balance` | `(susp_fl + susp_fr) / 2 - (susp_rl + susp_rr) / 2` | Balance de suspensión delante-detrás |

---

## Sistema de Seguridad (AST Sandbox)

Todas las fórmulas pasan por `SafeMathVisitor` antes de ejecutarse:

### ✅ Permitido
- Operaciones matemáticas: `+`, `-`, `*`, `/`, `**`, `%`
- Comparaciones: `>`, `<`, `>=`, `<=`, `==`
- Funciones NumPy: `np.sqrt()`, `np.abs()`, `np.mean()`, `np.max()`, `np.min()`, `np.diff()`, `np.cumsum()`, etc.
- Built-ins seguros: `max`, `min`, `abs`, `round`, `sum`, `len`
- Constantes: `np.pi`, `np.e`

### ❌ Prohibido (lanza `MathSecurityError`)
- Asignación de variables: `x = 5`
- Importaciones: `import os`
- Llamadas a sistema: `os.system()`, `exec()`, `open()`
- Atributos no-numpy: `str.upper()`, `list.append()`
- Cualquier función no incluida en la whitelist

---

## Botón "Prueba (Dry Run)"

El dry-run permite probar la fórmula contra datos reales antes de guardarla:

1. Inyecta temporalmente el canal en el `DynamicMathEngine`
2. Evalúa la expresión contra los datos de la sesión cargada
3. Muestra: forma del resultado (`shape`), valor mínimo y máximo
4. Restaura el estado original del engine (no persiste si no se guarda)

### Estados del Label

| Color | Mensaje | Significado |
|-------|---------|-------------|
| 🟢 Verde | "✅ Validación exitosa: shape=(3847,), min=0.02, max=2.34" | Fórmula válida y evaluada |
| 🔴 Rojo | "❌ Error: name 'invalid_var' is not defined" | Error de sintaxis o variable inexistente |

---

## Persistencia

Los canales se guardan en `math_channels.json` en el directorio de datos de la aplicación:

```json
{
  "g_total": {
    "expression": "np.sqrt(lateral_g**2 + longitudinal_g**2)",
    "group": "Chassis",
    "color": "#FF6600",
    "description": "Fuerza G total combinada"
  }
}
```
