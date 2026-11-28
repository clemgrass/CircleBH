---
estado: aceptado
fecha: 2026-11-27
---

# El arma se escribe por momentos

Reemplaza, del [ADR 0033](0033-las-armas-son-funciones-del-punto.md), la opción J ("`WeaponSpec` y `ProjectileWeapon`, como hoy"). Del [ADR 0029](0029-armas-por-terminos-y-tarjetas.md), reemplaza el marco cartesiano o polar y la forma de `WeaponSpec`. Sigue todo lo demás de los dos: el punto, las perillas, las sumas y los operadores, el orden fijo, los precios y la regla de no tener topes.

## Contexto y problema

El catálogo de mejoras (#127, `docs/investigaciones/2026-11-27-catalogo-de-mejoras.md`) trae 36 conceptos aprobados por el autor, ordenados por el momento de la vida del punto: nace, viaja, pega y termina. Hoy el arma es un `WeaponSpec` de 13 campos sueltos, y `check_weapons` rechaza casi todo lo que no es el punto.

El catálogo le pide diez cosas a la estructura del arma (su "Resumen"):

1. un eje por armónico;
2. el avance como polinomio, o con roce;
3. un ancla: donde nació, el jugador o el enemigo;
4. una duración, como dato;
5. renacer: al pegar y al terminar, la bala muere y suelta otras;
6. un orden fijo entre lo que sigue al golpe;
7. estado en la bala para la persecución y la carga;
8. un choque con radio;
9. funciones nuevas del enemigo, como el impulso;
10. reglas de "hacia dónde sale" que se excluyen entre sí.

El ADR 0033 dejó abierto si esto se hace agregando campos (J) o si el arma pasa a ser una lista de términos (K).

## Factores de decisión

- Que el arma se lea como el catálogo: el repo es un ejemplo de POO *(AGENTS.md)*.
- Que agregar un concepto sea agregar una pieza, no tocar todo.
- Que lo que se excluye no se pueda escribir en los datos: dos reglas de apuntar a la vez.
- Que todo siga siendo dato del balance (ADR 0004), determinista (ADR 0005) y testeable (ADR 0007).
- Que las tarjetas sigan siendo datos, y que el orden en que se toman no cambie el arma (ADR 0029).
- Que reuse lo que ya existe: `datafile` carga listas de dataclasses elegidas por su `kind`, y los enemigos ya se escriben como una lista de patrones que se suman (ADR 0021).

## Opciones consideradas

- J: agregar campos a `WeaponSpec`
- K: el arma es una sola lista de términos
- K por momentos: una lista por momento donde los conceptos se suman, y un solo valor donde se excluyen
- L: una clase de Python por concepto, sin datos (no discutida)

## Resultado de la decisión

Elegimos **K por momentos** *(decisión del autor, 2026-11-27)*.

### La forma del arma

```json
"weapon": {
  "title": "Punto",
  "birth": {
    "aim":     {"kind": "ranked", "order": "nearest"},
    "cadence": {"kind": "cooldown", "seconds": 0.6},
    "origin":  "player",
    "spread":  {"kind": "single"},
    "copies":  []
  },
  "path":   [{"kind": "advance", "axis": "along", "coefficients": [0.0, 300.0]}],
  "anchor": "birth",
  "hit":    [],
  "end":    {"kind": "vanish"},
  "trail":  {"gap": 0.0, "lifetime": 0.0},
  "payload": {"size": 0.0, "growth": 0.0, "lines": 1},
  "reach": 700.0,
  "lifetime": 0.0,
  "tau": 0.5
}
```

- **Una lista donde los conceptos se suman, un solo valor donde se excluyen.**
  - **Listas:** los términos de la trayectoria (`path`), las copias que se agregan (`copies`) y las reacciones al pegar (`hit`).
  - **Un solo valor:** hacia dónde apunta (`aim`), la cadencia (`cadence`), desde dónde nace (`origin`), cómo reparte las copias (`spread`), el ancla (`anchor`) y qué pasa al final (`end`).

  Así, `datafile` mismo rechaza dos reglas de apuntar: no hay dónde escribirlas.
- **Cada concepto es una dataclass con su `kind`,** y cada momento es una unión de ellas, como `PatternSpec` en los enemigos. Un concepto que todavía no se construye no está en la unión, y el balance que lo nombre no carga. `check_weapons` deja de llevar su lista de rechazos.
- **"Sin" es un valor, no un `null`:** `spread: single`, `end: vanish`, `copies: []`, `hit: []`, `trail.gap: 0` y `lifetime: 0` *(restricción del plan: `datafile` no acepta `null`)*.

### Cada concepto en su lugar

| Momento | Campo | Conceptos |
|---|---|---|
| Nace | `aim` | `ranked` (el `k`-ésimo por distancia o por otra clave, N8), `step` (N6) y `centroid` (N9) |
| | `cadence` | `cooldown`, `rhythm` (N12) y `motion` (N11) |
| | `origin` | `player` y `last_hit` (N13) |
| | `spread` | `single`, `rotated` (N1), `sectors` (N2) y `fan` (N3) |
| | `copies` | `parallel` (N4) y `mirror` (N5) |
| Viaja | `path` | `advance` (V4, V5, V7, V9), `harmonic` (V1, V2, V8), `spin` (V3), `drag` (T4), `pursuit` (V10) y `charge` (V11) |
| | `anchor` | `birth`, `player` (V6) y `enemy` (lo pone P8) |
| | `payload.growth` | V12 |
| | `trail` | T6 |
| Pega | `hit` | `pierce` (P1), `bounce` (P4), `refract` (P6), `chain` (P5), `orbit` (P8), `split` (P3) y `push` (P7) |
| | `payload.lines` | P2 |
| Termina | `end` | `vanish`, `burst` (T2), `return` (T3) y `wrap` (T5) |
| | `lifetime` | T1, como dato |

### La trayectoria

- **La posición es la suma de los términos, girada por el giro:** `p(t) = origen(t) + R(Ω·t)·Σ términos(t)`, con `Ω` la suma de los `spin`. Cada término va por su eje: `along` (por `û`) o `normal` (por `n̂`).
- **El marco polar desaparece como campo** *(propuesta de Claude)*. El polar del ADR 0029 con giro `Ω` es `R(Ω·t)` aplicado al avance, y sin giro es un armónico por `along`. Un campo menos, y la espiral sale de sumar `spin` al punto, como pide el ADR 0033.
- **El avance es un polinomio:** `a(t) = Σ cᵢ·tⁱ`. `d/dt` y `∫dt` actúan coeficiente a coeficiente, con `τ` para que el resultado siga siendo un largo. El bumerán es `[0, v, −v/T]`.
- **`origen(t)`** es donde nació (`anchor: birth`), donde estás tú ahora (`player`) o el centro de un enemigo (`enemy`).
- **La persecución y la carga dan una aceleración** *(propuesta de Claude)*. Sin ellas, la posición es una fórmula de `t`, como hoy. Con alguna, la bala integra su velocidad paso a paso, como un enemigo (ADR 0021), y los demás términos se suman en el marco de su rumbo. El detalle se decide en la tarea que construya V10.

### Pegar y terminar: renacer

- **Al pegar o al terminar, la bala puede morir y soltar otras** en el punto del golpe, con una dirección nueva y `t = 0`, el mismo `spec` y su generación más uno. Así se escriben el rebote, la refracción, el salto, la división, el estallido, la vuelta y el reaparecer, sin estado en la bala más allá de su generación y de a quién ya pegó.
- **El orden de las reacciones es fijo** *(propuesta de Claude)*, como el de los operadores del ADR 0029. No depende de cuándo se tomó cada tarjeta:
  1. `push` actúa en cada golpe;
  2. decide si la bala sigue la primera que tenga usos, en este orden: `pierce`, `bounce`, `refract`, `chain` y `orbit`;
  3. `split` actúa al final, si la bala no siguió.

  La lista `hit` se guarda ordenada por este orden, así que dos partidas con las mismas tarjetas dan el mismo `spec`.

### Las tarjetas

- **Perilla (`knob`):** la ruta nombra el momento y el `kind`, como `"path.harmonic.k"` o `"birth.cadence.seconds"`. En una lista, cambia **todos** los elementos de ese `kind` *(propuesta de Claude)*.
- **Agregar (`add`):** suma un elemento a `path`, `copies` o `hit`, con sus valores por semilla. Reemplaza al `TermChange` del plan.
- **Poner (`set`):** reemplaza un valor único, como `aim`, `cadence`, `spread` o `end`.
- **Operador (`operator`):** `d/dt` y `∫dt` sobre los coeficientes del avance.
- **Sin efecto, no se ofrece,** como hoy: la mano compara el `Loadout` antes y después.

### Lo que no cambia

- `ProjectileWeapon` sigue siendo la única arma, y `fₖ` apunta al `k`-ésimo (ADR 0033).
- La bala guarda el `spec` con que nació. Mejorar es reemplazar el `spec`.
- No hay topes (ADR 0029). `Cₙ` con `n = 64` y una división con `mᵈ` puntos son trabajo del #42.

### Consecuencias

- Bueno: el arma se lee como el catálogo. Cada concepto es una dataclass y una función, y agregar uno no toca a los demás.
- Bueno: lo que se excluye no se puede escribir, y `check_weapons` deja de llevar una lista de rechazos.
- Bueno: arma y enemigo se escriben igual, con una lista de conductas que se suman.
- Bueno: renacer deja casi toda la trayectoria como fórmula de `t`, que se testea con Hypothesis y dibuja la miniatura de la tarjeta.
- Malo: es el cambio más grande. Hay que reescribir `terms.py`, `weapons.py`, `cards.py` (`_change_path` no recorre listas), `render/cards.py`, `audio/voices.py`, `balance.json` y sus tests.
- Malo: la persecución y la carga agregan un segundo modo de trayectoria, integrado, que convive con las fórmulas.
- Malo: que una perilla cambie todos los elementos de un `kind` impide mejorar solo el segundo armónico.
- Malo: una lista `hit` larga, con la división y el rastro, puede llenar el cuadro (#42).

### Confirmación

- Un test comprueba que el punto de hoy, escrito en la forma nueva, da `p₀ + v·t·û` en cualquier `t` (Hypothesis), igual que antes del cambio.
- Un test comprueba que un `aim` con un `kind` desconocido no carga, y que el error nombra `weapon.birth.aim.kind`.
- Un test comprueba que dos armónicos se suman, y que un `spin` gira la suma en `Ω·t`.
- Un test de Hypothesis comprueba que `d/dt` y `∫dt` sobre los coeficientes se deshacen uno al otro.
- Un test de Hypothesis comprueba que cualquier orden de las mismas tarjetas `add` de `hit` da el mismo `spec`.
- Un test comprueba que una perilla sobre `path.harmonic.k` cambia todos los armónicos, y que una ruta a un `kind` que el arma no tiene no tiene efecto, así que no se ofrece.
- Una búsqueda de `frame` en `balance.py` y de la lista `unsupported` en `world/weapons.py` no encuentra nada.
- `poe balance-chequear` pasa con el `weapon` nuevo en `balance.py` y `balance.json`.
- `lint-imports` sigue en verde: las piezas nuevas viven en `world/` y en `balance.py`.

## Pros y contras de las opciones

### J: agregar campos a `WeaponSpec`
- Bueno: es el cambio más chico, y las tarjetas siguen siendo perillas con una ruta.
- Malo: `WeaponSpec` pasa de 13 a unos 33 campos, y cada concepto apagado es un 0.
- Malo: lo que se excluye (dos reglas de apuntar) se puede escribir, y lo rechaza el código.
- Malo: el orden entre conceptos queda escondido en el código, y agregar uno toca `WeaponSpec`, `check_weapons`, el balance y las tarjetas.

### K: una sola lista de términos
- Bueno: es lo más abierto: cada concepto es un elemento.
- Malo: mezcla lo que se suma con lo que se excluye, y la regla "solo uno de estos" queda fuera de los datos.
- Malo: el momento de cada término no se ve en el balance.

### K por momentos
- Bueno: sigue al catálogo y a los patrones de los enemigos, y lo que se excluye no se puede escribir.
- Malo: es el cambio más grande, y las perillas necesitan recorrer listas.

### L: una clase de Python por concepto (no discutida)
- Bueno: es la POO más directa: un concepto es una clase con su método.
- Malo: los conceptos dejan de ser datos del balance (ADR 0004), y las tarjetas tendrían que nombrar clases.

## Preguntas abiertas

- **Cómo convive la trayectoria integrada con las fórmulas** (V10 y V11): se decide en su tarea.
- **Los valores por semilla de una tarjeta `add`:** qué número del elemento sortea la lista. Se decide en la primera tarea que agregue tarjetas `add`.
- **Cómo muestra la tarjeta un arma con varias listas** (la miniatura y la fórmula antes y después): se decide al construir, como en el ADR 0029.
- **Si una perilla tiene que poder mejorar un solo elemento** de una lista, como el segundo armónico: se revisa si al jugar hace falta.
