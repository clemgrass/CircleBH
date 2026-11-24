---
estado: aceptado
fecha: 2026-11-24
---

# El balance se mide por tema, con pilotos de habilidad conocida y una ficha de lo que se siente

Amplía el ADR 0007 (la simulación sin ventana), el 0025 (el director y sus secciones) y el 0029 (los precios de las tarjetas). No reemplaza nada de ellos.

## Contexto y problema

Los números de equilibrio son una pregunta abierta desde la 0.1.0, y hasta ahora se ajustaron jugando, sin una medida. El autor quiere responder cuándo debería morir alguien que juega bien y cómo debería sentirse llegar hasta ahí (2026-11-24). El juego va a crecer de a un tema con su jefe, y cada tema puede cambiar las reglas, como romper la ley de Coulomb después del jefe 1 (diseño, "Después del MVP").

La línea base medida hoy (informe, "La línea base") muestra que, sin una medida, el balance estaba roto sin que se notara:

- el piloto de la demo muere en la intro en las 20 semillas, así que no sirve para medir;
- el arma quita a lo más 1,67 líneas/s y en las subidas entran hasta 3,6. Los drops tardan 166 s y 143 s en limpiarse, en vez de 15,5 s;
- el infinito queda plano desde los 70 s, porque se llenan sus dos topes.

Hay que decidir:

- qué meta se fija;
- con qué piloto se mide;
- qué se mide y dónde vive la medición;
- cómo se anota lo que se siente;
- cómo se mide un tema sin jugar los anteriores.

