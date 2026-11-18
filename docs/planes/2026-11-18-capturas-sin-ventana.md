# Capturas sin ventana: plan de implementación

> **Para agentes:** se ejecuta con superpowers:executing-plans, en la misma sesión (CLAUDE.md: sin desarrollo con subagentes). Los pasos usan casillas (`- [ ]`).

**Objetivo:** `uv run poe capturas` guarda tres PNG del plano vacío en `.capturas/` sin abrir una ventana, de forma determinista.

**Arquitectura:** `cli.py` convierte los argumentos en un `RunOptions`. `world/clock.py` tiene el reloj de pasos fijos y la conversión de tiempos a pasos. `__main__.py` elige entre el modo con ventana (reloj real × `--speed`) y el modo captura (paso a paso, sin esperar, con el driver `dummy`).

**Stack:** Python 3.14, pygame-ce 2.5.8, `argparse` de la biblioteca estándar y pytest.

**Spec:** `docs/specs/2026-11-18-capturas-sin-ventana.md`

## Restricciones globales

- Un paso dura exactamente `1/60` s, y el acumulador se topa en `0.25` s (ADR 0005).
- `world/` no importa `pygame.draw` ni `pygame.display` (ADR 0016). Solo `render/`, `scenes/` y `__main__.py` dibujan.
- El driver sin ventana es `SDL_VIDEODRIVER=dummy`, y se fija antes de `pygame.init()`.
- Los archivos se llaman `.capturas/<escenario>-seed<N>-t<segundos con 2 decimales>.png`, relativos a la carpeta actual.
- Los errores de la línea de comandos salen por `argparse`, con código 2.
- La ventana y las capturas miden 1280×720.
- `uv run poe fast` después de cada paso con código; `uv run poe check` antes del push.

## Foco de la revisión

1. `--capture inf` o `--capture nan`: debe dar un error de código 2. Con `inf`, el modo captura no terminaría nunca. → Tarea 2, test `test_capture_rechaza_tiempos_no_finitos`.
2. `--capture "0, 1"`, con espacios después de la coma: debe aceptarse como `(0.0, 1.0)`. → Tarea 2, test `test_capture_acepta_espacios`.
3. Dos tiempos que caen en el mismo paso (`0` y `0.001`): se guardan los dos archivos, cada uno con su nombre, y no se pierde ninguno. → Tarea 3, test `test_captura_dos_tiempos_en_el_mismo_paso`.
4. `.capturas/` no existe: se crea. → Tarea 3, lo cubre el test de punta a punta, que corre en una carpeta vacía.
5. El modo captura deja pygame inicializado y contamina otros tests: `main` siempre llama a `pygame.quit()`. → Tarea 3, `test_captura_deja_pygame_cerrado`.

---

### Tarea 1: Reloj de pasos fijos y pasos de captura

**Archivos:**
- Crear: `src/circlebh/world/clock.py`
- Test: `tests/test_clock.py`

**Interfaces:**
- Produce:
  - `STEP: float = 1 / 60` y `MAX_FRAME: float = 0.25`.
  - `class FixedStepClock` con `advance(self, real_dt: float) -> int`.
  - `capture_steps(times: Iterable[float]) -> list[int]`.

- [ ] **Paso 1: tests de `capture_steps`**
  - `test_capture_steps_segundos_enteros`: `capture_steps([0, 1, 2]) == [0, 60, 120]`.
  - `test_capture_steps_medio_segundo`: `capture_steps([0.5]) == [30]`.
  - `test_capture_steps_redondea_al_paso_mas_cercano`: `capture_steps([0.1]) == [6]`, porque `0.1 * 60` en flotante es `6.000000000000001`; y `capture_steps([1 / 60 * 0.4]) == [0]`.
  - `test_capture_steps_vacio`: `capture_steps([]) == []`.
