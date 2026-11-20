# Plan: los enemigos se mueven por patrones (issue #27)

> **Para quien ejecuta:** usa superpowers:executing-plans, tarea por tarea, en esta sesión (CLAUDE.md descarta el desarrollo con subagentes). Los pasos usan casillas (`- [ ]`).

**Meta:** el hexágono se mueve como un imán. Lo traen `seek` y la carga del jugador, se repele de los otros con Coulomb y un núcleo duro, tiene inercia y roce, y todo eso se declara como patrones en `balance.json`.

**Arquitectura:** las leyes de fuerza son funciones puras en `world/charges.py`. Los patrones, en `world/patterns.py`, suman aceleraciones. `world/swarm.py` arma el paso simultáneo del enjambre con la grilla de `world/grid.py`, y aplica la red de seguridad. `Enemy` integra con Euler semi-implícito, y `World` orquesta.

**Stack:** Python 3.14.10, pygame-ce 2.5.8 (solo `Vector2` en `world/`), pytest + Hypothesis, poe.

**Spec:** `docs/specs/2026-11-19-patrones-de-enemigos.md`. Lee también el ADR 0006, el ADR 0020 y AGENTS.md.

**Rama:** `feat/separacion`. Un solo PR, con un commit por tarea.

## Restricciones globales

- `world/` es lógica pura: de Pygame solo usa `Vector2`, sin `draw` ni `display` (ADR 0003, 0016).
- Pasos fijos `STEP = 1/60` (ADR 0005). No se agrega azar.
- `balance.py` y `balance.json` calzan siempre. Cada cambio de datos: `poe balance-exportar`, y verificar con `poe balance-chequear` (ADR 0004).
- Los identificadores van en inglés. Los docstrings, comentarios y commits, en español de Chile, sin voseo.
- No se instalan paquetes.
- **`pyproject.toml` se toca solo con aprobación explícita del cambio** (CLAUDE.md). Aplica a la tarea `poe benchmark` (Tarea 8).
- TDD: el test primero, y se muestra fallando por la razón correcta. Después de `fast` en verde, **modo explicación** (ADR 0017) en las tareas 3, 4, 5 y 6: un fragmento de 5 a 10 líneas, qué hace, qué caminos se consideraron y qué lo haría fallar.
- `uv run poe fast` después de cada cambio. `uv run poe check` antes del push.
- Commits Conventional, con la descripción en español y el trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Una tarea a la vez: se muestra el resultado y se espera la aprobación antes de la siguiente (AGENTS.md).

**Números iniciales** (del spec y de la simulación de la sesión; se ajustan jugando):

| Campo | Valor |
|---|---|
| `player.charge` | −14.0 |
| `charges.k` | 171000.0 |
| `charges.cutoff` | 150.0 |
| `charges.softening` | 1.0 |
| `charges.player_softening` | 24.0 |
| `charges.core_strength` | 20000.0 |
| `charges.core_reach` | 1.2 (× la suma de los radios envolventes) |
| `charges.core_exponent` | 8.0 |
| `hexagon.friction` | 2.0 |
| `hexagon.charge_per_line` | 1.0 |
| `seek.strength` | 240.0 |

## Foco de revisión

Lo que el spec implica y ningún escenario del spec ejercita, en orden de probabilidad:

1. **Un enemigo que muere a mitad del paso** (pierde su última línea por una bala) no puede entrar al cálculo siguiente con masa 0. → Tarea 6, `test_enemigo_muerto_no_divide_por_cero`.
2. **Un hexágono centrado sobre el jugador quieto durante muchos pasos** no debe dar `nan` ni pasar `speed`. → Tarea 5, `test_hexagono_sobre_el_jugador_quieto_se_mantiene_finito`.
3. **Una posición no finita llega a la grilla:** `math.floor(nan)` lanza `ValueError`, y la partida se cae. → Tarea 4, `test_posicion_no_finita_da_error_claro`.
4. **Un hexágono que aparece encima de otro** (dos apariciones en el mismo lugar del círculo de 800). → Tarea 6, `test_aparecer_encima_de_otro_los_separa`.
5. **El piloto en movimiento con enemigos llegando:** la red de seguridad no debería actuar en una partida normal. → Tarea 7, se agrega `world.separations == 0` a la simulación de 60 s.

