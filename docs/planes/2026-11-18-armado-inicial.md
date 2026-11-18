# Armado inicial

Tareas para armar lo decidido en `docs/decisiones/`. Van en orden: cada una depende de las anteriores.
Al crear el repo en GitHub (tarea 1), cada tarea pasa a ser un issue del milestone 0.1.0, y este archivo queda como registro.

## 1. Crear el repo local y en GitHub
- **Qué:**
  - `git init` con la rama `main`;
  - un `.gitignore` para Python, `.venv/` y `.capturas/`;
  - `LICENSE` con el texto MIT;
  - un README mínimo: qué es el juego y enlaces a `docs/`;
  - un primer commit con los documentos;
  - el repo público en GitHub, y el push.
- **Por qué:** sin repo no hay issues, ni CI, ni PRs.
- **Terminado cuando:** el repo público existe y tiene un commit con `AGENTS.md`, `CLAUDE.md`, `docs/`, `LICENSE` y el README.
- **Nota:** es la única vez que se hace commit directo en `main`, porque todavía no existe nada contra qué abrir un PR. Crear el repo en GitHub es una acción pública, así que se hace con tu aprobación explícita. Antes hay que definir el nombre del copyright de `LICENSE` (ADR 0014).

## 2. Configurar el repo en GitHub y pasar este plan a issues
- **Qué:**
  - solo squash merge, con el título del PR como mensaje;
  - borrar las ramas después del merge;
  - secret scanning con push protection;
  - reporte privado de vulnerabilidades;
  - alertas de Dependabot, sin PRs automáticos;
  - *immutable releases*;
  - el milestone 0.1.0, el tablero de Projects con sus automatizaciones, y un issue por tarea de este plan.
- **Por qué:** ADR 0010 y 0011.
- **Terminado cuando:** `gh api` muestra cada ajuste y el tablero tiene los issues.
- **Verificar:** que las automatizaciones de Projects estén en el plan gratis, y el alcance de *immutable releases*.

## 3. Armar el esqueleto del proyecto con uv
- **Qué:**
  - `uv init --app --package`;
  - en `pyproject.toml`: `required-version`, `exclude-newer = "7 days"`, `no-build = true` y `license = "MIT"`;
  - `.python-version` con `3.14.10`;
  - `src/circlebh/` con `world/`, `render/`, `scenes/` y `balance.py` vacíos;
  - `uv run circlebh` abre una ventana con el plano vacío.
- **Por qué:** ADR 0001, 0002 y 0003.
- **Terminado cuando:** `uv run circlebh` abre la ventana y `uv lock --check` pasa.
- **Lo haces tú:** instalar `pygame-ce==2.5.8`, con el comando que te doy.
- **Verificar:** que `Vector2` funcione sin `pygame.init()`, y que `pygame-ce` no conviva con `pygame`.

## 4. Configurar los chequeos fast y check
- **Qué:**
  - las tareas de poethepoet: `fast`, `check`, `capturas` y `medios`, estas dos últimas vacías por ahora;
  - ruff, con las reglas del ADR 0008;
  - `mypy --strict`;
  - los dos contratos de import-linter;
  - pytest estricto, con perfiles de Hypothesis y cobertura;
  - `uv audit`;
  - el control de imágenes;
  - un primer test trivial.
- **Por qué:** ADR 0003, 0007, 0008, 0011 y 0013.
- **Terminado cuando:** `uv run poe check` pasa en verde. Además, se demuestra que falla en cada caso: un import de `pygame.draw` en `world/`, un PNG en la raíz y un test rojo.
- **Lo haces tú:** instalar las dependencias de desarrollo, con el comando que te doy.

## 5. Configurar los controles de la IA y pre-commit
- **Qué:**
  - `.claude/settings.json`, con los permisos del ADR 0012 y Superpowers en `enabledPlugins`;
  - el hook Stop, con su script;
  - `.pre-commit-config.yaml` con `poe fast`;
  - en el README, el paso `uv run pre-commit install`.
- **Por qué:** ADR 0012.
- **Terminado cuando:**
  - un `git push --force` es rechazado;
  - el hook Stop bloquea el turno con un test rojo y lo deja pasar con un `xfail` de ejercicio;
  - pre-commit bloquea un commit con un test rojo.
- **Verificar:** si un `ask` se puede limitar a una sección de `pyproject.toml`, y si Superpowers necesita que se declare su marketplace.

## 6. Configurar la CI y proteger main
- **Qué:**
  - `.github/workflows/ci.yml`, que corre `uv run poe check`;
  - permisos mínimos, `persist-credentials: false` y acciones fijadas por SHA;
  - después, el ruleset de `main` del ADR 0010.
- **Por qué:** ADR 0008, 0010 y 0011.
- **Terminado cuando:**
  - un PR muestra el chequeo `check` en verde;
  - `gh api` muestra el ruleset;
  - un push directo a `main` es rechazado.
- **Verificar:** que el autor de un PR no pueda aprobar su propio PR.

## 7. Agregar las plantillas de PR y de issue
- **Qué:**
  - `.github/pull_request_template.md`, con Qué cambia, Por qué, Verificación y Prueba manual;
  - una plantilla de issue, con Qué, Por qué y Terminado cuando.
- **Por qué:** ADR 0010 y 0013.
- **Terminado cuando:** un PR y un issue nuevos se abren con las plantillas.

## 8. Sacar capturas sin ventana
- **Qué:**
  - las opciones `--demo`, `--seed`, `--speed`, `--scenario` y `--capture` en `circlebh`;
  - el driver de video sin ventana;
  - `poe capturas`, que guarda en `.capturas/`.
- **Por qué:** ADR 0007 y 0013.
- **Terminado cuando:** `uv run poe capturas` guarda tres PNG del plano vacío, y se muestran en la sesión.
- **Verificar:** el nombre exacto del driver `dummy`.

## 9. Armar el workflow de release
- **Qué:**
  - `.github/workflows/release.yml`, con una matriz de PyInstaller en modo carpeta para Windows x64, macOS ARM y Linux x64;
  - un smoke en modo demo sin ventana;
  - zips y Release con notas automáticas;
  - el tag `vX.Y.Z`, y `workflow_dispatch` para probarlo sin publicar.
- **Por qué:** ADR 0009.
- **Terminado cuando:** una corrida manual, sin publicar, deja los tres zips como artefactos y el smoke pasa en los tres sistemas.
- **Verificar:** que el runner de macOS sea ARM, y que el driver sin ventana funcione en los tres sistemas.

## 10. Planificar la versión 0.1.0
- **Qué:** brainstorming y una spec, con escenarios de test, para la primera versión jugable. Por ejemplo: el jugador, el plano, la cámara, un arma y un enemigo. Después, su plan.
- **Por qué:** desde aquí empieza el juego.
- **Terminado cuando:** la spec y el plan están aprobados en `docs/specs/` y `docs/planes/`, y sus tareas son issues.
- **Decidir aquí:** si importar de JSON a Python va en el MVP o con el editor (ADR 0004).
