---
estado: aceptado
fecha: 2026-11-18
---

# Claude escribe todo el código y explica las partes cruciales

Reemplaza el "modo enseñanza": la parte de TDD del ADR 0007 (Claude escribe el test y el usuario implementa, con `xfail` de ejercicio) y la línea de ejercicios pendientes del ADR 0012. El resto de esos ADR sigue vigente.

## Contexto y problema

Con el modo enseñanza, Claude dejaba un hueco de 5 a 10 líneas en la lógica con decisiones reales y el usuario lo escribía. En el primer ejercicio, `FixedStepClock.advance` (tarea 8 del armado inicial), el usuario pidió que Claude lo resolviera. Después pidió cambiar la regla: prefiere que Claude escriba el código y le muestre y explique las partes cruciales.

Mientras un ejercicio queda pendiente, lo que depende de él no funciona. En la tarea 8, la ventana del juego se caía con `NotImplementedError` hasta que se resolvió.

## Factores de decisión

- Que el usuario entienda las decisiones reales del código, que es la razón del modo enseñanza.
- No bloquear el avance esperando código.
- Mantener la evidencia de TDD: el test se ve fallando por la razón correcta.

## Opciones consideradas

- Claude escribe todo y explica las partes cruciales
- Mantener el modo enseñanza
- Ejercicios opcionales: Claude escribe todo, pero ofrece un hueco cuando el usuario lo pide (no discutida)

## Resultado de la decisión

Elegimos **que Claude escriba todo y explique las partes cruciales**:

- Claude escribe todo el código, también la lógica con decisiones reales: curvas, colisiones, daño y progresión.
- TDD igual que antes: el test va primero y se muestra fallando por la razón correcta.
- En cada parte crucial, después de que el test pase, Claude muestra en la sesión el fragmento clave (de 5 a 10 líneas) y explica:
  - qué hace, en términos del juego;
  - los caminos que consideró y por qué eligió uno, con datos cuando se pueda;
  - qué lo haría fallar, o qué borde cuidan los tests.
- Si el usuario prefiere otro camino, lo dice y Claude lo cambia.
- Ya no hay `xfail` de ejercicio. pytest sigue en modo `strict`, y un `xfail` que pasa sigue rompiendo la suite.

### Consecuencias

- Bueno: nada queda bloqueado esperando código, y cada tarea se cierra entera.
- Bueno: la explicación queda en la sesión junto a la evidencia, y el usuario puede pedir otro camino.
- Malo: el usuario practica menos la escritura de código. Entiende las decisiones, pero no las escribe.
- Malo: la explicación vive en la sesión y no en el repo. Lo que haya que recordar debe ir en el docstring o en el commit.
- Neutro: el ADR 0010 justifica no usar el desarrollo con subagentes, en parte, por el modo enseñanza. La otra razón, avanzar una tarea a la vez, se mantiene.

### Confirmación

- `grep -rn "ejercicio pendiente" src tests` no devuelve nada.
- `AGENTS.md` tiene la sección "Modo explicación" en lugar de "Modo enseñanza".
- En la sesión, cada parte crucial nueva va acompañada de su fragmento y su explicación. Se ve en la revisión.

## Pros y contras de las opciones

### Claude escribe todo y explica
- Bueno: no bloquea, y conserva la comprensión de las decisiones.
- Malo: el usuario escribe menos código.

### Mantener el modo enseñanza
- Bueno: el usuario practica escribiendo.
- Malo: bloquea lo que depende del ejercicio, y el usuario ya dijo que no lo prefiere.

### Ejercicios opcionales (no discutida)
- Bueno: deja la puerta abierta a practicar.
- Malo: es una regla con excepción, y hay que decidir cada vez.
