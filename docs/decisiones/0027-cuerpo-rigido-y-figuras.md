---
estado: aceptado
fecha: 2026-11-21
---

# Los enemigos giran como cuerpos rígidos, y no todos son polígonos regulares

Reemplaza en parte al ADR 0020 en dos puntos:
- el tramo de la bala se mide en el marco del enemigo, que ahora también gira;
- los sectores angulares sirven solo para los polígonos regulares.

Lo demás del 0020 sigue igual: las líneas, la envolvente como primer descarte, el primer cruce y el empate por índice.

## Contexto y problema

En la 0.1.0, un enemigo es un polígono regular que solo se traslada (ADR 0020). La 0.2.0 trae enemigos que el modelo no cubre (spec de la 0.2.0, "Lo que cambia en el motor"):

- **El cuadrado y el pentágono giran.** El usuario pidió que el cuadrado gire y que, al perder líneas, "pierda el equilibrio y gire raro" (decisión 3).
- **La estrella y el círculo no son polígonos regulares.** La estrella tiene 10 líneas, y el círculo, una sola línea curva.
- **El círculo pesa más de lo que indican sus líneas.** Si su masa fuera su única línea, cualquier vecino lo sacaría disparado.

Hay que decidir cómo gira un enemigo, cómo se mide el golpe de una bala en un cuerpo que gira, qué pasa cuando pierde una línea y cómo se descartan las líneas de una figura que no es regular.

## Factores de decisión

- Que la bala quite la línea que de verdad golpea, también si el enemigo gira.
- Que los enemigos sin giro sigan exactamente igual que en la 0.1.0.
- Que cada conducta salga de una idea matemática (decisión 14), escrita como su fórmula.
- Que se pueda testear con propiedades, sin depender de valores concretos.
- Rendimiento: un paso por bala y por enemigo, sin subpasos.

## Opciones consideradas

Dónde se declara el giro:

- G1: un campo `spin` del tipo de enemigo
- G2: un patrón `spin`, como `seek` y `coulomb`

Cómo se mide el golpe con giro:

- T1: el tramo recto entre la pose de antes y la de ahora, en el marco del enemigo
- T2: subpasos, con la pose interpolada
- T3: el cruce exacto contra la curva de la bala en el marco del enemigo (no discutida)

Qué pasa con el giro al perder una línea:

- L1: el resto conserva su momento angular, `I·ω`, así que gira más rápido
- L2: el giro no cambia, y el resto gira en torno a su nuevo centro de masa
- L3: nada cambia: sigue girando en torno al centro del polígono (no discutida)

Cómo se descartan las líneas de una figura que no es regular:

- F1: la envolvente y después todas las líneas
- F2: sectores angulares generalizados a cualquier figura

## Resultado de la decisión

**G1, T1, L2 y F1.** L2 es decisión del usuario (2026-11-21).

- **G1:** `EnemySpec.spin` es la velocidad angular al aparecer, en rad/s, antihoraria si es positiva. Con 0 no gira. Se desvía de la spec, que lo proponía como patrón: los patrones son aceleraciones lineales que se suman (ADR 0021), y una velocidad angular inicial no lo es.
- **La pose:** cada enemigo tiene `angle` y `omega`, y `step` hace `θ ← θ + ω·dt`. Todos parten con `θ = 0`. Como aparecen en pasos distintos, igual se ven desfasados, y no se gasta azar del mundo.
- **El marco del enemigo:** un punto `q` del enemigo está en el plano en `c + R(θ)·q`, y un punto `p` del plano se ve desde el enemigo como `R(−θ)·(p − c)` (`world/rigid.py`).
- **T1:** el tramo de la bala va de `start`, con la pose de antes, a `end`, con la de ahora, ambos en el marco del enemigo. Sobre ese tramo siguen los sectores y el primer cruce del ADR 0020.
  - Sin giro, es el tramo relativo de la 0.1.0, y es exacto.
  - Con giro, el camino de la bala en el marco del enemigo es una curva. El tramo recto se aparta de ella a lo más `(2·|w|·|Δr| + w²·|r|) / 8`, con `w = ω·dt`: la cota del error de interpolar lineal, `max|q''| / 8`. Con el cuadrado del balance (`ω = 1,5`) y una bala a 300 unidades/s, son unas 0,05 unidades.
  - El balance exige `|ω·dt| ≤ 0,1`, el rango que verifican los tests.
