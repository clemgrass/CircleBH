@AGENTS.md

## Límites
Estos límites valen en todo modo de permisos, incluido auto mode:
- No leas secretos ni credenciales (`.env*`, `~/.ssh/`, `~/.config/gh/`, tokens).
- No fuerces un push, no uses `--no-verify` y no te saltes los hooks.
- No instales ni actualices paquetes. Dale el comando al usuario.
- No hagas merge de PRs ni borres el repo. No crees un PR ni un release sin mostrar su texto y tener aprobación.
- No cambies la configuración de tus propios controles (`.claude/`, `.github/`, `.pre-commit-config.yaml`, la configuración de herramientas en `pyproject.toml`) ni la del repo en GitHub (rulesets, ajustes) sin aprobación explícita de ese cambio.
- No salgas de la carpeta del proyecto.

## Claude Code en este proyecto
- Superpowers está activo. Usa sus skills de proceso (brainstorming, planes, TDD y verificación). No uses el desarrollo con subagentes. Si algo choca con `AGENTS.md`, manda `AGENTS.md`.
- El hook Stop corre `uv run poe fast` cuando hay cambios. Si falla, arréglalo; no lo esquives.
- Los commits donde escribiste código llevan el trailer `Co-Authored-By` de Claude.
