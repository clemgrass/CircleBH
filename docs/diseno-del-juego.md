# Diseño del juego: curvas (nombre por definir)

Un juego de acción del género survivors (oleadas de enemigos, ataque automático, mejoras al subir de nivel) en Pygame, donde **todo lo que se ve se dibuja con código** y **las armas son curvas matemáticas**.

## Por qué existe

El autor quiere experiencia demostrable en Pygame. El repo es público en GitHub y es parte de su portafolio: el código y el README se leen tanto como se juega el juego, y deben servir como ejemplo para enseñar Pygame.

## Lo que hace especial al juego

La restricción de no usar sprites ni imágenes es el tema del juego, no un límite. El juego es un gráfico que se dibuja en vivo: el jugador pelea dentro de un plano cartesiano y sus ataques son funciones trazándose.

## Lo que ve el jugador

- **El escenario es un plano cartesiano.** Los ejes X e Y van bien marcados y el resto es una cuadrícula muy suave que no distrae. Los ejes están fijos en el mundo: la cámara sigue al jugador, que puede alejarse del origen. En una esquina se muestran sus coordenadas, por ejemplo `(x: 142, y: −37)`.
- **Es blanco y negro con un solo color de acento**, reservado para el peligro: las balas enemigas y el destello cuando el jugador recibe daño. El fondo es negro, y una opción de la configuración lo invierte a blanco *(decisión del autor, 2026-11-20; ADR 0023)*. El acento es el rojo `#ff3b30`, el mismo sobre los dos fondos *(decisión del autor, 2026-11-21, al comparar capturas)*.
- **La experiencia trae un segundo color, que no es de peligro:** una luz azul detrás de cada punto *(decisión del autor, 2026-11-25; spec de la 0.3.0, decisiones 4 y 5)*. El rojo dice "esto te mata", y la luz azul, "esto es tuyo". Marca también el borde que se carga y la tarjeta elegida. Sobre el fondo blanco va más oscura, con el mismo tono, y no se invierte ([ADR 0031](decisiones/0031-la-luz-de-la-experiencia.md)).
- **Todo se lee por su forma y su movimiento:**

| Qué es | Cómo se ve |
|---|---|
| El jugador | una figura simple, por ejemplo un círculo con un punto que marca hacia dónde mira |
| Sus ataques | solo el trazo, sin relleno |
| Los enemigos | polígonos hechos de líneas, sin relleno *(decisión del autor, 2026-11-19)* |
| Las balas enemigas | puntos rellenos en el color de acento |
| La experiencia | un punto relleno chico, con una luz detrás que va de verde azulado a azul y crece con lo que vale *(decisión del autor, 2026-11-25; antes, puntos sin relleno, que se confundían con el círculo enemigo)* |
| Cuánto falta para subir de nivel | una línea fina en el borde de la pantalla, que se carga dando la vuelta completa, sin número *(decisión del autor, 2026-11-25)* |

La tabla es el punto de partida. El prototipo puede ajustarla si algo no se lee bien cuando la pantalla se llena.

## Cómo se juega

- **El primer ataque es un punto** *(decisión del autor, 2026-11-19)*: una bala que sale sola hacia el centro del enemigo más cercano, porque el punto es de donde parte la geometría cartesiana. Es el arma de la 0.1.0; las curvas llegan después.
- **Las armas son curvas** y disparan solas alrededor del jugador:
  - **Recta:** un rayo en la dirección en que se mueve el jugador.
  - **Círculo:** un anillo que se expande y revienta.
  - **Seno:** una onda que avanza ondulando.
  - **Espiral:** proyectiles que salen girando desde el centro.
