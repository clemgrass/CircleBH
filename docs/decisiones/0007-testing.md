---
estado: aceptado
fecha: 2026-11-18
---

# Testear con pytest estricto, Hypothesis y una simulación de partida completa

## Contexto y problema

Los tests son la red que deja avanzar sin miedo. Cubren la lógica (las curvas, el daño, las colisiones y la subida de nivel), no el dibujo. El proyecto también es de aprendizaje: el usuario escribe parte del código. Hay que decidir el runner, la forma de trabajar con TDD y los niveles de test.

## Factores de decisión

- Que los tests sean deterministas en la CI.
- Que encuentren casos borde que no se escribirían a mano.
- Que sirvan de enunciado para los ejercicios del modo enseñanza.
- Que atrapen errores que solo aparecen al juntar las piezas.

## Opciones consideradas

- TDD: Claude escribe el test y el usuario el código; el usuario escribe los dos; o se decide por tarea.
- Hypothesis: sí, para curvas y colisiones; o solo `pytest.mark.parametrize`.
- Niveles: unitarios y una simulación de partida; o solo unitarios.
- Runner: pytest; o unittest (no discutida).

## Resultado de la decisión

- **Herramientas:**
  - pytest 9.2.0 con `strict = true` en `[tool.pytest]`, para que un marker desconocido falle y un `xfail` que pasa rompa la suite;
  - Hypothesis 6.170.15 para curvas y colisiones, con un perfil de CI que usa `derandomize`;
  - coverage 7.17.2 y pytest-cov 7.1.0, como reporte sin umbral.
- **TDD:** Claude escribe el test, lo muestra fallando por la razón correcta y el usuario implementa.
  - Mientras el ejercicio está pendiente, el test se marca con `xfail(strict=True, reason="ejercicio pendiente: …")`.
  - Cuando el usuario lo implementa, el test pasa, la suite falla y el usuario quita la marca. Así no choca con el hook ni con pre-commit (ADR 0012).
- **Niveles:**
  - tests unitarios de `world`;
  - una simulación sin ventana, con semilla y un input sintético (el "piloto"), que juega 10 minutos y comprueba que no hay errores y que aparece el jefe;
  - la misma simulación se puede mirar con `circlebh --demo --seed N --speed K`.
- **Zona crítica:** las curvas, el daño y los lados, las colisiones y la grilla, la subida de nivel y las tarjetas, y la coherencia del balance.

### Consecuencias

- Bueno: cada ejercicio tiene un objetivo verificable.
- Bueno: Hypothesis reduce cada falla a su caso mínimo.
- Bueno: la simulación atrapa errores como oleadas que nunca terminan o un jefe que no aparece.
- Malo: Hypothesis es una dependencia más y una forma de escribir tests que hay que aprender.
- Malo: la simulación puede tardar segundos (no medido), así que no corre en `poe fast`.

### Confirmación

- `poe fast` corre los unitarios.
- `poe check` y la CI corren todo, simulación incluida, con Hypothesis determinista.
- `grep "ejercicio pendiente"` lista los ejercicios abiertos.

## Pros y contras de las opciones

### Claude el test, el usuario el código
- Bueno: el objetivo es claro y el verde dice cuándo se terminó.
- Malo: el usuario practica menos el diseño de casos de prueba.

### El usuario escribe los dos
- Bueno: aprende más.
- Malo: avanza más lento.

### Se decide por tarea
- Bueno: es flexible.
- Malo: hay que acordarlo cada vez.

### Hypothesis
- Bueno: encuentra casos borde y muestra en el portafolio que se saben testear propiedades.
- Malo: es una dependencia y una curva de aprendizaje.

### Solo `parametrize`
- Bueno: los tests son más directos.
- Malo: los casos borde quedan a mano.

### Unitarios y simulación
- Bueno: atrapa errores de integración sin tocar el dibujo.
- Malo: es más lento.

### Solo unitarios
- Bueno: es lo más rápido.
- Malo: lo que falle al juntar piezas se descubre jugando.

### unittest (no discutida)
- Bueno: viene con Python.
- Malo: es más verboso y Hypothesis está pensado para pytest.

## Más información

- https://docs.pytest.org/en/stable/reference/reference.html#confval-strict (consultado el 2026-11-18)
- https://docs.pytest.org/en/stable/how-to/skipping.html (consultado el 2026-11-18)
- https://hypothesis.readthedocs.io/en/latest/reference/api.html (`derandomize`; consultado el 2026-11-18)
- https://pypi.org/pypi/pytest/json y https://pypi.org/pypi/hypothesis/json (consultados el 2026-11-18)
