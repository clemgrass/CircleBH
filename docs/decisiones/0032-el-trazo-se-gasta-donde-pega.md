---
estado: aceptado
fecha: 2026-11-26
---

# El trazo se gasta donde pega

Reemplaza, del [ADR 0029](0029-armas-por-terminos-y-tarjetas.md), la regla de "la pasada" en "Cómo dañan los trazos". El resto del barrido sigue igual: cada punto de la curva es una bala durante un paso, probada con `Enemy.hit_by`.

## Contexto y problema

El círculo llegó con la regla de la pasada del ADR 0029 (#100): una pasada dura mientras la curva toca al enemigo, y en ella le quita a lo más `payload.lines`. Para tocar se contaba el envolvente del enemigo, agrandado en medio grosor del trazo.

En la prueba manual del 2026-11-26, el autor encontró que *(palabras del autor, resumidas)*:

1. no se ve cuándo hay contacto;
2. la línea es muy gruesa y quita claridad;
3. el círculo se siente demasiado poderoso;
4. parece que sigue para siempre: cada anillo vivía 3,6 s, y había dos a la vez;
5. la línea daña al entrar, pero después queda encima del enemigo y deja de dañar, y eso se siente raro.

El punto se lee bien porque la bala desaparece al pegar. El autor quiere que los trazos se sientan igual de claros, y que el criterio valga para todas las armas de trazo.

## Factores de decisión

- Que el contacto se vea en el mismo momento en que pasa, sin efectos aparte.
- Que una curva nunca quede encima de un enemigo sin dañarlo.
- Que un trazo no quite más líneas por segundo que el punto, ni en el peor caso, al menos al empezar.
- Que siga siendo la física de la bala: `hit_by`, los huecos de las figuras abiertas y el orden en que la curva barre.
- Que sirva igual para la recta, la rosa y lo que se sume después.

## Opciones consideradas

- A: el trazo se gasta donde pega
- B: mantener la pasada y sumar señales (un destello, una línea más fina y menos duración)
- C: el trazo entero se rompe al primer contacto

## Resultado de la decisión

Elegimos **A: el trazo se gasta donde pega** *(decisión del autor, 2026-11-26)*.

- **Cada punto de muestra sigue siendo una bala durante un paso.** Cuando cruza una línea de un enemigo, la quita, igual que el punto. Una curva quita a lo más `payload.lines` líneas por contacto con un enemigo: el primer cruce, en el orden en que barre.
- **Al pegar, el arco que cubre a ese enemigo desaparece.** En un trazo polar es el arco que el enemigo tapa visto desde el jugador: si está a distancia `d`, en la dirección φ, con radio envolvente `r`, es `θ ∈ [φ − asin(r/d), φ + asin(r/d)]`. Con `d ≤ r` es la curva entera. En un trazo cartesiano lo precisa la recta (#101). El hueco queda en la curva mientras dure: no vuelve a dibujarse ni a dañar. Por eso la curva nunca queda encima de un enemigo sin dañarlo, y el hueco es la señal del contacto.
- **El resto de la curva sigue** y puede pegarle a otros enemigos.
- **El hueco se guarda en el parámetro de la curva,** no en el índice del punto. En el anillo es un intervalo de θ, porque la cantidad de puntos cambia al crecer.
- *Corregido el 2026-11-26, antes de llegar a `main`, con el acuerdo del autor:* la primera versión gastaba solo los puntos que quedaban dentro del envolvente en el paso del golpe. Al pegar en la cara, eso cubre menos ángulo que el enemigo, y los bordes del anillo le seguían pegando.
- **El grosor del trazo es solo visual.** Ya no cuenta para tocar, porque no hay pasada.
- **Los números iniciales del círculo** *(decisión del autor)*:
  - `advance (200, 1)` y `R = 200`: el anillo vive 1 s;
  - `payload.width = 2`, el grosor de los enemigos;
  - `cooldown = 15,6 s`. Es el máximo de enemigos que un anillo puede tocar de una vez, por el cooldown del punto. En A, un enemigo de radio `r` a distancia `d` se lleva un arco de `2·asin(r/d)`. Caben más cuando están todos en el borde, así que el máximo es `⌊π / asin(r/R)⌋`, 26 con el hexágono, y `26 × 0,6 s = 15,6 s`. Así, al empezar, el anillo no quita más líneas por segundo que el punto, ni en el peor caso. Es un valor inicial: es un daño en área muy fuerte, y se afina al medir el balance (ADR 0030).

### Consecuencias

- Bueno: el contacto se ve en el hueco, en el paso en que pasa, como la bala que desaparece.
- Bueno: no queda una curva encima de un enemigo sin dañarlo.
- Bueno: un anillo le pega una vez a cada enemigo, y con el cooldown del máximo, no supera al punto al empezar.
- Bueno: es más simple que la pasada: no hay "tocar", ni pasadas guardadas por enemigo.
- Malo: con 15,6 s, el anillo sale cada cuatro compases, más o menos. Puede sentirse ausente hasta afinarlo.
- Malo: un enemigo encima del jugador, a una distancia menor que su radio, se lleva el anillo entero al pegar.
- Malo: la rosa, que dura siempre, se va gastando. Hay que ver en su tarea (#103) si se renueva.

### Confirmación

- Un test comprueba que el anillo que crece sobre un hexágono le quita la cara que mira al jugador, y que después el anillo tiene un hueco sobre él.
- Un test comprueba que el anillo no le quita la línea de atrás al hexágono que ya golpeó.
- Un test comprueba que, en el mismo anillo, otro enemigo en otra dirección también recibe su golpe.
- Un test comprueba que un punto del hueco no daña ni se dibuja.
- Un test comprueba que una curva que pasa por un hueco de una figura abierta no daña.
- `poe capturas --escenario circulo` muestra el anillo con huecos donde pegó.

## Pros y contras de las opciones

### A: el trazo se gasta donde pega
- Bueno: es la misma idea que la bala, y se lee igual.
- Bueno: el hueco marca el contacto sin un efecto aparte.
- Malo: la curva se ve rota después de pegar, y una curva muy gastada se ve poco.

### B: mantener la pasada y sumar señales
- Bueno: es el cambio más chico.
- Malo: la curva sigue encima del enemigo sin dañarlo, que es lo que se siente raro.
- Malo: el destello es un efecto aparte que hay que diseñar y afinar.

### C: el trazo entero se rompe al primer contacto
- Bueno: es lo más claro posible.
- Malo: el trazo se vuelve una bala gorda y pierde el barrido a varios enemigos.
- Malo: la rosa y el escudo durarían un golpe.
