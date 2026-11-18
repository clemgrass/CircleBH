---
estado: aceptado; la versión de uv la reemplaza el ADR 0015
fecha: 2026-11-18
---

# Gestionar el entorno con uv: versiones exactas, 7 días de antigüedad y sin compilar dependencias

## Contexto y problema

Si cada máquina usa otra versión, el resultado cambia. Además, un paquete recién publicado o comprometido es una puerta de entrada. Hace falta un gestor que fije el Python, las dependencias y la herramienta misma, y que la CI use los mismos archivos.

## Factores de decisión

- Reproducibilidad: que nada dependa de la máquina de una persona.
- Cadena de suministro: una edad mínima para las versiones y nada de scripts de instalación de terceros.
- Simplicidad: una sola herramienta.

## Opciones consideradas

- uv
- pip con venv (y pip-tools para el lock)
- Poetry (no discutida)

## Resultado de la decisión

Elegimos **uv**, configurado así:

- `.python-version` contiene `3.14.10`, y uv descarga ese Python si falta.
- `uv.lock` fija las versiones exactas, y la CI usa `uv sync --locked`.
- `required-version = "==0.13.4"` en `[tool.uv]` fija la versión de uv.
- `exclude-newer = "7 days"` impide usar versiones con menos de 7 días.
- `no-build = true` hace fallar cualquier dependencia que no traiga wheel.

Cada paquete nuevo se propone con su motivo, su última release y quién lo mantiene. El usuario lo aprueba y lo instala.

### Consecuencias

- Bueno: el mismo Python y las mismas versiones en todas las máquinas y en la CI.
- Bueno: una versión maliciosa recién publicada no entra antes de 7 días.
- Malo: quien quiera correr el juego desde el código necesita uv.
- Malo: una corrección de seguridad urgente también espera 7 días. Si hace falta, se exime ese paquete con `exclude-newer-package`, con su motivo escrito.
- Malo: para subir de versión de uv hay que editar `required-version`.

### Confirmación

- La CI corre `uv sync --locked`, que falla si el lock está desactualizado.
- `astral-sh/setup-uv` lee `required-version`, así que la CI usa el mismo uv.
- Verificado el 2026-11-18: `uv.lock` guarda el plazo (`exclude-newer-span = "P7D"`) y no una fecha fija, y `uv lock --check` sigue pasando con el tiempo.

## Pros y contras de las opciones

### uv
- Bueno: maneja el Python, el entorno, el lock exacto, la edad mínima y el bloqueo de compilación.
- Malo: es una herramienta específica, y no viene con Python.

### pip con venv
- Bueno: es lo más estándar y viene con Python.
- Malo: no tiene lock nativo ni edad mínima, y obliga a sumar herramientas.

### Poetry (no discutida)
- Bueno: es maduro y tiene lock.
- Malo: no maneja la versión de Python y su resolución es más lenta (no verificado).

## Más información

- https://docs.astral.sh/uv/reference/settings/#exclude-newer (consultado el 2026-11-18)
- https://docs.astral.sh/uv/reference/settings/#required-version (consultado el 2026-11-18)
- https://docs.astral.sh/uv/reference/settings/#no-build (consultado el 2026-11-18)
- https://github.com/astral-sh/setup-uv (v10.3.3, consultado el 2026-11-18)
