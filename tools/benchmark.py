"""Mide los milisegundos por paso de `World.update` en dos escenarios cargados (ADR 0006).

- **enjambre:** 300 hexágonos apretados alrededor del jugador quieto (ADR 0021).
- **jefe:** un enemigo de 100 líneas, solo y al alcance del arma, para medir las balas
  contra muchas líneas (ADR 0020).
- **infinito:** `max_alive` cuerpos del mazo del infinito, con sus ataques, que es lo
  que fija el tope (decisión 73).
- **infinito-tope:** lo mismo, con la velocidad y la cadencia en su tope.

En todos, el arma dispara, el contacto no termina la partida y no aparecen enemigos
nuevos, así que se mide siempre lo mismo. La meta es menos de 16,6 ms por paso: 60 FPS.

Se corre a mano: en la CI, un test de tiempo sería inestable.
"""

import random
import statistics
import sys
import time
from collections.abc import Callable
from dataclasses import replace

from pygame.math import Vector2

from circlebh.balance import BALANCE, StarPolygonShape
from circlebh.world.danger import NEUTRAL, Danger
from circlebh.world.director import body_weight, deck_weights
from circlebh.world.enemy import Enemy
from circlebh.world.game import World
from circlebh.world.swarm import lattice

WARMUP_STEPS = 60
MEASURED_STEPS = 600
BUDGET_MS = 1000 / 60
ENDLESS_SPACING = 100.0
"""La separación de la red del infinito: más que el núcleo duro entre los más grandes,
dos estrellas (`1,2 · (40 + 40) = 96`), para que nadie nazca encimado."""

QUIET = replace(
    BALANCE,
    director=replace(
        BALANCE.director,
        sections=(replace(BALANCE.director.sections[0], deck=()),),
    ),
)
"""El balance real, sin apariciones durante la medición: un director sin mazo no
compra."""


def swarm_world() -> World:
    """300 hexágonos en una red triangular apretada alrededor del jugador."""
    world = World(QUIET, random.Random(1), lethal=False)
    hexagon = QUIET.enemies["hexagon"]
    world.enemies = [Enemy(hexagon, p) for p in lattice(Vector2(), 300, 60)]
    return world


def boss_world() -> World:
    """Un enemigo quieto de 100 líneas a 300 unidades: el único blanco del arma."""
    world = World(QUIET, random.Random(1), lethal=False)
    hexagon = QUIET.enemies["hexagon"]
    boss = replace(
        hexagon,
        shape=StarPolygonShape(vertices=100, steps=(1,)),
        radius=200.0,
        charge_per_line=0.0,
        patterns=(),
    )
    world.enemies = [Enemy(boss, Vector2(300, 0))]
    return world


def endless_world(danger: Danger) -> World:
    """`max_alive` cuerpos del mazo del infinito, sorteados por peso con `Random(1)`, en
    una red triangular alrededor del jugador, todos con el peligro `danger`.

    Un divisor cuenta por sus fragmentos (`body_weight`), así que se sortea solo entre
    los que caben en lo que queda del tope."""
    world = World(QUIET, random.Random(1), lethal=False)
    enemies = QUIET.enemies
    [section] = [s for s in BALANCE.director.sections if s.kind == "endless"]
    rng = random.Random(1)
    room = BALANCE.director.max_alive
    specs = []
    while room > 0:
        deck = [
            (enemies[entry.enemy], weight)
            for entry, weight in zip(
                section.deck, deck_weights(section, enemies, 1.0), strict=True
            )
            if body_weight(enemies[entry.enemy], enemies) <= room
        ]
        [spec] = rng.choices([s for s, _ in deck], [w for _, w in deck])
        specs.append(spec)
        room -= body_weight(spec, enemies)
    positions = lattice(Vector2(), len(specs), ENDLESS_SPACING)
    world.enemies = [
        Enemy(spec, p, danger) for spec, p in zip(specs, positions, strict=True)
    ]
    return world


def measure(make_world: Callable[[], World]) -> tuple[float, float]:
    """El promedio y el percentil 95 de un paso, en ms."""
    world = make_world()
    for _ in range(WARMUP_STEPS):
        world.update(Vector2())
    times_ms = []
    for _ in range(MEASURED_STEPS):
        start = time.perf_counter()
        world.update(Vector2())
        times_ms.append((time.perf_counter() - start) * 1000)
    return statistics.fmean(times_ms), statistics.quantiles(times_ms, n=20)[-1]


def main() -> int:
    ok = True
    endless = BALANCE.director.endless
    capped = Danger(endless.speed_cap, endless.cadence_cap, 1.0)
    cases: list[tuple[str, Callable[[], World]]] = [
        ("enjambre", swarm_world),
        ("jefe", boss_world),
        ("infinito", lambda: endless_world(NEUTRAL)),
        ("infinito-tope", lambda: endless_world(capped)),
    ]
    for name, make_world in cases:
        mean, p95 = measure(make_world)
        ok = ok and mean < BUDGET_MS
        print(
            f"{name}: {MEASURED_STEPS} pasos, promedio {mean:.2f} ms, p95 {p95:.2f} ms"
            f" (meta: < {BUDGET_MS:.1f} ms)"
        )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