- **Las mejoras y las combinaciones salen de ideas matemáticas** *(decisión del autor, 2026-11-19)*: derivar, integrar, componer o sumar curvas, por ejemplo `r(θ, t) = v·t + A·sin(kθ)`, un anillo que ondula. La idea es diferenciarse de los survivors donde dos armas al máximo se fusionan. El mecanismo exacto sigue abierto.
  - **El sistema de armas queda decidido entero para el MVP, con las combinaciones incluidas** *(decisión del autor, 2026-11-24)*. Lo decide el ADR de mejoras de la 0.3.0 (#88 y #89), después de una investigación amplia que no se limita a las ideas de esta sección.
  - **El mecanismo** *(decisiones del autor, 2026-11-24; [ADR 0029](decisiones/0029-armas-por-terminos-y-tarjetas.md))*:
    - **Cada arma se arma con tres términos:** un avance, un armónico y un giro. La trayectoria es la fórmula, y lo que viaja es la bala.
    - **Una tarjeta hace una de tres cosas:**
      - cambia un parámetro;
      - le suma a un arma un término que no tiene. Combinar es sumar, y nada se funde;
      - le aplica un operador: `d/dt` deja el arma contigo, `∫dt` la acelera, `Cₙ` hace n copias, y también están el reflejo y la paralela.
    - **Una tarjeta puede traer un precio:** más presupuesto para el director, una contra en el arma, un efecto sobre los enemigos o un efecto que dura unos compases.
    - **Lo que importa es que las partidas lleguen a formas distintas.** Un test lo mide.
    - **Las armas y las tarjetas son datos del balance y cambian al jugar,** como los enemigos. No hay topes de mejora.
  - **Rosa** (`r = cos(kθ)`): pétalos que orbitan alrededor del jugador.
- **La experiencia la deja cada enemigo que matas, según su amenaza** (`threat`), y tu carga la atrae *(decisión del autor, 2026-11-25)*.
- **Al subir de nivel, el juego frena hasta quedar quieto y aparecen tres tarjetas** *(decisiones del autor, 2026-11-25; spec de la 0.3.0, decisiones 8, 9 y 11)*. Una tarjeta puede dar un arma nueva o mejorar una que ya tienes. No hace falta entender la fórmula para elegir, porque la diferencia se ve en el ataque:
  - **el frente** muestra el tipo de idea, su símbolo (`d/dt`, `C₃`, `+ A·sin(kθ)`), un verbo ("Derivar el círculo") y tu arma en movimiento, como la tienes ahora y con la tarjeta puesta;
  - **el reverso** muestra la fórmula, con lo nuevo subrayado, y el precio. La tarjeta se da vuelta con ↑ y ↓;
  - **R** (Y en el control) cambia la mano entera y **B** (X en el control) saca la tarjeta elegida de la partida, mientras queden usos;
  - las tarjetas usan la fuente Tektur, y lo que el repo incluye de terceros se anota en `CREDITS.md`.
- **Los enemigos son polígonos hechos de líneas, y sus líneas son su vida** *(decisión del autor, 2026-11-19; antes, un golpe convertía el hexágono en pentágono)*. Cada golpe quita la línea exacta que golpea, así que la forma que queda cuenta dónde le pegaste. Sin líneas, desaparece. Una figura abierta deja pasar las balas por sus huecos: el jugador tiene que moverse para encontrar el ángulo. Los polígonos con más lados llegan más tarde en la partida.
- **Cada arma hace daño a su manera:**
  - La **recta** y el **círculo** dañan en todo su trazo: el rayo y el anillo. Un trazo daña **por barrido** *(decisión del autor, 2026-11-24; ADR 0029)*: cada punto de la curva actúa como una bala, y la línea que la curva barre primero se pierde, con un tope de líneas por pasada. El anillo rompe la cara que te mira, y un escudo quieto daña a quien choca contra él.
  - El **seno** y la **espiral** son proyectiles que recorren la curva. Dejan una estela corta que se ve pero no hace daño.
  - La **rosa** daña con sus pétalos completos mientras orbitan.
- **Es un bullet hell:** hay enemigos que disparan, además de los que persiguen al jugador.
- **El jugador es un círculo y muere de un golpe.** Cada tarjeta de anillo extra le suma un anillo concéntrico por fuera, y los anillos se acumulan sin límite *(decisión del autor, 2026-11-24; ADR 0029. Antes, el anillo se recogía como una protección)*. Al perder un anillo, queda invulnerable un rato corto *(decisión del autor, 2026-11-25)*. Cada anillo es una vida más, pero agranda al jugador: el anillo de afuera es más grande que el de adentro, así que tener más vidas hace más fácil que algo te golpee. Cada golpe rompe el anillo de afuera. *(Lo propuso Claude: que se rompa el de afuera es lo que hace que el jugador se achique al perder una vida.)*
- **Fuera del ataque hay seis mejoras** *(decisión del autor, 2026-11-24; ADR 0029. La sexta, el 2026-11-25)*:
  - **velocidad;**
  - **radio menor:** los anillos quedan a `r₀ + i·Δ`, así que achicar el núcleo achica a todos;
  - **carga:** la experiencia siente tu carga como los enemigos, así que subirla atrae la experiencia y al enjambre a la vez;
  - **anillo extra;**
  - **el anillo revienta:** al romperse, se expande, empuja a los enemigos y borra las balas enemigas que cruza;
  - **reroll y banish.**
- **Hay diez tipos de enemigo además del jefe**, cada uno con su idea matemática y una reacción distinta del jugador: triángulo, cuadrado, pentágono, estrella, hexágono, octágono, imán inverso, regenerador, divisor y círculo *(decisión del autor, 2026-11-20; detalle en la spec `docs/specs/2026-11-20-version-0-2-0.md`)*. Todos son justos: ningún ataque llega sin aviso, ninguno queda encima de otro y siempre hay enemigos por todos lados.
- **La partida sigue la forma de un tema de house o techno** *(decisión del autor, 2026-11-20)*: intro, subida, drop 1, respiro, subida y drop 2, en unos 5 minutos. La forma es fija y lo que entra, dónde y cuándo varía con la semilla.
- **El jefe aparece cuando termina el drop 2** *(decisión del autor, 2026-11-20; antes, al minuto 10)*. Es un polígono enorme con aristas interiores, y se va rompiendo de a poco. La idea base es una capa de afuera de unos 100 lados con polígonos anidados adentro: al romper una capa queda expuesta la siguiente. El prototipo decide la forma exacta de lo interior. La cantidad de lados y de capas tiene que ser fácil de cambiar, porque dependen del equilibrio al jugar.
- **Después del último jefe empieza un modo infinito** *(decisión del autor, 2026-11-20)*. Es el último jefe implementado, no el primero. La dificultad crece exponencialmente y el jugador ya no recibe mejoras.
  - **Su tope de cuerpos es una regla de juego, no un límite del computador** *(decisión del autor, 2026-11-24)*. Se elige por lo que hace interesante al infinito y vale igual en todo computador. El juego final no tiene otros topes de rendimiento ni de mejoras: si algo no cabe en el cuadro, se optimiza (#42).
- **Cómo termina:** solo al morir, es decir, al recibir un golpe sin anillos *(decisión del autor, 2026-11-20; antes, se ganaba al destruir al jefe)*. La pantalla final muestra el tiempo, el tiempo en el modo infinito, los enemigos eliminados y el nivel alcanzado.

## La música

La música sale de la misma geometría que el juego, sobre una base de techno, y se genera con código, sin archivos de audio *(decisión del autor, 2026-11-20; [ADR 0022](decisiones/0022-musica-desde-la-matematica.md))*.

- Cada enemigo cercano es un loop: un polígono de n lados toca n golpes repartidos en el compás, y pierde un golpe por cada arista que pierde.
- Cada arma suena con un ritmo que sale de su `spec`, así que una mejora se oye.
- Con pocos enemigos la música se calma, y con muchos sube. La base cambia de tonalidad en cada partida.
- La evolución dentro de una partida larga, los super drops y que el jugador componga la base quedan para el MVP.

## El MVP

- Un menú, una partida de unos 5 minutos con la forma de un tema, el jefe al terminar el drop 2, el modo infinito y la pantalla final.
- 4 o 5 armas-curva.
- Los diez tipos de enemigo; el pentágono dispara.
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

Al terminar el MVP se hace una revisión de cómo expandir el juego. El autor quiere ir sumando dificultad, música y un jefe cada 4 a 6 minutos, como los temas de un set de DJ, y el modo infinito siempre empieza después del último *(2026-11-20)*. Ninguna de estas otras ideas está decidida:

- esconder cosas en coordenadas del plano, como un final secreto;
- sumar color;
- un editor visual de enemigos, armas y otras piezas, parecido a un editor de niveles: arma una pieza desde sus parámetros y muestra cómo se ven las combinaciones de ataques. Más adelante podría servir para diseñar un jugador que no sea un círculo;
- **romper la ley de Coulomb** *(idea del autor, 2026-11-21)*: al destruir al primer jefe se destruye la ley de cargas, y empieza otra ronda igual pero sin ella. Los enemigos dejan de moverse como cargas: se saben unos a otros y se coordinan para atrapar al jugador en equipo, casi como si se entendieran y hicieran trampa. Para compensar, el jugador llega con buenas mejoras y la mejora del jefe. Queda abierto cómo se mueven sin Coulomb y con qué idea matemática se coordinan. Toca al ADR 0021 (una sola ley de cargas), así que necesita un ADR propio.
  - **El imán inverso arma un panal** *(idea del autor, 2026-11-24, al ver la captura `iman-junta`)*: que sus 6 hexágonos calcen alrededor de la estrella, para que la figura se lea como un panal con el imán al medio. Hoy no calzan porque los enemigos chocan por su círculo envolvente: dos hexágonos no bajan de 48, y el panal exacto los pide a 41,6. Hay dos caminos medidos. Uno son 6 casillas a 48 con un resorte hacia la más cercana, sin romper la decisión 12. El otro es el choque por las líneas reales (la suma de Minkowski), que reescribe el núcleo duro del ADR 0021. Quedó fuera del MVP.

Para no cerrarle la puerta al editor, el MVP define los enemigos y las armas por sus parámetros (lados, velocidad, la curva y sus valores), no con código escrito a mano para cada uno. *(Lo propuso Claude: es lo mismo que pide el equilibrio, que los números vivan en un lugar fácil de cambiar.)* El editor no se construye en el MVP.

## Metas, no-metas y anti-metas

- **Metas:** que se juegue bien y se vea distinto a otros survivors; un código que sirva de ejemplo de Pygame, POO y trigonometría.
- **No-metas para el MVP:** secretos en el plano, el editor de enemigos y piezas, más contenido del listado arriba.
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
- Los números de equilibrio: los lados de cada polígono y del jefe, la velocidad, la frecuencia de las oleadas y la curva de experiencia. Cómo se miden lo decide el [ADR 0030](decisiones/0030-balance-medido-por-tema.md): una meta por tema, con lo que llega a cada jefe y la forma del riesgo por sección *(decisiones del autor, 2026-11-24)*.
- Qué tarjetas hay, con qué valores y qué precios. La estructura la decide el ADR 0029; el contenido vive en el balance y se afina jugando (#90).