---

### Tarea 1: El ADR 0021 y el texto del issue

**Archivos:**
- Crear: `docs/decisiones/0021-enemigos-por-patrones.md`

- [ ] Escribir el ADR en MADR 4, en español y en estado **propuesto**. Contexto: decisiones 22 a 30 del spec de la 0.1.0. Opciones: patrones que se suman / comportamiento con nombre / números fijos; núcleo duro / choque inelástico. Resultado: patrones en el balance, ley de a pares simétrica, el jugador como carga fija, inercia con roce y red de seguridad. **Confirmación:** los tests de conservación (Hypothesis), de grilla contra fuerza bruta, de orden de la lista y la simulación "nunca se tocan". Reemplaza en parte la decisión 12 del spec de la 0.1.0 y complementa el ADR 0006.
- [ ] Redactar el nuevo cuerpo del issue #27 (Qué, Por qué, Terminado cuando) desde el spec.
- [ ] **Mostrar los dos textos al usuario.** Con su aprobación: `gh issue edit 27 --body-file <archivo>` y commit `docs: ADR 0021, los enemigos se mueven por patrones`.

### Tarea 2: `datafile` entiende listas y patrones con `kind`

**Archivos:**
- Modificar: `src/circlebh/datafile.py`
- Test: `tests/test_datafile.py`

**Interfaces:**
- Produce: `load` y `dump` aceptan además:
  - `tuple[X, ...]` de largo variable (en JSON, una lista);
  - `typing.Literal["a"]` (el valor tiene que ser igual);
  - una unión de dataclasses (`A | B`), elegida por el campo `kind`, que cada miembro declara como `kind: Literal["..."]`;
  - un alias `type X = ...` (`typing.TypeAliasType`), que se desenvuelve con `__value__`.

  `dump` no cambia: `kind` es un campo normal.

Las dataclasses de los tests usan `@dataclass(frozen=True, kw_only=True)` con `kind: Literal["seek"] = "seek"` como primer campo, igual que las reales de la Tarea 3.

- [ ] **Tests** (en `test_datafile.py`, con dataclasses de prueba `_Seek(kind="seek", strength)`, `_Coulomb(kind="coulomb")` y `_Holder(patterns: tuple[_Pattern, ...])`, donde `type _Pattern = _Seek | _Coulomb`):
  - `test_lista_de_patrones_ida_y_vuelta`: `load(_Holder, {"patterns": [{"kind": "seek", "strength": 2}, {"kind": "coulomb"}]})` da `_Holder((_Seek(strength=2.0), _Coulomb()))`, y `dump` de eso vuelve al mismo dict (con `2.0`).
  - `test_lista_vacia_es_valida`: `{"patterns": []}` da `patterns == ()`.
  - `test_kind_desconocido_nombra_la_ruta`: `{"patterns": [{"kind": "seek", "strength": 1}, {"kind": "dash"}]}` da `DataFileError` con `.field == "patterns[1].kind"`.
  - `test_patron_sin_kind_nombra_la_ruta`: `[{"strength": 1}]` da `.field == "patterns[0].kind"`, con la razón "falta el campo".
  - `test_campo_que_sobra_en_un_patron`: `[{"kind": "coulomb", "k": 1}]` da `.field == "patterns[0].k"`.
  - `test_lista_donde_va_objeto`: `{"patterns": {"kind": "seek"}}` da `.field == "patterns"`.
- [ ] Correr `uv run pytest tests/test_datafile.py -q`: fallan con `TypeError: tipo de campo no soportado`.
- [ ] Implementar en `_load_value`: desenvolver `TypeAliasType`; `tuple` con `Ellipsis` → lista de cualquier largo; `Literal` → el valor está en `get_args`; `UnionType` → leer `kind` del objeto (si falta: "falta el campo" en `campo.kind`), buscar el miembro cuyo `kind` lo admite (si ninguno: `campo.kind` "se esperaba uno de: seek, coulomb") y cargar ese miembro.
- [ ] `uv run poe fast` en verde, y `uv run mypy` sin errores.
- [ ] Commit: `feat: datafile carga listas de patrones elegidos por kind`.

### Tarea 3: El balance declara cargas y patrones