- **L2:** al perder una línea, el enemigo que gira sigue con el mismo `ω`, como cuando un cuerpo se rompe: la línea que se suelta se lleva su parte del momento angular. Lo que queda gira en torno a su nuevo centro de masa `c'`, con la masa de cada línea en su punto medio. Ese centro hereda la velocidad que tenía su punto, `v' = v + ω × (c' − c)`, y las líneas no se mueven en el plano en ese paso. Los enemigos sin giro no cambian (spec de la 0.1.0, decisión 15). Llega con el #55.
- **F1:** las figuras que no son polígonos regulares descartan con la envolvente y después revisan todas sus líneas. Llegan con la estrella (#58).
- **`mass_per_line`:** la masa de un enemigo es `mass_per_line` por sus líneas. Vale 1 para todos menos el círculo, así que la regla de la 0.1.0, "masa = carga = líneas", queda como el caso con 1. Llega con el círculo (#59).

### Consecuencias

- Bueno: el hexágono, que no gira, golpea igual que antes.
- Bueno: el golpe con giro cuesta lo mismo que sin giro: dos rotaciones más por bala.
- Bueno: la bala sigue sin poder atravesar una línea entre dos pasos.
- Malo: con giro, el golpe es aproximado. Cerca de un vértice, o si la bala termina justo sobre una línea, puede tocarle la vecina o el paso siguiente.
- Malo: el giro tiene un tope en el balance. Un enemigo que gire más rápido necesita subpasos (T2).
- Malo: `θ = 0` al aparecer hace que todos los cuadrados nazcan como rombo.
- Bueno: con L2, `ω` nunca pasa de `spin`, así que el golpe con giro sigue dentro de lo verificado.
- Malo: con L2, el herido no gira más rápido. La herida se nota en el tambaleo, que con pocas líneas perdidas es sutil.

### Confirmación

- Un test de Hypothesis comprueba que, sin giro, `hit_by` da lo mismo que el tramo relativo de la 0.1.0 (`test_sin_giro_golpea_igual_que_antes`).
- Un test de Hypothesis comprueba que, con `|ω·dt| ≤ 0,1`, la línea golpeada es la misma que con 16 subpasos, fuera de los casos ambiguos: a menos del doble de la cota de un vértice, con un extremo del tramo sobre una línea, o rasante (`test_golpe_con_giro_coincide_con_subpasos`).
- Un test del balance comprueba que cada enemigo cumple `|spin·dt| ≤ 0,1`.
- Tests del ángulo: avanza `ω·dt` por paso, el giro negativo es horario, y sin giro no cambia.
- Un test comprueba que el jugador toca una línea girada que sin giro no tocaría.
- La pérdida de equilibrio (#55), las figuras (#58) y `mass_per_line` (#59) suman sus tests en su issue.

## Pros y contras de las opciones

### G1: campo `spin`
- Bueno: el giro queda a la vista en el balance, al lado de `speed` y `friction`.
- Bueno: no mezcla una condición inicial con fuerzas que se suman.
- Malo: si un ataque futuro necesita un torque, va a necesitar otra capa.

### G2: patrón `spin`
- Bueno: es lo que decía la spec.
- Malo: un patrón aporta una aceleración en cada paso. Un giro inicial no encaja ahí.

### T1: tramo recto en el marco del enemigo
- Bueno: reusa los sectores y el primer cruce del ADR 0020 sin cambios.
- Bueno: un solo cálculo por bala y por enemigo.
- Malo: es aproximado con giro, y el error crece con `ω·dt`.

### T2: subpasos
- Bueno: el error baja con el cuadrado de la cantidad de subpasos.
- Malo: cuesta tantas veces más como subpasos haya, para un error que con estos giros no se ve.

### T3: cruce exacto contra la curva (no discutida)
- Bueno: exacto.
- Malo: es una ecuación trascendente por línea, sin fórmula cerrada. Hay que resolverla numéricamente.

### L1: conservar `I·ω` del resto
- Bueno: se nota: cada línea perdida lo hace girar más rápido.
- Malo: no es lo que pasa cuando un cuerpo se rompe. La línea que se suelta se lleva su parte del momento angular, y el resto sigue con el mismo `ω`. Conservar `I·ω` es lo de una patinadora que encoge los brazos: la masa se mueve, pero no se va.
- Malo: con un cuadrado de lados iguales, `I` baja hasta 16 veces, de `4L²/3` a `L²/12`. Con `ω = 1,5`, la última línea giraría a 24 rad/s, y `ω·dt = 0,4` pasa el tope de T1. Hay que acotar `ω` o usar subpasos.

### L2: mismo `ω`, nuevo centro de masa
- Bueno: es la física de una ruptura. El resto gira en torno a su nuevo centro de masa, que hereda la velocidad del punto donde estaba, `ω × (c' − c)`.
- Bueno: `ω` nunca pasa de `spin`, así que T1 sigue dentro de su tope.
- Malo: no gira más rápido. Lo que cuenta la herida es el tambaleo: la figura gira descentrada.

### L3: nada cambia (no discutida)
- Bueno: no hay nada que construir.
- Malo: no cumple la decisión 3: no pierde el equilibrio.

### F1: envolvente y todas las líneas
- Bueno: simple, y la estrella tiene solo 10 líneas.
- Malo: con figuras de muchas líneas, revisa todas.

### F2: sectores generalizados
- Bueno: escala a figuras grandes.
- Malo: una línea de la estrella cruza varios sectores, y hay que mapear cada sector a varias líneas. Es más código para un ahorro que con 10 líneas no se nota.

## Más información

- ADR 0020, "Los enemigos son líneas y chocan por segmentos".
- ADR 0021, "Los enemigos se mueven por patrones del balance, con cargas e inercia".
- Spec de la 0.2.0, decisiones 3 y 14, y "Lo que cambia en el motor".
