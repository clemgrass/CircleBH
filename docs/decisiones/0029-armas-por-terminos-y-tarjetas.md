---
estado: aceptado; la regla de la pasada la reemplaza el ADR 0032, y las seis armas, los trazos y la regla de no ofrecer una suma que da un arma que ya existe, el ADR 0033, y el marco cartesiano o polar y la forma de `WeaponSpec`, el ADR 0034
fecha: 2026-11-24
---

# Las armas se arman con tres términos y mejoran con tarjetas que cambian su forma

Amplía el ADR 0022 (el ritmo de un arma con copias), el 0025 (`Danger` y el presupuesto también fuera del modo infinito) y el 0021 (la experiencia siente la carga del jugador). No reemplaza nada de ellos.

## Contexto y problema

Hoy hay una sola arma, el punto (`PointWeaponSpec`: `cooldown`, `speed` y `range`). No hay experiencia, niveles, tarjetas ni anillos. El diseño pide armas-curva (recta, círculo, seno, espiral y rosa), tarjetas que muestran la fórmula y mejoras que salen de ideas matemáticas. Además:

- tiene que diferenciarse de los survivors donde dos armas al máximo se fusionan;
- tiene que evitar la anti-meta: un survivors común con una capa geométrica encima.

Para el MVP, el autor quiere el sistema de armas decidido entero, con las combinaciones incluidas (2026-11-24). Lo más valioso para él son las formas únicas que salen al combinar. También quiere saber cómo dañan exactamente los trazos. Y las armas y tarjetas tienen que poder cambiar al jugar, igual que los enemigos.

Hay que decidir:

- cómo se describe un arma;
- cómo mejora y cómo se combina;
- cómo dañan los trazos;
- cómo se cobran las mejoras con costo;
- qué mejoras hay fuera del ataque;
- cómo se asegura que las partidas lleguen a formas distintas.

