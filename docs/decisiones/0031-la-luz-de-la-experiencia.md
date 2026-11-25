---
estado: propuesto
fecha: 2026-11-25
---

# La luz de la experiencia: un segundo color, que no es de peligro

Amplía el [ADR 0023](0023-fondo-negro-con-opcion-de-invertir.md).

## Contexto y problema

El ADR 0023 y el diseño dejan el juego en blanco y negro, con un solo color de acento: el rojo `#ff3b30`, reservado para el peligro. Es el mismo sobre los dos fondos, porque su negativo cambia de tono.

La spec de la 0.3.0 suma la experiencia y decide cómo se ve (decisiones 4, 5 y 12):

- un punto relleno chico, con una luz difusa detrás que va de verde azulado a azul y crece con lo que vale;
- un borde de la pantalla que se carga con el color intermedio de esa luz;
- la tarjeta elegida, marcada con ese mismo color intermedio, `#4cb6e0`.

Eso es un segundo color, y no es peligro: el rojo dice "esto te mata", y la luz, "esto es tuyo". Falta decidir sus valores, y qué pasa con ellos cuando la configuración invierte los colores. Una luz clara casi no se ve sobre el blanco.

## Factores de decisión

- Que la luz no se confunda con el rojo del peligro, tampoco con daltonismo rojo-verde *(decisión 4: por eso el halo va de verde azulado y no de verde puro)*.
- Que se lea sobre el negro y sobre el blanco.
- Que el valor del punto se lea dos veces, por el color y por el tamaño (decisión 4).
- Que los colores sigan viviendo en un solo lugar, `render/palette.py` (ADR 0023).
- Que invertir los colores siga sin casos especiales en el dibujo.

## Opciones consideradas

- La misma luz sobre los dos fondos
- La luz más oscura sobre el blanco, con el mismo tono
- El negativo de la luz, como el fondo y el trazo
- Sobre el blanco, solo el punto de color, sin halo (no discutida)

## Resultado de la decisión

Elegimos **la luz más oscura sobre el blanco, con el mismo tono** *(propuesta de Claude)*:

| | Bajo (vale menos) | Intermedio (borde y selección) | Alto (vale más) |
|---|---|---|---|
| Sobre el negro | `#3ad2c2` | `#4cb6e0` | `#5e9afe` |
| Sobre el blanco | `#0e8c82` | `#1673aa` | `#1e5ad2` |

- El intermedio de cada fondo es el punto medio exacto, canal por canal, entre el bajo y el alto. Sobre el negro es el `#4cb6e0` de la spec.
- `render/palette.py` define una `Light(low, high, selection)` con `at(t)`, que mezcla de `low` a `high`, y dos constantes, `ON_BLACK` y `ON_WHITE`. `Palette.light` lleva la de su fondo, y `Palette.inverted()` la cambia por la del otro: la luz no se invierte, como el acento.
- El halo se dibuja con transparencia, con un alfa que cae como `(1 − r/R)²` desde el centro (`render/glow.py`). Así sirve igual sobre los dos fondos, sin mezcla aditiva.
- El valor del punto va de 0 a 1 entre el menor y el mayor `threat` positivo del balance. Con él salen el color, con `Light.at`, y el radio del halo, de 10 a 22 unidades del plano.
- El rojo sigue siendo solo para el peligro, y la luz solo para lo que es del jugador: la experiencia, el borde y la tarjeta elegida.

### Las medidas

Medidas por Claude el 2026-11-25. El contraste es el de WCAG 2.1. El daltonismo se simuló con las matrices de Machado, Oliveira y Fernandes (2009) con severidad 1, y la distancia es ΔE de CIELAB 1976 contra el rojo simulado igual.

| Color | Fondo | Contraste | ΔE con el rojo | Deuteranopía | Protanopía |
|---|---|---|---|---|---|
| `#3ad2c2` | negro | 11,2:1 | 128 | 67 | 49 |
| `#4cb6e0` | negro | 9,1:1 | 122 | 92 | 69 |
| `#5e9afe` | negro | 7,5:1 | 124 | 117 | 92 |
| `#0e8c82` | blanco | 4,1:1 | 119 | 66 | 37 |
| `#1673aa` | blanco | 5,2:1 | 118 | 100 | 71 |
| `#1e5ad2` | blanco | 6,1:1 | 128 | 130 | 101 |

Todos pasan el 3:1 que WCAG pide a lo que no es texto (criterio 1.4.11). Una ΔE sobre 10 ya se distingue a simple vista. La menor, 37, es la del verde azulado oscuro con protanopía.

### Consecuencias

- Bueno: el valor de cada punto se lee de un vistazo, y el rojo sigue significando una sola cosa.
- Bueno: el fondo blanco tiene su luz, y nada se dibuja distinto según el fondo.
- Bueno: los seis colores viven en `render/palette.py`.
- Malo: ya no es "un solo color de acento". Cada color nuevo tiene que medirse contra los dos que hay.
- Malo: son seis valores que cuidar, y no tres. Cambiar el tono es cambiar dos filas.
- Malo: sobre el blanco, el halo se ve como una mancha suave, menos brillante que sobre el negro.

### Confirmación

- En `render/` y `scenes/`, ningún color se escribe fuera de `render/palette.py`, salvo el magenta de depuración (ADR 0023). Se revisa en el PR.
- `poe capturas --escenario experiencia` y `--escenario experiencia-invertida` muestran la fila de puntos de 1 a 3, con la luz que crece y cambia de tono, y el borde cargándose, sobre cada fondo.
- `Palette.inverted()` deja el acento igual y cambia `ON_BLACK` por `ON_WHITE`. Invertir dos veces da la paleta de partida.

## Pros y contras de las opciones

### La misma luz sobre los dos fondos
- Bueno: tres colores, y no seis.
- Malo: el verde azulado claro sobre el blanco tiene un contraste de 1,9:1. El punto que menos vale casi no se vería.

### La luz más oscura sobre el blanco, con el mismo tono
- Bueno: se lee sobre los dos fondos, y el significado no cambia: verde azulado es poco, azul es mucho.
- Malo: seis valores que mantener.

### El negativo de la luz
- Bueno: no hay casos especiales: es lo mismo que hace el ADR 0023 con el fondo y el trazo.
- Malo: el negativo del verde azulado y del azul tira a rojo y naranja, los colores del peligro. Es justo lo que hay que evitar.

### Sobre el blanco, solo el punto de color, sin halo (no discutida)
- Bueno: un punto de color se ve bien sobre el blanco, sin manchas.
- Malo: el tamaño ya no diría el valor, y la decisión 4 pide leerlo dos veces. Las dos versiones se dibujarían distinto.

## Preguntas abiertas

- Si el halo del punto que menos vale, el más chico, se distingue de una bala del jugador con el enjambre lleno. Se mira en la prueba manual y en el afinado (tarea 20 del plan).

## Más información

- Spec de la 0.3.0, decisiones 4, 5 y 12: `docs/specs/2026-11-25-version-0-3-0.md`.
- WCAG 2.1, criterio 1.4.11, "Non-text Contrast": https://www.w3.org/TR/WCAG21/#non-text-contrast. No se volvió a abrir en esta sesión.
- G. M. Machado, M. M. Oliveira y L. A. F. Fernandes, "A Physiologically-based Model for Simulation of Color Vision Deficiency", IEEE TVCG 15(6), 2009. Las matrices se usaron de memoria, sin volver a la fuente en esta sesión.
- Issue #97: "La experiencia".