**Archivos:**
- Modificar: `src/circlebh/balance.py`, `src/circlebh/balance.json`
- Modificar (tests que construyen specs): `tests/test_enemy.py`, `tests/test_weapons.py`, `tests/test_damage.py`, `tests/test_player.py`, `tests/test_balance.py`
- Test: `tests/test_balance.py`

**Interfaces:**
- Produce, en `balance.py` (con un docstring por campo, con unidades):
  - `PlayerSpec`: se agrega `charge: float`.
  - `ChargesSpec`: `k`, `cutoff`, `softening`, `player_softening`, `core_strength`, `core_reach`, `core_exponent`, todos `float`.
  - `SeekSpec`: `kind: Literal["seek"] = "seek"` y `strength: float`. `CoulombSpec`: `kind: Literal["coulomb"] = "coulomb"`. Ambas con `frozen=True, kw_only=True`.
  - `type PatternSpec = SeekSpec | CoulombSpec`.
  - `EnemySpec`: se agregan `friction: float`, `charge_per_line: float` y `patterns: tuple[PatternSpec, ...]`. `speed` pasa a ser la velocidad máxima (corregir el docstring).
  - `Balance`: se agrega `charges: ChargesSpec`.
  - Los valores salen de la tabla de "Números iniciales".

- [ ] **Tests:**
  - `test_balance_real_calza` ya existe; tiene que seguir pasando.
  - `test_exportar_e_importar_ida_y_vuelta` ya existe; ahora cubre los patrones (el `repr` de `SeekSpec` es Python válido).
  - Nuevo: `test_hexagono_declara_seek_y_coulomb`: `[type(p) for p in BALANCE.enemies["hexagon"].patterns] == [SeekSpec, CoulombSpec]`.
  - Nuevo: `test_rapidez_terminal_de_seek_no_pasa_speed`: para cada enemigo con `SeekSpec`, `strength / friction <= speed`. Es coherencia del balance: el tope no debería ser lo único que lo frena.
  - Nuevo: `test_el_nucleo_alcanza_antes_del_corte`: `core_reach * 2 * radius < cutoff` para cada enemigo. Si no, la grilla no ve el núcleo.
- [ ] Mostrarlos fallando: `AttributeError` o `ImportError` de `SeekSpec`.
- [ ] Escribir las clases y el bloque de datos, y después `uv run poe balance-exportar` y `uv run poe balance-chequear`, sin diferencias.
- [ ] Actualizar las constantes de los tests que construyen `EnemySpec`/`PlayerSpec` con los campos nuevos. Los que no prueban movimiento usan `patterns=()`, `friction=0.0` y `charge_per_line=0.0`.
- [ ] `uv run poe fast` en verde. **Los tests de movimiento de `test_enemy.py` y de `test_damage.py` todavía usan `step(target)`, que cambia en la Tarea 5. Si fallan aquí, es por los specs, no por eso.**
- [ ] Commit: `feat: el balance declara cargas y patrones de movimiento`.

### Tarea 4: La grilla espacial

**Archivos:**
- Crear: `src/circlebh/world/grid.py`
- Test: `tests/test_grid.py`

**Interfaces:**
- Produce: `class SpatialGrid` con `__init__(self, cell_size: float)` y `pairs(self, positions: Sequence[Vector2], radii: Sequence[float]) -> set[tuple[int, int]]`. Da los pares `(i, j)` con `i < j` y `distance(pᵢ, pⱼ) <= rᵢ + rⱼ`, el mismo criterio que `circles_touch`. Revisa la celda propia y las 8 vecinas, con la celda `(floor(x / cell), floor(y / cell))`.
  - `ValueError` si `2 · max(radii) > cell_size`: con eso, un par que se toca puede quedar a dos celdas.
  - `ValueError` con el índice si una posición no es finita.

- [ ] **Tests:**
  - `test_grilla_igual_a_todos_contra_todos` (Hypothesis): de 0 a 60 posiciones con coordenadas en `[-500, 500]` y radios en `[0, 30]`, `cell_size = 60`. El resultado es igual a la fuerza bruta con `circles_touch`. Incluye una estrategia que pone puntos justo en múltiplos de 60 (bordes de celda) y en coordenadas negativas.
  - `test_tangentes_cuentan_como_par`: `(0,0)` y `(20,0)` con radios 10 dan `{(0, 1)}`.
  - `test_lejanos_no_son_par`: `(0,0)` y `(500,0)` dan `set()`.
  - `test_celda_chica_da_error`: radios de 40 con `cell_size = 60` → `ValueError`.
  - `test_posicion_no_finita_da_error_claro`: `Vector2(nan, 0)` → `ValueError` que menciona el índice (Foco 3).
