---
estado: aceptado
fecha: 2026-11-20
---

# La música sale de la geometría del juego, sobre una base de techno

> El tempo por sesión, de 120 a 126 BPM, quedó reemplazado por el [ADR 0025](0025-director-con-forma-de-tema.md): ahora es `director.bpm`, fijo en el balance.
>
> El [ADR 0026](0026-la-musica-sigue-las-secciones.md) reemplaza dos puntos más:
> - la capa ya no sale solo de la intensidad, porque cada sección del tema la acota;
> - con la música prendida, una partida nueva espera el compás siguiente.
>
> Lo demás sigue vigente.

## Contexto y problema

El juego no tiene audio. El usuario quiere música que salga de la misma matemática que mueve el juego (las armas-curva, los ataques y la geometría de los polígonos), que suene bien, con aire de techno o house, y que sea distinta en cada partida, como un roguelike.

Hay que decidir cómo se relaciona la música con el juego, cómo se traduce cada pieza a sonido, y cómo se genera y se reproduce con pygame-ce sin romper el paso fijo ni el determinismo (ADR 0005).

Se decidió en la conversación del 2026-11-19 y el 2026-11-20, con dos prototipos desechables que el usuario escuchó (ver "Prototipos").

## Factores de decisión

- Que suene bien y a techno o house *(gusto del usuario)*.
- Que la matemática del juego se oiga: el ritmo, la forma y la energía salen de lo que pasa en el plano.
- Que cada partida suene distinta sin un sorteo aparte: la variación sale del juego *(decisión del usuario)*.
- Que la intensidad siga a la partida: tranquila con pocos enemigos y fuerte con muchos *(decisión del usuario)*.
- Que aguante N + 1: un enemigo, un arma o un patrón nuevo suena sin cambiar el modelo *(decisión del usuario)*.
- Que sea determinista y testeable: con la misma semilla, el mismo audio (ADR 0005 y 0007).
- Que no haya archivos de audio: todo se genera con código, como las imágenes (ADR 0013).
- Que cueste poca CPU: el paso del enjambre ya está en el borde de los 16,6 ms (#42).
- Que no sume dependencias en la 0.1.0.

## Opciones consideradas

Qué escucha a quién:

- La música escucha al juego, y el juego no escucha a la música
- Los dos se escuchan: las armas disparan al pulso

Cómo se traduce la matemática:

- Sonificación directa: cada evento es un sonido, y la forma del polígono es la onda (primer prototipo)
- A: una pista compuesta que el juego solo modula
- B: la geometría como estructura (loops euclidianos), sin una base
- C: la geometría como estructura, sobre una base de techno fija

Cómo se genera el audio:

- Un secuenciador propio que mezcla un bloque por semicorchea y lo encadena con `Channel.queue()`
- Sonidos pre-generados que el bucle dispara con `Channel.play()`
- El secuenciador propio, con numpy
- Un motor externo, como SuperCollider o pyo (no discutida)

Dónde corre la mezcla:

- En el bucle principal
- En un hilo propio
- En Python sin GIL (`3.14t`)

## Resultado de la decisión

### La relación

- **La música escucha al juego, y el juego no escucha a la música** *(decisión del usuario, 2026-11-19)*. Las armas no disparan al pulso y el balance no cambia. Que el juego también escuche queda como posible evolución, no decidida.
- **Lo único de cada partida sale del juego** *(decisión del usuario)*: cuántos enemigos hay, dónde están, cuándo les pegas y qué armas llevas.
- **La base varía un poco con la semilla** *(decisión del usuario, 2026-11-20)*. La tonalidad (de −5 a +2 semitonos) y el acorde inicial cambian en cada partida, y el tempo (de 120 a 126 BPM), una vez por sesión. Así, reiniciar no suena siempre igual. El azar sale de la semilla, nunca del reloj, con un generador propio de la música (`Random(f"musica-{seed}")`), para que prender o apagar la música no cambie la partida. La evolución dentro de una partida queda para el MVP.

### El camino C *(decisión del usuario, 2026-11-20)*

La música tiene dos capas, y la frontera entre ellas es la decisión de fondo:

- **El juego decide el tiempo, la densidad, el timbre y la energía:** cuándo suena cada nota, cuántas suenan, con qué forma de onda y en qué capa va la base.
- **La teoría musical decide qué notas son posibles:** la escala y los acordes los compone una persona. Así, la capa del juego nunca desafina, y no porque salga solo de la matemática, sino porque solo puede elegir notas del acorde que suena.

**La base fija** (para la 0.1.0, la del segundo prototipo):

- 124 BPM, swing de 56 % y deep house en La menor: Am9 – Fmaj9 – Dm9 – Em7, dos compases cada acorde.
- Batería sintetizada: bombo, hats, clap, riser e impacto. Pad y bajo de diente de sierra con filtro resonante, sidechain del bombo y delay ping-pong de corchea con puntillo.
- Cuatro capas, de 0 (calma: pad, sin bombo) a 3 (todo). La capa solo cambia al empezar una frase de 4 compases. Antes de subir suena un riser, y al llegar, un impacto. Al perder, cae a la capa 0 con un impacto.

**La geometría como estructura**:

| Del juego | En la música |
|---|---|
| Un enemigo de n lados | Un loop E(n, 16): n golpes repartidos lo más parejo posible en las 16 semicorcheas del compás (Toussaint 2005). Suena mientras vive. Solo tienen loop los 3 más cercanos |
| Su ángulo alrededor del jugador | Rota su loop |
| La arista i | El golpe i del loop. Si la arista no está, ese golpe calla |
| El golpe i | Toca la nota i del acorde que suena |
| Las aristas que le quedan | Su timbre: un punto recorre esas aristas a rapidez constante y su `x` es la onda. Entero es suave; con huecos, más brillante |
| Su distancia al jugador | Su volumen |
| Un arma | Un loop E(k, 16), con k calculado desde su `spec` actual. Para el arma punto, `k = round(compás / cooldown)`. Cada golpe suena solo si el arma de verdad disparó |
| Una bala que golpea | Un rim seco, cuantizado a la semicorchea |
| Una muerte | Un acorde corto, cuantizado a la corchea |
| Los enemigos y su cercanía | La intensidad: `I = 1 − e^(−x/3)`, con `x = Σ (líneas que quedan / lados) · e^(−d/400)`. Sube en ~1 s, baja en ~6 s, elige la capa y abre el filtro |

**Las armas cambian mucho durante la partida** *(lo remarcó el usuario)*. Por eso la voz de un arma se recalcula desde su `spec` en cada compás, igual que el arma lee su `spec` en cada paso: una mejora se oye.

### Cómo se genera *(decisiones del usuario, 2026-11-19)*

- **Un secuenciador propio que mezcla bloques.** Por cada semicorchea, Python mezcla lo que suena y lo deja en cola con `Channel.queue()`, que lo empieza justo cuando termina el anterior. Así, todo cae exacto en la grilla. Se descartó disparar sonidos con `Channel.play()` desde el bucle, porque pueden correrse hasta un cuadro (16 ms) y el bombo se oye cojo.
- **Sin hilo propio.** La reproducción ya corre en el hilo de audio de SDL. La mezcla corre en el bucle principal y avanza con el reloj de pasos, así que el audio es determinista. El trabajo de cada bloque se reparte entre los cuadros que dura (unos 7), para no comerse un cuadro entero.
- **Sin numpy en la 0.1.0.** Queda como plan B.

### Dónde vive *(Claude lo propone; el usuario aprobó la capa el 2026-11-20)*

- **Una capa nueva, `circlebh.audio`, hermana de `render`.** El contrato de import-linter pasa a `scenes → render | audio → world → balance`: `audio` lee el mundo y el balance, `scenes` la usa, y `render` y `audio` no se conocen. Todo `audio/` es puro y se testea: el ritmo euclidiano, la cuantización, las capas y la mezcla en arreglos. La reproducción con `pygame.mixer` quedó en `scenes/music.py`, como `Gamepads` con los controles, así que no se testea (ADR 0007) y la configuración de cobertura no cambió.
- **`World` deja la lista de eventos del paso:** golpe (con el enemigo y la arista), muerte y disparo. Hoy no existe, y sacarlos comparando un paso con el siguiente, como en el prototipo, es frágil. Son datos puros, así que `world/` sigue sin dibujar ni sonar.
- **Las voces se derivan de lo que ya está en el balance**, sin campos nuevos: el ritmo de un enemigo sale de sus lados y el de un arma, de su `spec`. Un tipo de enemigo nuevo suena solo. Un tipo de arma nuevo suma su clase de voz en `audio/`. Si después hace falta afinar una voz por entidad, se agrega un campo `voice` al balance, con un `kind`, como los patrones del ADR 0021.
- **La configuración de audio va en `settings.json`,** porque describe cómo se juega y no a una entidad (ADR 0018). Es configuración para el jugador y queda modular *(decisión del usuario, 2026-11-20)*: si suena la música, el volumen general y uno por capa (`base_volume` y `game_volume`).
- **La demo con `--speed` distinto de 1 no tiene música,** y las capturas tampoco.

### Con asterisco para el MVP (1.0) *(decisión del usuario, 2026-11-20)*

Lo de la 0.1.0 es una primera versión. Antes del MVP se revisa:

- **La CPU:** medir en el juego real y optimizar, con numpy, loops pre-generados o lo que muestre la medición.
- **La base, con el usuario:** que el usuario participe en componerla. Por ejemplo, que la base viva en datos que se puedan editar, en vez de en código.
- **La fatiga:** después de cierto tiempo, la música tiene que ir cambiando. Se mantienen las técnicas, pero cambia su tratamiento: otro filtro, otra textura o algo de ese estilo.
- **Los super drops:** un sistema de drops muy techno (build-up, silencio y la caída con todo), disparado por momentos fuertes de la partida, como las oleadas grandes o el jefe.
- **La saturación de la intensidad:** con unos 48 enemigos llega a 1 y la música deja de subir. Puede seguir los cambios de la partida y no solo cuántos enemigos hay.
- **El juego que también escucha** (las armas al pulso), si se quiere.

### Consecuencias

- Bueno: cada enemigo se oye como un patrón que dura mientras vive, y al pegarle cambia su ritmo. Lo que se repite se siente parte de la canción, y esa fue la falla del primer prototipo.
- Bueno: un enemigo nuevo suena sin escribir nada: su número de lados ya es su ritmo.
- Bueno: la capa del juego no puede desafinar.
- Bueno: con la misma semilla sale el mismo audio, así que se puede testear y reproducir.
- Malo: la armonía y la base no salen del juego; las compone una persona. La matemática del juego decide el tiempo, la densidad, el timbre y la energía, pero no las notas posibles.
- Malo: cuesta CPU. En el prototipo, mezclar una semicorchea tomó 22–26 ms de media y 80 ms como máximo, repartibles en unos 7 cuadros, y el enjambre ya está en el borde (#42).
- Malo: un golpe suena entre 120 y 350 ms después, por la cuantización y el bloque en cola. Como acento dentro de un loop, se acepta.
- Malo: `World` gana una lista de eventos y el contrato de capas cambia.

### Confirmación

- Un test de Hypothesis comprueba que E(k, n) tiene k golpes y que sus intervalos difieren a lo más en 1.
- Un test de Hypothesis comprueba que toda nota de la capa del juego pertenece al acorde del compás en que suena.
- Un test comprueba que, si un enemigo pierde la arista i, el golpe i de su loop calla.
- Un test comprueba que el loop de un arma cambia cuando cambia su `cooldown`.
- Un test comprueba que ningún evento se agenda antes de su tiempo más el bloque en cola, y que todo cae en la grilla.
- Un test comprueba que la capa solo cambia al empezar una frase.
- Un test comprueba que los mismos eventos dan los mismos bytes de audio.
- `lint-imports` comprueba que `world` no importa `audio`, y que `audio` y `render` no se importan entre sí.
- Una medición, a mano como `poe benchmark`, reporta los milisegundos por cuadro de la mezcla.

### Implementación (#44, 2026-11-20)

- `uv run poe musica` (120 s, semilla 1): la mezcla cuesta 2,7 ms por paso de media, con p99 de 9,3 ms. Con el jugador inmortal, 3,3 ms y p99 de 10,6 ms. Cumple la meta de 4 ms de media. Con todos los arreglos de la revisión, la demo cuesta 3,0 ms de media y dos corridas dan el mismo sha256 (`e99dddadd360c247`).
- La revisión de la rama encontró ese defecto. La prueba manual encontró que la música se callaba a los pocos segundos: una carrera en pygame-ce 2.5.8 al encolar justo cuando un bloque termina. Se arregló en `audio/playback.py`, con un colchón de dos bloques y la recuperación del bloque atascado.
- Queda un pico de 40 a 100 ms la primera vez que suena el acorde corto de cada acorde en cada tonalidad. Va al asterisco de CPU del MVP. La batería se genera al crear el secuenciador (173 ms una vez), porque generarla a mitad de partida trababa un cuadro en 70 ms.

## Pros y contras de las opciones

### La música escucha al juego
- Bueno: no toca el balance ni cómo se juega.
- Malo: el jugador no "toca" la música; la provoca.

### Los dos se escuchan
- Bueno: se siente más musical, como Rez o Thumper.
- Malo: cambia los `cooldown`, el balance y cómo se juega.

### Sonificación directa
- Bueno: es la traducción más literal de la matemática.
- Malo: el usuario la escuchó y "suena pésimo": desconectada y monótona. Los eventos sueltos no se repiten, el disparo cada 0,6 s no calza con el pulso, las notas chocan con la armonía y no hay forma.

### A: pista compuesta que el juego modula
- Bueno: es lo que mejor suena.
- Malo: la matemática del juego queda de adorno.

### B: geometría como estructura, sin base
- Bueno: la matemática está en todo.
- Malo: sin una base que sostenga, puede volver a sonar suelto.

### C: geometría como estructura, sobre una base de techno
- Bueno: la base asegura el género y la forma; la geometría da el ritmo, el timbre y la energía.
- Malo: la base y la armonía las compone una persona.

### Secuenciador propio con `Channel.queue()`
- Bueno: la grilla es exacta, es determinista y se puede testear.
- Malo: es un mezclador propio, con su costo de CPU.

### Sonidos pre-generados con `Channel.play()`
- Bueno: pygame mezcla en C, y es lo más simple.
- Malo: cada sonido puede correrse hasta un cuadro, y los cambios continuos, como abrir el filtro, se pre-generan por escalones.

### Con numpy
- Bueno: es mucho más rápido y permite filtros de verdad.
- Malo: es una dependencia nueva. Queda como plan B.

### Motor externo (no discutida)
- Bueno: son sintetizadores completos.
- Malo: son pesados y sacan el sonido de Python.

### Mezcla en el bucle principal
- Bueno: avanza con el reloj de pasos, así que es determinista.
- Malo: compite con el juego por el cuadro; hay que repartir el trabajo.

### Hilo propio
- Bueno: el audio se independiza de los cuadros.
- Malo: con GIL no calcula en paralelo, sino que se turna cada 5 ms. Además trae datos compartidos y arriesga el determinismo si el juego se atrasa.

### Python sin GIL
- Bueno: un hilo sí correría en paralelo.
- Malo: cambia el ADR 0001, y no se pudo verificar que pygame-ce lo soporte. Una extensión que no lo declara vuelve a activar el GIL.

## Prototipos

Dos scripts desechables que no tocaron `src/`. El segundo quedó como referencia en `docs/prototipos/musica_camino_c.py`: no se mantiene ni se testea, y con la semilla 1, el jugador inmortal y 120 s reproduce el mismo audio que escuchó el usuario (sha256 `efd82d383fbac5fe`). El primero no se guardó. Corrieron la partida simulada de la demo (semilla 1), sacaron los eventos comparando cada paso con el anterior y mezclaron un bloque por semicorchea en Python puro, sin numpy ni hilos.

### Primero: sonificación directa (2026-11-20)

- **Timbre de un polígono:** un punto recorre las aristas a rapidez constante, con `x` al canal izquierdo e `y` al derecho. En un osciloscopio XY se dibuja el polígono. La DFT del hexágono cerrado dio armónicos solo en k = 1, 5, 7, 11, 13, con magnitud exacta 1/k² (0,040; 0,020; 0,008; 0,006). El cuadrado dio una onda triangular, y el círculo sería una seno pura. Con aristas perdidas el sonido se vuelve áspero, y con una sola arista es un diente de sierra.
- **Armonía:** La menor hexatónica (A B C D E G); la arista k toca la nota k. Acordes Am–F–C–G.
- **Determinismo:** dos corridas dieron el mismo audio (sha256 `83a3bc1e9a20bc20`).
- **Intensidad:** en la demo normal, el piloto muere 9 veces en 90 s y la música no pasa del nivel 2. Con el jugador inmortal sube de 0 a 4 en ~30 s y se satura con unos 48 enemigos.
- **Costo:** 12,5–16 ms de media por semicorchea, p99 26–30 ms y máximo 43 ms.
- **Latencia golpe → sonido:** ~185 ms de media y ~350 ms de máximo.
- **Veredicto del usuario:** "suena pésimo": desconectado y monótono. La causa fue traducir la matemática directo a sonido y no a estructura musical.

### Segundo: camino C (2026-11-20)

- Base y geometría como se describen arriba.
- **Costo:** 22–26 ms de media por semicorchea, p99 44–48 ms y máximo 80 ms.
- **Nivel:** −10 dBFS RMS y picos de 0,8, sin saturar.
- **Stems:** se generó la base sola, el juego solo y todo junto, para separar lo que aporta cada parte. Todo junto dio el mismo sha256 que antes de separar (`efd82d383fbac5fe`).
- **Veredicto del usuario:** le gustó para la 0.1.0, con los asteriscos de arriba para el MVP.

## Más información

- G. Toussaint, "The Euclidean Algorithm Generates Traditional Musical Rhythms", Bridges 2005, pp. 47–56 (leído el 2026-11-20): https://cgm.cs.mcgill.ca/~godfried/publications/banff.pdf. Representa los ritmos como polígonos en un círculo: E(3,8) es el tresillo (un triángulo) y E(5,8), el cinquillo (un pentágono).
- pygame-ce, `pygame.mixer` (consultado el 2026-11-19): https://pyga.me/docs/ref/mixer.html. `Sound(buffer=...)` acepta datos crudos sin numpy; no hay callback de audio; `Channel.queue()` encadena un sonido justo al terminar el anterior.
- pygame-ce, `pygame.sndarray` (consultado el 2026-11-19): https://pyga.me/docs/ref/sndarray.html. Solo funciona con numpy.
- SDL2, `SDL_OpenAudioDevice` (consultado el 2026-11-19): https://wiki.libsdl.org/SDL2/SDL_OpenAudioDevice. El callback de audio "runs in a separate thread in most cases".
- Python 3.14, "Python support for free threading" (consultado el 2026-11-19): https://docs.python.org/3.14/howto/free-threading-python.html. El Python del proyecto es 3.14.10 con GIL (`Py_GIL_DISABLED = 0`), y `sys.getswitchinterval()` da 0,005 s.
- import-linter 2.16: las capas hermanas independientes se escriben con `|`. Se verificó en el código instalado (`importlinter/contracts/layers.py`), porque la documentación en línea dio 404.
- Las charlas de GDC sobre Rez, Thumper y Tetris Effect se citan como referencia de música interactiva, pero no se consultaron.
