# Los enemigos se mueven por patrones: el hexágono, como un imán

Issue #27, rama `feat/separacion`. Lo decidió el usuario en la sesión del 2026-11-19. Reemplaza la sección "Enemigos" del spec de la 0.1.0 en lo que dice del movimiento y de la separación (decisiones 22 a 30 de ese spec).

Lo que no viene de "Decisiones del usuario" es propuesta de Claude y está marcado.

## Intención

Sin separación, los hexágonos que te persiguen terminan en una sola mancha. El issue pedía corregir la superposición: cada uno se corre la mitad. El usuario quiere algo más interesante y más matemático: **que los hexágonos se comporten como imanes del mismo polo**. Se rechazan más fuerte mientras más se acercan, nunca llegan a tocarse, y el movimiento tiene una física que da gusto mirar.

Además, **el movimiento es el comportamiento de cada tipo de enemigo, no una ley del mundo**. El balance dice con qué patrones se mueve cada tipo, y el código traduce cada patrón a una fuerza. Así nace la "IA" de los enemigos, y deja preparado el editor futuro del diseño del juego.

La recompensa visual: cargas que se repelen y que algo junta se ordenan solas en una red de triángulos (cristales de Coulomb). Los hexágonos que te persiguen forman un enjambre con forma de panal, que se mueve, se deforma y se reordena. Al usuario le gusta que ese movimiento sea raro: "le da el movimiento necesario".

El jugador también tiene carga, de signo contrario: atrae a los hexágonos, pero la fuerza no lo mueve, porque su control tiene que ser exacto. Si quedas dentro de un hexágono abierto (decisión 16 del spec de la 0.1.0), tu carga lo tira hacia ti y sus vecinos lo empujan, así que se mueve raro a tu alrededor. Estar tan encima de él es peligroso.

## Decisiones del usuario

1. **El hexágono se mueve como un imán del mismo polo** frente a los otros enemigos: repulsión de Coulomb, `k·q₁·q₂ / r²`, más una atracción hacia el jugador. Las dos salen de un potencial, y el enemigo baja por su pendiente (idea "B" de la sesión).
2. **La carga es la cantidad de líneas que le quedan al enemigo.**
3. **Con inercia y roce.** El enemigo tiene velocidad propia: se pasa de largo, rebota contra el campo del vecino y oscila.
4. **Es el comportamiento del hexágono, y va en el JSON.** Cada tipo de enemigo declara sus patrones en el balance, y cada patrón se traduce a su clase en el código.
5. **Patrones que se suman** (opción 1 de la sesión), no un comportamiento con nombre por enemigo. El usuario la eligió porque se extiende a resortes, enemigos que disparan, pathfinding o embestidas que atraviesan a los demás.
6. **Todo en un solo PR, el del #27**: los patrones, la física, la grilla y el benchmark.
7. **Nunca se tocan, aunque sean muchos.** Coulomb de lejos y un núcleo duro de cerca (opción "a" tras la revisión del spec). Con `seek` de fuerza constante, la presión del enjambre crece con la cantidad de enemigos, y Coulomb con corte no la aguanta.
8. **El jugador tiene carga de atracción, pero la ley no lo afecta**: su movimiento sigue exacto y preciso. Atrae a los hexágonos con la misma ley de Coulomb. Si queda dentro de un hexágono, a este lo mueven y lo empujan de forma rara, y eso agrega dificultad. Que el enjambre se mueva raro está bien.
9. **Masa = carga = líneas.** Un herido empuja menos, y a él lo empujan igual que a cualquiera. Corrige lo que dijo Claude en la sesión ("lo empujan más"), que con Coulomb no se cumple.

## Metas, no-metas y anti-metas