- [ ] **Paso 2:** correr `uv run pytest tests/test_clock.py -q`. Se espera que falle con `ModuleNotFoundError: circlebh.world.clock`.
- [ ] **Paso 3:** implementar `capture_steps` con `round(t / STEP)` para cada tiempo, en el mismo orden.
- [ ] **Paso 4: tests del ejercicio `advance`**, cada uno con `@pytest.mark.xfail(strict=True, reason="ejercicio pendiente: FixedStepClock.advance")`:
  - `test_advance_un_paso`: un reloj nuevo, `advance(1 / 60) == 1`.
  - `test_advance_acumula_el_resto`: `advance(1 / 120) == 0`, y después `advance(1 / 120) == 1`.
  - `test_advance_un_cuarto_de_segundo`: `advance(0.25) == 15`.
  - `test_advance_topa_una_pausa_larga`: `advance(10) == 15`, no 600.
- [ ] **Paso 5:** crear `FixedStepClock` con `__init__` (acumulador en `0.0`) y `advance` que lanza `NotImplementedError`, con un docstring que explique el contrato y los tres caminos posibles. Correr `uv run pytest tests/test_clock.py -q`. Se espera `4 passed, 4 xfailed`.
- [ ] **Paso 6: mostrar los tests del ejercicio fallando por la razón correcta**: `uv run pytest tests/test_clock.py -q --runxfail -k advance`. Se espera `4 failed` con `NotImplementedError`.
- [ ] **Paso 7:** commit `feat: agregar el reloj de pasos fijos y los pasos de captura`.
- [ ] **Paso 8: el usuario implementa `advance` y quita las cuatro marcas `xfail`.** Se espera `8 passed` en `tests/test_clock.py`. Las tareas 2 y 3 no dependen de `advance`, pero el modo con ventana de la tarea 3 sí. La tarea 3 no se cierra sin esto.

### Tarea 2: Línea de comandos y escenarios