La investigación completa, con fuentes y mediciones, está en `docs/investigaciones/2026-11-24-balance.md` (#90).

## Factores de decisión

- Que sirva para N temas, cada uno con sus reglas *(decisión del autor, 2026-11-24)*.
- Que la meta la fije el autor, y la medida diga si se cumple.
- Que sea reproducible: la misma semilla da la misma partida (ADR 0005), y los tests no son inestables (ADR 0007).
- Que la habilidad del piloto se pueda graduar, para que la meta hable de "alguien que juega bien".
- Que lo que se siente quede anotado y se pueda comparar en el tiempo.
- Que sea barato para una persona, después de cada cambio.

## Opciones consideradas

La meta:

- G1: ganas el tema y mueres en el infinito
- G2: el tema ya filtra
- G3: G1 de base, y el jugador sube el riesgo con los precios
- Un muro al final, como el Reaper (no discutida)

El piloto:

- P0: el círculo de la demo
- P1: un campo de fuerzas con ruido
- P2: mirar adelante con copias del mundo
- P3: repetir partidas grabadas

Dónde vive la medición:

- T1: una herramienta manual
- T2: propiedades como tests de `simulacion`

La sensación:

- S1: una ficha después de cada partida
- S2: la tensión por sección
- S3: A/B con la misma semilla
- S4: grabar y anotar
- No anotarla (no discutida)

Con qué poder llega el jugador al tema k:

- Jugar siempre desde el principio
- Guardar al jugador como llegó
- Declarar un poder de referencia por tema

## Resultado de la decisión

**G3 por tema, P1 y P3, T1 y T2, S1 y S2 en cada sesión y S3 al comparar, y el jugador guardado como llegó** *(decisiones del autor, 2026-11-24)*.

### La meta: G3, fijada por tema

- **La meta de cada tema k** es la supervivencia hasta su jefe para quien llegó a él, `S(jefe_k | tema_k)`, y la forma de su riesgo por sección. El riesgo `h` es la tasa de muerte: las muertes en la sección divididas por el tiempo que pasaron ahí todas las partidas (Isaksen y Nealen, 2015).
- **La forma buscada:** `h` casi 0 en la intro, sube en las subidas, tiene su pico en los drops, baja en el respiro, y el pico del drop 2 es mayor que el del drop 1. En el infinito crece siempre.
- **La base es el patrón del género:** la mayoría llega al jefe, y la habilidad se mide después. Los precios de las tarjetas (ADR 0029, M8) dejan que el jugador suba su propio riesgo.
- **El infinito tiene que crecer siempre** *(decisión del autor, 2026-11-24)*. Hoy queda plano. Cómo se arregla lo decide un ADR propio, porque toca al ADR 0025 y a las decisiones 20 y 74 de la spec de la 0.2.0.
- **Los números** (cuánto vale `S` en cada tema y qué σ es "alguien que juega bien") quedan abiertos. Se fijan con la herramienta, jugando.

### Un contrato de medición

- **Todo tema emite los mismos eventos del mundo**, y la medición sale solo de ellos y del reloj. No sale de la ley que mueve a los enemigos. Si un tema cambia las reglas, la misma herramienta lo mide.
- **Los eventos del contrato:**
  - los que ya existen: `Shot`, `Hit`, `Death` y `Regrow`;
  - tres nuevos: un enemigo aparece, empieza una sección y el jugador muere, con lo que lo tocó *(propuesta de Claude)*.

  Hoy la aparición se deduce comparando la lista de enemigos, y la muerte, de `game_over`.
- **Nada se escribe con nombres fijos.** La herramienta, los tests y la ficha leen los temas y sus secciones del balance.

### Los pilotos: P1 y P3

- **P1 esquiva con un campo de fuerzas.**
  - Cada enemigo lo empuja con `1/d²` desde su círculo envolvente, como las cargas del ADR 0021. Cada bala empuja más fuerte, desde donde va a estar.
  - La habilidad es un error angular de desviación σ.
  - Su azar sale de su propia `Random`, sembrada con la semilla de la partida, nunca de la del mundo.
  - Esquiva lo que lo puede matar, no lo que mueve a los enemigos, así que sirve con otras reglas.
  - Se mide con tres σ.
  - Vive en `src/circlebh/pilot.py`, junto a P0, que se queda en la demo.
- **P3 repite una partida tuya.**
  - Se graban la semilla, el balance y la intención de cada paso, y se vuelve a jugar exacta.
  - Sirve para medir tus partidas con las mismas medidas y para **calibrar σ:** "alguien que juega bien" es el σ cuyo `S` se parece al tuyo, como hace King con su bot (Gudmundsson et al., 2018).
  - Una grabación vale solo para el código y el balance con que se grabó.

### Las medidas

| | Qué mide | Cuándo |
|---|---|---|
| O1 | `S(t)` y `h(t)` por sección, para cada piloto | Ya |
| O2 | Las líneas que entran contra las que quita el jugador, por sección, y los vivos por compás | Ya |
| O3 | El tiempo para matar a cada tipo, qué % muere y la puntería | Ya |
| O4 | Cuánto tarda en limpiarse cada drop, en compases | Ya |
| O5 | El crecimiento del infinito: los multiplicadores, los cuerpos y `h(t)` | Ya |
| O6 | La presión: cuántas veces pasa una amenaza cerca del jugador | Ya |
| O7 | Los niveles por minuto y por sección | Con la experiencia (#91) |
| O8 | Cuánto se elige cada tarjeta, y cuánto cambia `S` al prohibirla | Con las tarjetas (#91) |

### Dónde vive: T1 y T2

- **T1, una herramienta manual, como `poe benchmark`.**
  - Corre N semillas con P1 (tres σ) y con las grabaciones de P3.
  - Escribe un informe en Markdown en `.capturas/`, con O1 a O8 por tema y sección y la meta al lado.
  - Puede comparar dos informes, antes y después de un cambio.
  - No corre en la CI.
- **T2, pocas propiedades como tests de `simulacion`.**
  - Solo las cualitativas:
    - P1 con menos σ vive al menos lo mismo que con más;
    - todo tema emite los eventos del contrato;
    - ningún drop se queda pegado más de K compases con P1;
    - en el infinito, el riesgo crece.
  - Un test entra cuando el juego lo cumple. Los dos últimos esperan al balance del arma y al ADR del infinito, porque hoy fallarían. No se marcan con `skip`.
  - Una banda de `S` como test espera a que la meta tenga números.

### Con qué poder llega el jugador: guardado como llegó

- **La herramienta guarda la partida de P1 al empezar cada tema** y mide el tema k desde ahí, sin jugar los anteriores cada vez.
- **Está medido** (informe, "Guardar y retomar una partida"): un `World` copiado con `deepcopy` o con `pickle` sigue idéntico 50 s, y la copia cuesta 1,7 ms y 35 KiB con 40 enemigos.
- **Una partida guardada vale para un código y un balance.** La herramienta la regenera si cambian.
- **`pickle` solo carga archivos que escribió la misma herramienta,** en `.capturas/`, porque cargar un `pickle` ajeno ejecuta código.

### La sensación: S1 y S2 en cada sesión, S3 al comparar

- **S1, una ficha de un minuto después de cada partida:**
  - la semilla, el commit y la sección donde moriste;
  - si la muerte fue justa (sí o no, y por qué en una línea);
  - "¿otra partida?", de 0 a 4;
  - seis preguntas del iGEQ de 0 a 4: dos de tensión, dos de desafío y dos de flow (IJsselsteijn et al., 2013).
- **S2, la tensión de 1 a 5 en cada sección del tema,** para ponerla al lado del `h(t)` medido y de O6.
- **S3, cuando un PR cambia el balance:** su prueba manual juega la misma semilla antes y después, y dice cuál se sintió mejor y por qué.
- **Se anota en archivos versionados,** una fila por partida en `docs/sensacion/`, con una plantilla que lee las secciones del balance. Las preguntas del iGEQ se copian del cuestionario al armar la plantilla, y su traducción al español no es oficial.
- **La ficha dice qué sentiste, y el porqué sale de las medidas.** Valve: "People don't know why they do what they do".

### Consecuencias

- Bueno: "cuándo muere alguien que juega bien" pasa a ser un número por tema, medible y comparable.
- Bueno: un tema nuevo, aunque cambie las reglas, se mide sin código nuevo si cumple el contrato.
- Bueno: la línea base ya encontró tres problemas que jugando no se veían: el arma, los drops y el infinito plano.
- Bueno: la ficha y la tensión por sección dejan comparar lo que se siente entre versiones.
- Malo: es un piloto más, una herramienta más, tres eventos y una carpeta de fichas que mantener.
- Malo: P1 no juega como una persona. Si se afina el juego para él, se ajusta al bot (Rupp et al., 2024). P3 y la ficha lo compensan, pero con una sola persona la muestra es chica.
- Malo: las grabaciones y las partidas guardadas caducan con cada cambio de código o de balance.
- Malo: la ficha no es un instrumento validado para una persona sola, y el autor es juez y parte.
- Malo: los tests de `simulacion` se alargan. P1 con 20 semillas tarda ~28 s en 8 núcleos.

### Confirmación

**Tests:**
- Un test de `simulacion` comprueba que P1 con menos σ vive al menos lo mismo que con más, en un conjunto fijo de semillas.
- Un test comprueba que P1 es determinista: la misma semilla y el mismo σ dan dos veces la misma partida.
- P1 recibe su `Random` como parámetro, y una búsqueda de `world.rng` y `.rng` en `pilot.py` no encuentra usos del azar del mundo.
- Un test comprueba que cada sección emite el evento de inicio, cada enemigo nuevo el de aparición y la muerte del jugador el suyo.
- Un test comprueba que una partida guardada y retomada da los mismos eventos que la original.
- Un test comprueba que una grabación de P3 vuelve a jugar la misma partida.
- Cuando el balance del arma y el ADR del infinito lo permitan, entran los tests de los drops y del infinito.

**Comandos:**
- La herramienta T1 escribe su informe en `.capturas/` con O1 a O6 por tema y sección, y la meta al lado.
- Una búsqueda de los nombres de las secciones (`intro`, `drop_1`, …) en la herramienta y en los tests no encuentra nombres escritos a mano.
- `lint-imports` comprueba que `world` no importa los pilotos ni la herramienta.

**A mano:**
- Las sesiones de prueba dejan su ficha en `docs/sensacion/`.
- Los PR que cambian el balance traen en su prueba manual el A/B con la misma semilla.

## Pros y contras de las opciones

### G1: ganas el tema y mueres en el infinito
- Bueno: es el patrón del género. Entre el 70 % y el 85 % termina la partida base.
- Malo: a un experto el tema le puede parecer fácil.

### G2: el tema ya filtra
- Bueno: hay tensión todo el rato, más bullet hell.
- Malo: con muerte de un golpe y un tema de 4 min, quien empieza casi nunca ve el jefe.

### G3: G1 de base y el riesgo por los precios
- Bueno: el jugador elige su riesgo dentro del juego (Chen, 2007) y reusa los precios del ADR 0029.
- Malo: hay que medir al que paga y al que no, y los precios pasan a ser parte de la dificultad.

### Un muro al final (no discutida)
- Bueno: es simple y pone un final claro.
- Malo: choca con el ADR 0025, que decide que el infinito crece.

### P0: el círculo
- Bueno: ya existe.
- Malo: muere en la intro en las 20 semillas.

### P1: campo de fuerzas con ruido
- Bueno: es barato, es la misma matemática del enjambre, y el ruido gradúa la habilidad (medido: 85, 73 y 43 s).
- Malo: se puede acorralar, y no juega como una persona.

### P2: mirar adelante
- Bueno: puede jugar muy bien.
- Malo: cuesta K·N pasos por decisión, y puede jugar mejor que una persona.

### P3: grabaciones
- Bueno: son partidas humanas de verdad, y calibran a P1.
- Malo: caducan con cada cambio, y son de una sola persona.

### T1: herramienta manual
- Bueno: da los números finos sin alargar la CI.
- Malo: no protege nada sola.

### T2: propiedades como tests
- Bueno: protege lo que nunca debería romperse, sin tests inestables.
- Malo: alarga `simulacion`, y puede afinar el juego para esas semillas.

### S1: ficha
- Bueno: un minuto, comparable en el tiempo.
- Malo: no está validada para una persona sola.

### S2: tensión por sección
- Bueno: se pone al lado del `h(t)` medido.
- Malo: la memoria puede distorsionarla (no verificado).

### S3: A/B con la misma semilla
- Bueno: comparar es más confiable que puntuar (PAGAN, 2019).
- Malo: la segunda partida ya trae aprendizaje.

### S4: grabar y anotar
- Bueno: es lo más completo.
- Malo: es caro; solo vale en los hitos.

### No anotarla (no discutida)
- Bueno: no cuesta nada.
- Malo: lo que se siente se pierde, y no se puede comparar.

### Jugar desde el principio
- Bueno: es lo más fiel.
- Malo: cada tema nuevo alarga la medición.

### Guardar como llegó
- Bueno: es fiel y rápido. Medido: idéntico 50 s, 1,7 ms.
- Malo: caduca con cada cambio, y `pickle` pide cuidado.

### Poder de referencia por tema
- Bueno: es simple.
- Malo: puede no parecerse a una partida real.

## Más información

- Informe: `docs/investigaciones/2026-11-24-balance.md`, con las fuentes consultadas el 2026-11-24 y lo no verificado marcado.
- Prototipos: `docs/prototipos/medir_balance.py` (la línea base), `docs/prototipos/piloto_campo.py` (P1) y `docs/prototipos/guardar_mundo.py` (guardar y retomar).
- A. Isaksen y A. Nealen, AIIDE 2015: https://cdn.aaai.org/ojs/12846/12846-52-16362-1-2-20201228.pdf.
- J. Chen, "Flow in Games", CACM 2007: https://khoury.northeastern.edu/~lieber/courses/csu670/f08/materials/p31-chen-flow-in-games.pdf.
- Gudmundsson et al., CIG 2018, DOI 10.1109/CIG.2018.8490442.
- Rupp et al., 2024: https://arxiv.org/html/2407.11396v1.
- IJsselsteijn, de Kort y Poels, GEQ, 2013: https://pure.tue.nl/ws/portalfiles/portal/21666907/Game_Experience_Questionnaire_English.pdf.
- Valve, GDC 2009: https://cdn.fastly.steamstatic.com/apps/valve/2009/GDC2009_ValvesApproachToPlaytesting.pdf.

## Preguntas abiertas

- **Los números:** cuánto vale `S(jefe_k | tema_k)` en cada tema y qué σ es "alguien que juega bien". Se fijan con T1 y P3.
- **La experiencia:** cuántos niveles hay en un tema de unos 4 min. El género ronda un nivel por minuto en partidas de 20 a 30 min (inferencia del informe). Se mide con O7 cuando exista (#91).
- **Si la presión (O6) se parece a la tensión que se siente (S2).** Si no, O6 sale.
- **Cómo crece el infinito.** Lo decide su propio ADR.