- **Metas:**
  - Los hexágonos no se superponen nunca, ni con 300 apretados.
  - Con pocos, se ven como imanes: se repelen de lejos y oscilan.
  - El movimiento de cada tipo de enemigo sale de su lista de patrones en `balance.json`.
  - Un hexágono herido empuja menos.
  - Cerca del jugador, su carga tira a los hexágonos, y uno que te rodea se mueve raro entre tu atracción y el empuje de sus vecinos.
  - El movimiento del jugador no cambia: ninguna fuerza lo mueve.
  - La grilla da los mismos pares que revisar todos contra todos.
  - `poe benchmark` da menos de 16,6 ms por paso con 300 enemigos.
- **No-metas** (el modelo las recibe después sin cambiar):
  - Los patrones de ataque (disparar, embestir). Irían en otra lista, `attacks`, porque no son fuerzas.
  - Las fases ("orbita 3 s, después embiste"): una máquina de estados, donde cada fase es una lista de patrones.
  - Los resortes, el pathfinding y los polos opuestos entre tipos distintos.
  - Que cada línea sea una carga (idea "C" de la sesión).
  - Que las fuerzas muevan al jugador.
  - Enemigos más grandes que el corte de la repulsión.
  - Otros tipos de enemigo y el editor.
- **Anti-metas** (sería un fracaso aunque funcione):
  - Que se vea como un algoritmo ordenando y no como imanes.
  - Enemigos superpuestos, o una red de seguridad que corrige sin parar.
  - Que la conducta de un tipo de enemigo quede escrita a mano en Python, fuera del balance.
  - Que el resultado dependa del orden de la lista de enemigos.

## Restricciones

- `world/` es lógica pura. De Pygame solo usa `Vector2` (ADR 0003, 0016).
- Pasos fijos de 1/60 s (ADR 0005). Sin azar nuevo.
- `balance.py` y `balance.json` deben calzar siempre. La importación reescribe el bloque de datos con el `repr` de las dataclasses (ADR 0004).
- `datafile` hoy entiende `float`, `int`, `bool`, `str`, tuplas de largo fijo, dataclasses y `dict[str, Dataclass]`. No entiende listas de largo variable ni tipos que cambian según un campo.
- La grilla espacial va desde el inicio y se confirma con Hypothesis contra la fuerza bruta (ADR 0006). El benchmark incluye un enemigo con muchas líneas (ADR 0020).
- `Enemy.hit_by` mide el tramo de la bala entre `previous` y `position`. Es exacto mientras el enemigo solo se traslade (ADR 0020).
- Las clases son simples, con herencia. Sin ECS (AGENTS.md).

## Enfoques considerados

- **1. Patrones que se suman (elegido por el usuario).** Cada patrón es una fuerza, y el enemigo suma las de todos sus patrones. En el código, `Pattern` es la clase base, cada patrón hereda de ella, y su `kind` en el JSON elige la clase.
  - A favor: cada patrón es un término del potencial, así que el código se lee como la fórmula. Los tipos nuevos combinan patrones sin escribir clases. Es la forma estándar de los "steering behaviors" de Reynolds.
  - En contra: `datafile` tiene que aprender listas y tipos distintos según `kind`.
- **2. Un comportamiento con nombre por enemigo** (`"behavior": {"kind": "magnet", ...}`).
  - A favor: menos piezas.
  - En contra: un enemigo "imán + disparar" necesita otra clase que repita la parte del imán.
- **3. Números fijos en `EnemySpec`, sin mapeo.**
  - A favor: es lo más chico.
  - En contra: no da lo que pidió el usuario. Se descartó.

Para que no se toquen con muchos enemigos (decisión 7):

- **a. Núcleo duro (elegido por el usuario).** Se cumple "nunca se tocan". En contra: una fuerza empinada puede volverse inestable con pasos de 1/60 s.
- **b. Que se toquen bajo presión, con un choque sin rebote.** Es más robusto, pero el enjambre se aprieta hasta tocarse.

## Diseño

### La física

Cada enemigo tiene posición `p`, velocidad `v`, masa `m` y carga `q`:

- `m` = líneas que le quedan;
- `q` = `charge_per_line` · líneas que le quedan.

