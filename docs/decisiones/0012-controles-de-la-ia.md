---
estado: aceptado; la línea de ejercicios pendientes la reemplaza el ADR 0017
fecha: 2026-11-18
---

# Controlar a la IA con permisos, un hook Stop y pre-commit, sin sandbox

## Contexto y problema

Una regla que solo está escrita se olvida en una sesión larga, y un control que estorba se esquiva. Hay que elegir pocos controles deterministas, y que sirvan, para que la IA no lea credenciales, no fuerce un push, no se salte los hooks, no instale paquetes y no cambie sus propios controles.

## Factores de decisión

- Pocos controles, y que sirvan.
- Que valgan en todo modo de permisos, incluido auto mode.
- Que no dependan de la máquina de una persona.

## Opciones consideradas

- Hook Stop: correr `poe fast` cuando hubo cambios, o dejarlo solo como instrucción.
- Hooks de git: pre-commit con `poe fast`, pre-commit solo con ruff, o ninguno.
- Sandbox: activado, con `gh` fuera; o solo permisos.

## Resultado de la decisión

- **Configuración versionada:** en `.claude/settings.json`.
  - Superpowers se activa con `enabledPlugins` (ADR 0010).
  - `deny`:
    - force push, en todas sus formas;
    - `--no-verify`;
    - `gh pr merge` y `gh repo delete`;
    - instalar o actualizar: `uv add`, `uv remove`, `uv lock --upgrade`, `pip install` y `uv pip install`;
    - leer `.env*`, `~/.ssh/**` y `~/.config/gh/**`.
  - `ask`:
    - editar `.claude/**`, `.github/**`, `.pre-commit-config.yaml` y la configuración de herramientas en `pyproject.toml`;
    - `gh pr create` y `gh release *`.
- **Hook Stop de Claude Code:** si `git status` muestra cambios, corre `uv run poe fast`. Si falla, sale con código 2 y Claude no puede cerrar el turno. Respeta `stop_hook_active` para no repetirse en bucle.
- **pre-commit 4.7.0:** corre `uv run poe fast` antes de cada commit, de la persona o de la IA. El README indica `uv run pre-commit install`.
- **Ejercicios pendientes:** se marcan con `xfail` estricto (ADR 0007), para que el hook y pre-commit no los bloqueen.
- **Sin sandbox:** el riesgo de un subproceso comprometido se acepta, porque las dependencias son pocas y conocidas.
- **Límites escritos en `CLAUDE.md`:** porque el clasificador de auto mode lee `CLAUDE.md`, no `settings.json`.

### Consecuencias

- Bueno: nunca se entrega ni se hace commit de algo que no pase el chequeo rápido.
- Bueno: un `ask` pregunta incluso en auto mode, así que los propios controles no cambian sin aprobación.
- Malo: suma hasta 10 s al final de los turnos con cambios, y a cada commit.
- Malo: cada clon tiene que correr `pre-commit install`.
- Malo: las reglas de Bash no son una barrera de seguridad, y un `deny` de `Read` no frena a un script que abra el archivo por su cuenta. Sin sandbox, eso queda sin cubrir.

### Confirmación

- `.claude/settings.json` y `.pre-commit-config.yaml` están versionados.
- Al armarlos, se prueba que un `git push --force` es rechazado y que el hook Stop bloquea con un test rojo.
- Pendiente de verificar al armar: si un `ask` se puede limitar a una sección de `pyproject.toml` (si no, aplica a todo el archivo) y si Superpowers necesita que se declare su marketplace.

## Pros y contras de las opciones

### Hook Stop
- Bueno: el chequeo no se olvida.
- Malo: suma tiempo.

### Solo como instrucción
- Bueno: es más liviano.
- Malo: se olvida.

### pre-commit con `poe fast`
- Bueno: cubre también los commits de la persona.
- Malo: necesita instalarse en cada clon y bloquea commits a medio hacer.

### pre-commit solo con ruff
- Bueno: es rápido.
- Malo: los tests rojos los ve recién la CI.

### Sin hooks de git
- Bueno: es lo más simple.
- Malo: un commit roto llega a la CI.

### Sandbox
- Bueno: es una barrera real del sistema operativo.
- Malo: necesita bubblewrap y socat, y `gh` requiere una excepción (no verificado cómo).

### Solo permisos
- Bueno: es lo más simple.
- Malo: no frena a un subproceso.

## Más información

- https://code.claude.com/docs/en/permissions.md (las reglas de Bash no son una barrera; los `deny` de `Read` no cubren subprocesos; consultado el 2026-11-18)
- https://code.claude.com/docs/en/auto-mode-config.md (el clasificador lee `CLAUDE.md`; consultado el 2026-11-18)
- https://code.claude.com/docs/en/hooks.md (Stop, código de salida 2, `stop_hook_active`; consultado el 2026-11-18)
- https://code.claude.com/docs/en/sandboxing.md (consultado el 2026-11-18)
- Claude Code 2.1.327