La investigación completa, con fuentes, mediciones y la partida de ejemplo de cada modelo, está en `docs/investigaciones/2026-11-24-mejoras.md` (#88 y #89). El prototipo está en `docs/prototipos/mejoras_armas.html`.

## Factores de decisión

- Que mejorar cambie la forma o la ley del movimiento, no solo números *(anti-meta del diseño)*.
- Que combinar no funda armas *(decisión del autor, 2026-11-19)*.
- Que, eligiendo al azar en muchas partidas, se llegue a formas distintas *(objetivo del autor, 2026-11-24)*. La meta, o sea qué forma conviene, la decide el jugador.
- Que sea modular: armas, tarjetas, valores y precios cambian en `balance.json` sin tocar código *(decisión del autor, 2026-11-24; ADR 0004)*.
- Que la tarjeta muestre la fórmula, aunque no haga falta entenderla para elegir *(diseño)*.
- Que una mejora se oiga *(ADR 0022)*.
- Que sea determinista y testeable *(ADR 0005 y 0007)*.
- Que quepa en la CPU *(#42)*.

## Opciones consideradas

Cómo mejora y se combina un arma (los modelos del informe):

- M1: perillas. Cada tarjeta cambia un parámetro de la fórmula
- M2: suma de términos. Combinar es sumar
- M3: operadores (`d/dt`, `∫dt`, `Cₙ`, reflejo, paralela)
- M4: cadena de trayectoria, forma y disparador, como en Noita
- M5: una familia, la superfórmula de Gielis
- M6: una función de varias variables, `F(x, t, v)`
- M7: iteración fractal, con L-systems

Cómo se cobra:

- M8: una capa de precios sobre cualquier tarjeta
- Sin mejoras con costo (no discutida)

Cómo dañan los trazos:

- A: barrido
- B: corte
- C: contacto por pulso

Cómo se asegura la variedad:

- Valores por semilla, una mano que favorece las formas y un test de variedad
- Confiar en el diseño de las tarjetas, sin medir (no discutida)

## Resultado de la decisión

**M1, M2 y M3 para mejorar y combinar, M8 para cobrar, el barrido para dañar y las tres palancas de variedad** *(decisiones del autor, 2026-11-24)*.

### Un arma son tres términos en un marco

Las seis armas se escriben con los mismos tres términos *(hallazgo de la investigación)*:

- **Avance `a(t)`:** un polinomio en t, como `v·t`.
- **Armónico `A·sin(k·u + φ)`:** u es el tiempo en un proyectil y la posición sobre la curva en un trazo.
- **Giro `Ω·t`.**

Cada arma es un **proyectil** o un **trazo**, y se mueve en un marco **cartesiano** (a lo largo de una dirección `û`) o **polar** (alrededor del jugador).

| Arma | Tipo | Marco | Términos |
|---|---|---|---|
| Punto | proyectil | cartesiano | avance |
| Recta | trazo | cartesiano | avance |
| Seno | proyectil | cartesiano | avance + armónico |
| Círculo | trazo | polar | avance |
| Espiral | proyectil | polar | avance + giro |
| Rosa | trazo | polar | armónico + giro |

### Dos capas: la trayectoria y lo que viaja

- **La trayectoria es la fórmula.** Por lo general, la fórmula no cambia la bala misma: cambia cuántas salen, por dónde van y a qué velocidad *(matiz del autor)*.
- **Lo que viaja:**
  - en un proyectil, el tamaño, las líneas por golpe y cuántos atraviesa;
  - en un trazo, las líneas por pasada, la duración y el grosor.

  En un trazo, la curva entera daña, así que la trayectoria también es lo que golpea.

### Cómo mejora y se combina

- **M1, perillas:** un parámetro de cualquiera de las dos capas. Por ejemplo, "k sube a 5" o "quita una línea más".
- **M2, combinar es sumar un término que el arma no tiene.**
  - El término se adapta al marco del arma que lo recibe. Círculo + armónico es un anillo que ondula. Recta + giro es un faro.
  - Las dos armas siguen existiendo: nada se funde.
  - Una suma que da un arma que ya existe no se ofrece. Por ejemplo, punto + giro es la espiral.
- **M3, operadores sobre la trayectoria:**
  - `d/dt` baja un grado el avance (`v·t → v·τ`): el arma se queda contigo;
  - `∫dt` lo sube (`v·t → v·t²/2τ`): el arma acelera;
  - `Cₙ` hace n copias rotadas;
  - el reflejo hace una copia espejada respecto de `û`;
  - la paralela hace dos copias a `±d`.

  Derivar la forma no se usa, porque en el círculo y el seno no se ve.
- **El orden de los operadores es fijo:** `d/dt` o `∫dt`, después la paralela, después `Cₙ` y al final el reflejo. Dos partidas con las mismas tarjetas dan la misma arma, sin importar en qué orden se tomaron.
- **Lo que no tiene efecto no se ofrece.** `Cₙ` no se ofrece en un círculo sin armónico, ni el reflejo en un arma sin armónico ni giro.

### Cómo dañan los trazos: por barrido

- **Cada punto de la curva actúa como una bala durante un paso,** y se reusa `Enemy.hit_by` (ADR 0027). La línea que la curva barre primero se pierde. El cruce se mide en el marco del enemigo, así que un escudo quieto daña a quien choca contra él.
- **Una pasada** dura mientras la curva toca al enemigo, y quita a lo más `líneas por pasada`.
- **Una curva que pasa por un hueco de una figura abierta no daña.**

### Cómo se cobra (M8)

Cada tarjeta puede traer un precio, que es un dato. Hay cuatro tipos:

- **Presupuesto:** un factor sobre el presupuesto y la ráfaga de las secciones que quedan.
- **Contra en el arma:** dentro del operador, como `d/dt`.
- **Sobre el enemigo:** los multiplicadores `Danger`, que ahora valen en toda la partida y en las dos direcciones (< 1 frena, > 1 apura), y los pesos del mazo.
- **Con duración:** un efecto que dura una cantidad de compases.

Una herramienta manual, como `poe benchmark`, reporta lo que cada tarjeta gana en líneas por segundo junto a lo que cobra en amenaza por compás. Los precios se afinan jugando (#90).

### Fuera del ataque (#89)

| Mejora | Qué cambia | Cómo funciona |
|---|---|---|
| Velocidad | `PlayerSpec.speed` | — |
| Radio menor | `PlayerSpec.radius` | Los anillos quedan a `r₀ + i·Δ`, así que achicar el núcleo los achica a todos |
| Carga | `PlayerSpec.charge` | La experiencia siente la carga con la ley de Coulomb: atrae la experiencia y al enjambre a la vez. No hay un radio de recogida aparte |
| Anillo extra | Una vida más como tarjeta | Te agranda |
| Control de la mano | Reroll y banish | Con usos limitados en el balance. El banish lleva pocos, para cuidar la variedad |

### Variedad

- **Valores por semilla.** El valor que trae una tarjeta sale de una lista del balance, elegido con la `Random` del mundo. Por ejemplo, k en {3, 5, 7, 5/2}.
- **Una mano que favorece las formas.** Al menos una tarjeta de la mano cambia la clase de forma.
- **Un test de variedad.** Juega N partidas con tarjetas al azar y mide la clase de forma final: la estructura de la fórmula y los k, sin lo que solo escala. Falla si la más común pasa de un tope o si `2^H` baja de un piso.

  Con el prototipo y 8 tarjetas, ninguna forma pasa del 8,2 % y hay entre 130 y 584 clases distintas por arma (informe, sección "Variedad").

### Las decisiones menores *(propuestas de Claude; el autor las revisa al aceptar)*

- **La mano trae 3 tarjetas,** como dice el diseño. Una tarjeta puede dar un arma nueva o mejorar una que ya tienes.
- **Hay hasta 4 armas a la vez.** Es un número del balance.
- **Cómo se apilan los números:**
  - las tasas se multiplican (`v × 1,25`, `cooldown × 0,8`);
  - las cantidades se suman (n de `Cₙ`, líneas y atraviesa).

  Dentro de una misma capa, lo que suma va antes que lo que multiplica.

### Sin topes en el juego final *(decisión del autor, 2026-11-24)*

- **No hay topes de mejora ni de rendimiento.** No hay un máximo para n de `Cₙ`, ni para los puntos de muestra de un trazo, ni para cuánto sube un parámetro. La razón: la experiencia no tiene que depender del computador. Un tope medido en una máquina hace que el juego dependa de esa máquina.
- **Si una combinación no cabe en el cuadro, es un problema de optimización, no de diseño.** Lo resuelve el #42, que pasa a revisar a fondo el rendimiento de todo el juego.
- **Los topes de rendimiento quedan solo como depuración,** en la configuración (ADR 0018), y no cambian una partida normal.
- **Siguen los límites que vienen de la matemática del juego:**
  - el `cooldown` no baja de un paso, 1/60 s (ADR 0005);
  - el ritmo tiene 16 semicorcheas (ADR 0022).
- **El ritmo:** un arma con `Cₙ` suena con `E(min(16, disparos por compás · n), 16)`. Una rosa sin avance suena con sus pétalos. La voz sigue saliendo del `spec` (ADR 0022).
- **El código:** `Weapon` sigue siendo la base, con dos hijas, `ProjectileWeapon` y `TraceWeapon` (herencia simple, como pide `AGENTS.md`). Las dos leen un mismo `WeaponSpec` con los términos, los operadores, lo que viaja y el `cooldown`. Mejorar sigue siendo reemplazar el `spec`.
- **En el balance:** las armas, las tarjetas con sus valores por semilla y sus precios, los anillos y los usos de reroll y banish entran a `balance.py` y `balance.json`, coordinados (ADR 0004).
- **El modo infinito sigue sin mejoras** (spec de la 0.2.0). Los precios ya tomados siguen valiendo en él.

### Consecuencias

- Bueno: cada tarjeta de forma cambia lo que se ve, y la anti-meta queda lejos.
- Bueno: combinar no funde y no hay que escribir cada mezcla a mano. Un arma nueva solo declara sus términos.
- Bueno: todo es dato, así que armas y tarjetas cambian al jugar sin tocar código.
- Bueno: el barrido no suma una regla de daño: es la misma física de la bala.
- Bueno: la variedad se mide y un test la protege.
- Malo: es mucho sistema para el MVP. El #91 tiene que partirlo en piezas.
- Malo: el barrido cuesta CPU, porque son muchos puntos de muestra por enemigo. Hay que filtrar con la grilla y medir (#42).
- Malo: sin topes, una combinación de tarjetas puede pasarse de los 16,6 ms del cuadro en un computador lento. Hasta que el #42 lo resuelva, el juego corre más lento en ese computador.
- Malo: el anillo rinde mucho más que un proyectil, porque toca a todos a la vez. Equilibrarlo es trabajo del #90.
- Malo: la medición de variedad cuenta firmas, y dos firmas distintas pueden verse casi iguales.
- Malo: `Danger` sale del modo infinito, y la sección `endless` comparte el mecanismo con los precios.

### Confirmación

**Tests de las armas:**
- Un test comprueba que cada arma de `balance.json` se arma con sus términos, y que su posición en un tiempo dado es la de su fórmula (por ejemplo, el punto da `p₀ + v·t·û`).
- Un test de Hypothesis comprueba que `d/dt` baja un grado el avance, que `∫dt` lo sube, y que uno deshace al otro.
- Un test de Hypothesis comprueba que cualquier orden de las mismas tarjetas de operador da el mismo `spec`.
- Un test comprueba que no se ofrecen tarjetas sin efecto: `Cₙ` en un círculo sin armónico, el reflejo en el punto, y el giro en el punto.

**Tests del daño:**
- Un test comprueba que un anillo que crece sobre un hexágono le quita la línea que mira al jugador.
- Un test comprueba que una pasada no quita más de `líneas por pasada`.
- Un test comprueba que un escudo quieto daña a un enemigo que avanza hacia él.
- Un test comprueba que una curva que pasa por un hueco no daña.

**Tests de la variedad:**
- Un test de propiedades comprueba la variedad: con N partidas al azar, la forma más común no pasa del tope y `2^H` no baja del piso.
- Un test comprueba que la misma semilla da los mismos valores de tarjeta, y que la mano trae al menos una tarjeta de forma cuando hay alguna.

**Tests de los precios:**
- Un test comprueba que el precio de presupuesto multiplica el de las secciones que quedan.
- Un test comprueba que `Danger` < 1 frena a los enemigos.
- Un test comprueba que un precio con duración termina en su compás.

**Tests fuera del ataque:**
- Un test comprueba que, con más carga, la experiencia y los enemigos sienten más atracción.
- Un test comprueba que los anillos quedan a `r₀ + i·Δ` y que la tarjeta de radio los achica a todos.

**Comandos:**
- `lint-imports` comprueba que las armas y las tarjetas viven en `world/` y no importan `render` ni `audio`.
- `poe balance-chequear` falla si las armas, las tarjetas o sus precios no calzan entre `balance.py` y `balance.json`.
- `poe benchmark` reporta el costo del barrido con los trazos (#42).
- Una búsqueda de `max`, `cap` y `tope` en las armas, las tarjetas y `PlayerSpec` de `balance.py` no encuentra topes de mejora. Solo están los límites de la matemática: el `cooldown` mínimo de un paso y las 16 semicorcheas.
- La herramienta manual de precios reporta líneas por segundo contra amenaza por compás.

## Pros y contras de las opciones

### M1: perillas
- Bueno: es lo más simple y legible ("k sube a 5").
- Malo: solo, es lo más cercano a la anti-meta.

### M2: suma de términos
- Bueno: combina sin fundir, con una sola operación.
- Malo: la recta y la espiral no son periódicas, y hay que verlas como movimiento más forma. El dibujo y el choque pasan a ser polilíneas genéricas.

### M3: operadores
- Bueno: cambia la forma o la ley del movimiento, y trae la contra adentro (`d/dt` defiende, pero deja de matar).
- Malo: no todo operador aplica a toda arma, y las formas crecen rápido.

### M4: cadena tipo Noita
- Bueno: es lo más combinatorio.
- Malo: es lo más difícil de equilibrar y de leer, y los disparadores multiplican los choques.

### M5: superfórmula
- Bueno: habla el idioma de los enemigos (m = lados).
- Malo: no cubre al punto ni las trayectorias, y n₁, n₂ y n₃ son opacos en una tarjeta.

### M6: `F(x, t, v)`
- Bueno: es lo más fácil de medir.
- Malo: casi todo es numérico, y combinar no tiene una lectura natural.

### M7: fractal
- Bueno: cada nivel se ve al tiro.
- Malo: da pocos niveles (los segmentos crecen como `4ⁿ`), y todas las armas terminan pareciendo fractales.

### M8: precios
- Bueno: reusa el director y `Danger`, y lleva la idea del autor ("×2 trae más enemigos", "derivar frena a los enemigos").
- Malo: el presupuesto es abstracto y hay que afinarlo jugando.

### Sin mejoras con costo (no discutida)
- Bueno: es más simple.
- Malo: pierde una idea central del milestone.

### A: barrido
- Bueno: es la misma física que la bala, respeta los huecos y hace que importe por dónde barre la curva.
- Malo: cuesta CPU, y una recta quieta solo daña a lo que se le cruza.

### B: corte
- Bueno: es muy legible: el daño es la cantidad de cruces.
- Malo: ignora el orden en que llega la curva, y la rosa necesita inmunidad.

### C: contacto por pulso
- Bueno: es lo más simple y lo más común del género.
- Malo: ignora la forma y los huecos.

### Las tres palancas de variedad
- Bueno: la variedad se agranda, se recorre y se protege con un test.
- Malo: suman datos al balance y un test lento, que conviene correr con `simulacion`.

### Confiar sin medir (no discutida)
- Bueno: no cuesta nada.
- Malo: un cambio en el balance puede empobrecer las formas sin que nadie lo note.

## Más información

- Informe: `docs/investigaciones/2026-11-24-mejoras.md`, con las fuentes del género y de la matemática, consultadas el 2026-11-24, y lo no verificado marcado.
- Prototipo: `docs/prototipos/mejoras_armas.html`. Mediciones: `docs/prototipos/medir_mejoras.js`.
- Vampire Survivors, evoluciones: https://vampire.survivors.wiki/w/Evolution. La fusión de la que se diferencia el juego.
- Hades, Chaos: https://hades.wiki.fextralife.com/Chaos. La contra con duración.
- Noita, varitas: https://noita.wiki.gg/wiki/Guide:_Wand_Mechanics. La composición, que no se eligió.
- MathWorld, rosas, Lissajous y epiciclos: https://mathworld.wolfram.com/RoseCurve.html y https://mathworld.wolfram.com/Epitrochoid.html.
- G. Toussaint, ritmos euclidianos (Bridges 2005): https://cgm.cs.mcgill.ca/~godfried/publications/banff.pdf.

## Preguntas abiertas

- **Los números:** los valores de cada arma, las listas por semilla, los precios, y el piso y el tope del test de variedad. Se afinan al construir y jugando (#90).
- **Cómo se ve la tarjeta:** cómo muestra la fórmula y el cambio sin volverse ilegible. Se decide al construir (#91).
- **La experiencia:** su curva, cuánto deja cada enemigo y cuántos niveles hay en una partida. Toca al #90.
- **Si contar firmas basta para medir variedad**, o si hace falta comparar las formas dibujadas.