En cada paso se calcula su aceleración como la suma de lo que aporta cada patrón, menos el roce:

```
a = Σ patrón.aceleración − γ·v
```

**La interacción entre dos enemigos es de a pares y simétrica** *(decisión de Claude, tras la revisión)*. La fuerza que `j` ejerce sobre `i` es la misma, con signo contrario, que la que `i` ejerce sobre `j` (tercera ley de Newton). La aceleración de `i` es esa fuerza dividida por `mᵢ`. La forma de la fuerza es **una sola ley para todos los enemigos**, con sus números en la sección `charges` del balance. El patrón `coulomb` solo dice "este enemigo la siente".

- **Coulomb, de lejos.** `F = k · qᵢ · qⱼ / r²`, en la dirección que los une. Con `m = líneas`, la aceleración es `aᵢ = k · cᵢ · cⱼ · linesⱼ / r²`, donde `c` es `charge_per_line`: depende de las líneas del vecino, no de las propias. Un herido empuja menos, y a él lo empujan igual. Con cargas de signo contrario, la misma fórmula atrae, y la tercera ley se sigue cumpliendo: queda abierta la puerta a los polos opuestos.
  - *(Decisión de Claude)* Se corta en `cutoff`, medido de centro a centro. Al valor de la fuerza se le resta el que tiene en `cutoff`, para que no salte de golpe a cero en el borde.
  - *(Decisión de Claude)* Se suaviza cerca de `r = 0`, con `r² + ε²` en el denominador, para que sea finita.
- **El núcleo duro, de cerca** (decisión 7). Una fuerza que crece muy rápido por debajo de una distancia de contacto, y que es cero por encima.
  - Forma propuesta *(decisión de Claude)*: una potencia alta, `F = K · ((d₀ / r)ⁿ − 1)` para `r < d₀`, donde `d₀` es un poco más que la suma de los radios envolventes. Es el término repulsivo del potencial de Lennard-Jones.
  - **Siempre repele**, sea cual sea el signo de las cargas: si no, dos polos opuestos colapsarían.
  - **No depende de la carga, sí de la masa**: es la misma fuerza para los dos, así que un herido, más liviano, sale más empujado por el núcleo.
  - Quien construye elige `K`, `n` y `d₀` con una simulación. Tienen que cumplir lo siguiente:
    - con 300 hexágonos apretados contra el jugador quieto, ningún par de envolventes se superpone;
    - es estable con `dt = 1/60`. Como guía, la rigidez `√(dF/dr / m)·dt` no debería pasar de 1 en la distancia de equilibrio de la multitud más apretada.

**El jugador, una carga fija** (decisión 8). Tiene carga `q_p`, de signo contrario a la de los hexágonos, y se comporta como una carga de masa infinita: atrae, pero nada lo acelera.

- Sobre el enemigo `i`, la parte de Coulomb es la misma ley: `aᵢ = k · cᵢ · q_p / r²`. Con signos contrarios, atrae.
- *(Decisión de Claude)* **Sin corte.** Es un solo cuerpo, así que cuesta `O(N)` y no pasa por la grilla.
- *(Decisión de Claude)* **Sin núcleo duro entre el jugador y un enemigo**: así puedes quedar dentro de uno abierto.
- *(Decisión de Claude)* **Con su propio suavizado**, de la escala del radio del enemigo. Cerca del centro, la atracción se comporta como un resorte, y el hexágono oscila alrededor tuyo en vez de clavarse en un punto. Un hexágono centrado sobre ti no te mata, porque su apotema (24·cos 30° ≈ 20,8) es mayor que tu radio (12). Te mata cuando sus vecinos lo empujan y le meten una línea encima tuyo.
- *(Decisión de Claude)* **`seek` se queda.** Coulomb a 800 unidades, donde aparecen los enemigos, es casi cero. `seek` los trae desde lejos, y la carga del jugador manda de cerca. Un valor inicial razonable para `q_p` es el que iguala la atracción a `seek` a unas 100 unidades: `|q_p| ≈ 240 · 100² / 171000 ≈ 14`.

