# AGENTS.md

Juego del género survivors en Python con pygame-ce. Todo se dibuja con código y las armas son curvas matemáticas.
Es un repo público de portafolio: el código y el README se leen como ejemplo de Pygame, POO y trigonometría.

- Diseño del juego: `docs/diseno-del-juego.md`.
- Decisiones: `docs/decisiones/`. No reabras lo que ya deciden.

## Forma de trabajar

### Ritmo
- Una tarea a la vez. Al terminarla, muestra el resultado y espera la aprobación explícita antes de seguir.
- No te adelantes. Que un plan esté aprobado no aprueba el código, ni el texto de un PR, ni el paso siguiente.
- Si algo grande no está claro, pregunta antes. Una duda menor que no cambia lo que se construye la decides tú y la cuentas.
- El trabajo grande se parte en piezas chicas que se puedan revisar de una vez.

### Quién decide
- Decide el usuario. Tú investigas, propones con fundamentos y recomiendas una opción.
- Investiga en fuentes primarias y vigentes: la documentación oficial de la versión en uso, changelogs y releases. Anota la URL y la fecha, y marca lo que no pudiste verificar.
- Si hay varias formas válidas, elige la más estándar, simple y fácil de mantener, y explica por qué.
- Prioridad: simplicidad, mantenibilidad, seguridad, automatización y, al final, velocidad.
- No cambies lo ya decidido. Si ves una mejora grande, detente y explica sus beneficios, costos y desventajas.

### Modo explicación (ADR 0017)
- Tú escribes todo el código. TDD: el test primero, y lo muestras fallando por la razón correcta.
- En la lógica con decisiones reales (curvas, colisiones, daño, progresión), después de que el test pase, muestras en la sesión el fragmento clave (5 a 10 líneas) y explicas qué hace, qué caminos consideraste y por qué elegiste uno, y qué lo haría fallar.
- Si el usuario prefiere otro camino, lo cambias.

### Decisiones por escrito
- Queda escrito lo difícil de revertir, lo que afecta a más de una pieza y lo que alguien va a cuestionar en seis meses.
- Los ADR van en `docs/decisiones/NNNN-titulo.md`, en formato MADR 4 en español, y siempre llevan la sección **Confirmación**: cómo se verifica que el código los cumple.
- Un ADR nace **propuesto** y pasa a **aceptado** cuando el usuario lo confirma. Uno aceptado no se reescribe: se reemplaza por otro.
- Las alternativas son reales. Si falta una obvia, se agrega marcada "(no discutida)". Las contras van siempre.
- Lo que no está claro queda como pregunta abierta. Las decisiones que el usuario toma en la conversación se anotan apenas las toma.
- Las specs van en `docs/specs/AAAA-MM-DD-tema.md`, con una sección "Escenarios de test", y los planes en `docs/planes/AAAA-MM-DD-tema.md`. Estas rutas reemplazan las que traen las skills.

### Entender antes de construir
- Primero se entiende qué se quiere y por qué. Después, cómo.
- Antes de cambiar algo, lee el código y los documentos que lo explican. No supongas que el estado sigue igual que en la sesión anterior.

### Listo significa evidencia
- Algo está terminado cuando muestras el comando de verificación y su salida. "Debería funcionar" no cuenta.
- Lo que no pudiste verificar se dice tal cual, con el motivo.
- Si el cambio se ve en pantalla, corre `uv run poe capturas` y muestra en la sesión el estado inicial, la interacción y el resultado.

### Textos
- Español de Chile, tuteando: "puedes", "elige". Nunca voseo.
- Los identificadores van en inglés. Los comentarios, docstrings, README, issues, PRs y descripciones de commits, en español.
- Los términos técnicos van en inglés cuando no tienen traducción natural.
- Oraciones cortas, lo importante primero, sin relleno.
- No menciones la organización ni el curso que motivó el proyecto: ni en el código, ni en documentos, commits, issues o PRs.

### Herramientas
- Crea y edita archivos con las herramientas de edición, no con scripts de shell.
- No salgas de la carpeta del proyecto ni toques otros repos.
- Lo que creas para probar queda versionado o documentado.
- Nada depende de una persona, de su cuenta ni de su máquina.
- Instalar y actualizar lo hace el usuario: dale el comando listo, con `!` adelante. Cada paquete nuevo se propone con su motivo, su última release y quién lo mantiene.

### Continuidad
- Deja el estado al día en el issue en curso: qué quedó a medias y cuál es el próximo paso concreto. Actualízalo antes de quedarte sin contexto.

