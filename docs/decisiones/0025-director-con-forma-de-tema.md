---
estado: aceptado
fecha: 2026-11-20
---

# La partida sigue la forma de un tema, con un director que cuenta compases

Reemplaza en parte al ADR 0022: el tempo deja de elegirse una vez por sesión, entre 120 y 126 BPM, y pasa a ser un número fijo del balance. Lo demás del 0022 sigue igual.

## Contexto y problema

Hoy los enemigos aparecen de a uno cada 2 s (`spawning.interval`), y la partida no tiene forma. Para la 0.2.0, el usuario quiere que la partida siga la forma de un tema de house o techno de unos 5 minutos: intro, subida, drop 1, respiro, subida y drop 2. Al terminar el drop 2 aparece el jefe, y después del último jefe empieza un modo infinito cuya dificultad crece exponencialmente. La forma es fija, y qué entra, dónde y cuándo varía con la semilla (spec `docs/specs/2026-11-20-version-0-2-0.md`, decisiones 15 a 23).

Hay que decidir cómo se describe esa forma, en qué unidad se mide el tiempo y de dónde sale el tempo, sin romper el determinismo (ADR 0005) ni la regla de que la música escucha al mundo sin cambiarlo (ADR 0022).

## Factores de decisión

- Que la partida se sienta como un tema: calma, subidas y drops que se notan.
- Que cada partida sea única, pero con sentido *(decisión del usuario)*.
- Que todo sean números del balance, fáciles de cambiar (ADR 0004).
- Que un enemigo nuevo entre a la partida sin reescribir el guion.
- Que la misma semilla dé la misma partida, con la música prendida o apagada (ADR 0005 y 0022).
- Que el drop caiga en el golpe de la música.
- Que se pueda testear con propiedades (ADR 0007).

## Opciones consideradas

Cómo se describe la forma:

- A: secciones con presupuesto de amenaza
- B: una lista de eventos con rangos de azar
- C: un director que reacciona a la tensión

En qué se mide el tiempo:

- En compases
- En segundos

De dónde sale el tempo:

- Un número fijo del balance
- El mundo lo elige en cada partida, y la música cambia de tempo al reiniciar
- La música lo elige por sesión y se lo entrega al mundo

## Resultado de la decisión

**A, en compases, con el tempo fijo en el balance** *(decisiones del usuario, 2026-11-20)*.

- **El balance describe el tema** en una sección `director`:
  - el tempo, `bpm`;
  - la lista de secciones, cada una con su nombre, su largo en compases, el presupuesto al empezar y al terminar, el mazo de enemigos con pesos y las formaciones que puede usar.

  Cada tipo de enemigo suma `threat`, su costo.
- **El director vive en `world/`.** Junta presupuesto en cada paso y compra al azar del mazo de la sección, con la `Random` del mundo. Lo comprado entra a una cola, y salen como máximo `spawning.max_per_step` enemigos por paso, en el cuadrante relativo al jugador con menos enemigos vivos.
- **El reloj cuenta compases:** `compás = pasos · STEP · bpm / 240`. Los límites entre secciones se comparan en compases, así que no hace falta que un compás dure una cantidad entera de pasos.
- **Una sección `wave` termina cuando se limpia su oleada**, no al cumplir sus compases. Así funcionan los drops, y así funcionará el jefe.
- **El modo infinito es la última sección:** `presupuesto(t) = B₀ · 2^(t/T)`. Bajo el tope de cuerpos vivos, `director.max_alive`, el presupuesto compra enemigos. Por encima, sube multiplicadores de peligro con tope.
- **El tempo es fijo, `director.bpm`, y parte en 124**, el de la base del ADR 0022. La música lo lee del balance, en vez de elegirlo con `bpm_for(seed)`. La tonalidad y el acorde inicial siguen variando con la semilla, como dice el 0022.
- **La música sigue escuchando sin cambiar nada.** El director no sabe que la música existe, y la música puede leer la sección en que va el director. Con la música apagada, la partida es la misma.

### Consecuencias

- Bueno: la forma del tema se lee en el JSON y se cambia sin código.
- Bueno: un enemigo nuevo solo trae su `threat` y entra a los mazos que corresponda.
- Bueno: el drop cae en el compás exacto, así que la música puede marcarlo en el golpe.
- Bueno: el modo infinito no se pone lento antes de ponerse difícil, porque el tope de cuerpos lo protege.
- Malo: el presupuesto es un número abstracto, y hay que afinarlo jugando.
- Malo: se pierde la variación de tempo entre sesiones que daba el ADR 0022.
- Malo: si una oleada no se limpia, el director espera, y la música tiene que sostener el drop mientras tanto.

### Confirmación

- Un test de Hypothesis comprueba que, con cualquier semilla, las secciones van en orden y cada una empieza en su compás exacto.
- Un test comprueba que, con un `bpm` cuyo compás no dura una cantidad entera de pasos, cada límite cae en el paso correcto.
- Un test de Hypothesis comprueba que lo comprado en una sección no supera su presupuesto acumulado.
- Un test comprueba que dos mundos con la misma semilla y la misma entrada aparecen los mismos enemigos en los mismos pasos.
- Un test comprueba que nunca salen más de `max_per_step` enemigos en un paso.
- Un test comprueba que una sección `wave` no termina mientras quede un enemigo de su oleada.
- Un test comprueba que la música toma su tempo de `director.bpm`.
- `lint-imports` comprueba que `world` no importa `audio`.
- `poe balance-chequear` falla si `director` no calza entre `balance.py` y `balance.json`.

## Pros y contras de las opciones

### A: secciones con presupuesto
- Bueno: la forma es fija y el detalle tiene azar, que es lo que pidió el usuario.
- Bueno: todo son números del balance.
- Malo: el presupuesto es abstracto.

### B: lista de eventos
- Bueno: es el control más fino; cada momento queda escrito a mano.
- Malo: son muchos datos que mantener, y las partidas se parecen.
- Malo: un enemigo nuevo obliga a tocar el guion entero.

### C: director reactivo
- Bueno: se adapta al jugador.
- Malo: cuesta predecirlo, testearlo y explicarlo, y choca con "justo".

### En compases
- Bueno: el drop cae en el golpe.
- Malo: el mundo necesita el tempo.

### En segundos
- Bueno: no toca el ADR 0022.
- Malo: la música cambia de capa solo al empezar una frase de 4 compases (`audio/intensity.py`), así que el drop sonaría hasta unos 8 s tarde.

### Tempo fijo en el balance
- Bueno: es lo más simple y determinista. Un tema tiene su tempo, y aquí vive junto a sus secciones.
- Malo: se pierde la variación de 120 a 126 BPM.

### El mundo elige el tempo en cada partida
- Bueno: se mantiene la variación.
- Malo: al reiniciar cambia el tempo, y se rompe la transición de DJ del ADR 0022, que mantiene la grilla.

### La música elige el tempo por sesión y se lo entrega al mundo
- Bueno: se mantiene todo lo de hoy.
- Malo: la partida ya no depende solo de su semilla, y `--seed 1` daría resultados distintos según la sesión. Choca con el ADR 0005.

## Más información

- Spec `docs/specs/2026-11-20-version-0-2-0.md`.
- La forma típica de un tema de house o techno, con un primer drop cerca del primer tercio, un respiro y un segundo drop, sale de memoria y no se verificó en una fuente. Los compases de cada sección se afinan jugando.
