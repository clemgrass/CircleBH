---
estado: aceptado
fecha: 2026-11-18
---

# Avanzar la lógica con paso fijo de 1/60 s y dejar que la cámara escale el plano

## Contexto y problema

Los tests de colisiones y daño necesitan que la lógica sea determinista. El juego tiene que verse nítido en cualquier pantalla y con la misma área visible para todos. Hay que decidir cómo avanza el tiempo, cómo se adapta la ventana y de dónde sale el azar.

## Factores de decisión

- Determinismo: el mismo input y la misma semilla dan el mismo resultado.
- Que el juego vaya a velocidad real aunque la máquina sea lenta.
- Trazos nítidos, porque todo es vectorial.
- Evitar APIs marcadas como experimentales.

## Opciones consideradas

- Tiempo: paso fijo con acumulador, atado al frame, o `dt` variable.
- Ventana: la cámara escala el plano, `pygame.SCALED` o una ventana fija de 1280x720.

## Resultado de la decisión

- **Tiempo:**
  - `world.update(1/60)` se repite según el tiempo real acumulado;
  - el tiempo de cada frame se topa en 0,25 s, para que una pausa larga no congele el juego;
  - no hay interpolación al dibujar;
  - `clock.tick(60)` y sin vsync en el MVP.
- **Ventana:** se puede redimensionar y poner en pantalla completa. La cámara siempre muestra la misma área del plano en 16:9, con franjas si la proporción no calza. Los grosores de línea y las fuentes escalan con la cámara.
- **Azar:**
  - una sola `random.Random(seed)` que se inyecta en `world`, nunca las funciones del módulo `random`;
  - la semilla es aleatoria en cada partida, se muestra en la pantalla final y se puede fijar con `--seed`;
  - los tests verifican propiedades, no valores concretos del azar.

### Consecuencias

- Bueno: la lógica es determinista y testeable, y una partida se puede repetir con `--seed`.
- Bueno: la velocidad del juego no depende de los FPS.
- Bueno: los trazos se ven nítidos a cualquier resolución.
- Malo: son unas 10 líneas más en el bucle, y la cámara también escala grosores y fuentes.
- Malo: en un monitor de 144 Hz, la lógica sigue a 60 pasos por segundo, porque no hay interpolación.

### Confirmación

- Los tests de `world` corren con pasos fijos y semilla fija.
- La simulación de una partida completa termina sin errores y hace aparecer al jefe.
- En la revisión se comprueba que nadie use las funciones del módulo `random`.

## Pros y contras de las opciones

### Paso fijo con acumulador
- Bueno: es determinista y va a velocidad real.
- Malo: es un poco más de código en el bucle.

### Atado al frame
- Bueno: es lo más simple y también es determinista.
- Malo: en una máquina lenta, todo el juego va en cámara lenta.

### `dt` variable
- Bueno: se adapta solo.
- Malo: el resultado depende de los FPS, y un proyectil rápido puede atravesar a un enemigo.

### La cámara escala el plano
- Bueno: trazos nítidos y la misma área visible para todos.
- Malo: grosores y fuentes también hay que escalarlos.

### `pygame.SCALED`
- Bueno: casi no requiere código.
- Malo: está marcada como API experimental, y al estirar se puede perder nitidez (no verificado).

### Ventana fija de 1280x720
- Bueno: es lo más simple.
- Malo: en 4K se ve chica y no hay pantalla completa.

## Más información

- https://pyga.me/docs/ref/time.html (consultado el 2026-11-18)
- https://pyga.me/docs/ref/display.html (SCALED experimental, vsync; consultado el 2026-11-18)
- https://docs.python.org/3.14/library/random.html#notes-on-reproducibility (consultado el 2026-11-18)
- https://gafferongames.com/post/fix_your_timestep/ (artículo de referencia, no es documentación oficial)
