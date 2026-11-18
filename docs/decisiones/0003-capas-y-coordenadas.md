---
estado: aceptado; el contrato que prohíbe pygame.draw y pygame.display lo reemplaza el ADR 0016
fecha: 2026-11-18
---

# Separar world, render y scenes, con coordenadas matemáticas en world

## Contexto y problema

Los tests deben cubrir la lógica sin abrir una ventana. Las armas son fórmulas, y el README las explica tal como se escriben en papel. Hay que decidir cómo se separa la lógica del dibujo, en qué coordenadas trabaja la lógica y cómo se hace cumplir esa separación.

## Factores de decisión

- Que la lógica se pueda testear sin pantalla.
- Que el código de cada arma se lea como su fórmula.
- Que la regla no se olvide en una sesión larga.
- Que el editor futuro quede posible: armar enemigos y armas desde parámetros.

## Opciones consideradas

- Separación: `world/` y `render/` aparte, o un `draw()` en cada entidad.
- Coordenadas: matemáticas (Y hacia arriba) o de pantalla (Y hacia abajo).
- Cumplimiento: import-linter, solo la revisión, o `banned-api` de ruff por carpeta.

## Resultado de la decisión

- **Estructura:** *src layout* con `uv init --app --package`. El paquete es `circlebh` (nombre provisorio) y el comando también se llama `circlebh`.
- **Capas:** en `src/circlebh/`, `scenes` → `render` → `world` → `balance`, en una sola dirección.
- **`world/`:** es lógica pura, sin `draw()`. De Pygame solo usa `pygame.math.Vector2`.
- **`render/`:** es genérico y dibuja a partir de los parámetros, por ejemplo un polígono de n lados.
- **Coordenadas:** `world` usa coordenadas matemáticas, con Y hacia arriba y ángulos antihorarios en radianes. Solo la cámara invierte la Y.
- **Sin `pygame.sprite`:** está pensado para imágenes y rectángulos, y aquí todo es círculos, polígonos y curvas.
- **Cumplimiento:** import-linter 2.16, con dos contratos. Uno de capas, y otro que prohíbe `pygame.display` y `pygame.draw` en `world`.

### Consecuencias

- Bueno: todo `world` se testea sin pantalla.
- Bueno: las curvas se escriben como en el README.
- Bueno: las coordenadas que ve el jugador en la esquina salen directo de `world`.
- Malo: cada cosa nueva toca dos lugares, `world` y `render`.
- Malo: suma una dependencia de desarrollo, import-linter.

### Confirmación

- `lint-imports` corre en `poe check` y en la CI.
- Los tests de `world` corren en la CI, que no tiene pantalla.
- Pendiente de verificar al armar: que `Vector2` funcione sin `pygame.init()`.

## Pros y contras de las opciones

### `world/` y `render/` aparte
- Bueno: la separación es clara y se puede verificar.
- Malo: hay dos lugares por cada cosa nueva.

### `draw()` en cada entidad
- Bueno: es el estilo de los tutoriales de Pygame y se lee más directo.
- Malo: la lógica y el dibujo quedan mezclados, y cuesta asegurar que los tests no dependan de una ventana.

### Coordenadas matemáticas
- Bueno: coinciden con las fórmulas y con el plano que ve el jugador.
- Malo: hay que convertirlas al dibujar.

### Coordenadas de pantalla
- Bueno: no hay conversión.
- Malo: las fórmulas llevan los signos cambiados, y las coordenadas que se muestran habría que invertirlas igual.

### import-linter
- Bueno: el contrato es explícito y se lee en `pyproject.toml`.
- Malo: es una dependencia más.

### Solo la revisión
- Bueno: no suma nada.
- Malo: la regla se olvida, y si `world` abre una ventana, los tests fallan de formas raras.

### `banned-api` de ruff por carpeta
- Bueno: no suma dependencias.
- Malo: el contrato se lee peor, y no se verificó que funcione bien por carpeta.

## Más información

- https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/ (consultado el 2026-11-18)
- https://import-linter.readthedocs.io/ (consultado el 2026-11-18)
- https://pypi.org/pypi/import-linter/json (consultado el 2026-11-18)
