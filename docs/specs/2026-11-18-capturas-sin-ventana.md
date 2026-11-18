# Capturas sin ventana

Tarea 8 del plan de armado inicial (#8). Estado: **aprobada** el 2026-11-18.

## Para qué

Que Claude pueda mostrar evidencia visual en la sesión sin abrir una ventana: el estado inicial, la interacción y el resultado (ADR 0013). El mismo modo sirve para el smoke del release en tres sistemas (ADR 0009, tarea 9) y, más adelante, para `poe medios`.

## Alcance

- **Sí:** la tubería. Las opciones de línea de comandos, el reloj de pasos fijos, un escenario `plano-vacio`, el modo captura y `poe capturas`.
- **No:** nada visible nuevo. Con el plano vacío, las tres capturas salen idénticas, y `--seed` y `--speed` todavía no tienen efecto visible. Lo decidió el usuario: la lógica del tiempo se prueba con tests, y las capturas prueban que el dibujo llega al PNG.
- **Anti-meta:** capturas que dependan de la velocidad de la máquina. La misma semilla y los mismos tiempos dan los mismos PNG.

## Enfoques considerados

- **A. Simular sin reloj real (elegido por el usuario).** Con `--capture`, el programa avanza pasos fijos de 1/60 s lo más rápido que puede, sin esperar, y guarda un PNG en el paso de cada tiempo pedido. Es determinista, tarda una fracción de segundo y sirve para el smoke. En contra: hay dos fuentes de tiempo (el reloj real y "un paso más") que mantener coherentes.
- **B. Tiempo real con el driver `dummy`.** Un solo camino de código, pero no es determinista, y una captura a los 10 minutos tarda 10 minutos. Choca con el ADR 0005.
- **Descartado: un script aparte en `tools/`.** El ADR 0013 fija que las capturas salen de `circlebh --demo … --capture`, y un script no ejercitaría el bucle real.

## Diseño

Las decisiones de esta sección son propuestas de Claude, salvo el enfoque A.

**Línea de comandos** (`circlebh/cli.py`, con `argparse` de la biblioteca estándar):

| Opción | Valor | Por defecto | Regla |
|---|---|---|---|
| `--demo` | — | apagado | partida simulada, sin teclado |
| `--scenario` | nombre | `plano-vacio` | debe existir; el error lista los válidos |
| `--seed` | entero ≥ 0 | al azar | se imprime al arrancar (ADR 0005) |
| `--speed` | número > 0 | `1` | multiplica el tiempo real en el modo con ventana; en captura no tiene efecto |
| `--capture` | `t1,t2,…` en segundos | — | exige `--demo`; tiempos ≥ 0; se ordenan y se quitan los repetidos |

`parse_args(argv)` devuelve un `RunOptions` (dataclass congelada) o termina con el error de `argparse` (código 2).

**Reloj de pasos fijos** (`circlebh/world/clock.py`, ADR 0005):
- `FixedStepClock.advance(real_dt) -> int`: suma el tiempo real al acumulador, topado en 0,25 s, y devuelve cuántos pasos de 1/60 s corresponden, guardando el resto.
- **Ejercicio del usuario** (modo enseñanza): el cuerpo de `advance`, de 5 a 10 líneas. Claude escribe los tests y los muestra fallando, marcados con `xfail(strict=True, reason="ejercicio pendiente: …")`.

**Pasos de captura** (`circlebh/world/clock.py`): `capture_steps(times) -> list[int]` convierte cada tiempo al paso más cercano, `round(t * 60)`. Así, `t = 1` es el paso 60.

**Escenarios** (`circlebh/scenes/scenarios.py`): un diccionario de nombre a escenario. Por ahora, solo `plano-vacio`. Cuando exista `world`, cada escenario va a armar su estado inicial.

**Dibujo** (`circlebh/render/plane.py`): `draw_empty_plane` sale de `__main__.py`, sin cambios.

**Modo captura** (`circlebh/__main__.py`):
1. Antes de `pygame.init()`, fija `SDL_VIDEODRIVER=dummy`.
2. Avanza paso a paso y, en cada paso de captura, dibuja y guarda el PNG.
3. Termina después de la última captura e imprime la ruta de cada archivo.

**Archivos:** `.capturas/<escenario>-seed<N>-t<segundos con 2 decimales>.png`, por ejemplo `plano-vacio-seed1-t1.00.png`. Si ya existe, se sobrescribe.

**`poe capturas`:** `circlebh --demo --scenario plano-vacio --seed 1 --capture 0,1,2`.

## Escenarios de test

`render/` y `scenes/` no se testean (ADR 0007). Lo demás:

- **`parse_args`**
  - Feliz: `--demo --scenario plano-vacio --seed 7 --capture 0,1,2` da esos valores.
  - Borde: `--capture 2,0,2` queda `(0.0, 2.0)`; sin `--seed`, la semilla es un entero ≥ 0.
  - Negativo: `--capture` sin `--demo`, un escenario desconocido, `--speed 0`, un tiempo negativo y `--capture a,b` terminan con código 2.
- **`capture_steps`**
  - Feliz: `[0, 1, 2]` da `[0, 60, 120]`.
  - Borde: `0.5` da 30; un tiempo que no cae justo en un paso va al más cercano.
  - Negativo: una lista vacía da una lista vacía.
- **`FixedStepClock.advance`** (ejercicio)
  - Feliz: `1/60` da 1 paso.
  - Borde: `1/120` dos veces da 0 y después 1, porque el resto se acumula; `0.25` da 15.
  - Negativo: `10` se topa en 0,25 s y da 15, no 600.
- **Modo captura, de punta a punta:** en una carpeta temporal, `main([... "--capture", "0,1"])` crea dos PNG con los nombres esperados y de 1280×720. Abre pygame con el driver `dummy`, así que corre en la CI.

## Pendiente de verificar al construir

- El nombre exacto del driver: en la tarea 3 funcionó `SDL_VIDEODRIVER=dummy` en Linux. Se confirma en la documentación de SDL. Windows y macOS se prueban en la tarea 9.
