---
estado: propuesto
fecha: 2026-11-20
---

# La música sigue las secciones del tema, y la partida empieza en el compás

Reemplaza en parte al ADR 0022 en dos puntos:
- la capa de la base ya no sale solo de la intensidad;
- con la música prendida, una partida nueva espera el compás siguiente.

Lo demás del 0022 sigue igual.

## Contexto y problema

Al probar el director (#52, ADR 0025), el drop no se notaba. La música no sabía en qué sección iba la partida: elegía la capa solo por cuántos enemigos había y qué tan cerca estaban. Una subida con muchos enemigos sonaba igual que un drop, y un respiro con muchos enemigos no se calmaba. En el juego, el drop compraba apenas un poco más rápido que la subida.

El usuario pidió **un drop típico**: se escucha la subida, un silencio corto y el golpe con todo, y justo después empiezan a llover enemigos. Tiene que ser un cambio de momento claro (spec de la 0.2.0, decisiones 24 a 26).

Además, la grilla de la música corre desde que abre el juego, y el reloj del director parte de cero en cada partida. Desde la segunda partida, cada drop habría sonado hasta un compás corrido de lo que se ve.

## Factores de decisión

- Que el drop se oiga y se vea como un cambio de momento claro.
- Que el respiro se calme de verdad, para que el drop contraste.
- Que la forma del tema siga en el balance, sin código por sección (ADR 0025).
- Que la música siga escuchando sin cambiar la partida (ADR 0022).
- Que el golpe caiga en el compás exacto también después de reiniciar.

## Opciones consideradas

Cómo sabe la música que viene un drop:

- A: cada sección declara qué capas permite
- B: solo marcar el borde del drop

Cómo calza el golpe al reiniciar:

- R1: la partida nueva empieza en el compás siguiente de la música
- R2: la música reinicia su grilla con la partida
- R3: no hacer nada

## Resultado de la decisión

**A y R1** *(decisiones del usuario, 2026-11-20)*.

- **Cada sección del balance suma `layers`, su capa mínima y máxima.** Dentro de ese rango, la intensidad elige como antes. Los drops piden la capa 3, y el respiro no pasa de la 1.
- **Las frases se cuentan desde el compás en que entró la partida.** Como las secciones empiezan en múltiplos de 4 compases, cada sección abre una frase.
- **La subida:** en la frase anterior a una sección que pide la capa 3, si la que suena pide menos.
  - Suenan un riser de 4 compases y un redoble de clap que se acelera.
  - En el último pulso calla la base: batería, pad y bajo. La capa del juego sigue.
  - En el primer pulso de la sección suena el impacto.
  - Depende del tema, no de la capa que suena, así que también pasa si la subida ya estaba en la capa 3.
- **El filtro sigue a la capa:** se abre en el drop aunque haya pocos enemigos cerca, y su techo baja en las secciones que piden menos.
- **En el juego, cada sección suma `burst`:** una ráfaga de amenaza que se compra en su primer paso. Como se aparece a 800 unidades y la esquina de la pantalla queda a ~760, la ráfaga entra por los bordes cerca de 1 s después del golpe.
- **R1:** al reiniciar con la música prendida, el mundo nuevo se crea al tiro, pero no avanza hasta que entra la tonalidad nueva. Ese mismo compás trae la tonalidad, el impacto y el primer paso de la partida. Con la música apagada, nada espera. La partida es idéntica: solo cambia cuándo empieza.

### Consecuencias

- Bueno: el drop se anuncia y cae en el golpe, en cualquier partida.
- Bueno: el contraste entre el respiro y el drop es claro.
- Bueno: la forma musical del tema se lee y se cambia en el JSON.
- Malo: la capa ya no refleja solo la tensión de la partida. Un drop con pocos enemigos suena igual de fuerte.
- Malo: entre la R y el inicio de la partida pasa hasta un compás (~1,9 s).
- Malo: el riser de 4 compases cuesta unos 250 ms de síntesis al crear el secuenciador.

### Confirmación

- Un test comprueba que en un drop sin enemigos la capa es 3, y que en un respiro con la intensidad al máximo no pasa de 1.
- Un test comprueba que en la frase anterior a un drop suena la subida, que el último pulso queda en silencio y que el impacto cae en la primera semicorchea del drop. Otro test cubre el caso en que la subida ya suena en la capa 3.
- Un test comprueba que no hay subida antes de una sección que no pide la capa 3.
- Un test emula un reinicio con R1 y comprueba que el director entra al drop a lo más un paso después de que la música decide el golpe.
- Un test comprueba que las secciones del balance empiezan en múltiplos de una frase.
- Un test comprueba que la ráfaga se compra en el primer paso de su sección, y una sola vez.
- El test de la música apagada sigue comprobando que la partida es idéntica paso a paso.

## Pros y contras de las opciones

### A: capas por sección
- Bueno: el respiro se calma y el drop no baja.
- Malo: la capa deja de salir solo de la intensidad.

### B: solo el borde
- Bueno: es más chico y no toca cómo se elige la capa.
- Malo: el respiro no se calma, y el drop puede bajar a la mitad si hay pocos enemigos cerca.

### R1: la partida espera el compás
- Bueno: mantiene la transición de DJ del ADR 0022.
- Malo: el inicio se demora hasta un compás.

### R2: la música reinicia su grilla
- Bueno: el inicio es inmediato.
- Malo: la transición de DJ pasa a ser un corte.

### R3: no hacer nada
- Bueno: no cuesta nada.
- Malo: desde la segunda partida, los drops quedan corridos hasta un compás.

## Más información

- Spec `docs/specs/2026-11-20-version-0-2-0.md`, sección "El drop".
- ADR 0022: los "super drops" estaban en la lista para el MVP. Esto los adelanta, atados a las secciones del tema en vez de a momentos fuertes de la partida.