- [ ] Mostrarlos fallando (`ModuleNotFoundError`), implementar y `uv run poe fast`.
- [ ] Modo explicación: el recorrido de 3×3 celdas y por qué el test la compara con la fuerza bruta.
- [ ] Commit: `feat: grilla espacial para encontrar pares cercanos`.

### Tarea 5: La ley de cargas, los patrones y la inercia

**Archivos:**
- Crear: `src/circlebh/world/charges.py`, `src/circlebh/world/patterns.py`
- Modificar: `src/circlebh/world/enemy.py`
- Tests: `tests/test_charges.py`, `tests/test_patterns.py`, `tests/test_enemy.py`, `tests/test_damage.py`

**Interfaces:**
- Produce, en `charges.py` (cada fórmula escrita en su docstring):
  - `pair_force(offset: Vector2, qi: float, qj: float, contact: float, spec: ChargesSpec) -> Vector2`: la fuerza sobre `i` desde `j`, con `offset = pᵢ − pⱼ`, `r = |offset|` y `contact = rᵢ + rⱼ`. Si `r == 0`, da `Vector2()`. Si no, da `(f(r) + g(r)) · offset / r`, donde:
    - `f(r) = k·qᵢ·qⱼ·[r / (r² + ε²)^{3/2} − rc / (rc² + ε²)^{3/2}]` si `r < rc = cutoff`, y 0 si no;
    - `g(r) = K·((d₀ / r)ⁿ − 1)` si `r < d₀ = core_reach · contact`, y 0 si no. No depende de las cargas.
  - `player_force(offset: Vector2, q: float, player_charge: float, spec: ChargesSpec) -> Vector2`: la fuerza sobre el enemigo desde el jugador, `k·q·q_p·offset / (r² + ε_p²)^{3/2}`, con `offset = p − jugador`, sin corte y sin núcleo.
- Produce, en `patterns.py`:
  - `@dataclass(frozen=True) class Context`: `player_position: Vector2`, `player_charge: float`, `charges: ChargesSpec` y `neighbors: Sequence[Enemy]` (los vecinos a menos de `cutoff`, sin el propio).
  - `class Pattern(ABC)` con `acceleration(self, enemy: Enemy, context: Context) -> Vector2`.
  - `class Seek(Pattern)`, a partir de un `SeekSpec`: `strength` hacia el jugador, y `Vector2()` si está encima.
  - `class Coulomb(Pattern)`: `(Σ pair_force(pᵢ − pⱼ, qᵢ, qⱼ, rᵢ + rⱼ) + player_force(pᵢ − P, qᵢ, q_p)) / mᵢ`.
  - `make_pattern(spec: PatternSpec) -> Pattern`, con `match` sobre el tipo de spec.
  - `Enemy` se importa solo bajo `TYPE_CHECKING`, para no crear un ciclo.
- Produce, en `Enemy`:
  - `velocity: Vector2`, en cero al aparecer;
  - `patterns: list[Pattern]`: instancias propias, creadas en `__init__`;
  - la propiedad `mass` = `len(edges)`;
  - la propiedad `charge` = `spec.charge_per_line · len(edges)`;
  - `acceleration(self, context: Context) -> Vector2` = `Σ patrón − spec.friction · velocity`;
  - `step(self, acceleration: Vector2) -> None` reemplaza a `step(target)`: guarda `previous`, hace `v += a·STEP`, acota con `clamp_magnitude(speed)` y hace `p += v·STEP`.