**Archivos:**
- Crear: `src/circlebh/cli.py`, `src/circlebh/scenes/scenarios.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produce:
  - `scenes/scenarios.py`: `@dataclass(frozen=True) class Scenario: name: str; description: str`, y `SCENARIOS: dict[str, Scenario]` con la clave `"plano-vacio"`.
  - `cli.py`: `@dataclass(frozen=True) class RunOptions: demo: bool; scenario: str; seed: int; speed: float; capture: tuple[float, ...]`, y `parse_args(argv: Sequence[str] | None = None) -> RunOptions`.

- [ ] **Paso 1: tests**. Los negativos usan `pytest.raises(SystemExit)` y comprueban que el código sea `2`.
  - `test_opciones_completas`: `--demo --scenario plano-vacio --seed 7 --speed 2 --capture 0,1,2` da `RunOptions(True, "plano-vacio", 7, 2.0, (0.0, 1.0, 2.0))`.
  - `test_valores_por_defecto`: `[]` da `demo=False`, `scenario="plano-vacio"`, `speed=1.0` y `capture=()`, con un `seed` entero ≥ 0.
  - `test_capture_ordena_y_quita_repetidos`: `--demo --capture 2,0,2` da `(0.0, 2.0)`.
  - `test_capture_acepta_espacios`: `--demo --capture "0, 1"` da `(0.0, 1.0)`.
  - `test_capture_exige_demo`: `--capture 0` termina con código 2.
  - `test_escenario_desconocido`: `--scenario nada` termina con código 2.
  - `test_speed_debe_ser_positiva`: `--speed 0` y `--speed -1` terminan con código 2.
  - `test_capture_rechaza_negativos`: `--demo --capture -1` termina con código 2.
  - `test_capture_rechaza_texto`: `--demo --capture a,b` termina con código 2.
  - `test_capture_rechaza_tiempos_no_finitos`: `--demo --capture inf` y `--demo --capture nan` terminan con código 2.
  - `test_seed_negativa`: `--seed -1` termina con código 2.
- [ ] **Paso 2:** correr `uv run pytest tests/test_cli.py -q`. Se espera que falle con `ModuleNotFoundError: circlebh.cli`.
- [ ] **Paso 3:** implementar `scenarios.py` y `cli.py`.
  - `--scenario` usa `choices=sorted(SCENARIOS)`.
  - `--capture`, `--speed` y `--seed` usan funciones `type=` propias que lanzan `argparse.ArgumentTypeError`. Los tiempos usan `math.isfinite`.
  - "`--capture` exige `--demo`" se valida con `parser.error(...)`.
  - La semilla por defecto sale de `secrets.randbelow(2**32)`, no del módulo `random` (ADR 0005).
- [ ] **Paso 4:** correr `uv run pytest tests/test_cli.py -q`. Se espera `11 passed`. Después, `uv run poe fast`.
- [ ] **Paso 5:** commit `feat: agregar las opciones de línea de comandos y los escenarios`.

### Tarea 3: Modo captura y `poe capturas`

**Archivos:**
- Crear: `src/circlebh/render/plane.py`
- Modificar: `src/circlebh/__main__.py` (entero), `pyproject.toml` (tarea `capturas`)
- Test: `tests/test_captura.py`

**Interfaces:**
- Consume: `parse_args` y `RunOptions` (tarea 2); `FixedStepClock`, `capture_steps` y `STEP` (tarea 1); `SCENARIOS` (tarea 2).
- Produce:
  - `render/plane.py`: `draw_empty_plane(screen: pygame.Surface) -> None`, que se mueve sin cambios desde `__main__.py`.
  - `__main__.py`: `main(argv: Sequence[str] | None = None) -> None` y `capture_path(scenario: str, seed: int, t: float) -> Path`.

- [ ] **Paso 1: tests**. Todos usan `monkeypatch.chdir(tmp_path)`.
  - `test_capture_path`: `capture_path("plano-vacio", 1, 1.0) == Path(".capturas/plano-vacio-seed1-t1.00.png")`.
  - `test_captura_de_punta_a_punta`: `main(["--demo", "--seed", "1", "--capture", "0,1"])` crea exactamente `plano-vacio-seed1-t0.00.png` y `plano-vacio-seed1-t1.00.png` en `.capturas/`. Cada uno, cargado con `pygame.image.load`, mide `(1280, 720)`.
  - `test_captura_dos_tiempos_en_el_mismo_paso`: `--capture 0,0.001` crea `t0.00` y otra vez `t0.00`. Como los dos nombres coinciden, se espera **un** archivo, y el comando no falla.
  - `test_captura_deja_pygame_cerrado`: después de `main([... "--capture", "0"])`, `pygame.get_init()` es `False`.
- [ ] **Paso 2:** correr `uv run pytest tests/test_captura.py -q`. Se espera que falle por `ImportError` de `capture_path`.
- [ ] **Paso 3:** crear `render/plane.py` moviendo `draw_empty_plane`, `BACKGROUND` y `AXIS_COLOR` desde `__main__.py`.
- [ ] **Paso 4:** reescribir `__main__.py`.
  - `main(argv)` llama a `parse_args`, imprime `semilla: N` y elige el modo. Usa `try/finally` con `pygame.quit()`.
  - **Modo captura:** fija `os.environ["SDL_VIDEODRIVER"] = "dummy"` antes de `pygame.init()` y crea `.capturas/` con `mkdir(parents=True, exist_ok=True)`. Recorre los pasos desde 0 hasta el último de `capture_steps`. En cada paso con capturas, dibuja y guarda un PNG por cada tiempo que cae ahí, e imprime la ruta.
  - **Modo con ventana:** el bucle de hoy, pero el tiempo real de cada frame (`clock.tick(60) / 1000 * speed`) pasa por `FixedStepClock.advance`. Como todavía no hay `world` que actualizar, los pasos devueltos se descartan, y se deja un comentario que lo explica.
- [ ] **Paso 5:** correr `uv run pytest -q`. Se espera que todo pase, incluidos `test_humo.py` y los 4 tests nuevos.
- [ ] **Paso 6:** en `pyproject.toml`, `[tool.poe.tasks.capturas]` pasa a `cmd = "circlebh --demo --scenario plano-vacio --seed 1 --capture 0,1,2"`, con su `help`. Correr `uv run poe capturas`. Se espera que imprima 3 rutas y que existan los 3 PNG.
- [ ] **Paso 7:** mostrar los 3 PNG en la sesión (leyéndolos con Read). Confirmar el nombre del driver en https://wiki.libsdl.org/SDL2/SDL_HINT_VIDEODRIVER y anotar la fecha.
- [ ] **Paso 8:** `uv run circlebh`. La ventana sigue funcionando, ahora con el reloj del usuario. `uv run poe check` en verde.
- [ ] **Paso 9:** commit `feat: sacar capturas sin ventana con poe capturas`.
