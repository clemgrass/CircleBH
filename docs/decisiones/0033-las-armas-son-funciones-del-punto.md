---
estado: aceptado
fecha: 2026-11-27
---

# Las armas son funciones del punto

Reemplaza, del [ADR 0029](0029-armas-por-terminos-y-tarjetas.md), las seis armas de dos tipos (proyectil y trazo), "Cómo dañan los trazos" y la regla de que una suma que da un arma que ya existe no se ofrece. Deja sin efecto el [ADR 0032](0032-el-trazo-se-gasta-donde-pega.md), porque ya no hay trazos. Del 0029 sigue todo lo demás: los tres términos, las perillas, las sumas y los operadores (M1, M2 y M3), los precios (M8), las mejoras fuera del ataque, las palancas de variedad y la regla de no tener topes.

## Contexto y problema

El círculo llegó como trazo (#100). La recta, la espiral, el seno y la rosa se construyeron en la rama `feat/recta-espiral-seno-y-rosa` (#101, #102 y #103), con la rosa por pétalos.

El 2026-11-27, al ver las armas nuevas, el autor dijo *(palabras del autor, resumidas)*:

1. no le gustó cómo se sentían, ninguna de las nuevas;
2. usa tanto el punto que siente que la mecánica central del juego debería girar en torno a él: la idea del género es mejorar al jugador y a ese punto inicial;
3. quiere que los ataques sean siempre puntos;
4. no quiere que se fuerce la aparición de esas armas. Prefiere sumar tantos conceptos matemáticos como mejoras entretenidas haya, y que esas formas aparezcan solo si, en teoría, salen de combinarlas;
5. vuelve a la idea del milestone: el punto es una función de varias variables que entrega cada punto que dispara, con su tamaño, rapidez, cooldown y lo demás, y eso es lo que se mejora.

Hay que decidir qué es un arma, qué da una tarjeta de arma nueva, a qué enemigo apunta cada arma y a qué arma va cada mejora.

## Factores de decisión

- Que el centro del juego sea el punto y mejorarlo *(autor)*.
- Que todo ataque sea un punto: se lee como la bala que desaparece al pegar (ADR 0032) *(autor)*.
- Que las formas salgan de combinar, sin metas con nombre *(autor)*.
- Que mejorar cambie la ley del punto y no solo números *(anti-meta del diseño)*.
- Que dos armas no terminen iguales, y que el azar empuje construcciones distintas (ADR 0029).
- Que todo siga siendo dato del balance (ADR 0004), determinista (ADR 0005) y testeable (ADR 0007).

## Opciones consideradas

Qué es un arma:

- A: cada arma es una función del punto, y un arma nueva es otra copia del punto del inicio
- B: las seis armas del ADR 0029, con los trazos
- C: un solo punto, sin armas nuevas (no discutida)

A qué enemigo apunta cada arma:

- D: la `k`-ésima apunta al `k`-ésimo enemigo más cercano, y la cuenta da la vuelta
- E: la `k`-ésima apunta al `k`-ésimo, y las que sobran, al más cercano
- F: todas apuntan al más cercano (no discutida)

A qué arma va cada mejora:

- G: cada tarjeta de la mano dice a qué arma va
- H: se elige la tarjeta y después el arma
- I: al tomar un arma nueva, la anterior queda congelada

Cómo se escribe en el código:

- J: `WeaponSpec` y `ProjectileWeapon`, como hoy, ahora como `f₁` a `f₄`
- K: la función como una lista de términos componibles

## Resultado de la decisión

Elegimos **A, D, G y J** *(decisiones del autor, 2026-11-27)*.

### Un arma es una función del punto

- **Todo ataque es un punto.** No hay trazos: ni la recta, ni el anillo, ni la rosa como curvas que dañan. Sale el círculo de `main` (#100).
- **Un arma es una función** `f(t; v, A, ω, Ω, n, …)` que entrega cada punto que dispara: su trayectoria, su tamaño, su rapidez, su cooldown, cuántas líneas quita y cuántas atraviesa. Sigue los tres términos del ADR 0029 en su marco.
- **Una tarjeta cambia la función de un arma** de una de tres formas, como en el 0029: una perilla (M1), un término sumado (M2) o un operador (M3).
- **Un disparo puede soltar varios puntos.** `Cₙ`, el reflejo y la paralela son mejoras, y el catálogo puede sumar otras, como la división al pegar.
- **Ninguna forma se fuerza.** No hay armas con nombre como meta. Punto más giro se ofrece, aunque dé una espiral; lo que salga de combinar, sale solo.

### El arma nueva es otro punto

- **Partes con `f₁`, el punto del inicio.** La tarjeta "arma nueva" suma `f₂`, `f₃` o `f₄`, que parten iguales a ese punto, y cada una se mejora por su lado.
- **El tope de 4 armas** sigue en el balance (`level_up.max_weapons`).
- **El balance guarda una sola función base,** el punto, en vez de un catálogo de armas con nombre *(propuesta de Claude)*.

### Cada arma apunta a un enemigo distinto

- **`fₖ` apunta al `k`-ésimo enemigo más cercano** que el punto puede apuntar hoy (`nearest`: vivo, que no sea fantasma ni tenga el centro en el jugador). Así el fuego se reparte solo.
- **Si hay `n` enemigos y `n < k`, la cuenta da la vuelta:** `fₖ` apunta al `((k − 1) mod n) + 1`-ésimo. Con 2 enemigos y 4 armas, `f₃` vuelve al más cercano y `f₄` al segundo. Con uno, todas le apuntan a él.
- **Solo vale para las armas que apuntan a un enemigo.** Si el catálogo trae una mejora que cambia hacia dónde sale el punto, esa arma deja de usar el orden.

### Cada tarjeta dice a qué arma va

- **La mano reparte pares (mejora, arma),** como ya lo hace `Offer(card, weapon)`.
- **El frente muestra la etiqueta del arma,** `f₂`, y su forma actual en miniatura. **El reverso** muestra la fórmula de esa arma antes y después.
- Una tarjeta del jugador (velocidad, radio, carga, anillos) no va a ningún arma, como hoy.

### El catálogo de mejoras

- **Un issue aparte recorre, de forma exhaustiva, los conceptos matemáticos** que puedan ser mejoras entretenidas: términos, operadores, simetrías, sucesiones, geometría, ritmo y lo que aparezca *(decisión del autor)*. Cada uno con qué hace con el punto, cómo se ve, su contra o precio y con qué choca.
- **El trabajo del catálogo termina con las mejoras listas en el balance,** no con una lista de ideas *(decisión del autor)*. Su issue sigue abierto hasta entonces: la investigación va en su propio PR, y la construcción, en tareas chicas con su issue cada una *(corregido el 2026-11-27, antes de llegar a `main`, con el acuerdo del autor; antes decía "el issue termina…", y no calzaba con el plan, que lo parte en piezas)*.
- **Mientras tanto,** se construye con lo que el 0029 ya decide para el punto: perillas, términos y operadores.

### En el código *(J)*

- **Sigue `WeaponSpec`, y `ProjectileWeapon` es la única arma.** Cada una sabe su número `k`. Salen `TraceWeapon`, `Trace`, el barrido y el círculo del balance.
- **Si el catálogo trae conceptos que no caben en los campos de `WeaponSpec`,** como la división al pegar o el rebote, ese issue decide si se agregan campos o si la función pasa a ser una lista de términos (K), con los conceptos a la vista.

### Consecuencias

- Bueno: el centro del juego es uno solo, tu punto, y se lee igual en cada golpe.
- Bueno: las construcciones salen de las decisiones del jugador, y dos armas pueden terminar muy distintas.
- Bueno: el fuego se reparte entre enemigos sin que el jugador lo piense.
- Bueno: es más barato que los trazos, que eran lo que más costaba por paso.
- Malo: se pierde el trabajo del círculo como trazo (#100), del ADR 0032 y de la rama de las armas nuevas. Se rescata lo que sirva, como la bala que gira alrededor del jugador y su anticipación.
- Malo: un arma nueva tarde en la partida parte débil. Se afina con los números (ADR 0030).
- Malo: si las mejoras son sobre todo números, el juego cae en la anti-meta. El catálogo tiene que traer sobre todo cambios de ley.
- Malo: varios puntos por disparo pueden llenar la pantalla y el cuadro. Lo cuidan el balance y el #42.

### Confirmación

- Un test comprueba que el balance trae una sola función base, el punto, y que `check_weapons` rechaza `kind: "trace"`.
- Un test comprueba que la tarjeta de arma nueva suma `f₂` igual al punto del inicio, y que no se ofrece con `max_weapons` armas.
- Un test comprueba que, con 4 enemigos, `f₁` a `f₄` apuntan del más cercano al cuarto.
- Un test comprueba que, con 2 enemigos y 4 armas, `f₃` apunta al más cercano y `f₄` al segundo, y que con uno todas le apuntan a él.
- Un test comprueba que una mejora de `f₂` no cambia `f₁`.
- Una búsqueda de `TraceWeapon`, `Trace` y `sweep` en `src/` no encuentra nada.
- `poe capturas --escenario mano` muestra tarjetas con `f₁` y `f₂`.

## Pros y contras de las opciones

### A: cada arma es una función del punto
- Bueno: todo gira en torno al punto, y las formas salen de combinar.
- Malo: las armas nuevas no traen una identidad propia de entrada; se la da el jugador.

### B: las seis armas del ADR 0029
- Bueno: cada arma trae una forma reconocible desde que la tomas.
- Malo: al autor no le gustó cómo se sienten, y los trazos se leen peor que el punto.

### C: un solo punto, sin armas nuevas (no discutida)
- Bueno: es lo más simple.
- Malo: no hay forma de tener dos construcciones a la vez, y se pierde la decisión de invertir o empezar otra.

### D: el `k`-ésimo más cercano, dando la vuelta
- Bueno: el fuego se reparte parejo con cualquier cantidad de enemigos.
- Malo: con pocos enemigos, un arma puede apuntar al segundo aunque el primero esté más cerca y sea más peligroso.

### E: las que sobran, al más cercano
- Bueno: concentra el fuego en la amenaza inmediata.
- Malo: con 2 enemigos y 4 armas, el segundo recibe una sola.

### F: todas al más cercano (no discutida)
- Bueno: es lo de hoy.
- Malo: varias armas gastan balas en el mismo enemigo.

### G: cada tarjeta dice a qué arma va
- Bueno: la decisión queda en la mano, sin pasos extra, y el azar empuja construcciones distintas.
- Malo: a veces sale para `f₂` la mejora que querías para `f₁`.

### H: elegir la tarjeta y después el arma
- Bueno: es lo que da más control.
- Malo: es un paso más, y casi siempre conviene darle todo al arma más fuerte: la variedad baja.

### I: el arma anterior queda congelada
- Bueno: es lo más claro.
- Malo: castiga empezar otra arma y obliga a cerrar una construcción antes de tiempo.

### J: `WeaponSpec` y `ProjectileWeapon`
- Bueno: es el cambio más chico, y reusa `terms.py`, la mano y los tests del punto.
- Malo: un concepto que no quepa en los campos fijos obliga a cambiar la estructura después.

### K: una lista de términos componibles
- Bueno: es lo más abierto para un catálogo grande.
- Malo: es diseñar la abstracción antes de conocer los conceptos.

## Preguntas abiertas

- **El catálogo de mejoras,** con sus valores y precios: lo resuelve su issue.
- **Si la función pasa a ser una lista de términos (K):** lo decide el issue del catálogo, si hace falta.
- **Cómo se ve la etiqueta `fₖ` en la tarjeta y en el juego**, por ejemplo si cada arma lleva una marca junto a sus puntos: se decide al construir.