- [ ] **Tests de `charges`:**
  - `test_tercera_ley` (Hypothesis): para `offset` no nulo, cargas en `[-12, 12]` y `contact` en `[1, 60]`, se cumple `pair_force(o, qi, qj, c) == approx(−pair_force(−o, qj, qi, c))`. Con masas `mᵢ, mⱼ`, eso deja `Σ m·a = 0`.
  - `test_cargas_iguales_se_repelen`: `pair_force(Vector2(80, 0), 6, 6, 48, spec).x > 0`.
  - `test_cargas_contrarias_se_atraen_de_lejos`: con `r = 100`, `.x < 0`.
  - `test_nucleo_repele_aunque_se_atraigan`: con cargas `6` y `−6` y `r = 50` (dentro de `d₀ = 57,6`), `.x > 0`.
  - `test_cero_en_el_corte_y_mas_alla`: con `r = 150` y `r = 151` da `Vector2()`.
  - `test_mismo_punto_no_divide_por_cero`: `offset = Vector2()` da `Vector2()`.
  - `test_el_jugador_atrae`: `player_force(Vector2(100, 0), 6, -14, spec).x < 0`.
  - `test_el_jugador_atrae_sin_corte`: con `offset = (800, 0)`, `.x < 0`.
  - `test_jugador_encima_es_finito`: `player_force(Vector2(), 6, -14, spec) == Vector2()`, y con `offset = (1e-9, 0)` el resultado es finito.
- [ ] **Tests de `patterns` y `Enemy`:**
  - `test_seek_apunta_al_jugador_con_strength`: un enemigo en `(300, 0)` y el jugador en el origen dan `(−240, 0)`.
  - `test_seek_encima_del_jugador_es_cero`.
  - `test_seek_no_depende_de_la_velocidad`.
  - `test_herido_empuja_menos`: la aceleración de `Coulomb` sobre A, con un vecino B de 6 líneas, es mayor que con B de 3 líneas.
  - `test_lo_que_recibe_no_depende_de_sus_lineas`: la aceleración de Coulomb sobre A, con el núcleo fuera de alcance y la carga del jugador en 0, es igual con A de 6 líneas que con A de 3.
  - `test_no_se_repele_a_si_mismo`: con `neighbors = [enemy]`, `Coulomb` da `Vector2()`.
  - `test_sin_fuerzas_el_roce_frena`: con `velocity = (100, 0)` y sin patrones, cada `step(enemy.acceleration(ctx))` baja la rapidez.
  - `test_nunca_pasa_speed` (Hypothesis): con cualquier aceleración, `velocity.length() <= speed + 1e-9`.
  - `test_en_reposo_sin_fuerzas_no_se_mueve`.
  - `test_carga_y_masa_bajan_al_perder_lineas`: después de `remove_edge(0)`, `mass == 5` y `charge == 5 · charge_per_line`.
  - `test_hexagono_sobre_el_jugador_quieto_se_mantiene_finito` (Foco 2): el hexágono real parte en el origen con el jugador ahí, y pasan 600 pasos con `Context` sin vecinos. Todas las posiciones son finitas, y `|v| <= speed`.
- [ ] Reescribir los tests de `test_enemy.py` que usaban `step(target)`, para que prueben lo mismo con `step(acceleration)`. En concreto: `previous` es la posición antes del paso, y llegar justo sin oscilar ya no aplica, así que se borra y se cuenta en el PR. En `test_damage.py`, el enemigo rápido que avanza hacia la bala usa `velocity` fija, `friction = 0` y `step(Vector2())`.
- [ ] Mostrarlos fallando, implementar y `uv run poe fast`.
- [ ] Modo explicación: `pair_force`, con el corte restado y el núcleo, y por qué la masa es igual a la carga.
- [ ] Commit: `feat: el hexágono se mueve con cargas, seek e inercia`.

### Tarea 6: El enjambre en el mundo, con la red de seguridad

**Archivos:**
- Crear: `src/circlebh/world/swarm.py`
- Modificar: `src/circlebh/world/game.py`
- Tests: `tests/test_swarm.py`, `tests/test_game.py`