**Integración** *(decisión de Claude)*: Euler semi-implícito, el estándar en juegos porque es estable con roce:

```
v ← v + a·dt
v ← v acotada a |v| ≤ speed
p ← p + v·dt
```

`speed` del balance pasa a ser la velocidad máxima. Nada se mueve más rápido que hoy, y el tope también ayuda a la estabilidad: nadie avanza más de 2 unidades por paso.

**Simultáneo** *(decisión de Claude)*: primero se calculan las aceleraciones de todos con las posiciones del inicio del paso, y recién después se mueven todos. Así, el orden de la lista no cambia el resultado.

### Los patrones del hexágono

- **`seek`, la atracción.** Una aceleración de largo constante `strength` hacia la posición actual del jugador, como una gravedad que apunta hacia él. Su potencial es un cono, `m · strength · |p − jugador|`. Con el roce, la rapidez terminal es `strength / γ`. Sobre el jugador vale cero, sin dividir por cero.
- **`coulomb`, sentir las cargas.** No tiene números propios: aplica la ley de `charges` con los enemigos a menos de `cutoff` (Coulomb y núcleo) y con el jugador (solo Coulomb, sin corte). *(Decisión de Claude: se llamaba `repel`, pero ahora también atrae hacia el jugador.)*

Un enemigo con carga y sin `coulomb` igual empuja a los demás, pero él no se mueve por ellos. *(Decisión de Claude: hoy solo existe el hexágono, que tiene los dos.)*

### La red de seguridad *(decisión de Claude)*

Queda como último recurso: con el núcleo duro bien elegido, no debería actuar nunca. Después de mover a todos, cada par cuyos círculos envolventes se superponen se aparta la mitad de la superposición, en la dirección que los une. También se quita la parte de la velocidad que los acerca, para que no reboten.

- Las correcciones de todos los pares se **suman y se aplican juntas**, para que no dependan del orden de la lista. Un par aislado queda tangente; en un grupo, puede quedar un resto, y se corrige en el paso siguiente.
- Si dos están en el mismo punto exacto, usa una dirección fija. Este caso sí depende del orden de la lista, y queda fuera del test de orden.

### Los datos

En `balance.json` (los números son propuestos, y se ajustan jugando y con la simulación del núcleo):

```json
"player": {"speed": 240.0, "radius": 12.0, "charge": -14.0},
"charges": {
  "k": 171000.0,
  "cutoff": 150.0,
  "softening": 1.0,
  "core_strength": "…",
  "core_distance": "…",
  "core_exponent": "…"
},
"enemies": {
  "hexagon": {
    "sides": 6,
    "radius": 24.0,
    "speed": 120.0,
    "friction": 2.0,
    "charge_per_line": 1.0,
    "patterns": [
      {"kind": "seek", "strength": 240.0},
      {"kind": "coulomb"}
    ]
  }
}
```

- `friction` es `γ`, en 1/s. Es un campo del enemigo y no un patrón: sin roce, un enemigo con inercia se desliza para siempre. *(Decisión de Claude.)*
- Los números iniciales salen de una cuenta. Con `strength = 240` y `γ = 2`, la rapidez terminal es 120, igual a `speed`. Con `k = 171000` y la fuerza ya restada en el corte, un vecino de 6 líneas a 60 unidades (2,5 radios) empuja con 240, lo mismo que tira `seek`: `171000 · 6 · (1/60² − 1/150²) ≈ 240`.
- `player.charge` es `q_p`. Va en el jugador porque describe a una entidad (ADR 0018).
- Los nombres de los campos del núcleo y del suavizado del jugador los fija quien construye.
- **`datafile` aprende dos cosas**, con sus tests:
  - tuplas de largo variable, `tuple[X, ...]`, que en el JSON son listas;
  - un tipo de patrón que se elige con el campo `kind`.

  Un `kind` desconocido, un campo que falta o un campo que sobra da un error con la ruta: `enemies.hexagon.patterns[1].kind`. El mecanismo concreto (unión de dataclasses, `Literal` o una clase base con registro) lo elige quien construye. Tiene que pasar `mypy` y salir bien en el `repr` que usa la importación.

