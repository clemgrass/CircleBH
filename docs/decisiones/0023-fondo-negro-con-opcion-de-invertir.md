---
estado: aceptado
fecha: 2026-11-20
---

# Fondo negro, con una opción de la configuración que invierte los colores

## Contexto y problema

El diseño dice que el juego es blanco y negro, con un solo color de acento para el peligro. Quedó abierto si el fondo es negro o blanco, para decidirlo mirando la escena real (#28). Ahora hay una escena con el plano, el jugador, sus balas, los enemigos de líneas y la pantalla de muerte.

Los colores estaban repartidos en `render/plane.py`, `render/world_view.py` y `scenes/death.py`: cambiar el fondo era tocar cinco valores.

Se decidió en la conversación del 2026-11-20, mirando capturas de las dos versiones con la misma semilla (`oleadas` en 8 s y 25 s, la muerte de `enemigo-persigue` y una ventana de 900×900 con franjas).

## Factores de decisión

- Que las líneas finas, de 1 a 2 px, se lean bien.
- Que una partida larga no canse la vista.
- Que el color de acento, todavía abierto, tenga margen para destacar.
- Que quien prefiera el otro fondo lo pueda tener *(pedido del usuario)*.
- Que cambiar los colores sea tocar un solo lugar.

## Opciones consideradas

- Fondo negro, sin opción
- Fondo blanco, sin opción
- Fondo negro por defecto, con una opción que invierte los colores
- Seguir el tema claro u oscuro del sistema operativo (no discutida)

## Resultado de la decisión

Elegimos **el fondo negro por defecto, con una opción que invierte los colores** *(decisión del usuario, 2026-11-20)*:

- `render/palette.py` define una `Palette` con tres colores: el fondo, el trazo y las franjas. `DARK` es la paleta por defecto: fondo negro, trazo blanco y franjas `#202020`.
- `Palette.inverted()` devuelve el negativo de cada color: fondo blanco, trazo negro y franjas `#dfdfdf`.
- La opción vive en `settings.json` (ADR 0018), como `accessibility.invert_colors`, y su valor por defecto es `false`.
- Todo lo que se dibuja usa el trazo. Lo que tapa o desvanece la escena, como la sombra de la muerte, usa el fondo. Así la inversión no necesita casos especiales.
- Los círculos de choque de depuración siguen en magenta: no son parte de la paleta.

### Consecuencias

- Bueno: el negro cansa menos en sesiones largas y deja más colores posibles para el acento.
- Bueno: quien prefiera el papel cuadriculado lo tiene con una línea de la configuración.
- Bueno: los colores viven en un solo lugar, y las funciones de dibujo los reciben como parámetro.
- Malo: son dos versiones que mirar en cada cambio visual.
- Malo: el acento, cuando llegue, tiene que leerse bien sobre los dos fondos. El negativo de un color cambia su tono (el rojo pasa a cian), así que el acento no se va a invertir igual que el resto.

### Confirmación

- `settings.json` trae `accessibility.invert_colors` en `false`, y `tests/test_settings.py` valida el campo.
- En `render/` y `scenes/`, ningún color se escribe fuera de `render/palette.py`, salvo el magenta de depuración. Se revisa en el PR.
- Con `invert_colors: true`, las capturas salen idénticas a las del fondo blanco con que se decidió.

## Pros y contras de las opciones

### Fondo negro, sin opción
- Bueno: una sola versión que mirar.
- Bueno: las líneas brillan y la muerte "se oscurece" sin ajustes.
- Malo: quien prefiere un fondo claro no tiene salida.

### Fondo blanco, sin opción
- Bueno: parece papel cuadriculado, calza con "las armas son curvas" y se distingue de casi todos los survivors.
- Malo: una pantalla completa en blanco cansa más, sobre todo con poca luz.
- Malo: los acentos claros, como el amarillo o el cian, se pierden.

### Fondo negro por defecto, con opción de invertir
- Bueno: el negro por defecto, y el blanco a una línea de distancia.
- Malo: dos versiones que mantener legibles, y el acento queda más difícil.

### Seguir el tema del sistema operativo (no discutida)
- Bueno: el juego calza con el resto del escritorio sin configurar nada.
- Malo: no verifiqué si pygame-ce 2.5.8 expone el tema del sistema. Sumaría un camino distinto en cada sistema operativo.

## Preguntas abiertas

- El color de acento, y cómo se ve con la paleta invertida: se decide cuando existan balas enemigas.

## Más información

- Issue #28: "Elegir el fondo negro o blanco".
- `docs/diseno-del-juego.md`, sección "Lo que ve el jugador".
