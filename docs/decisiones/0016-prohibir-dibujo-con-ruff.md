---
estado: aceptado
fecha: 2026-11-18
---

# Prohibir `pygame.draw` y `pygame.display` fuera del dibujo con ruff

Reemplaza el segundo contrato de import-linter del ADR 0003. El contrato de capas y el resto del ADR 0003 siguen vigentes.

## Contexto y problema

El ADR 0003 pide dos contratos de import-linter: uno de capas, y otro que prohíbe `pygame.display` y `pygame.draw` en `world`. El segundo no se puede escribir. import-linter 2.16 trata cada paquete externo como un solo nodo y lo rechaza:

```
Invalid forbidden module pygame.display: subpackages of external packages are not valid.
```

Además, import-linter mira las sentencias `import`, no el uso de atributos. `import pygame` seguido de `pygame.draw.line(...)` pasaría igual, y es la forma más común de escribir Pygame.

## Factores de decisión

- Que `world` no pueda dibujar ni tocar la pantalla, sin importar cómo se escriba el import.
- Que `world` siga usando `Vector2` (ADR 0003).
- No sumar dependencias ni código propio.

## Opciones consideradas

- La regla `TID251` (banned-api) de ruff
- Prohibir todo `pygame` en `world` con import-linter
- Un script propio que revise el AST

## Resultado de la decisión

Elegimos **`TID251` de ruff**:

- `pygame.draw` y `pygame.display` están prohibidos en todo el proyecto, con un mensaje que cita este ADR.
- La regla se libera con `per-file-ignores` solo donde se dibuja: `src/circlebh/render/`, `src/circlebh/scenes/` y `src/circlebh/__main__.py`.
- Así también cubre `balance.py` y cualquier módulo nuevo que no sea de dibujo.
- import-linter queda con un solo contrato: el de capas.

### Consecuencias

- Bueno: detecta `import pygame.draw`, `from pygame import draw` y `pygame.draw.line(...)` después de `import pygame`.
- Bueno: corre en `poe fast`, no solo en `poe check`, porque es parte de `ruff check`.
- Bueno: no suma dependencias.
- Malo: el cumplimiento de la arquitectura queda repartido en dos herramientas.
- Malo: un módulo nuevo de dibujo fuera de `render/` o `scenes/` necesita su propia excepción.

### Confirmación

- `pyproject.toml` tiene `[tool.ruff.lint.flake8-tidy-imports.banned-api]` con `pygame.draw` y `pygame.display`, y los `per-file-ignores` de `TID251` solo nombran `render/`, `scenes/` y `__main__.py`.
- Un `pygame.draw.line(...)` en `world/` hace fallar `poe fast` y `poe check`.

## Pros y contras de las opciones

### `TID251` de ruff
- Bueno: resuelve nombres completos, así que detecta el uso de atributos.
- Malo: son dos herramientas para la arquitectura.

### Prohibir todo `pygame` en `world`
- Bueno: queda en un solo contrato de import-linter.
- Malo: `world` no podría usar `Vector2`, y habría que escribir un vector propio.

### Script propio con AST
- Bueno: todo queda en un lugar.
- Malo: es código nuevo que mantener para hacer lo que ruff ya hace.

## Más información

- `lint-imports` con import-linter 2.16, probado el 2026-11-18: el mensaje de arriba.
- `ruff check` con ruff 0.17.4 y `TID251`, probado el 2026-11-18 con `import pygame.draw`, `from pygame import draw`, `pygame.draw.line(...)` y `pygame.display.flip()`: los cuatro fallan, y `from pygame.math import Vector2` pasa.
- https://docs.astral.sh/ruff/rules/banned-api/ (consultado el 2026-11-18)
- https://import-linter.readthedocs.io/en/stable/contract_types.html#forbidden-modules (consultado el 2026-11-18; no verificado que la página documente la restricción de submódulos externos)