### El código

- En `balance.py` van `ChargesSpec`, las dataclasses de cada patrón (`SeekSpec`, `CoulombSpec`), `PlayerSpec` con `charge` y `EnemySpec` con `friction`, `charge_per_line` y `patterns`.
- En un `world/patterns.py` *(nombre propuesto)* van `Pattern`, la clase base con `acceleration(enemy, context) -> Vector2`, sus subclases `Seek` y `Coulomb`, y una función que crea la instancia desde su spec.
  - **Cada enemigo tiene sus propias instancias de patrón.** El balance da los números, y el estado (los timers de un futuro `dash`) vive en el mundo.
  - `context` le da al patrón lo que necesita: la posición y la carga del jugador, la ley de `charges` y los vecinos cercanos.
- `Player` no cambia su movimiento: no recibe fuerzas.
- La ley de a pares (Coulomb + núcleo) es una función pura en `world/`, con su fórmula en el docstring.
- `Enemy` agrega `velocity` (en cero al aparecer), `mass` y `charge`.
- En `world/grid.py`, `SpatialGrid(cell_size)` con `pairs(positions, radii) -> set[tuple[int, int]]`, los pares `(i, j)` con `i < j` cuyos círculos se tocan (como en el plan de la 0.1.0). La misma grilla sirve para dos cosas:
  - los vecinos de la repulsión, con radio `cutoff / 2` para cada uno (vale porque `cutoff` es uno solo para todos);
  - la red de seguridad, con el radio envolvente.

### El orden de cada paso

1. Se mueve el jugador.
2. Cada enemigo guarda `previous`, y se calculan las aceleraciones de todos con las posiciones del inicio del paso.
3. Se integran velocidades y posiciones.
4. La red de seguridad separa a los que quedaron superpuestos, si hay.
5. Las balas avanzan y golpean, el arma dispara, se quitan los muertos, aparece uno nuevo si toca y se revisa el contacto (como hoy).

`hit_by` sigue siendo exacto: entre `previous` y `position` el enemigo solo se trasladó, sumando la física y la red de seguridad.

### Benchmark y evidencia

- `poe benchmark`: los milisegundos por paso con 300 hexágonos apretados alrededor del jugador, más un enemigo de 100 líneas sin carga, que solo mide el costo de las balas (ADR 0020). El contacto no termina la partida en el benchmark. Se corre a mano. La meta es menos de 16,6 ms.
- **Escenario nuevo para las capturas** *(decisión de Claude)*: con `spawning.interval = 2` s, en 6 s hay apenas tres hexágonos y no se ve el panal. Un escenario `panal` arranca con unos 40 hexágonos alrededor del jugador quieto, **sin contacto y sin arma**, para ver cómo se ordenan sin que la partida termine. Hoy `Scenario` solo tiene la bandera `pilot`, así que se le agregan el estado inicial y esos dos interruptores. `oleadas` sigue para ver la llegada normal.

## Escenarios de test

`render/` y `scenes/` no se testean (ADR 0007). Cada comportamiento lleva un caso feliz, uno borde y uno negativo.

- **`datafile`:**
  - feliz: una lista de patrones de distinto `kind` se carga y vuelve igual con `dump`;
  - borde: una lista vacía de patrones es válida;
  - negativo: un `kind` desconocido, un campo que sobra dentro de un patrón y un patrón sin `kind` dan `DataFileError` con la ruta (`patterns[1].kind`).
- **Balance:** el `balance.json` real calza, y exportar e importar con patrones da lo mismo (ida y vuelta).
- **`seek`:**
  - feliz: apunta al jugador con largo `strength`;
  - borde: sobre el jugador vale cero, sin error;
  - negativo: no depende de la velocidad del enemigo.