**Interfaces:**
- Consume: `SpatialGrid` (Tarea 4), y `Context` y `Enemy.acceleration`/`step` (Tarea 5).
- Produce, en `swarm.py`:
  - `step_swarm(enemies: Sequence[Enemy], player_position: Vector2, player_charge: float, charges: ChargesSpec) -> int`. Calcula todas las aceleraciones con las posiciones del inicio, después mueve a todos y al final llama a `separate`. Devuelve cuántos pares corrigió la red de seguridad.
    - Para los vecinos, usa `SpatialGrid(charges.cutoff).pairs(positions, [cutoff / 2] * n)`. Ese `cell_size` es válido porque `2 · cutoff/2 = cutoff`.
    - Solo entran los enemigos vivos.
  - `separate(enemies: Sequence[Enemy]) -> int`: los pares con las envolventes superpuestas, encontrados con una grilla de `cell_size = 2 · max(radius)`. Suma las correcciones y las aplica juntas. A cada uno le corresponde la mitad de la superposición, en la dirección que los une, o `(1, 0)` si están en el mismo punto. Además quita la mitad de la velocidad relativa de acercamiento a cada uno.
  - `lattice(center: Vector2, count: int, spacing: float) -> list[Vector2]`: los `count` puntos de una red triangular de lado `spacing`, sin el centro, ordenados por distancia y después por ángulo. Lo usan la simulación, el benchmark y el escenario `panal`.
- Produce, en `World`:
  - `__init__(self, balance, rng, *, lethal: bool = True, armed: bool = True)`. Con `lethal=False`, el contacto no termina la partida. Con `armed=False`, no hay armas.
  - `separations: int`, cuántos pares corrigió la red de seguridad en toda la partida.
  - `update` sigue el orden del spec: el jugador; `step_swarm`; las armas; los muertos; la aparición; el contacto.

- [ ] **Tests de `swarm`:**
  - `test_dos_sueltos_se_alejan`: dos hexágonos sin `seek` (spec con `patterns=(CoulombSpec(),)`), a 80 unidades, con la carga del jugador en 0. Después de 30 pasos, la distancia es mayor.
  - `test_orden_de_la_lista_no_importa` (Hypothesis): de 2 a 12 hexágonos en posiciones distintas, separadas al menos 1e-3. Un `step_swarm` con la lista y otro con la lista permutada dan las mismas posiciones por enemigo (`approx`, con `abs=1e-9`).
  - `test_superpuestos_quedan_tangentes_y_sin_acercarse`: dos a 30 unidades, que se acercan a 10 u/s cada uno. Después de `separate`, quedan a 48 y la velocidad relativa en esa dirección es ≥ 0. Devuelve 1.
  - `test_misma_posicion_no_divide_por_cero`: dos en `(5, 5)`. Después de `separate`, quedan a 48 y todo es finito.
  - `test_separados_no_se_tocan`: dos a 100 unidades no cambian, y devuelve 0.
  - `test_lattice_sin_superponerse`: `lattice(Vector2(), 300, 60)` da 300 puntos distintos, todos a ≥ 60 entre sí y ninguno en el centro.
- [ ] **Tests de `World`:**
  - `test_el_jugador_se_mueve_igual_con_enemigos_cerca`: la misma intención por 60 pasos con y sin hexágonos alrededor da la misma `player.position`, exacta.
  - `test_enemigo_muerto_no_divide_por_cero` (Foco 1): se le quitan todas las líneas menos una a un hexágono, una bala lo mata en el paso y `update` sigue sin error.
  - `test_aparecer_encima_de_otro_los_separa` (Foco 4): un enemigo puesto justo donde aparecerá el siguiente. Después del paso de aparición y uno más, las envolventes no se superponen.
  - `test_la_bala_golpea_al_que_movio_el_empujon`: un hexágono que la red de seguridad acaba de mover recibe igual el golpe de una bala que cruza su línea (el tramo de `previous` a `position` incluye el empujón).
  - `test_sin_letalidad_no_termina` y `test_desarmado_no_dispara`.
- [ ] Revisar los tests de `test_game.py` y `test_pilot.py` que dependían de la línea recta, y adaptarlos. Para el PR, anotar qué cambió, por ejemplo la nueva duración de la partida de la semilla 1.
- [ ] Mostrarlos fallando, implementar y `uv run poe fast`.
- [ ] Modo explicación: el paso simultáneo de `step_swarm` y la suma de correcciones de `separate`.
- [ ] Commit: `feat: los hexágonos se repelen como imanes y no se superponen`.

### Tarea 7: Nunca se tocan, medido

**Archivos:**
- Test: `tests/test_simulacion.py`

