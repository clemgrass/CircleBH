---
estado: aceptado
fecha: 2026-11-18
---

# Trabajar con issues, squash merge y un ruleset en main

## Contexto y problema

El proyecto lo hace una persona con ayuda de una IA, en un repo público. Hay que decidir dónde viven las tareas, cómo se integra el trabajo, cómo se protege `main`, si queda rastro de la IA y qué framework de flujo usa el agente.

## Factores de decisión

- Que `main` esté siempre verde y su historial se lea solo.
- Transparencia en un repo público.
- Poco mantenimiento, porque trabaja una sola persona.

## Opciones consideradas

- Rastro de la IA: trailer `Co-Authored-By`; mención solo en el README; o ningún rastro.
- Tareas: Issues con milestones; Issues con milestones y un tablero de Projects; o un archivo en el repo.
- Merge: squash con el título del PR; merge commit; o rebase.
- Framework para el agente: Superpowers sin desarrollo con subagentes; Superpowers completo; o ninguno.

## Resultado de la decisión

- **Rastro de la IA:** los commits donde Claude escribió código llevan el trailer `Co-Authored-By` de Claude.
- **Tareas:**
  - en GitHub Issues, con un milestone por versión y un tablero de Projects;
  - el tablero se mueve solo con sus automatizaciones: un issue cerrado o un PR con merge pasa a "Hecho";
  - un issue es una rama y un PR. El issue lleva un título en español y un cuerpo con Qué, Por qué y Terminado cuando.
- **Ramas:** `tipo/descripcion-corta`, en español y sin tildes.
- **Commits:** Conventional Commits, con el tipo en inglés y la descripción en español.
- **Push:** al final de la tarea, con `poe check` en verde.
- **PR:**
  - antes de crearlo, el usuario ve el título y el cuerpo;
  - si hay una revisión abierta, `main` se integra con merge, no con rebase;
  - el squash merge, con el título del PR, lo hace el usuario después de la prueba manual (ADR 0013);
  - las ramas se borran solas después del merge.
- **Ruleset en `main`:**
  - exige PR, con 0 aprobaciones porque hay una sola persona;
  - exige que pase el chequeo `check`;
  - bloquea el force push y el borrado;
  - exige historial lineal;
  - nadie se lo puede saltar.
- **Framework:** Superpowers, sin el desarrollo con subagentes, porque choca con el modo enseñanza y con avanzar una tarea a la vez. Si algo choca con `AGENTS.md`, manda `AGENTS.md`.

### Consecuencias

- Bueno: `main` tiene un commit por PR, y las notas del release salen de ahí.
- Bueno: un visitante ve el avance en el tablero y en los milestones.
- Bueno: queda escrito qué parte escribió la IA.
- Malo: los commits intermedios no quedan en `main`, aunque siguen en el PR.
- Malo: el tablero es una pieza más.
- Malo: algunos lectores miran con recelo el trailer de la IA.

### Confirmación

- El ruleset está configurado en GitHub y se puede revisar con `gh api`.
- La plantilla de PR existe en `.github/`.
- Pendiente de verificar al armar: que el autor de un PR no puede aprobarlo él mismo, y que las automatizaciones de Projects están en el plan gratis.

## Pros y contras de las opciones

### Trailer `Co-Authored-By`
- Bueno: es transparente commit a commit.
- Malo: algunos lo miran con recelo.

### Mención solo en el README
- Bueno: los commits quedan limpios.
- Malo: no se sabe qué parte escribió quién.

### Ningún rastro
- Bueno: es lo más limpio.
- Malo: no queda registro.

### Issues con milestones
- Bueno: es simple.
- Malo: no hay una vista de tablero.

### Issues con tablero
- Bueno: el estado se ve de un vistazo.
- Malo: hay que mantenerlo.

### Archivo en el repo
- Bueno: no depende de GitHub.
- Malo: no se cierra con los PRs y se desactualiza.

### Squash
- Bueno: el historial queda limpio.
- Malo: se pierden los commits intermedios en `main`.

### Merge commit
- Bueno: es más fiel a lo que pasó.
- Malo: el historial se llena de commits.

### Rebase
- Bueno: deja un historial lineal con todos los commits.
- Malo: choca con integrar `main` con merge.

### Superpowers sin subagentes
- Bueno: trae checklists de TDD y de verificación que calzan con las reglas del proyecto.
- Malo: es una pieza más que entender.

### Superpowers completo
- Bueno: avanza más rápido en tareas grandes.
- Malo: deja al usuario fuera de la implementación.

### Ningún framework
- Bueno: es más predecible.
- Malo: se pierden esos checklists.

## Más información

- https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets (disponibles en repos públicos con GitHub Free; consultado el 2026-11-18)
- https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/configuring-commit-squashing-for-pull-requests (consultado el 2026-11-18)