## Stack (ADR 0001, 0002, 0015)
- Python 3.14.10 (en `.python-version`), pygame-ce 2.5.8 y uv 0.13.7 (en `required-version`).
- Python y uv se suben juntos: el release de uv tiene que agregar el parche de Python que se fija.
- `uv.lock` fija versiones exactas, con `exclude-newer = "7 days"` y `no-build = true`.
- Las dependencias se actualizan a mano al empezar cada milestone.

| Comando | Para qué |
|---|---|
| `uv run circlebh` | jugar |
| `uv run circlebh --demo --seed N --speed K` | ver la partida simulada |
| `uv run poe fast` | después de cada cambio |
| `uv run poe check` | antes del push; es lo mismo que corre la CI |
| `uv run poe capturas` | evidencia en la sesión |
| `uv run poe medios` | regenerar las imágenes del README |

## Arquitectura (ADR 0003 a 0006, 0016)
- En `src/circlebh/`, las importaciones van en una sola dirección: `scenes` → `render` → `world` → `balance`. `lint-imports` lo verifica.
- `world/` es lógica pura: no tiene `draw()` ni usa `pygame.display` ni `pygame.draw`. De Pygame solo usa `Vector2`. La regla `TID251` de ruff lo verifica, y solo `render/`, `scenes/` y `__main__.py` tienen la excepción.
- `world` usa coordenadas matemáticas: Y hacia arriba y ángulos antihorarios en radianes. Solo la cámara las pasa a pantalla. Cada curva se escribe como su fórmula.
- Clases simples con herencia y funciones cortas. Sin ECS, sin metaclases y sin `pygame.sprite`.
- Enemigos y armas se definen por parámetros en `balance.py`, con dataclasses, y se reflejan en `balance.json`, dentro del paquete y leído con `importlib.resources`.
  - Ninguno de los dos manda: deben calzar siempre.
  - Si difieren, el chequeo nombra el campo y se corrige a mano, exportando o importando, antes de jugar.
- La lógica avanza en pasos fijos de 1/60 s con acumulador. El azar sale solo de la `random.Random(seed)` inyectada.
- En las colisiones, cada cuerpo es un círculo. Se usa una grilla espacial y funciones propias en `world/`.
- No hay archivos de imagen. La única excepción es `docs/media/`, que genera `poe medios`, y `poe check` lo verifica.

## Tests (ADR 0007)
- `pytest` en modo `strict` e Hypothesis.
- La zona crítica:
  - las curvas;
  - el daño y la pérdida de lados;
  - las colisiones y la grilla, que debe dar lo mismo que revisar todos contra todos;
  - la subida de nivel y las tarjetas;
  - la coherencia del balance.
- Cada comportamiento nuevo lleva al menos un caso feliz, uno borde y uno negativo.
- Dobles, en este orden: real, fake, stub y mock, y solo de tipos propios. Los tests con azar verifican propiedades, no valores concretos.
- Cada bug parte con un test que lo reproduce. Un test inestable se arregla: sin esperas, sin reintentos y sin `skip`.
- La cobertura es para analizar, no una meta. `render/` y `scenes/` no se testean. El test que no se puede escribir se declara.

## Proceso (ADR 0010)
- **Ramas e issues:**
  - nunca se trabaja directo en `main`;
  - un issue es una rama `tipo/descripcion-corta` y un PR;
  - el issue lleva un título en español y un cuerpo con Qué, Por qué y Terminado cuando. Va en un milestone por versión y en el tablero.
- **Commits:** Conventional Commits, con el tipo en inglés y la descripción en español (`feat: agregar arma seno`). El push va al final, con `poe check` en verde.
- **PR:**
  - antes de crearlo, revisa el diff contra los ADR y este archivo, y muestra el título y el cuerpo;
  - la plantilla trae Qué cambia, Por qué, Verificación y Prueba manual. Tú escribes los pasos y el usuario, el resultado;
  - si hay una revisión abierta, `main` se integra con merge, no con rebase;
  - el squash merge, con el título del PR, lo hace el usuario.
- **Versiones:** SemVer 0.x, y 1.0.0 es el MVP completo. Un tag `vX.Y.Z` en `main` dispara el release.

## Preguntas abiertas
- El nombre del juego. `circlebh` es provisorio.
- El fondo negro o blanco y el color de acento: se decide con un prototipo desechable.
- Los números de equilibrio y qué parámetro mejora cada tarjeta.
- Si importar de `balance.json` a `balance.py` va en el MVP o con el editor.
