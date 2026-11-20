# Diseño del juego: curvas (nombre por definir)

Un juego de acción del género survivors (oleadas de enemigos, ataque automático, mejoras al subir de nivel) en Pygame, donde **todo lo que se ve se dibuja con código** y **las armas son curvas matemáticas**.

## Por qué existe

El autor quiere experiencia demostrable en Pygame. El repo es público en GitHub y es parte de su portafolio: el código y el README se leen tanto como se juega el juego, y deben servir como ejemplo para enseñar Pygame.

## Lo que hace especial al juego

La restricción de no usar sprites ni imágenes es el tema del juego, no un límite. El juego es un gráfico que se dibuja en vivo: el jugador pelea dentro de un plano cartesiano y sus ataques son funciones trazándose.

## Lo que ve el jugador

- **El escenario es un plano cartesiano.** Los ejes X e Y van bien marcados y el resto es una cuadrícula muy suave que no distrae. Los ejes están fijos en el mundo: la cámara sigue al jugador, que puede alejarse del origen. En una esquina se muestran sus coordenadas, por ejemplo `(x: 142, y: −37)`.
- **Es blanco y negro con un solo color de acento**, reservado para el peligro: las balas enemigas y el destello cuando el jugador recibe daño. El prototipo decide si el fondo es negro o blanco.
- **Todo se lee por su forma y su movimiento:**

| Qué es | Cómo se ve |
|---|---|
| El jugador | una figura simple, por ejemplo un círculo con un punto que marca hacia dónde mira |
| Sus ataques | solo el trazo, sin relleno |
| Los enemigos | polígonos hechos de líneas, sin relleno *(decisión del autor, 2026-11-19)* |
| Las balas enemigas | puntos rellenos en el color de acento |
| La experiencia | puntos pequeños sin relleno |

La tabla es el punto de partida. El prototipo puede ajustarla si algo no se lee bien cuando la pantalla se llena.

## Cómo se juega

- **El primer ataque es un punto** *(decisión del autor, 2026-11-19)*: una bala que sale sola hacia el centro del enemigo más cercano, porque el punto es de donde parte la geometría cartesiana. Es el arma de la 0.1.0; las curvas llegan después.
- **Las armas son curvas** y disparan solas alrededor del jugador:
  - **Recta:** un rayo en la dirección en que se mueve el jugador.
  - **Círculo:** un anillo que se expande y revienta.
  - **Seno:** una onda que avanza ondulando.
  - **Espiral:** proyectiles que salen girando desde el centro.
- **Las mejoras y las combinaciones salen de ideas matemáticas** *(decisión del autor, 2026-11-19)*: derivar, integrar, componer o sumar curvas, por ejemplo `r(θ, t) = v·t + A·sin(kθ)`, un anillo que ondula. La idea es diferenciarse de los survivors donde dos armas al máximo se fusionan. El mecanismo exacto sigue abierto.
  - **Rosa** (`r = cos(kθ)`): pétalos que orbitan alrededor del jugador.
- **Al subir de nivel aparecen tres tarjetas.** Cada una muestra la fórmula del arma y el parámetro que cambia, por ejemplo "`y = A·sin(ωx)`: ω sube a 3". Una tarjeta puede dar un arma nueva o mejorar una que ya tienes. No hace falta entender la fórmula para elegir, porque la diferencia se ve en el ataque.
- **Los enemigos son polígonos hechos de líneas, y sus líneas son su vida** *(decisión del autor, 2026-11-19; antes, un golpe convertía el hexágono en pentágono)*. Cada golpe quita la línea exacta que golpea, así que la forma que queda cuenta dónde le pegaste. Sin líneas, desaparece. Una figura abierta deja pasar las balas por sus huecos: el jugador tiene que moverse para encontrar el ángulo. Los polígonos con más lados llegan más tarde en la partida.
- **Cada arma hace daño a su manera:**
  - La **recta** y el **círculo** dañan en todo su trazo: el rayo y el anillo.
  - El **seno** y la **espiral** son proyectiles que recorren la curva. Dejan una estela corta que se ve pero no hace daño.
  - La **rosa** daña con sus pétalos completos mientras orbitan.
- **Es un bullet hell:** hay enemigos que disparan, además de los que persiguen al jugador.
- **El jugador es un círculo y muere de un golpe.** Si recoge una protección, se le suma un anillo concéntrico por fuera, y los anillos se acumulan sin límite. Cada anillo es una vida más, pero agranda al jugador: el anillo de afuera es más grande que el de adentro, así que tener más vidas hace más fácil que algo te golpee. Cada golpe rompe el anillo de afuera. *(Lo propuso Claude: que se rompa el de afuera es lo que hace que el jugador se achique al perder una vida.)*
- **El jefe aparece al minuto 10.** Es un polígono enorme con aristas interiores, y se va rompiendo de a poco. La idea base es una capa de afuera de unos 100 lados con polígonos anidados adentro: al romper una capa queda expuesta la siguiente. El prototipo decide la forma exacta de lo interior. La cantidad de lados y de capas tiene que ser fácil de cambiar, porque dependen del equilibrio al jugar.
- **Cómo termina:** el jugador gana si destruye al jefe y pierde si recibe un golpe sin anillos. La pantalla final muestra el tiempo, los enemigos eliminados y el nivel alcanzado.