- **Inercia y roce:**
  - feliz: sin fuerzas, la rapidez baja en cada paso;
  - borde: la rapidez nunca pasa `speed`;
  - negativo: un enemigo en reposo y sin fuerzas no se mueve.
- **La ley de a pares:**
  - feliz: dos hexágonos sueltos en reposo, sin `seek`, se alejan;
  - Hypothesis: la cantidad de movimiento se conserva (`Σ m·a = 0` entre enemigos), con cargas de cualquier signo, líneas y posiciones cualquiera;
  - feliz: un herido empuja menos (la aceleración que causa baja con sus líneas), y la que recibe por Coulomb no depende de sus líneas;
  - feliz: el núcleo repele aunque las cargas sean de signo contrario;
  - borde: en el mismo punto exacto no hay división por cero ni `nan`;
  - borde: a más de `cutoff` la parte de Coulomb es cero, y justo en `cutoff` también;
  - negativo: un enemigo no se repele a sí mismo.
- **La carga del jugador:**
  - feliz: un hexágono cerca del jugador acelera hacia él, y más fuerte mientras más cerca (hasta el suavizado);
  - borde: con el centro del hexágono justo sobre el jugador, la aceleración es finita y sin `nan`;
  - borde: lejos, a 800 unidades, la atracción existe aunque sea chica (no hay corte);
  - negativo: el jugador se mueve exactamente igual con y sin enemigos cerca, para la misma intención;
  - negativo: un hexágono completo centrado sobre el jugador no lo toca.
- **Nunca se tocan** (simulación, marcada `simulacion` como los tests largos de hoy): 300 hexágonos apretados contra el jugador quieto, sin contacto. Después de unos segundos, ningún par de envolventes se superpone y la red de seguridad no actuó.
- **Orden de la lista (Hypothesis):** permutar la lista de enemigos da las mismas posiciones después de un paso (con `approx`, porque las sumas de flotantes cambian de orden). Excluye a los que están en el mismo punto exacto.
- **Grilla (Hypothesis):** con cualquier conjunto de posiciones y radios, incluidos cuerpos en el borde de una celda y celdas negativas, `pairs` da exactamente los mismos pares que la fuerza bruta.
- **Red de seguridad:**
  - feliz: dos superpuestos quedan tangentes y sin velocidad de acercamiento;
  - borde: en la misma posición no divide por cero;
  - negativo: dos que no se tocan no se mueven.
- **El hexágono herido** (integración): después de perder líneas, su carga y su masa bajan.
- **El golpe con la física:** una bala contra un enemigo que la repulsión acaba de mover lo golpea igual (el tramo relativo incluye el empujón).
- **No se puede testear:** que se vea como imanes y que el movimiento raro se sienta bien. Se verifica con las capturas de `panal` y con la prueba manual.

## Lo que queda a quien construye

- El mecanismo de `kind` en `datafile`, con las condiciones de arriba.
- Los números del núcleo, `ε` y el tamaño de la celda (al menos `cutoff`), con las condiciones de arriba y una simulación que quede versionada como test o en el benchmark.
- Los tests de simulación y del piloto que dependen de tiempos exactos (por ejemplo, la muerte de la semilla 1 a los 5,23 s) cambian con la inercia. Se revisan y se cuenta en el PR qué cambió.
- Si `weapons.nearest` busca en la grilla: queda como pregunta abierta del spec de la 0.1.0. No se toca en este PR, salvo que el benchmark lo pida.
- El ADR nuevo (0021, propuesto): los enemigos se mueven por patrones definidos en el balance, con inercia y roce, y la interacción entre ellos es una ley de a pares. Reemplaza en parte la decisión 12 del spec de la 0.1.0.
- El texto del issue #27 se actualiza (Qué, Por qué, Terminado cuando), mostrando antes el texto al usuario.
