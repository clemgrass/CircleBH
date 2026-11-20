---
estado: aceptado; que los enemigos choquen como círculos lo reemplaza el ADR 0020
fecha: 2026-11-18
---

# Detectar colisiones con círculos y una grilla espacial

## Contexto y problema

En un bullet hell hay cientos de cuerpos a la vez. Con 50 proyectiles y 300 enemigos, revisar todos contra todos son 15.000 pares por paso. En Python puro, eso estimamos que cuesta unos 5 ms de los 16,6 ms de un frame (no medido). Hay que decidir qué forma tiene cada cuerpo al chocar y cómo se buscan los pares.

## Factores de decisión

- Rendimiento: 60 FPS con la pantalla llena.
- Que se pueda testear y que la matemática quede a la vista en el código.
- Evitar APIs experimentales.

## Opciones consideradas

- Círculos con fuerza bruta: medir y optimizar después
- Círculos con una grilla espacial desde el inicio
- `pygame.geometry` (`Circle`, `collidecircle`)
- Un hitbox igual al polígono dibujado (no discutida)

## Resultado de la decisión

- **Grilla espacial desde el inicio:** primero descarta los pares que están lejos.
- **Cada cuerpo choca como un círculo**, aunque se dibuje como polígono.
- **Funciones propias en `world/`:**
  - círculo contra círculo;
  - segmento contra círculo, para la recta;
  - anillo contra círculo, para el círculo que se expande;
  - prueba polar para los pétalos de la rosa: un enemigo en `(r, θ)` está dentro si `r ≤ R·|cos(kθ)|`.
- **Benchmark:** un comando, no un test, mide los milisegundos por paso en un escenario cargado. La meta es 60 FPS.

### Consecuencias

- Bueno: rinde desde el primer día.
- Bueno: las colisiones de cada arma salen de su fórmula.
- Malo: la grilla suma unas 40 líneas y es una fuente típica de errores en los bordes de las celdas.
- Malo: el hitbox circular no calza exacto con el polígono dibujado. La diferencia se nota poco (no verificado jugando).

### Confirmación

- Un test de Hypothesis comprueba que, con cualquier conjunto de posiciones, la grilla encuentra exactamente los mismos pares que la fuerza bruta.
- El comando de benchmark muestra que la meta de 60 FPS se cumple. Se corre a mano, porque en la CI un test de tiempo sería inestable.

## Pros y contras de las opciones

### Fuerza bruta, medir y optimizar después
- Bueno: es lo más simple.
- Malo: está en el límite del presupuesto del frame.

### Grilla desde el inicio
- Bueno: rinde ya.
- Malo: es más código antes de saber si hace falta.

### `pygame.geometry`
- Bueno: está hecho en C.
- Malo: es un módulo experimental.
- Malo: no cubre el anillo ni la rosa.
- Malo: saca la matemática del código que se muestra.

### Hitbox igual al polígono (no discutida)
- Bueno: es exacto.
- Malo: es mucho más caro, cambia con cada lado perdido y no se nota al jugar.

## Más información

- https://pyga.me/docs/ref/geometry.html (módulo experimental; consultado el 2026-11-18)