## La música

La música sale de la misma geometría que el juego, sobre una base de techno, y se genera con código, sin archivos de audio *(decisión del autor, 2026-11-20; [ADR 0022](decisiones/0022-musica-desde-la-matematica.md))*.

- Cada enemigo cercano es un loop: un polígono de n lados toca n golpes repartidos en el compás, y pierde un golpe por cada arista que pierde.
- Cada arma suena con un ritmo que sale de su `spec`, así que una mejora se oye.
- Con pocos enemigos la música se calma, y con muchos sube. La base cambia de tonalidad en cada partida.
- La evolución dentro de una partida larga, los super drops y que el jugador componga la base quedan para el MVP.

## El MVP

- Un menú, una partida de 10 minutos que termina con el jefe, y la pantalla final.
- 4 o 5 armas-curva.
- 3 o 4 tipos de polígono, y al menos uno dispara.
- El jefe.
- Los anillos de protección del jugador.
- La subida de nivel con tarjetas.
- Las coordenadas del jugador en pantalla, sin nada escondido en el plano todavía.

## Calidad

- Tests sobre la lógica: las curvas, el daño a los polígonos, las colisiones y la subida de nivel. El dibujo no se testea.
- El README explica la matemática de cada arma: su fórmula, qué hace cada parámetro y cómo se ve.
- No hay fecha límite: el autor avanza a su ritmo. El plan apunta al MVP completo, sin recortar.
- El código tiene que leerse como ejemplo: clases simples con herencia y funciones cortas, sin abstracciones avanzadas como ECS o metaclases. *(Lo propuso Claude: el código es lo que muestra la experiencia en Pygame.)* Los identificadores van en inglés; los comentarios y el README, en español.

## Después del MVP

Al terminar el MVP se hace una revisión de cómo expandir el juego. Ninguna de estas ideas está decidida:

- combinar curvas, por ejemplo seno con círculo para formar una figura de Lissajous;
- esconder cosas en coordenadas del plano, como un final secreto;
- sumar color;
- un editor visual de enemigos, armas y otras piezas, parecido a un editor de niveles: arma una pieza desde sus parámetros y muestra cómo se ven las combinaciones de ataques. Más adelante podría servir para diseñar un jugador que no sea un círculo.

Para no cerrarle la puerta al editor, el MVP define los enemigos y las armas por sus parámetros (lados, velocidad, la curva y sus valores), no con código escrito a mano para cada uno. *(Lo propuso Claude: es lo mismo que pide el equilibrio, que los números vivan en un lugar fácil de cambiar.)* El editor no se construye en el MVP.

## Metas, no-metas y anti-metas

- **Metas:** que se juegue bien y se vea distinto a otros survivors; un código que sirva de ejemplo de Pygame, POO y trigonometría.
- **No-metas para el MVP:** combinaciones de curvas, secretos en el plano, el editor de enemigos y piezas, más contenido del listado arriba.
- **Anti-metas:** cualquier archivo de imagen o sprite dibujado a mano; un survivors común con una capa geométrica encima, donde las curvas no cambian cómo se juega; cualquier mención de la organización o el curso que motivó el proyecto (en el código, en el README o en los commits).

## Restricciones

- Python 3.14 con pygame-ce 2.5.8 ([ADR 0001](decisiones/0001-pygame-ce-y-python-3-14.md)).
- Nada de archivos de imagen. Todo se dibuja con las funciones de dibujo de Pygame. Las únicas imágenes del repo son capturas que genera el propio juego para el README ([ADR 0013](decisiones/0013-evidencia-e-imagenes.md)).
- Repo público en GitHub.

## Caminos considerados

1. **Geometría solo como estética**, con mecánicas de survivors común. Es lo más rápido, pero lo nuevo se queda en lo visual. Se descartó.
2. **Las armas son curvas** y las mejoras cambian sus parámetros. Los enemigos son polígonos que pierden lados.
3. **El camino 2 con la fórmula a la vista** en las tarjetas de mejora, para jugar con los parámetros.

El autor eligió el **2 con un toque del 3**: la fórmula aparece en la tarjeta, pero no hace falta entenderla para jugar.

Sobre el color: el blanco y negro estricto es lo más fiel a la idea, pero cuesta distinguir qué hace daño. El autor eligió **blanco y negro con un solo color de acento** para el peligro.

## Ya decidido

- La arquitectura, las herramientas y la versión de Pygame: [docs/decisiones/](decisiones/).
- El lugar de los números de equilibrio: `balance.py` y `balance.json`, coordinados ([ADR 0004](decisiones/0004-balance-coordinado.md)).

## Preguntas abiertas

- El nombre del juego. `circlebh` es provisorio.
- El fondo negro o blanco, y el color de acento: se deciden con un prototipo desechable.
- Los números de equilibrio: los lados de cada polígono y del jefe, la velocidad, la frecuencia de las oleadas y de las protecciones, y la curva de experiencia.
- Qué parámetro mejora cada tarjeta de cada arma.
- Cómo se mejoran y se combinan las armas con ideas matemáticas (derivar, integrar, componer), y si las combinaciones entran al MVP o quedan para después.
