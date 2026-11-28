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

*(Pendiente: se llena cuando el autor apruebe el método.)*
