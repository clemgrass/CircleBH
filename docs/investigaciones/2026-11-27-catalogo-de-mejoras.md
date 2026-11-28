# Investigación: el catálogo de mejoras del punto

Issue #127, tarea 8b del plan `docs/planes/2026-11-25-version-0-3-0.md`. Reemplaza al #104 y al #105.

Fecha: 2026-11-27. Cada fuente lleva su URL y la fecha de consulta. Lo marcado **(no verificado)** no salió de una página leída.

## Qué y por qué

- **Qué:** recorrer, de forma exhaustiva, los conceptos matemáticos que puedan ser mejoras entretenidas de una función del punto, y dejar las aprobadas listas para construir en la 8c.
- **Por qué:** desde el [ADR 0033](../decisiones/0033-las-armas-son-funciones-del-punto.md), las formas salen de combinar mejoras. El catálogo es el corazón del juego.
- **La anti-meta:** un survivors común donde las mejoras son solo números. El catálogo tiene que traer sobre todo cambios de ley.

## Decisiones del autor en esta investigación *(2026-11-27)*

- **Se decide en papel, sin prototipo jugable.** La razón del autor: la vez anterior, el problema fue que las armas nunca lo convencieron, no la distancia entre el prototipo y el juego. Esta vez la idea de partida, el punto, sí lo convence.
- **Qué es "entretenida",** a partir de cómo se sintió `f₂` (#126):
  - se sintió balanceado: con más enemigos, más ataques;
  - disparar dos veces fue entretenido, pero por una razón muy sencilla.

  De ahí salen dos preguntas para cada concepto: cómo escala con el enjambre y qué decisión nueva le da al jugador. Si la única respuesta es "más disparos", el concepto cuenta como número.
- **Que se visualice claro.** Al revisar Nace, el autor dejó fuera N7 y N10 porque no se los visualizaba claramente. N10 le pareció vago: si el arma sube sola cuando hay muchos enemigos, no se ve qué gana una mejora. De ahí sale una tercera pregunta, con más peso que las otras dos: ¿se ve en pantalla qué cambió?
- **El catálogo se ordena por el momento de la vida del punto,** con las áreas de la matemática como lista de chequeo (ver "Método").

## Alcance

- **Entra:** todo lo que cambia una función `fₖ`: cuándo y cómo nace el punto, por dónde viaja, qué pasa cuando pega y qué pasa cuando termina.
- **No entra:**
  - las mejoras fuera del ataque (velocidad, radio, carga, anillos y su reventón): son las tareas 14 y 15;
  - el sistema de precios: es la tarea 17. Aquí cada concepto *propone* su precio o su contra, con los tipos de M8 (ADR 0029).
- **No se reabre:** lo que deciden los ADR 0029 y 0033. Los tres términos, las perillas, las sumas y los operadores entran al catálogo como conceptos más, con la misma ficha que los nuevos.

## Lo que hay hoy en el código *(rama `main`, commit 4264a8a)*

- **El punto:** cartesiano, apunta al `k`-ésimo enemigo más cercano con anticipación, avanza con grado 1 y quita una línea por golpe (`balance.json`, `weapon`).
- **`check_weapons` rechaza casi todo lo demás** (`world/weapons.py`): el marco polar, `aim: motion`, `d/dt` y `∫dt`, `Cₙ`, el reflejo, la paralela, el tamaño, las líneas por golpe y atravesar. Ninguno está construido: hasta los operadores del 0029 dependen de este catálogo.
- **La anticipación supone una recta.** `intercept` busca el cruce con una bala que va derecho a rapidez `v`. Un concepto que cambia la trayectoria (`∫dt`, un armónico, un giro) apunta mal con ella. Cada ficha dice cómo apunta.
- **El marco polar gira en torno a donde nació la bala**, no en torno al jugador (`world/terms.py`). Una órbita alrededor del jugador no cabe en `WeaponSpec` como está.
- **Las tarjetas** son perillas (`KnobChange`), de arma nueva y del jugador. No hay tarjetas de término ni de operador.
- **"Termina" no tiene nada:** la bala desaparece al pegar o al llegar a `reach`.

## Método

### Los cuatro momentos del punto

Cada concepto va en el momento en que actúa. Cada momento tiene su lugar en el código, así que dos conceptos del mismo momento compiten por el mismo enganche:

| Momento | Qué decide | Dónde engancha hoy |
|---|---|---|
| **Nace** | cuántos puntos, cuándo y hacia dónde | `ProjectileWeapon._fire`, `ranked_target`, `intercept` |
| **Viaja** | la trayectoria | `projectile_offset`, `Bullet` |
| **Pega** | qué pasa al golpear | `ProjectileWeapon._strike`, `Enemy.hit_by` |
| **Termina** | qué pasa al llegar a `reach` | `Bullet.expired` |

Un concepto que actúa en dos momentos va en el primero y se nombra en el otro.

### La ficha de cada concepto

| Campo | Qué dice |
|---|---|
| **Fórmula** | la ley, escrita como en el código: coordenadas matemáticas, ángulos en radianes |
| **Qué hace con el punto** | en una oración |
| **Cómo se ve** | un dibujo en texto, o la forma descrita si no se puede dibujar |
| **Ley o número** | si cambia la ley del punto o solo un número |
| **Cómo escala con el enjambre** | si rinde igual con 1 que con 50 enemigos, más con muchos o más con pocos |
| **Qué decisión nueva da** | qué cambia en cómo juegas; "ninguna" lo marca como número |
| **Cómo apunta** | si `intercept` le sirve o necesita otra regla |
| **Precio o contra** | uno de los tipos de M8: presupuesto, contra en el arma, sobre el enemigo o con duración |
| **Con qué choca** | otros conceptos con los que se anula, se repite o se rompe |
| **Cabe en `WeaponSpec`** | sí (y en qué campo), con un campo nuevo, o pide la estructura K del ADR 0033 |
| **Fuente** | la referencia matemática, con URL y fecha |

### La lista de chequeo: área × momento

Al final, una tabla cruza las áreas de la matemática con los cuatro momentos. Cada casilla queda con al menos un concepto, o con "no encontré nada, porque…". Las áreas de partida *(propuesta de Claude; se suman las que aparezcan)*:

- simetría y grupos (rotaciones, reflejos, `Cₙ` y `Dₙ`);
- cálculo (`d/dt`, `∫dt`, la composición);
- series y armónicos (Fourier, epiciclos, Lissajous);
- sucesiones (Fibonacci, el ángulo áureo, las progresiones);
- teoría de números (primos, el máximo común divisor, los ritmos euclidianos);
- geometría (reflexión, inversión, las cónicas, las envolventes);
- sistemas dinámicos (órbitas, atractores, las ecuaciones de un péndulo o de un resorte);
- fractales e iteración (división recursiva, L-systems);
- probabilidad (paseos al azar, distribuciones);
- grafos (cadenas, árboles, el vecino más cercano);
- física del juego (cargas, roce, la ley del ADR 0021).

### Cómo se cierra

1. El catálogo, momento por momento, con la tabla de chequeo.
2. Un resumen: cuántos conceptos son ley y cuántos número, y cuáles recomienda Claude para la 0.3.0.
3. **El autor aprueba la lista.**
4. Si la lista pide campos que no caben en `WeaponSpec`, un ADR decide entre agregarlos (J) o pasar a una lista de términos (K).
5. Las tareas de la 8c, en el plan, con un issue cada una colgado del #127.

## Cómo se eligió el método

### Cómo decidir qué es entretenido

- **A: solo en papel.** Elegida *(autor)*.
  - Bueno: es lo más barato y permite recorrer muchos conceptos.
  - Malo: no prueba cómo se siente.
- **B: en papel, y después un prototipo jugable de los que se elijan,** en HTML o como spike dentro del juego. Era la recomendación de Claude.
  - Bueno: se prueba lo elegido antes de construirlo.
  - Malo: cuesta un prototipo, y el autor no ve en el prototipo la causa del fracaso anterior.
- **C: un prototipo jugable de todos.**
  - Bueno: es lo más fiel.
  - Malo: es lo más caro, y construye conceptos que se van a descartar.

### Cómo ordenar el catálogo

- **1: por área de la matemática.**
  - Bueno: muestra qué áreas faltan recorrer.
  - Malo: conceptos de áreas distintas pueden hacer lo mismo en el juego, y no dice dónde engancha cada uno.
- **2: por el momento de la vida del punto.** Elegida, con la 1 como lista de chequeo *(autor, a propuesta de Claude)*.
  - Bueno: los choques y lo que cabe en `WeaponSpec` se leen del enganche, y se ven los momentos vacíos.
  - Malo: sola, no asegura recorrer toda la matemática. Por eso lleva la tabla de chequeo.
- **3: por el efecto en el juego.**
  - Bueno: es la más cercana al criterio de qué es entretenido.
  - Malo: es subjetiva, y un concepto cae en varias secciones.

## El catálogo

Notación: `û` es la dirección del disparo, `θ₀` su ángulo, `R(α)` la rotación en `α` antihoraria, `N` la cantidad de enemigos apuntables y `@` el jugador en los dibujos. Los precios dicen el tipo de M8 y el sentido; los números se fijan en las tareas 17 y 20.

### Nace: cuántos puntos, cuándo y hacia dónde

| | Concepto | Ley o número | Escala con el enjambre | Cabe en `WeaponSpec` | Autor |
|---|---|---|---|---|---|
| N1 | `Cₙ`, copias rotadas | ley | más cuando te rodean | sí, `copies` | entra |
| N2 | `Cₙ` por sectores | ley | más cuando te rodean | campo nuevo | entra |
| N3 | Abanico | ley | más con grupos al frente | campo nuevo | entra |
| N4 | Paralela | número | más con filas y formaciones | sí, `parallel` | entra |
| N5 | Reflejo | ley, solo con armónico o giro | igual | sí, `mirror` | entra |
| N6 | Paso angular entre disparos (ángulo áureo) | ley | más cuando te rodean | campo nuevo | entra |
| N7 | Apuntar con tu movimiento | ley | igual | sí, `aim: motion`, más un ángulo | fuera |
| N8 | Orden del objetivo | ley sin decisión | igual | campo nuevo | entra |
| N9 | Centro de masa del enjambre | ley | más con grupos compactos | campo nuevo | entra |
| N10 | Cadencia que crece con el enjambre | ley | por definición | campo nuevo | fuera |
| N11 | Cadencia que depende de tu velocidad | ley | igual | campo nuevo | entra |
| N12 | Ritmo euclidiano | ley | igual | campo nuevo | entra |
| N13 | Origen en el último golpe | ley | más en enjambres densos | campo nuevo | entra |
| N14 | Dispersión al azar | número (contra) | más con grupos grandes | campo nuevo | fuera |

**Decisión del autor (2026-11-27):** entran todos menos N7, N10 y N14. Claude recomendaba N1, N2, N6, N7 y N10, y no recomendaba N8 solo.

#### N1. `Cₙ`: copias rotadas

- **Fórmula:** cada disparo suelta `n` puntos, con `ûⱼ = R(2πj/n)·û` para `j = 0, …, n − 1`.
- **Qué hace:** el disparo hacia tu enemigo trae `n − 1` compañeros repartidos parejo en la vuelta.
- **Cómo se ve:**
  ```
          ·
          ↑
     · ←  @  → ·      C₄
          ↓
          ·
  ```
- **Ley o número:** ley: cambia hacia dónde sale el punto.
- **Escala con el enjambre:** rinde más cuando te rodean. Con un solo enemigo, `n − 1` puntos se pierden.
- **Decisión nueva:** meterte en medio del enjambre en vez de alejarte.
- **Cómo apunta:** la copia 0 con `intercept`; las demás, rotadas desde ella.
- **Precio o contra:** presupuesto (`Cₙ` multiplica balas, como "×2 trae más enemigos" del milestone).
- **Con qué choca:** con N2, porque los dos reparten copias en la vuelta: o se elige uno o N2 es una mejora de `Cₙ`. Con N6 se suma bien: `n` brazos que giran.
- **Cabe en `WeaponSpec`:** sí, `copies`. Hoy `check_weapons` lo rechaza. Sin tope (ADR 0029): el foco 3 del plan (`n = 64`) sigue valiendo.
- **Fuente:** MathWorld, *Dihedral Group*, https://mathworld.wolfram.com/DihedralGroup.html (2026-11-27): `Dₙ` es el grupo de simetría del polígono regular de `n` lados, de orden `2n`, generado por una rotación en `2π/n` y un giro. La página *Cyclic Group* de MathWorld define `Cₙ` solo como grupo generado por un elemento, sin hablar de rotaciones.

#### N2. `Cₙ` por sectores

- **Fórmula:** el plano alrededor del jugador se parte en `n` sectores de ancho `2π/n`, con el primero centrado en `θ₀`. Cada copia apunta, con `intercept`, al enemigo más cercano de su sector. Un sector vacío no dispara.
- **Qué hace:** como `Cₙ`, pero cada copia busca su propio enemigo en vez de salir a ciegas.
- **Cómo se ve:**
  ```
       ◇ ← ·        · → ◇
              ↖    ↗
                @            sector vacío: no dispara
              ↙
       ◇ ← ·
  ```
- **Ley o número:** ley.
- **Escala con el enjambre:** es la forma más directa de "más enemigos, más ataques": con un enemigo dispara uno; rodeado, dispara `n`.
- **Decisión nueva:** te conviene que el enjambre te rodee, no que venga de un lado.
- **Cómo apunta:** `intercept` por copia. Es una partición de Voronoi en ángulo: cada sector es la región más cercana a su dirección.
- **Precio o contra:** sobre el enemigo (más velocidad o cadencia), porque premia quedar rodeado.
- **Con qué choca:** con N1 (ver arriba) y con el orden de `fₖ` (ADR 0033): dentro de su sector, `fₖ` apunta al `k`-ésimo o al más cercano. Se propone el más cercano, y que `fₖ` desplace sus sectores en `π/n·(k − 1)` para que dos armas con N2 no se pisen.
- **Cabe en `WeaponSpec`:** un campo nuevo, por ejemplo `copies_aim: "rotated" | "sectors"`.
- **Fuente:** Wikipedia, *Voronoi diagram*, https://en.wikipedia.org/wiki/Voronoi_diagram (2026-11-27): cada celda reúne los puntos más cercanos a su semilla que a cualquier otra.

#### N3. Abanico

- **Fórmula:** `n` puntos en un arco de ancho `α` centrado en `û`: `ûⱼ = R(α·(j/(n − 1) − 1/2))·û`.
- **Qué hace:** concentra las copias hacia tu enemigo, como una escopeta.
- **Cómo se ve:**
  ```
            · · ·
             \|/
              @
  ```
- **Ley o número:** ley, aunque se acerca a "más disparos" si `α` es chico.
- **Escala con el enjambre:** rinde más con grupos y formaciones al frente; con enemigos sueltos, la mayoría falla.
- **Decisión nueva:** encarar al grupo, acercarte para que el arco abarque menos espacio vacío.
- **Cómo apunta:** el centro con `intercept`; el resto, rotado.
- **Precio o contra:** contra en el arma: el alcance baja (`reach`), para que obligue a acercarse.
- **Con qué choca:** con N1 (es su opuesto: con `α = 2π(n−1)/n`, el abanico es `Cₙ` girado medio paso cuando `n` es par). Se puede escribir uno con el otro: N1 es un abanico de ancho completo.
- **Cabe en `WeaponSpec`:** un campo nuevo, `spread`, o un `copies` con ancho.
- **Fuente:** concepto del género (escopeta); la fórmula es nuestra.

#### N4. Paralela

- **Fórmula:** dos copias corridas `±d` por la normal `n̂`: `p(t) ± d·n̂`.
- **Qué hace:** dispara un riel doble hacia el mismo enemigo.
- **Cómo se ve:**
  ```
       · →
     @
       · →
  ```
- **Ley o número:** número: el punto sigue la misma ley, solo hay dos. Es el "disparar dos veces" de `f₂`.
- **Escala con el enjambre:** más con filas y formaciones; con un enemigo chico, una de las dos falla.
- **Decisión nueva:** ninguna.
- **Cómo apunta:** `intercept` para el centro, y las dos corridas.
- **Precio o contra:** ninguno o presupuesto bajo.
- **Con qué choca:** con N3 (un abanico de 2 con `α` chico se ve casi igual).
- **Cabe en `WeaponSpec`:** sí, `parallel`. Hoy `check_weapons` lo rechaza.
- **Fuente:** ADR 0029 (M3).

#### N5. Reflejo

- **Fórmula:** una copia con la normal invertida: `p(t) = p₀ + x(t)·û − y(t)·n̂`. En el marco polar, `Ω → −Ω`.
- **Qué hace:** sin armónico ni giro, nada (la copia coincide). Con armónico, dos ondas en contrafase que se cruzan: una trenza.
- **Cómo se ve (con armónico):**
  ```
     @ ⌒⌒⌒ →
       ⌣⌣⌣ →     se cruzan cada medio período
  ```
- **Ley o número:** ley, pero solo después de un concepto de Viaja.
- **Escala con el enjambre:** igual.
- **Decisión nueva:** ninguna directa: cambia la forma, no dónde estar.
- **Cómo apunta:** igual que el original.
- **Precio o contra:** ninguno.
- **Con qué choca:** no se ofrece sin armónico ni giro (ADR 0029).
- **Cabe en `WeaponSpec`:** sí, `mirror`. Hoy `check_weapons` lo rechaza.
- **Fuente:** ADR 0029 (M3).

#### N6. Paso angular entre disparos

- **Fórmula:** el disparo número `m` sale en `θₘ = θ₀ + m·ψ`, sin mirar a ningún enemigo. `θ₀` es el ángulo hacia tu enemigo cuando tomas la tarjeta. `ψ` sale de la tarjeta:
  - **ángulo áureo**, `ψ = 2π(1 − 1/φ) = π(3 − √5) ≈ 2,39996 rad ≈ 137,508°`;
  - **racional**, `ψ = 2π·p/q`: hay solo `q` direcciones, que se recorren como el polígono estrellado `{q/p}`, el mismo de los enemigos.
- **Qué hace:** el arma deja de apuntar y pasa a regar la vuelta entera. Con el ángulo áureo, ningún disparo cae sobre otro y la vuelta se llena pareja y rápido. Con `p/q`, quedan `q` rayos fijos.
- **Cómo se ve:** como los puntos viajan a la misma rapidez, los disparos en vuelo forman los brazos en espiral de un girasol que se abre. Con `p/q`, una estrella de `q` rayos que se dibuja punta por punta.
  ```
        ·     ·
     ·    @     ·      áureo: brazos que se abren
       ·    ·  ·
  ```
- **Ley o número:** ley: cambia hacia dónde sale, y su forma sale sola (ADR 0033).
- **Escala con el enjambre:** rinde más cuando te rodean y es pésimo contra un enemigo solo.
- **Decisión nueva:** no apuntas: te pones donde el riego pega. Con dos armas, una que apunta y otra que riega es una construcción distinta de dos que apuntan.
- **Cómo apunta:** no usa `intercept` ni el orden de `fₖ` (ADR 0033: "esa arma deja de usar el orden").
- **Precio o contra:** la contra viene adentro: deja de apuntar.
- **Con qué choca:** con N2, N7, N8 y N9: todos dicen hacia dónde sale. Se suma con N1: `n` brazos.
- **Cabe en `WeaponSpec`:** un campo nuevo: `aim: "step"` y `step_angle: ψ`.
- **Fuentes:**
  - Wikipedia, *Golden angle*, https://en.wikipedia.org/wiki/Golden_angle (2026-11-27): el valor `π(3 − √5)` rad ≈ 137,5078° y su papel en la filotaxis.
  - Wikipedia, *Low-discrepancy sequence*, https://en.wikipedia.org/wiki/Low-discrepancy_sequence (2026-11-27): la sucesión `{n·α}` llena el intervalo de forma pareja, y `α = φ − 1` es la de menor discrepancia.
  - Wikipedia, *Fermat's spiral*, https://en.wikipedia.org/wiki/Fermat%27s_spiral (2026-11-27): el modelo de Vogel (1979) del girasol, con `θ = n × 137,508°`. **(No verificado:** el radio `r = c·√n`, porque la raíz se perdió al leer la página).
  - Que los disparos en vuelo formen brazos en espiral es deducción nuestra **(no verificado en un dibujo)**.

#### N7. Apuntar con tu movimiento

- **Fórmula:** `û = R(β)·m̂`, con `m̂` la dirección en que te mueves (la última, si estás quieto; `+x` al empezar) y `β` de la tarjeta: `0` adelante, `π` atrás (una estela), `±π/2` a los lados.
- **Qué hace:** el arma apunta con tu cuerpo, no al enemigo.
- **Cómo se ve:**
  ```
     β = 0:   @ → · · ·       β = π:   · · · ← @ (huyes y dejas un rastro)
  ```
- **Ley o número:** ley.
- **Escala con el enjambre:** igual; con `β = π`, más cuando te persiguen en fila.
- **Decisión nueva:** moverte es apuntar. Huir pasa a ser atacar con `β = π`.
- **Cómo apunta:** sin `intercept`.
- **Precio o contra:** la contra viene adentro: no sigue al enemigo.
- **Con qué choca:** con N6, N8 y N9.
- **Cabe en `WeaponSpec`:** casi: `aim: "motion"` existe, falta el ángulo `β`. La regla de la última dirección ya estaba escrita en la tarea 8 tachada.
- **Fuente:** ADR 0029 (la recta, `aim: motion`).

#### N8. Orden del objetivo

- **Fórmula:** `ranked_target` ordena por otra clave: la distancia al revés (el más lejano), las líneas que le quedan o su `threat`.
- **Qué hace:** cambia a quién le dispara el arma.
- **Cómo se ve:** igual que el punto; cambia el blanco.
- **Ley o número:** ley sin decisión: el arma decide sola, y el jugador no cambia cómo juega.
- **Escala con el enjambre:** igual.
- **Decisión nueva:** ninguna clara. Con "el más lejano", tal vez acercarte para que el lejano no esté tan lejos.
- **Cómo apunta:** `intercept`.
- **Precio o contra:** ninguno.
- **Con qué choca:** con el orden de `fₖ` (ADR 0033): el `k`-ésimo según la nueva clave.
- **Cabe en `WeaponSpec`:** un campo nuevo, `target_order`.
- **Fuente:** ninguna; es una variante de `nearest`.
- **Nota:** es el más cercano a la anti-meta de esta lista. Claude no lo recomienda solo.

#### N9. Centro de masa del enjambre

- **Fórmula:** apunta a `c = (1/N)·Σ pᵢ` de los enemigos dentro de un radio `ρ`, o a los `m` más cercanos.
- **Qué hace:** dispara al medio del grupo, no a un enemigo.
- **Cómo se ve:**
  ```
          ◇ ◇
     @ → · ✕ ◇        ✕: el centro de masa
          ◇
  ```
- **Ley o número:** ley.
- **Escala con el enjambre:** más con grupos compactos. Si te rodean parejo, el centro de masa eres tú y no tiene hacia dónde disparar.
- **Decisión nueva:** sacar al enjambre de un solo lado. Se combina con lo que pasa al pegar (dividirse, estallar).
- **Cómo apunta:** sin anticipación, o con la velocidad media del grupo en `intercept`.
- **Precio o contra:** la contra viene adentro: puede pasar entre enemigos sin tocar a nadie.
- **Con qué choca:** con N6, N7 y N8. El centro de masa sobre el jugador se trata como "sin objetivo", igual que `ranked_target`.
- **Cabe en `WeaponSpec`:** un campo nuevo, `aim: "centroid"` y su radio.
- **Fuente:** la ley de cargas ya usa centros de masa (ADR 0021 y 0027).

#### N10. Cadencia que crece con el enjambre

- **Fórmula:** `cooldown(N) = cooldown₀ / (1 + c·ln(1 + N_ρ))`, con `N_ρ` los enemigos a menos de `ρ`.
- **Qué hace:** el arma dispara más rápido cuantos más enemigos tienes cerca.
- **Cómo se ve:** igual que el punto, más seguido cuando el enjambre se acerca.
- **Ley o número:** ley: la cadencia pasa a ser una función del enjambre (la `x` de `F(x, t, v)` del milestone).
- **Escala con el enjambre:** por definición, y con logaritmo para que no se dispare.
- **Decisión nueva:** dejar que se acerquen para disparar más, o alejarte y perder cadencia.
- **Cómo apunta:** `intercept`.
- **Precio o contra:** la contra viene adentro: con pocos cerca, no gana nada.
- **Con qué choca:** con las perillas de `cooldown` (se multiplican: `cooldown₀` es el de la perilla). Con N12, que fija el ritmo.
- **Cabe en `WeaponSpec`:** un campo nuevo, `crowd_rate` y `crowd_radius`.
- **Fuente:** el milestone 0.3.0 (`F(x, t, v)`), y la sensación de `f₂` (decisión del autor).

#### N11. Cadencia que depende de tu velocidad

- **Fórmula:** `cooldown(s) = cooldown₀ · (1 + c·s/s_max)`, con `s` tu rapidez. Con `c < 0`, disparas más rápido mientras te mueves; con `c > 0`, mientras estás quieto.
- **Qué hace:** ata la cadencia a tu movimiento.
- **Cómo se ve:** igual que el punto.
- **Ley o número:** ley (la `v` de `F(x, t, v)`).
- **Escala con el enjambre:** igual.
- **Decisión nueva:** quedarte quieto para disparar más, con el riesgo de no esquivar, o moverte siempre.
- **Cómo apunta:** `intercept`.
- **Precio o contra:** la contra viene adentro, según el signo.
- **Con qué choca:** con N10 y N12, que también cambian la cadencia.
- **Cabe en `WeaponSpec`:** un campo nuevo, `motion_rate`.
- **Fuente:** el milestone 0.3.0 (`F(x, t, v)`).

#### N12. Ritmo euclidiano

- **Fórmula:** el arma dispara en los golpes de `E(k, 16)`: `k` disparos repartidos lo más parejo posible entre las 16 semicorcheas del compás.
- **Qué hace:** cambia el "cada `cooldown`" por un patrón de ráfagas atado al compás.
- **Cómo se ve:** disparos agrupados que siguen la música.
  ```
     E(5, 16):  x . . x . . x . . x . . x . . .
  ```
- **Ley o número:** ley del "cuándo". Con `k` alto, se acerca a un `cooldown` menor.
- **Escala con el enjambre:** igual.
- **Decisión nueva:** poca: aprendes el ritmo y te mueves entre ráfagas. Su fuerza es que se oye (ADR 0022).
- **Cómo apunta:** `intercept`.
- **Precio o contra:** ninguno.
- **Con qué choca:** con todas las perillas de `cooldown`, porque lo reemplaza: hay que decidir si `k` sale del `cooldown` (como hoy en la música) o lo manda. Con N10 y N11.
- **Cabe en `WeaponSpec`:** un campo nuevo, `rhythm`. El ritmo del arma pasa a mandar sobre el de la música, al revés de hoy.
- **Fuentes:** Wikipedia, *Euclidean rhythm*, https://en.wikipedia.org/wiki/Euclidean_rhythm (2026-11-27); G. Toussaint, *The Euclidean Algorithm Generates Traditional Musical Rhythms*, Bridges 2005, https://cgm.cs.mcgill.ca/~godfried/publications/banff.pdf (citado en el ADR 0029).
- **Variante descartada:** el polirritmo `p:q` (dos grillas a la vez). Se oye, pero en el juego es "a veces disparas doble": número. Fuente: Wikipedia, *Polyrhythm*, https://en.wikipedia.org/wiki/Polyrhythm (2026-11-27).

#### N13. Origen en el último golpe

- **Fórmula:** el disparo nace en el punto donde pegó el último disparo de esa arma, si fue hace menos de `T` segundos; si no, en el jugador.
- **Qué hace:** el arma salta dentro del enjambre, de golpe en golpe.
- **Cómo se ve:**
  ```
     @ → ✕ → ✕ → ✕        cada ✕ es un golpe, y desde ahí sale el siguiente
  ```
- **Ley o número:** ley.
- **Escala con el enjambre:** más en enjambres densos, donde el siguiente enemigo queda cerca del golpe. Con enemigos sueltos, vuelve al jugador.
- **Decisión nueva:** poca: el arma trabaja sola dentro del grupo, así que te conviene mantener al enjambre junto.
- **Cómo apunta:** `ranked_target` desde el último golpe, con `intercept` desde ahí.
- **Precio o contra:** sobre el enemigo, porque es fuerte contra los drops densos.
- **Con qué choca:** con los conceptos de Pega que encadenan (rebote, división): se parece y hay que elegir. Con N9.
- **Cabe en `WeaponSpec`:** un campo nuevo, `origin: "player" | "last_hit"`, y la memoria del último golpe en el arma.
- **Fuente:** ninguna; es de diseño.

#### N14. Dispersión al azar

- **Fórmula:** `û = R(ε)·û`, con `ε ~ 𝒩(0, σ²)` sacado de la `Random` del mundo.
- **Qué hace:** el punto sale torcido.
- **Cómo se ve:** los disparos se abren en un cono.
- **Ley o número:** número: es una contra, no una mejora.
- **Escala con el enjambre:** más con grupos grandes, donde un disparo torcido igual pega a otro.
- **Decisión nueva:** ninguna.
- **Cómo apunta:** `intercept` más el error.
- **Precio o contra:** sirve de **contra en el arma** para otras tarjetas, como "N1 a cambio de dispersión".
- **Con qué choca:** con el determinismo, no: sale de `World.rng` (ADR 0005), pero cada disparo saca un número, así que cambia las manos siguientes respecto de una partida sin dispersión. Las dos siguen siendo repetibles.
- **Cabe en `WeaponSpec`:** un campo nuevo, `scatter`.
- **Fuente:** ninguna.

#### Lo que se revisó en Nace y quedó fuera

- **Los primos:** disparar en los compases o semicorcheas primos. Se oye raro y en el juego es solo "a veces disparas": número.
- **Fibonacci en la cantidad:** el disparo `m` suelta `F(m mod c)` puntos. Es "más disparos" con otro orden: número. Fibonacci queda en N6, por el ángulo áureo.
- **La ráfaga:** `m` disparos seguidos y una pausa. Es un caso de N12 con otro `k`.
- **El arma nueva `fₖ`:** ya está construida (#126).

### Viaja: la trayectoria

Las perillas que ya existen (`v`, `cooldown` y `reach`) son números y no se repiten aquí.

| | Concepto | Ley o número | Se ve claro | Escala con el enjambre | Cabe en `WeaponSpec` |
|---|---|---|---|---|---|
| V1 | Armónico: la onda | ley | sí | igual | sí, ya funciona |
| V2 | Vaivén: avanza a tirones | ley | a medias | igual | campo nuevo |
| V3 | Giro: la espiral | ley | sí | más cuando te rodean | sí, `frame` y `spin` |
| V4 | `d/dt`: la mina | ley | sí | más cuando vienen a ti | sí, `degree`, más una duración |
| V5 | `∫dt`: acelera | ley | sí | más con enemigos lejos | sí, `degree` |
| V6 | Anclar al jugador | ley | sí | igual | campo nuevo |
| V7 | Bumerán | ley | sí | más con enemigos en fila | pide cambiar el avance |
| V8 | Rizo: la trocoide | ley | sí | más con grupos | campo nuevo |
| V9 | Curva: la parábola | ley | sí | igual | campo nuevo |
| V10 | Persecución | ley sin decisión | sí | igual | pide estado en la bala |
| V11 | Carga: la bala siente al enjambre | ley | sí | más con muchos | pide estado en la bala |
| V12 | Crece mientras viaja | ley de lo que viaja | sí | más con grupos | campo nuevo y otro choque |

**Decisión del autor (2026-11-27):** entran todos. Claude no recomendaba V2 solo.

#### V1. Armónico: la onda

- **Fórmula:** `y(t) = A·sin(k·t + φ)` por la normal, sumado al avance: `p(t) = p₀ + a(t)·û + y(t)·n̂`.
- **Qué hace:** el punto ondula de lado mientras avanza.
- **Cómo se ve:**
  ```
     @ ∿∿∿∿∿∿ →
  ```
- **Ley o número:** ley. Otra tarjeta suma un segundo armónico (M2 del ADR 0029), y `k` sale de una lista por semilla.
- **Escala con el enjambre:** igual. Con `A` grande, barre más ancho y falla más a los enemigos chicos.
- **Decisión nueva:** poca: cambia la forma. Su fuerza está en lo que combina: con N5 da la trenza, y con V3, una espiral que ondula.
- **Cómo apunta:** `intercept` sigue sirviendo, porque el avance por `û` no cambia; la onda se desvía a lo más `A`.
- **Precio o contra:** la contra viene adentro: falla a lo que está justo en la recta si `A` es grande.
- **Con qué choca:** con nada; es la base de N5.
- **Cabe en `WeaponSpec`:** sí, `harmonics`. `check_weapons` no lo rechaza y `projectile_offset` ya lo calcula: falta solo la tarjeta de término.
- **Fuente:** ADR 0029 (M2).

#### V2. Vaivén: avanza a tirones

- **Fórmula:** el armónico va por `û` en vez de la normal: `x(t) = a(t) + A·sin(k·t)`. Si `A·k > v`, a ratos retrocede.
- **Qué hace:** el punto avanza, frena y vuelve un poco, como un resorte.
- **Cómo se ve:** igual que el punto, pero con tirones; en una captura quieta no se distingue.
- **Ley o número:** ley.
- **Escala con el enjambre:** igual.
- **Decisión nueva:** ninguna clara.
- **Cómo apunta:** `intercept` con la rapidez media `v` se equivoca hasta `A`.
- **Precio o contra:** ninguno.
- **Con qué choca:** con V1, por el armónico: hoy un armónico solo puede ir de lado (cartesiano) o por el radio (polar).
- **Cabe en `WeaponSpec`:** con el marco polar y `Ω = 0` ya da esto, pero entonces no puede tener a la vez una onda de lado. Un campo `axis` por armónico (`"normal"` o `"along"`) resuelve V2, V8 y V9.
- **Fuente:** ninguna; es el armónico en el otro eje.
- **Nota:** de esta lista, es el que menos se ve. Claude no lo recomienda solo.

#### V3. Giro: la espiral

- **Fórmula:** en el marco polar, `r(t) = a(t)` y `θ(t) = θ₀ + Ω·t`. Con el avance de grado 1 es la espiral de Arquímedes, `r = (v/Ω)·(θ − θ₀)`, con vueltas separadas por `2π·v/Ω` (deducido de la fórmula).
- **Qué hace:** el punto sale girando y se aleja en espiral.
- **Cómo se ve:**
  ```
        ╭──╮
       │ @╮ │
        ╰─╯ ╯ →
  ```
- **Ley o número:** ley.
- **Escala con el enjambre:** más cuando te rodean, porque recorre toda la vuelta.
- **Decisión nueva:** el arma ya no pega en línea recta: te conviene estar a una distancia en que la espiral cruce al enjambre.
- **Cómo apunta:** `intercept` no sirve. Se propone adelantar el giro: si el enemigo está a distancia `D`, la espiral llega en `t* = D/v`, así que `θ₀ = θ_enemigo − Ω·t*`. Así el punto le llega después de girar.
- **Precio o contra:** la contra viene adentro: tarda más en llegar.
- **Con qué choca:** con V6: hoy la espiral gira en torno a donde nació, no en torno a ti (ver V6).
- **Cabe en `WeaponSpec`:** sí, `frame: "polar"` y `spin`. Hoy `check_weapons` rechaza el marco polar.
- **Fuente:** MathWorld, *Archimedes' Spiral*, https://mathworld.wolfram.com/ArchimedesSpiral.html (2026-11-27). La fórmula de la página es una imagen y no se pudo leer; la separación de las vueltas la deducimos nosotros.

#### V4. `d/dt`: la mina

- **Fórmula:** el avance baja de grado: `a(t) = v·t → v·τ`. El punto aparece a `v·τ` de donde nació y se queda ahí.
- **Qué hace:** el disparo deja una mina quieta. Con V3, la mina gira en un círculo de radio `v·τ`. Con V3 y V6, gira en torno a ti: un satélite.
- **Cómo se ve:**
  ```
     @      ·        la mina, a v·τ, quieta
  ```
- **Ley o número:** ley.
- **Escala con el enjambre:** más cuando el enjambre viene hacia ti, porque se mete en las minas.
- **Decisión nueva:** llevar al enjambre por donde dejaste las minas, o quedarte cerca del satélite.
- **Cómo apunta:** hacia tu enemigo, para que la mina quede en su camino; sin `intercept`.
- **Precio o contra:** la contra viene adentro: deja de alcanzar lejos (ADR 0029: "`d/dt` defiende, pero deja de matar").
- **Con qué choca:**
  - **Nunca termina:** el avance queda en `v·τ` (150) y nunca llega a `reach` (700). Pide una duración, del momento Termina.
  - **Salta:** en `t = 0` ya está a `v·τ`, así que la bala aparece allá sin cruzar lo que hay en el medio.
  - Con V5, se deshacen uno al otro (ADR 0029).
- **Cabe en `WeaponSpec`:** sí, `advance.degree: 0`, más una duración que hoy no existe. Hoy `check_weapons` lo rechaza.
- **Fuente:** ADR 0029 (M3).

#### V5. `∫dt`: acelera

- **Fórmula:** el avance sube de grado: `a(t) = v·t²/(2τ)`. Su rapidez es `v·t/τ`: igual a `v` en `t = τ`, y después más.
- **Qué hace:** el punto sale lento y se dispara.
- **Cómo se ve:** `@ ·  ·    ·        ·              ·  →` (cada paso, más lejos que el anterior).
- **Ley o número:** ley.
- **Escala con el enjambre:** más con enemigos lejos; contra los de cerca, llega tarde.
- **Decisión nueva:** mantener la distancia, porque de lejos pega más rápido.
- **Cómo apunta:** `intercept` supone rapidez fija. Hay que resolver `|d + vₑ·t| = v·t²/(2τ)`, que es de cuarto grado: con un método numérico, como bisección.
- **Precio o contra:** la contra viene adentro: lento de cerca.
- **Con qué choca:** con V4 (se deshacen).
- **Cabe en `WeaponSpec`:** sí, `advance.degree: 2`. Hoy `check_weapons` lo rechaza.
- **Fuente:** ADR 0029 (M3).

#### V6. Anclar al jugador

- **Fórmula:** el origen de la trayectoria te sigue: `p(t) = jugador(t) + desplazamiento(t)`, en vez de `p₀ + desplazamiento(t)`.
- **Qué hace:** tus disparos se mueven contigo. Solo, el punto hereda tu movimiento; con V3, la espiral sale de ti aunque corras; con V3 y V4, es el satélite que te orbita.
- **Cómo se ve:**
  ```
       ·
     ·   ·      V3 + V4 + V6: satélites que te siguen
       @   →
     ·   ·
  ```
- **Ley o número:** ley.
- **Escala con el enjambre:** igual.
- **Decisión nueva:** el ataque se arrastra contigo: moverte es mover el ataque.
- **Cómo apunta:** `intercept` con la velocidad relativa: la del enemigo menos la tuya.
- **Precio o contra:** ninguno.
- **Con qué choca:** con V10 y V11, que tienen estado propio y no se sabe qué sería "anclarlos".
- **Cabe en `WeaponSpec`:** un campo nuevo, `anchor: "birth" | "player"`. La tarea 9 tachada ya definía la espiral "centrada en el jugador de ahora".
- **Fuente:** ninguna; es el marco de la fórmula.

#### V7. Bumerán

- **Fórmula:** `a(t) = v·t·(1 − t/T)`. Llega a `v·T/4` en `T/2` y vuelve a donde nació en `T`. Con V6, vuelve a ti.
- **Qué hace:** el punto va y vuelve, y puede pegar en la ida y en la vuelta.
- **Cómo se ve:**
  ```
     @ ⇄ ·
  ```
- **Ley o número:** ley.
- **Escala con el enjambre:** más con enemigos en fila, porque los cruza dos veces.
- **Decisión nueva:** ponerte para que la vuelta pase por el enjambre; con V6, la vuelta te sigue.
- **Cómo apunta:** `intercept` para la ida, si el enemigo está a menos de `v·T/4`.
- **Precio o contra:** la contra viene adentro: no llega lejos.
- **Con qué choca:** con V4 y V5.
- **Cabe en `WeaponSpec`:** no: es un avance de dos términos (`v·t − v·t²/T`), y `AdvanceSpec` tiene uno solo. Si el avance pasa a ser un polinomio, `a(t) = Σ cᵢ·tⁱ`, el bumerán cabe y `d/dt` y `∫dt` actúan término a término. Es un argumento para la estructura.
- **Fuente:** ninguna; es una parábola en `t`.

#### V8. Rizo: la trocoide

- **Fórmula:** al avance se le suma un vector que gira: `x(t) = v·t − R·sin(ω·t)` y `y(t) = R·(1 − cos(ω·t))`. Es la curva de un punto pegado a una rueda que rueda. Si `R > v/ω`, la curva hace rulos (deducido: es el caso *prolate* de MathWorld).
- **Qué hace:** el punto avanza dando vueltas, como un resorte visto de lado.
- **Cómo se ve:**
  ```
     @ ─ᘓᘓᘓᘓ→
  ```
- **Ley o número:** ley.
- **Escala con el enjambre:** más con grupos, porque los rulos barren más ancho.
- **Decisión nueva:** poca: cambia la forma.
- **Cómo apunta:** `intercept` con la rapidez media `v`, con un error de hasta `2R`.
- **Precio o contra:** ninguno.
- **Con qué choca:** con V1 y V2: es un armónico en cada eje, desfasados un cuarto. Sumar armónicos así da los epiciclos y, en el límite, cualquier curva: la serie de Fourier.
- **Cabe en `WeaponSpec`:** con el campo `axis` por armónico de V2: son dos armónicos, uno por eje.
- **Fuentes:**
  - MathWorld, *Trochoid*, https://mathworld.wolfram.com/Trochoid.html (2026-11-27): `x = aφ − b·sin φ`, `y = a − b·cos φ`, y con `b > a` es una cicloide *prolate*. Que haga rulos lo deducimos; la página no lo dice.
  - Wikipedia, *Deferent and epicycle*, https://en.wikipedia.org/wiki/Deferent_and_epicycle (2026-11-27): cualquier trayectoria se puede representar con epiciclos, porque son una serie de Fourier compleja.

#### V9. Curva: la parábola

- **Fórmula:** un avance de grado 2 por la normal: `y(t) = c·t²/(2τ)`. El punto se tuerce hacia un lado, como una pelota con efecto.
- **Qué hace:** el disparo hace una curva. Con N5, dos curvas que se cierran sobre el enemigo como una pinza.
- **Cómo se ve:**
  ```
            ↗
     @ ─ ─╯       con N5:  @ ⊂ ◇  (dos arcos que se juntan)
  ```
- **Ley o número:** ley.
- **Escala con el enjambre:** igual.
- **Decisión nueva:** poca: la pinza esquiva a los enemigos que están en el medio.
- **Cómo apunta:** hay que girar `û` para que la parábola pase por el enemigo: el ángulo sale de resolver la curva en el tiempo de llegada.
- **Precio o contra:** la contra viene adentro: tarda más.
- **Con qué choca:** con V10, que también curva.
- **Cabe en `WeaponSpec`:** con un avance por eje (el polinomio de V7 más el `axis` de V2).
- **Fuente:** ninguna; es el tiro parabólico.

#### V10. Persecución

- **Fórmula:** la bala corrige su rumbo en cada paso hacia su enemigo: `ṗ = v·(q − p)/|q − p|`, con `q` la posición del enemigo ahora. Con un giro máximo `ω_max`, la curva se ve más.
- **Qué hace:** el punto persigue a su enemigo hasta pegarle.
- **Cómo se ve:** balas que se curvan siguiendo a un enemigo que esquiva.
- **Ley o número:** ley sin decisión, como N8: el arma decide sola.
- **Escala con el enjambre:** igual. Rinde más contra enemigos rápidos, que hoy se escapan.
- **Decisión nueva:** ninguna.
- **Cómo apunta:** no necesita `intercept`.
- **Precio o contra:** presupuesto, porque casi no falla. O el giro máximo como contra en el arma.
- **Con qué choca:**
  - **Con el diseño de `terms.py`:** hoy la posición es una función pura del `spec` y de `t`. La persecución no tiene una fórmula cerrada en general, así que hay que integrarla paso a paso, con la bala guardando su posición y su rumbo.
  - Con V1, V3 y V8: ¿la onda se suma al rumbo que cambia? Hay que decidirlo.
  - Con V6 y V11.
- **Cabe en `WeaponSpec`:** no: pide estado en la bala, un cambio de estructura.
- **Fuente:** MathWorld, *Pursuit Curve*, https://mathworld.wolfram.com/PursuitCurve.html (2026-11-27): la estudió Bouguer en 1732, y solo tiene una forma cerrada en casos especiales.

#### V11. Carga: la bala siente al enjambre

- **Fórmula:** la bala tiene una carga `q` y siente la ley de cargas del ADR 0021, la misma que mueve a los enemigos y a la experiencia: `p̈ = Σ F(enemigo, bala)`, integrada paso a paso.
- **Qué hace:** el punto se desvía hacia los enemigos (o los esquiva, con el otro signo), y puede dar la vuelta a uno grande como una honda.
- **Cómo se ve:** balas que se tuercen hacia el enjambre y lo rodean.
- **Ley o número:** ley, y es la física del juego.
- **Escala con el enjambre:** más con muchos, porque hay más que la atraiga.
- **Decisión nueva:** poca.
- **Cómo apunta:** `intercept` al disparar, y después manda la física.
- **Precio o contra:** ninguno; con muchos enemigos se puede quedar orbitando sin pegar.
- **Con qué choca:** con V10 (los dos tuercen) y con el diseño de `terms.py`, como V10.
- **Cabe en `WeaponSpec`:** no: pide estado en la bala. Puede reusar la ley de `world/charges`.
- **Fuente:** ADR 0021.

#### V12. Crece mientras viaja

- **Fórmula:** el radio del punto crece con el tiempo: `s(t) = s₀ + c·t`.
- **Qué hace:** el disparo es una bola de nieve: chico al salir y grande lejos.
- **Cómo se ve:** `@ · ∘ ○ ◯ →`
- **Ley o número:** ley de lo que viaja: cambia qué es pegar.
- **Escala con el enjambre:** más con grupos, sobre todo si atraviesa (Pega).
- **Decisión nueva:** mantener la distancia para que llegue grande.
- **Cómo apunta:** `intercept`.
- **Precio o contra:** ninguno.
- **Con qué choca:** con el choque: hoy la bala es un tramo que cruza líneas (`Enemy.hit_by`, ADR 0020). Con radio, el choque pasa a ser un círculo que barre, otra función de choque.
- **Cabe en `WeaponSpec`:** `payload.size` existe (hoy rechazado), y el crecimiento es un campo nuevo.
- **Fuente:** ninguna.

#### Lo que se revisó en Viaja y quedó fuera

- **La inversión en un círculo:** convierte una recta que no pasa por el centro en un círculo que sí pasa, así que el punto daría una vuelta y volvería a ti. Pero el punto nace en el centro, y ahí la inversión degenera: viene desde el infinito. Solo funcionaría con N4, y cuesta visualizarlo. Fuente: MathWorld, *Inversion*, https://mathworld.wolfram.com/Inversion.html (2026-11-27).
- **La espiral logarítmica:** `a(t) = v·τ·(e^{t/τ} − 1)`, que es la suma de todas las integrales. En pantalla se parece a V5 con V3. Fuente: MathWorld, *Logarithmic Spiral*, https://mathworld.wolfram.com/LogarithmicSpiral.html (2026-11-27).
- **Lissajous:** dos armónicos, uno por eje, con frecuencias distintas. Es V8 con otros valores: entra si entra V8.
- **La onda cuadrada o triangular:** son sumas de armónicos impares. Con `A` chico, no se distinguen de V1.
- **El caos (Lorenz) y el paseo al azar:** no se visualizan claro, y el paseo saca un número de `World.rng` en cada paso.
- **La rapidez según la distancia al enemigo:** es un número.

#### Lo que Viaja le pide a la estructura

1. **Un eje por armónico** (`axis`): V2, V8 y V9.
2. **El avance como polinomio,** `a(t) = Σ cᵢ·tⁱ`: V7 y V9, y deja a `d/dt` y `∫dt` como operaciones término a término.
3. **El anclaje** (`anchor`): V6.
4. **Una duración** que no dependa del avance: V4. Viene de Termina.
5. **Estado en la bala,** con integración paso a paso: V10 y V11. Es el cambio más grande: la posición deja de ser una función pura de `t`.
6. **Un choque con radio:** V12.

### Pega: qué pasa al golpear

Hoy, al cruzar una línea, la bala la quita y desaparece (`ProjectileWeapon._strike`). El golpe se mide en el marco del enemigo, así que se sabe qué línea fue, en qué punto y con qué dirección llegó la bala.

| | Concepto | Ley o número | Se ve claro | Escala con el enjambre | Cabe en `WeaponSpec` |
|---|---|---|---|---|---|
| P1 | Atravesar | número que se ve | sí | más con filas | sí, `payload.pierce` |
| P2 | Cortar las vecinas | número que se ve | sí | igual | sí, `payload.lines`, más una regla |
| P3 | Dividirse al pegar | ley | sí | más con enjambres densos | campo nuevo |
| P4 | Rebotar en la línea | ley | sí | más con enjambres densos | campo nuevo |
| P5 | Saltar al vecino más cercano | ley | sí | más con enjambres densos | campo nuevo |
| P6 | Refractarse | ley | a medias | más con filas | campo nuevo |
| P7 | Empujar y hacer girar | ley | sí | igual | campo nuevo y una función del enemigo |
| P8 | Quedarse orbitando al enemigo | ley | sí | menos con muchos | campo nuevo |
| P9 | Polarizar al enemigo | ley | a medias | más con muchos | campo nuevo |
| P10 | Cortar al enemigo en dos | ley | sí | igual | pide figuras nuevas |

**Decisión del autor (2026-11-27):** entran todos menos P9 y P10. Claude no recomendaba P6 ni P10.

#### P1. Atravesar

- **Fórmula:** la bala sigue después de pegar, hasta `pierce + 1` enemigos distintos.
- **Qué hace:** un disparo pasa a través de una fila.
- **Cómo se ve:** `@ · → ◇ → ◇ → ◇`
- **Ley o número:** número, pero se ve.
- **Escala con el enjambre:** más con filas y formaciones.
- **Decisión nueva:** ponerte en línea con la fila.
- **Cómo apunta:** `intercept`.
- **Precio o contra:** ninguno.
- **Con qué choca:**
  - Con P3, P4 y P5: ¿la bala sigue derecho, se divide o rebota? Se propone que atravesar se gaste primero.
  - **Un mismo enemigo no cuenta dos veces:** la bala guarda a quién ya pegó, porque en el paso siguiente puede volver a cruzar otra línea del mismo.
- **Cabe en `WeaponSpec`:** sí, `payload.pierce`. Hoy `check_weapons` lo rechaza. Pide guardar en la bala los enemigos ya golpeados.
- **Fuente:** ADR 0029 (lo que viaja).

#### P2. Cortar las vecinas

- **Fórmula:** el golpe quita la línea que cruzó y `lines − 1` más, alternando entre sus vecinas en la figura (la siguiente y la anterior en el orden de las aristas).
- **Qué hace:** un golpe arranca un trozo del polígono, no una línea.
- **Cómo se ve:** al hexágono le falta un tramo de tres lados seguidos.
- **Ley o número:** número, pero se ve.
- **Escala con el enjambre:** igual; rinde más contra los de muchas líneas.
- **Decisión nueva:** ninguna.
- **Cómo apunta:** `intercept`.
- **Precio o contra:** ninguno.
- **Con qué choca:** con las figuras abiertas y con el giro (ADR 0027): quitar varias líneas corre el centro de masa más de una vez, en orden. Con P10.
- **Cabe en `WeaponSpec`:** sí, `payload.lines`, más la regla de cuáles quita. Hoy `check_weapons` lo rechaza.
- **Fuente:** ADR 0029 (lo que viaja).

#### P3. Dividirse al pegar

- **Fórmula:** al pegar, la bala suelta `m` hijas desde el punto del golpe, en `Cₘ` alrededor de su dirección: `ûⱼ = R(2πj/m)·û`. Cada hija es una bala nueva, con el mismo `spec` y `t = 0`. Con profundidad `d`, las hijas también se dividen, hasta `d` generaciones: a lo más `mᵈ` puntos por disparo.
- **Qué hace:** cada golpe revienta en un abanico de puntos que siguen pegando.
- **Cómo se ve:**
  ```
              ·
     @ → ◇ ✕ ─ ·        m = 3
              ·
  ```
- **Ley o número:** ley: cada golpe es un disparo nuevo.
- **Escala con el enjambre:** más con enjambres densos, donde las hijas encuentran a otro enseguida. Es la forma más visible de "más enemigos, más ataques": crece porque pegó, no por un contador.
- **Decisión nueva:** mantener al enjambre junto en vez de dispersarlo.
- **Cómo apunta:** la madre con `intercept`; las hijas, a ciegas.
- **Precio o contra:** presupuesto, porque crece como `mᵈ`.
- **Con qué choca:**
  - Con P1, P4 y P5: todos dicen qué sigue después del golpe.
  - Con el rendimiento: `mᵈ` sin tope (ADR 0029). Es trabajo del #42, y un caso de foco como `n = 64` en `Cₙ`.
  - Las hijas no deben pegarle al mismo enemigo en el paso en que nacen: nacen en la línea que la madre acaba de quitar.
- **Cabe en `WeaponSpec`:** un campo nuevo, `split: (m, d)`. La bala guarda su generación.
- **Fuentes:** Wikipedia, *Fractal canopy*, https://en.wikipedia.org/wiki/Fractal_canopy (2026-11-27): un árbol en que cada tramo se parte en dos al final. Que crezca como `mᵈ` lo deducimos nosotros. El "dividirse al pegar" es una idea de partida del plan (tarea 8b).

#### P4. Rebotar en la línea

- **Fórmula:** al pegar, la bala sale reflejada respecto de la línea que golpeó: `û' = û − 2(û·n̂)·n̂`, con `n̂` la normal de esa línea. Rebota hasta `b` veces.
- **Qué hace:** el punto rebota como una bola de billar en los lados de los enemigos.
- **Cómo se ve:**
  ```
     @ → ╲◇
          ↘ ◇        el ángulo de salida es el de entrada
  ```
- **Ley o número:** ley, y usa la geometría de los enemigos: cómo rebota depende de qué lado golpeó.
- **Escala con el enjambre:** más con enjambres densos.
- **Decisión nueva:** buscar ángulos en que el rebote caiga sobre el grupo.
- **Cómo apunta:** la primera con `intercept`; los rebotes, por la ley de la reflexión.
- **Precio o contra:** ninguno.
- **Con qué choca:** con P1, P3 y P5. Con el giro del enemigo: la normal se toma con la pose de ahora.
- **Cabe en `WeaponSpec`:** un campo nuevo, `bounces`. La bala renace en el punto del golpe con `û'` (ver "Lo que Pega le pide a la estructura").
- **Fuente:** Wikipedia, *Specular reflection*, https://en.wikipedia.org/wiki/Specular_reflection (2026-11-27): el ángulo de reflexión es igual al de incidencia, y en vectores, `d̂ₛ = d̂ᵢ − 2·d̂ₙ(d̂ₙ·d̂ᵢ)`.

#### P5. Saltar al vecino más cercano

- **Fórmula:** al pegar, la bala renace en el punto del golpe y apunta, con `intercept`, al enemigo más cercano a ese punto que todavía no golpeó. Salta hasta `c` veces, y solo si el vecino está a menos de `ρ`.
- **Qué hace:** un disparo encadena enemigos, como un rayo.
- **Cómo se ve:** `@ → ◇ ↗ ◇ → ◇ ↘ ◇` (la bala dibuja el camino entre vecinos).
- **Ley o número:** ley.
- **Escala con el enjambre:** más con enjambres densos; con enemigos sueltos, `ρ` la corta.
- **Decisión nueva:** mantener al enjambre junto.
- **Cómo apunta:** `intercept` en cada salto.
- **Precio o contra:** ninguno.
- **Con qué choca:** con N13 (origen en el último golpe), que hace algo parecido entre disparos y no dentro de uno. Con P1, P3 y P4.
- **Cabe en `WeaponSpec`:** un campo nuevo, `chain: (c, ρ)`. La bala guarda a quién ya pegó, como en P1.
- **Fuente:** Wikipedia, *Nearest neighbor graph*, https://en.wikipedia.org/wiki/Nearest_neighbor_graph (2026-11-27): cada punto va hacia el que tiene más cerca. El camino de la cadena es un recorrido de ese grafo, sin repetir.

#### P6. Refractarse

- **Fórmula:** la bala atraviesa la línea y se tuerce con la ley de Snell, `sin θ₂ = sin θ₁ / η`, con `θ` medido desde la normal de la línea y `η` de la tarjeta. Si `sin θ₂` pasara de 1, se refleja (reflexión total).
- **Qué hace:** el punto cruza al enemigo y sale desviado, como la luz en el agua.
- **Cómo se ve:** `@ ──◇╲` (entra derecho y sale torcido). Al ojo, se confunde con un rebote.
- **Ley o número:** ley.
- **Escala con el enjambre:** más con filas.
- **Decisión nueva:** poca.
- **Cómo apunta:** `intercept`.
- **Precio o contra:** ninguno.
- **Con qué choca:** con P1, de la que es una versión que tuerce, y con P4, que toma en la reflexión total.
- **Cabe en `WeaponSpec`:** un campo nuevo, `refraction: η`.
- **Fuente:** Wikipedia, *Snell's law*, https://en.wikipedia.org/wiki/Snell%27s_law (2026-11-27): `n₁·sin θ₁ = n₂·sin θ₂`, y la reflexión total cuando el seno tendría que pasar de 1.

#### P7. Empujar y hacer girar

- **Fórmula:** el golpe le da al enemigo un impulso `J = μ·v·û` en el punto del golpe: `Δv = J/M` y `Δω = (r × J)/I`, con `r` desde su centro de masa e `I` su momento de inercia.
- **Qué hace:** los golpes empujan a los enemigos y, si pegan de lado, los hacen girar.
- **Cómo se ve:** enemigos que retroceden y dan vueltas al recibir los golpes.
- **Ley o número:** ley, y usa el cuerpo rígido del ADR 0027.
- **Escala con el enjambre:** igual; con un enjambre denso, el empujado choca a los demás por la ley de cargas.
- **Decisión nueva:** empujar al enjambre lejos o a un lado; pegar en el borde para hacerlo girar.
- **Cómo apunta:** `intercept`.
- **Precio o contra:** la contra viene adentro: un enemigo empujado lejos tarda más en morir.
- **Con qué choca:** con los enemigos anclados (`anchored`) y las acciones que fijan la velocidad o el giro (`world/actions.py`): mandan ellas o el impulso.
- **Cabe en `WeaponSpec`:** un campo nuevo, `push: μ`. `Enemy` necesita una función `apply_impulse` y un momento de inercia, que hoy no tiene.
- **Fuentes:** Wikipedia, *Impulse (physics)*, https://en.wikipedia.org/wiki/Impulse_(physics) (2026-11-27): `J = Δp`. **(No verificado:** `Δω = (r × J)/I`, porque la página no habla del cuerpo rígido; es mecánica estándar).

#### P8. Quedarse orbitando al enemigo

- **Fórmula:** al pegar, la bala pasa a girar en torno al enemigo: `p(t) = c_enemigo(t) + ρ·(cos Ωt, sin Ωt)`, con `ρ` un poco mayor que su radio. En cada vuelta cruza sus líneas y le quita una, hasta que muere; después desaparece.
- **Qué hace:** el disparo se pega al enemigo y lo muele.
- **Cómo se ve:** un punto dando vueltas alrededor de un polígono que va perdiendo lados.
- **Ley o número:** ley: es V6 con el ancla en el enemigo.
- **Escala con el enjambre:** menos con muchos: una bala se dedica a uno. Rinde contra los grandes y el jefe.
- **Decisión nueva:** dejar las balas en los grandes y esquivar al resto.
- **Cómo apunta:** `intercept`.
- **Precio o contra:** la contra viene adentro.
- **Con qué choca:** con P1, P3, P4 y P5. Con V6 comparte el campo `anchor`.
- **Cabe en `WeaponSpec`:** con el `anchor` de V6, más `"enemy"`.
- **Fuente:** ninguna.

#### P9. Polarizar al enemigo

- **Fórmula:** el enemigo golpeado invierte el signo de su carga por `T` segundos. Con la ley del ADR 0021, atrae al enjambre en vez de repelerlo.
- **Qué hace:** el golpeado se vuelve un imán, y el enjambre se amontona a su alrededor.
- **Cómo se ve:** a medias: el enjambre se junta en torno a un enemigo; se lee mejor si el golpeado se marca.
- **Ley o número:** ley, con la física del juego.
- **Escala con el enjambre:** más con muchos.
- **Decisión nueva:** polarizar y después usar P3 o P5, que rinden en grupos densos.
- **Cómo apunta:** `intercept`.
- **Precio o contra:** la contra viene adentro: un enjambre amontonado también es más peligroso.
- **Con qué choca:** con la carga del jugador (ADR 0029, fuera del ataque).
- **Cabe en `WeaponSpec`:** un campo nuevo, `polarize: T`. `Enemy` necesita guardar un signo con duración.
- **Fuente:** ADR 0021.

#### P10. Cortar al enemigo en dos

- **Fórmula:** el camino de la bala, prolongado, parte al polígono: las líneas de cada lado de la recta pasan a ser dos enemigos, que se separan como cuerpos rígidos.
- **Qué hace:** el disparo rebana.
- **Cómo se ve:** un hexágono que se abre en dos mitades que salen girando.
- **Ley o número:** ley.
- **Escala con el enjambre:** igual; con enemigos grandes, multiplica a los chicos.
- **Decisión nueva:** poca.
- **Cómo apunta:** `intercept`.
- **Precio o contra:** la contra viene adentro: deja más enemigos, aunque más chicos.
- **Con qué choca:** con `split_into`, que ya parte a algunos al morir (decisión 71 de la spec de la 0.2.0), y con P2.
- **Cabe en `WeaponSpec`:** el campo sí (`slice`), pero el mundo no: hoy un enemigo es un `EnemySpec` del balance, y las mitades serían figuras nuevas que no están en él. Es el concepto más caro de esta lista.
- **Fuente:** ninguna.

#### Lo que se revisó en Pega y quedó fuera

- **La explosión en área:** un círculo que daña todo lo que toca no es un punto (ADR 0033). P3 con `m` grande y poco alcance da algo parecido con puntos.
- **El contagio:** que los vecinos también pierdan una línea. Es daño en área, por la misma razón.
- **Congelar o frenar al enemigo:** es un número con duración, y se ve poco. Queda como precio sobre el enemigo (M8), con el signo contrario.
- **El crítico:** un golpe que al azar quita más líneas. Es un número y gasta `World.rng`.
- **Elegir qué línea quita** (la opuesta, la que mira al jugador): no se ve qué cambió.
- **La línea que sale disparada:** la línea quitada vuela y daña. Es un segmento, no un punto (ADR 0033).

#### Lo que Pega le pide a la estructura

1. **Renacer en el golpe.** P3, P4, P5 y P6 se escriben igual: al pegar, la bala muere y nacen una o más balas en el punto del golpe, con una dirección nueva y `t = 0`. Así la posición sigue siendo una función pura de `t` (`terms.py`), sin el estado de V10 y V11. La bala solo guarda su generación y a quién ya pegó.
2. **Un orden fijo entre lo que sigue al golpe:** atravesar, después rebotar o refractarse, después saltar, y al final dividirse. Como los operadores del ADR 0029, el orden no depende de cuándo se tomó cada tarjeta.
3. **Funciones nuevas del enemigo:** un impulso (P7), un signo de carga con duración (P9) y quitar varias líneas en orden (P2).
4. **El ancla en el enemigo** (P8), que extiende el `anchor` de V6.
5. **Figuras que no están en el balance** (P10).

### Termina: qué pasa al final

Hoy la bala desaparece cuando su avance llega a `reach` (`Bullet.expired`), y no deja nada.

| | Concepto | Ley o número | Se ve claro | Escala con el enjambre | Cabe en `WeaponSpec` |
|---|---|---|---|---|---|
| T1 | Duración | número que habilita | — | igual | campo nuevo |
| T2 | Estallar al terminar | ley | sí | más cuando te rodean | campo nuevo |
| T3 | Volver a ti | ley | sí | más con enemigos en fila | campo nuevo |
| T4 | Frenar y quedarse | ley | sí | más cuando vienen a ti | campo nuevo |
| T5 | Reaparecer por el otro lado | ley | a medias | más cuando te rodean | campo nuevo |
| T6 | Dejar un rastro | ley | sí | más cuando te persiguen | campo nuevo |
| T7 | Los vértices del que muere | ley | sí | más con enjambres densos | campo nuevo |

**Decisión del autor (2026-11-27):** entran T2 a T6. Quedan fuera T1 y T7. Claude no recomendaba T5 solo.

**T1 como dato, no como tarjeta** *(propuesta de Claude)*: V4, P8, T4 y T6 no terminan sin una duración. La duración queda como un campo del arma que fija la tarjeta que la necesita, y no se ofrece sola. Así lo decía ya su ficha.

#### T1. Duración

- **Fórmula:** la bala termina a los `L` segundos, aunque su avance no llegue a `reach`. Termina con lo primero que pase.
- **Qué hace:** sola, nada que se vea. Hace posibles a V4, V6 con V4 (el satélite), P8 y T4, que hoy nunca terminan.
- **Cómo se ve:** no se ve; es la regla de cuándo se apaga.
- **Ley o número:** número, pero sin él varias leyes no existen.
- **Escala con el enjambre:** igual.
- **Decisión nueva:** ninguna.
- **Cómo apunta:** no cambia.
- **Precio o contra:** ninguno.
- **Con qué choca:** con nada. No se ofrece como tarjeta: es un dato del arma, y la tarjeta que la necesita lo cambia.
- **Cabe en `WeaponSpec`:** un campo nuevo, `lifetime`. `0` es "sin duración", porque `datafile` no acepta `null` (restricciones del plan).
- **Fuente:** ninguna.

#### T2. Estallar al terminar

- **Fórmula:** al terminar sin haber pegado, la bala suelta `m` puntos en `Cₘ` desde donde está. Es P3, pero al final.
- **Qué hace:** cada disparo que falla revienta al final de su alcance, como un fuego artificial.
- **Cómo se ve:**
  ```
                 ·
     @ ─ ─ ─ ─ · ✱ ·      al llegar a reach
                 ·
  ```
- **Ley o número:** ley.
- **Escala con el enjambre:** más cuando te rodean a la distancia de `reach`.
- **Decisión nueva:** mantener al enjambre a la distancia en que revientan.
- **Cómo apunta:** `intercept`; los puntos del estallido, a ciegas.
- **Precio o contra:** presupuesto, como P3.
- **Con qué choca:** con P3, con el que comparte la forma de soltar `m` puntos (se escribe igual: renacer). Con T3, T4 y T5, porque todos dicen qué pasa al final.
- **Cabe en `WeaponSpec`:** un campo nuevo, `burst: m`.
- **Fuente:** ninguna.

#### T3. Volver a ti

- **Fórmula:** al llegar a `reach`, la bala renace donde está y apunta, con `intercept`, a donde vas a estar tú. Desaparece al llegar a ti.
- **Qué hace:** todo disparo vuelve, y pega en la vuelta.
- **Cómo se ve:** `@ ⇄ · ` con la vuelta siguiéndote.
- **Ley o número:** ley.
- **Escala con el enjambre:** más con enemigos entre tú y el final del alcance.
- **Decisión nueva:** ponerte para que la vuelta cruce al enjambre.
- **Cómo apunta:** la ida, a tu enemigo; la vuelta, a ti, con tu velocidad.
- **Precio o contra:** ninguno.
- **Con qué choca:** con V7 (el bumerán), que vuelve por su fórmula y no te persigue. Se diferencian en que T3 llega a `reach` y te sigue. Con T2, T4 y T5.
- **Cabe en `WeaponSpec`:** un campo nuevo, `on_end: "vanish" | "burst" | "return" | "stop" | "wrap"`, que agrupa T2 a T5.
- **Fuente:** ninguna.

#### T4. Frenar y quedarse

- **Fórmula:** la bala siente un roce lineal: su rapidez es `v·e^{−t/τ_f}`, y su avance, `a(t) = v·τ_f·(1 − e^{−t/τ_f})`. Nunca pasa de `v·τ_f`: se frena y se queda ahí `L` segundos (T1).
- **Qué hace:** los disparos se frenan y forman un anillo de minas a `v·τ_f` de donde nacieron.
- **Cómo se ve:**
  ```
       ·   ·
     ·   @   ·      un anillo de minas que se va armando
       ·   ·
  ```
- **Ley o número:** ley: es el roce del ADR 0021 en la bala.
- **Escala con el enjambre:** más cuando el enjambre viene hacia ti y cruza el anillo.
- **Decisión nueva:** quedarte dentro del anillo que armaste, o llevar al enjambre hacia él.
- **Cómo apunta:** hacia tu enemigo, para que la mina quede en su camino.
- **Precio o contra:** la contra viene adentro: deja de alcanzar lejos.
- **Con qué choca:** con V4, que también deja minas, pero aparecen de golpe; T4 se ve llegar. Con V5 (`∫dt`), con el que se contradice. Con T2, T3 y T5.
- **Cabe en `WeaponSpec`:** un avance exponencial, que no es un polinomio (V7), más `lifetime`.
- **Fuente:** la deducimos de `ẍ = −ẋ/τ_f`. Las páginas de Wikipedia *Drag (physics)* y *Stokes's law* (2026-11-27) dan el roce proporcional a la velocidad, pero no la caída exponencial ni la distancia `v·τ_f` (**no verificado** en una fuente).

#### T5. Reaparecer por el otro lado

- **Fórmula:** al llegar a `reach`, la bala reaparece en el punto opuesto del círculo de radio `reach` en torno a donde nació (`p → 2·p₀ − p`) y sigue con el mismo `û`. Ahora viene de atrás hacia el centro.
- **Qué hace:** el disparo que se pasa vuelve por la espalda y cruza el círculo otra vez.
- **Cómo se ve:** `· → @ → → →|` y reaparece `|· → @`: entra por el lado opuesto.
- **Ley o número:** ley. Es el plano proyectivo: un disco con los puntos opuestos del borde pegados.
- **Escala con el enjambre:** más cuando te rodean, porque cruza dos lados.
- **Decisión nueva:** poca.
- **Cómo apunta:** `intercept`.
- **Precio o contra:** ninguno.
- **Con qué choca:** con T2, T3 y T4. Repite una vez o hasta `w` veces.
- **Cabe en `WeaponSpec`:** en el `on_end` de T3, más las vueltas.
- **Fuente:** Wikipedia, *Real projective plane*, https://en.wikipedia.org/wiki/Real_projective_plane (2026-11-27): se forma desde un disco pegando los pares de puntos opuestos de su borde.
- **Nota:** se ve a medias: un punto que salta de un lado al otro se puede leer como un error.

#### T6. Dejar un rastro

- **Fórmula:** mientras viaja, la bala suelta un punto quieto cada `Δ` segundos, que dura `L` (T1).
- **Qué hace:** cada disparo deja una línea de puntos detrás.
- **Cómo se ve:** `@ · · · · · →` (los puntos quedan después de que pasa).
- **Ley o número:** ley.
- **Escala con el enjambre:** más cuando te persiguen y cruzan el rastro. Con V3, el rastro es una espiral.
- **Decisión nueva:** dibujar con tus disparos dónde va a pisar el enjambre.
- **Cómo apunta:** `intercept`.
- **Precio o contra:** presupuesto: muchos puntos por disparo.
- **Con qué choca:** con el rendimiento: `L/Δ` puntos quietos por bala viva (#42).
- **Cabe en `WeaponSpec`:** un campo nuevo, `trail: (Δ, L)`.
- **Fuente:** ninguna.
- **Nota:** actúa mientras viaja, así que por la regla del método va en Viaja. Va aquí porque apareció después de que el autor revisó Viaja, y porque lo que importa es lo que queda.

#### T7. Los vértices del que muere

- **Fórmula:** cuando la bala le quita la última línea a un enemigo, de cada vértice que tenía sale un punto hacia afuera, por el radio desde su centro: `ûᵥ = (vértice − centro)/|vértice − centro|`.
- **Qué hace:** el polígono que muere revienta en sus vértices, y cada uno es un disparo tuyo.
- **Cómo se ve:**
  ```
       ↖   ↗
         ⬡          un hexágono suelta 6 puntos
       ↙   ↘
  ```
- **Ley o número:** ley, y une al arma con la forma de los enemigos: un triángulo suelta 3 y un hexágono, 6.
- **Escala con el enjambre:** más con enjambres densos, donde un vértice mata a otro y encadena.
- **Decisión nueva:** pelear dentro del grupo, donde las reacciones en cadena rinden.
- **Cómo apunta:** a ciegas, por los radios.
- **Precio o contra:** presupuesto, porque puede encadenar sin fin.
- **Con qué choca:**
  - Con `split_into`, que también actúa cuando muere el enemigo (decisión 71 de la spec de la 0.2.0).
  - Con P3: los dos sueltan puntos después de pegar. Se diferencian en que T7 solo pasa al matar y depende del enemigo.
  - Con las figuras abiertas: se toman los vértices de la figura entera, no solo los de las líneas que le quedaban.
- **Cabe en `WeaponSpec`:** un campo nuevo, `on_kill: "vertices"`. Es un momento que hoy no existe: el que mata. La bala necesita saber que su golpe mató (`Enemy.alive` después de `remove_edge`).
- **Fuente:** ninguna.

#### Lo que se revisó en Termina y quedó fuera

- **Un disparo gratis al terminar:** relanzar desde el jugador. Es "más disparos": número.
- **Devolver el `cooldown` si no pegó:** no se ve.
- **Recoger experiencia:** es una mejora fuera del ataque (tareas 14 y 15).
- **El mundo con forma de toro:** el plano no tiene borde. T5 es la versión que sí lo tiene: el círculo del alcance.

## La lista de chequeo: área × momento

Los conceptos que entraron van por número; los que el autor dejó fuera, entre paréntesis; los que Claude descartó al revisar, en cursiva.

| Área | Nace | Viaja | Pega | Termina |
|---|---|---|---|---|
| Simetría y grupos | N1, N2, N3, N5 | V3 | P4 | T5 |
| Cálculo | — ¹ | V4, V5, V7, V9 | — ¹ | — ¹ |
| Series y armónicos | — ² | V1, V2, V8, *Lissajous*, *onda cuadrada* | — ¹ | — ¹ |
| Sucesiones | N6 | — ³ | P3 | — ⁴ |
| Teoría de números | N6, N12, *primos*, *Fibonacci en la cantidad* | — ⁵ | — ⁴ | — ⁴ |
| Geometría | N2, N9 | V3, V9, *inversión* | P2, P4, P6, (P10) | (T7) |
| Sistemas dinámicos | N11, (N10) | V10, V11, *caos* | P8 | T4 |
| Fractales e iteración | — ⁶ | *L-systems* (ADR 0029, M7) | P3 | T2 |
| Probabilidad | (N14) | *paseo al azar* | *crítico* | — ⁷ |
| Grafos | N8, N13 | — ⁸ | P5 | — ⁸ |
| Física del juego | (N7) | V6, V11, V12 | P1, P7, (P9) | T4, T6 |
| Topología *(apareció al revisar)* | — ⁹ | V6 | P8 | T5 |
| Ritmo | N12, *polirritmo*, *ráfaga* | — ¹⁰ | — ¹⁰ | — ¹⁰ |

**Por qué quedaron vacías:**

1. **El instante no tiene derivada.** Nacer, pegar y terminar pasan en un paso: derivar o integrar, o sumarles un armónico, no tiene sobre qué actuar. Lo que sigue al instante es una trayectoria nueva, y eso es Viaja.
2. **Un armónico en el ángulo de salida** (`θₘ = θ₀ + A·sin(k·m)`) da un abanico que barre ida y vuelta. Se ve como N3 con N6, así que no suma una ley.
3. **Un avance por sucesión** (saltos de Fibonacci, por ejemplo) es discreto: en pantalla, el punto se teletransporta.
4. **Al pegar y al terminar, una sucesión** solo puede contar cuántos puntos salen, y eso ya lo hacen P3 y T2 con `m`.
5. **Una trayectoria que se cierra** cuando la razón de sus frecuencias es racional es una propiedad de V8, no un concepto nuevo.
6. **Un fractal de disparos** al nacer sería soltar puntos que se dividen solos; eso es P3 sin el golpe, o T2.
7. **Cualquier azar al terminar** es un número y gasta `World.rng`.
8. **Un grafo en la trayectoria o al final** solo tiene sentido si se recorren enemigos, y eso es P5.
9. **Una topología al nacer** sería nacer en otro lugar, y eso es N13.
10. **El ritmo** actúa sobre cuándo se dispara. Después de nacer, el punto ya no escucha el compás. Que una bala pegue a tiempo con la música queda como idea para el ADR 0022, no como mejora.

## Resumen

- **Entraron 36 de 43:**
  - Nace: 11 de 14.
  - Viaja: 12 de 12.
  - Pega: 8 de 10.
  - Termina: 5 de 7.
- **Ley o número:** de los que entraron, solo 3 son números (N4, P1 y P2), y los tres se ven. La anti-meta queda lejos.
- **Lo que la lista le pide a la estructura del arma** (sale de "Lo que Viaja le pide" y "Lo que Pega le pide"):
  1. un eje por armónico;
  2. el avance como polinomio, o como una ley con nombre (polinomio o exponencial, T4);
  3. un ancla: donde nació, el jugador o el enemigo;
  4. una duración, como dato y no como tarjeta;
  5. renacer: al pegar y al terminar, la bala muere y suelta otras con una dirección nueva;
  6. un orden fijo entre lo que sigue al golpe y al final;
  7. estado en la bala solo para V10 y V11;
  8. un choque con radio (V12);
  9. funciones nuevas del enemigo: el impulso (P7) y quitar varias líneas en orden (P2);
  10. reglas de "hacia dónde sale" que compiten: N2, N6, N8 y N9.
- **Siguiente paso:** con la lista aprobada, un ADR decide si esto cabe agregando campos a `WeaponSpec` (J) o si el arma pasa a ser una lista de términos (K). Después, las tareas de la 8c.
