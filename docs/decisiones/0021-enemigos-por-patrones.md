---
estado: propuesto
fecha: 2026-11-19
---

# Los enemigos se mueven por patrones del balance, con cargas e inercia

Reemplaza en parte la decisión 12 del spec de la 0.1.0: la separación por mitades deja de ser el movimiento y queda como red de seguridad. Complementa el ADR 0006 (la grilla y el benchmark siguen) y el ADR 0004 (el balance aprende listas de patrones).

## Contexto y problema

Los hexágonos van en línea recta hacia el jugador y, sin nada más, terminan en una sola mancha. El issue #27 pedía apartarlos al chocar. En la sesión del 2026-11-19, el usuario pidió algo más: que se comporten como imanes del mismo polo, con una física interesante, y que la conducta de cada tipo de enemigo se declare en el JSON, como su "IA" (spec `2026-11-19-patrones-de-enemigos.md`, decisiones 22 a 30 del spec de la 0.1.0).

Hay que decidir cómo se declara la conducta, qué ley mueve a los enemigos y cómo se evita que se superpongan cuando son muchos.

## Factores de decisión

- Que la conducta viva en el balance, para el editor futuro (diseño del juego).
- Que se pueda extender a resortes, disparos, embestidas, pathfinding y fases sin cambiar el modelo.
- Que la matemática quede a la vista: cada fuerza con su fórmula.
- Que los enemigos no se superpongan, ni con 300 apretados.
- Que el control del jugador siga exacto.
- Que el resultado no dependa del orden de la lista ni de la máquina (ADR 0005).

## Opciones consideradas

Para declarar la conducta:

- Patrones que se suman como fuerzas
- Un comportamiento con nombre por enemigo
- Números fijos en `EnemySpec`, sin mapeo

Para que no se superpongan:

- Coulomb con un núcleo duro de cerca
- Coulomb y un choque inelástico bajo presión
- Solo la separación por mitades del issue (no discutida)

## Resultado de la decisión

- **Patrones que se suman.** Cada tipo de enemigo declara en `balance.json` una lista de patrones. Cada patrón es una aceleración, y su campo `kind` elige la clase en `world/patterns.py`. Cada enemigo tiene sus propias instancias de patrón, para guardar estado en el futuro. Los ataques y las fases llegarán como capas aparte, porque no son fuerzas.
- **Inercia con roce.** Cada enemigo integra `a = Σ patrones − γ·v` con Euler semi-implícito, y su rapidez se acota a `speed`.
- **Una sola ley de cargas de a pares**, con sus números en la sección `charges` del balance. La fuerza es simétrica (tercera ley de Newton):
  - Coulomb, `k·qᵢ·qⱼ/r²`, con corte en `cutoff`, la fuerza del corte restada y suavizado cerca de `r = 0`;
  - un núcleo duro, `K·((d₀/r)ⁿ − 1)` por debajo de `d₀`, que siempre repele.
- **Masa = carga = líneas que le quedan** (con `charge_per_line`). Un herido empuja menos, y a él lo empujan igual que a cualquiera.
- **El jugador es una carga fija**, de signo contrario. Atrae a los enemigos sin corte y sin núcleo, pero nada lo acelera, así que su control sigue exacto.
- **El paso es simultáneo:** las aceleraciones se calculan con las posiciones del inicio del paso.
- **La separación por mitades queda como red de seguridad:** suma las correcciones de todos los pares, las aplica juntas y quita la velocidad de acercamiento.

### Consecuencias

- Bueno: la conducta del hexágono se lee como una suma de términos de un potencial, y un tipo nuevo combina patrones sin escribir clases.
- Bueno: con muchos enemigos, el enjambre se ordena solo en una red triangular.
- Bueno: un hexágono que te rodea se mueve raro entre tu atracción y el empuje de sus vecinos. Esa es una dificultad nueva, que sale de la física.
- Malo: `datafile` crece. Aprende tuplas de largo variable, `Literal` y uniones elegidas por `kind`.
- Malo: hay más números que afinar (`k`, el corte, el núcleo, el roce y la carga del jugador), y un núcleo demasiado rígido puede volverse inestable con pasos de 1/60 s.
- Malo: el enemigo ya no llega justo sobre su objetivo: se pasa de largo y oscila. Es intencional.

### Confirmación

- Un test de Hypothesis comprueba la tercera ley: `pair_force(o, qi, qj) = −pair_force(−o, qj, qi)` con cualquier carga y distancia.
- Un test de Hypothesis comprueba que permutar la lista de enemigos da las mismas posiciones después de un paso.
- Un test de Hypothesis comprueba que la grilla da los mismos pares que revisar todos contra todos (ADR 0006).
- Una simulación (`simulacion`) con 300 hexágonos apretados contra el jugador quieto comprueba que ningún par se superpone y que la red de seguridad no actúa.
- Un test comprueba que el jugador se mueve exactamente igual con y sin enemigos cerca.
- `poe balance-chequear` falla si los patrones de `balance.py` y `balance.json` no calzan.

## Pros y contras de las opciones

### Patrones que se suman
- Bueno: se combinan, y cada patrón es una fórmula.
- Malo: es lo que más código pide ahora (listas y `kind` en `datafile`).

### Un comportamiento con nombre por enemigo
- Bueno: menos piezas.
- Malo: "imán + disparar" necesita otra clase que repita la parte del imán.

### Números fijos en `EnemySpec`
- Bueno: es lo más chico.
- Malo: la conducta queda en Python y no en el balance, que es lo que pidió el usuario.

### Núcleo duro
- Bueno: se cumple "nunca se tocan".
- Malo: hay que afinarlo para que sea estable.

### Choque inelástico bajo presión
- Bueno: es robusto.
- Malo: con muchos, se aprietan hasta tocarse.

### Solo la separación por mitades (no discutida)
- Bueno: es lo más simple.
- Malo: no hay física que mirar, y con muchos el enjambre vibra.

## Más información

- Spec `docs/specs/2026-11-19-patrones-de-enemigos.md`.
- C. W. Reynolds, "Steering Behaviors For Autonomous Characters" (GDC 1999): https://www.red3d.com/cwr/steer/ (no consultado en esta sesión).
