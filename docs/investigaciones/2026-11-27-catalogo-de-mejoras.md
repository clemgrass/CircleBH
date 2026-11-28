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

### Viaja, Pega y Termina

*(Pendientes: se llenan después de que el autor revise Nace.)*