- [ ] **Tests:**
  - `test_300_hexagonos_nunca_se_tocan` (`@pytest.mark.simulacion`): `World(BALANCE, Random(1), lethal=False, armed=False)`, y se reemplazan los enemigos por 300 hexágonos en `lattice(Vector2(), 300, 60)`. Pasan 600 pasos con el jugador quieto. Se exige `world.separations == 0` y que ningún par de envolventes se superponga al final, revisado por fuerza bruta.
  - En `test_simulacion_de_60_s_sin_errores`, agregar que la red de seguridad no actuó en ninguna partida (Foco 5). `simulate` devuelve hoy duraciones: se agrega `simulate_worlds` o se cuenta aparte, lo que pida menos cambio. Se decide al implementar y se cuenta.
- [ ] Correr `uv run pytest -m simulacion -q`. Si el de 300 falla, se ajustan `core_strength`, `core_reach` o `core_exponent` en el balance (con exportar y chequear). Se respeta `ω·dt < 1` en la distancia de equilibrio, y se cuenta el cambio.
- [ ] Commit: `test: 300 hexágonos no se superponen nunca`.

### Tarea 8: El benchmark

**Archivos:**
- Crear: `tools/benchmark.py`
- Modificar: `pyproject.toml` (la tarea `[tool.poe.tasks.benchmark]`), **con aprobación explícita antes**

- [ ] **Mostrar al usuario el bloque de `pyproject.toml` y esperar su aprobación:**
  ```toml
  [tool.poe.tasks.benchmark]
  help = "Milisegundos por paso con 300 hexágonos y un enemigo de 100 líneas (ADR 0006). A mano, no en la CI."
  cmd = "python tools/benchmark.py"
  ```
- [ ] `tools/benchmark.py`: `World(BALANCE, Random(1), lethal=False)`, con 300 hexágonos en `lattice(Vector2(), 300, 60)` más un enemigo de `replace(hexagon, sides=100, radius=200, charge_per_line=0.0, patterns=())` a 400 unidades. El arma sigue disparando. Hace 60 pasos de calentamiento y después mide 600 con `time.perf_counter`. Imprime el promedio y el percentil 95 en ms, y sale con código 1 si el promedio pasa 16,6.
- [ ] Correr `uv run poe benchmark` y mostrar la salida. Si pasa la meta, hay que perfilar (`python -m cProfile`) antes de cambiar nada, y mostrar el resultado al usuario.
- [ ] Commit: `chore: poe benchmark mide el paso con 300 enemigos`.

### Tarea 9: El escenario `panal` y la evidencia

**Archivos:**
- Modificar: `src/circlebh/scenes/scenarios.py`, `src/circlebh/scenes/game.py`

- [ ] `Scenario` agrega `crowd: int = 0`, `lethal: bool = True` y `armed: bool = True`. El escenario `panal` tiene `pilot=False`, `crowd=40`, `lethal=False` y `armed=False`, con la descripción "40 hexágonos alrededor del jugador quieto, sin contacto ni arma: se ordenan como imanes".
- [ ] `GameScene.start` pasa `lethal` y `armed` a `World` y, si hay `crowd`, agrega esos hexágonos en `lattice(Vector2(), crowd, 90)`, más abiertos que el equilibrio, para que se vea cómo se acercan y se ordenan.
- [ ] `uv run poe capturas --escenario panal --tiempos 0,3,8` y `uv run poe capturas --escenario oleadas`. Mostrar las imágenes en la sesión.
- [ ] Commit: `feat: escenario panal para ver el orden del enjambre`.

### Tarea 10: Cierre

- [ ] `uv run poe check` en verde, con la salida en la sesión.
- [ ] El ADR 0021 queda en **propuesto** hasta que el usuario lo confirme. Con su confirmación, pasa a aceptado en un commit `docs:`.
- [ ] AGENTS.md: la sección "Arquitectura" dice que los enemigos se mueven por patrones del balance (ADR 0021). Va en un commit `docs:`, mostrando antes el cambio.
- [ ] La prueba manual (memoria del proyecto): pasos en el chat para el usuario, por ejemplo jugar 2 minutos, dejar que te rodeen, entrar en un hexágono abierto, ver el panal y revisar que el control no cambia. Esperar su resultado.
- [ ] Estado al día en el issue #27.
- [ ] PR con la plantilla, `Closes #27` y los tests que cambiaron (Tarea 6). Mostrar el título y el cuerpo antes de crearlo. El push va con `poe check` en verde.
