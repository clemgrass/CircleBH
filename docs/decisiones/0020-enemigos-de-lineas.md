---
estado: aceptado
fecha: 2026-11-19
---

# Los enemigos son líneas y chocan por segmentos

Reemplaza en parte al ADR 0006: la regla "cada cuerpo choca como un círculo, aunque se dibuje como polígono" deja de valer para los enemigos. El resto del ADR 0006 sigue vigente: la grilla espacial, las funciones propias en `world/` y el benchmark.

## Contexto y problema

En la 0.1.0, el usuario decidió que los enemigos están hechos de líneas (spec de la 0.1.0, decisión 15). Cada línea es una parte del enemigo, y una bala quita la línea exacta que golpea. Así, la forma que queda depende de dónde le pegaste, y un enemigo herido puede quedar abierto, con huecos.

El ADR 0006 hace chocar a cada enemigo como un círculo, y descartó un hitbox igual al polígono por caro. Con líneas que se pierden una a una, el círculo no puede decir qué línea se golpeó. Hay que decidir cómo se detecta el golpe y cómo se mantiene barato cuando haya muchos enemigos y balas a la vez.

## Factores de decisión

- Saber qué línea golpeó cada bala, sin ambigüedad.
- Que una bala rápida no atraviese una línea entre dos pasos.
- Rendimiento: es un bullet hell, y la meta es 60 FPS con la pantalla llena (ADR 0006).
- Que la matemática quede a la vista y se pueda testear.

## Opciones consideradas

- Segmentos, con el círculo envolvente como primer descarte y sectores angulares
- Segmentos, con el círculo envolvente y revisando todas las líneas
- Segmentos, con una caja envolvente en vez del círculo
- Seguir con el círculo y quitar una línea cualquiera en cada golpe (no discutida)

## Resultado de la decisión

Elegimos **segmentos, con el círculo envolvente y sectores angulares**:

- **Cada enemigo es una lista de líneas**, las aristas `k` de su polígono regular, de su vértice `k` al `k + 1` (`regular_polygon`, ADR 0003). Una línea golpeada se quita, y el enemigo sin líneas desaparece.
- **El círculo envolvente** tiene el radio del polígono completo y contiene todas sus líneas. Es el primer descarte: si el cuerpo no toca el círculo, no se revisa ninguna línea. Es la pieza que usa la grilla del ADR 0006.
- **La bala es un punto, y se prueba su tramo, no su posición.** Un punto nunca cae justo sobre una línea. Por eso, en cada paso se cruza el tramo que recorrió la bala con las líneas del enemigo, medido desde el enemigo: como el enemigo solo se traslada, el tramo relativo va de `p₀ − e₀` a `p₁ − e₁`. El golpe es la primera línea que cruza ese tramo (el menor parámetro `t`). Si dos líneas empatan, por ejemplo en un vértice, gana la de índice menor.
- **Los sectores angulares eligen qué líneas revisar.** La arista `k` cae entera dentro del sector `k`, el que va de `π/2 + 2πk/n` a `π/2 + 2π(k + 1)/n` visto desde el centro. A lo largo de un tramo que no pasa por el centro, el ángulo cambia de forma monótona y barre menos de `π`. Por eso solo se revisan los sectores que cubre ese barrido, más uno a cada lado para absorber el redondeo en los bordes. Si el tramo pasa por el centro, o cerca, se revisan todas.
- **El jugador muere al tocar una línea**, círculo contra segmento: la distancia de su centro al punto más cercano del segmento no pasa su radio. El círculo envolvente también sirve de primer descarte aquí. Los sectores no se usan para el contacto: hay un solo jugador.
- **A futuro:** un enemigo muy grande puede usar varios subcírculos envolventes, uno por grupo de líneas, en vez de uno solo. No se construye ahora.

### Consecuencias

- Bueno: lo que se ve es lo que choca, y la forma del enemigo cuenta dónde le pegaron.
- Bueno: el tramo hace imposible que una bala atraviese una línea entre dos pasos, sin depender de su velocidad.
- Bueno: los sectores ya están listos para el jefe. Medido el 2026-11-19 en Python 3.14.10 con pygame-ce 2.5.8: la prueba exacta contra 6 líneas cuesta unos 6,5 µs por bala, y contra 100 líneas, unos 121 µs. La envolvente cuesta unos 0,46 µs por par.
- Malo: más código y más casos borde que un círculo. Los vértices y los tramos que cruzan dos sectores son los típicos.
- Malo: los sectores no ahorran casi nada con 6 líneas. Se hacen ahora, por decisión del usuario, para no tener que cambiar el modelo cuando llegue el jefe.
- Malo: una figura abierta deja pasar balas por sus huecos, y el jugador puede quedar dentro de un enemigo sin tocar sus líneas. El usuario lo aceptó como mecánica: el jugador tiene que moverse para encontrar el ángulo (spec de la 0.1.0, decisión 18).

### Confirmación

- Un test de Hypothesis comprueba que, con cualquier tramo y cualquier conjunto de líneas restantes, los sectores dan la misma línea golpeada que revisar todas.
- Un test de Hypothesis comprueba que el círculo envolvente nunca descarta un golpe que la prueba exacta encontraría.
- `world/collisions.py` tiene tests de la intersección de tramos (incluido el vértice y el extremo exacto) y del círculo contra un segmento (incluido el tangente).
- El comando de benchmark del ADR 0006, cuando exista, incluye un enemigo con muchas líneas.

## Pros y contras de las opciones

### Envolvente y sectores angulares
- Bueno: con muchas líneas, revisa unas pocas en vez de todas.
- Malo: los bordes entre sectores necesitan cuidado, y por eso llevan un test de propiedad.

### Envolvente y revisar todas las líneas
- Bueno: es lo más simple, y con 6 líneas cuesta casi lo mismo.
- Malo: con un jefe de 100 líneas, cada bala dentro de su envolvente cuesta unos 121 µs.

### Caja envolvente en vez de círculo
- Bueno: se ajusta mejor a figuras alargadas.
- Malo: son cuatro comparaciones en vez de una, cambia si el enemigo rota y la grilla ya usa círculos.

### Seguir con el círculo y quitar una línea cualquiera (no discutida)
- Bueno: no cambia el ADR 0006.
- Malo: la forma no dice dónde le pegaste, que es lo que pidió el usuario.

## Más información

- ADR 0006, "Detectar colisiones con círculos y una grilla espacial".
- Spec de la 0.1.0, decisiones 14 a 19.
