---
estado: aceptado
fecha: 2026-11-18
---

# Verificar con poethepoet, ruff, mypy estricto y CI solo en Linux

## Contexto y problema

Si algo pasa en local y falla en la CI, se pierde la confianza, y un chequeo lento no lo corre nadie. Hace falta un chequeo rápido para después de cada cambio y uno completo para antes del push, y el completo tiene que ser el mismo comando en local y en la CI.

## Factores de decisión

- El mismo comando en local y en la CI.
- Que funcione igual en Linux, Windows y macOS.
- Herramientas estables.

## Opciones consideradas

- Tareas: poethepoet, un script Python propio, o un Makefile o justfile.
- Tipos: mypy estricto, pyright o ty.
- Sistemas en la CI: solo Linux, o Linux, Windows y macOS.

## Resultado de la decisión

| | `uv run poe fast` | `uv run poe check` |
|---|---|---|
| Cuándo | después de cada cambio | antes del push y en la CI |
| Formato | `ruff format` | `ruff format --check` |
| Lint | `ruff check --fix` | `ruff check` |
| Tipos | — | `mypy --strict` sobre todo `src/` |
| Capas | — | `lint-imports` (ADR 0003) |
| Tests | unitarios | todos, con la simulación (ADR 0007) |
| Otros | — | `uv audit` (ADR 0011), control de imágenes (ADR 0013), reporte de cobertura |
| Meta de tiempo | menos de 10 s | menos de 1 minuto (estimado) |

- **Versiones:** poethepoet 0.49.0, ruff 0.17.4 y mypy 2.4.1.
- **Reglas de ruff:** las de por defecto más `I`, `B`, `UP`, `SIM` y `N`. No hay una regla que exija docstrings: eso queda para la revisión.
- **CI:**
  - GitHub Actions, solo en Linux, en cada PR y en cada push a `main`;
  - `astral-sh/setup-uv` v10.3.3, fijado por SHA;
  - los ejecutables por sistema se arman en el release (ADR 0009).

### Consecuencias

- Bueno: hay un solo comando que recordar, y es igual en todas partes.
- Bueno: `mypy --strict` también sobre `render/` muestra que se sabe tipar código de Pygame.
- Malo: poethepoet es una dependencia más.
- Malo: mypy es más lento que las alternativas.
- Malo: un problema propio de Windows o macOS se ve recién al armar el release.

### Confirmación

- El workflow de CI corre `uv run poe check`, y el ruleset de `main` lo exige (ADR 0010).

## Pros y contras de las opciones

### poethepoet
- Bueno: las tareas se declaran en `pyproject.toml` y funcionan igual en todos los sistemas.
- Malo: es una dependencia.

### Script propio
- Bueno: no tiene dependencias.
- Malo: es código propio que hay que mantener.

### Makefile o justfile
- Bueno: son muy conocidos.
- Malo: make no viene en Windows, y just hay que instalarlo aparte.

### mypy
- Bueno: es el estándar, es estable y es Python puro.
- Malo: es más lento.

### pyright
- Bueno: es rápido.
- Malo: el paquete de PyPI descarga Node (no verificado).

### ty
- Bueno: es muy rápido.
- Malo: sigue en Beta (0.0.x).

### Solo Linux
- Bueno: es rápido y simple.
- Malo: no ve diferencias entre sistemas.

### Tres sistemas
- Bueno: atrapa diferencias entre sistemas.
- Malo: tarda más y deja tres resultados que revisar en cada PR.

## Más información

- https://pypi.org/ (versiones de ruff, mypy, ty, pyright y poethepoet; consultado el 2026-11-18)
- https://github.com/astral-sh/setup-uv (lee `required-version`; consultado el 2026-11-18)
- https://docs.github.com/en/billing/concepts/product-billing/github-actions (gratis con runners estándar en repos públicos; consultado el 2026-11-18)
