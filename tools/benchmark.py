"""Mide los milisegundos por paso de `World.update` en un escenario cargado (ADR 0006).

300 hexágonos apretados alrededor del jugador quieto, más un enemigo de 100 líneas sin
carga, que mide el costo de las balas contra muchas líneas (ADR 0020). El arma dispara,
y el contacto no termina la partida. La meta es menos de 16,6 ms por paso: 60 FPS.

Se corre a mano: en la CI, un test de tiempo sería inestable.
"""

import random
import statistics
import sys
import time
from dataclasses import replace

from pygame.math import Vector2

from circlebh.balance import BALANCE
from circlebh.world.enemy import Enemy
from circlebh.world.game import World
from circlebh.world.swarm import lattice

HEXAGONS = 300
WARMUP_STEPS = 60
MEASURED_STEPS = 600
BUDGET_MS = 1000 / 60


def loaded_world() -> World:
    """El escenario del benchmark, siempre con la semilla 1."""
    world = World(BALANCE, random.Random(1), lethal=False)
    hexagon = BALANCE.enemies["hexagon"]
    big = replace(hexagon, sides=100, radius=200.0, charge_per_line=0.0, patterns=())
    world.enemies = [Enemy(hexagon, p) for p in lattice(Vector2(), HEXAGONS, 60)]
    world.enemies.append(Enemy(big, Vector2(900, 0)))
    return world


def main() -> int:
    world = loaded_world()
    for _ in range(WARMUP_STEPS):
        world.update(Vector2())
    times_ms = []
    for _ in range(MEASURED_STEPS):
        start = time.perf_counter()
        world.update(Vector2())
        times_ms.append((time.perf_counter() - start) * 1000)
    mean = statistics.fmean(times_ms)
    p95 = statistics.quantiles(times_ms, n=20)[-1]
    print(
        f"{len(world.enemies)} enemigos, {MEASURED_STEPS} pasos:"
        f" promedio {mean:.2f} ms, p95 {p95:.2f} ms (meta: < {BUDGET_MS:.1f} ms)"
    )
    return 0 if mean < BUDGET_MS else 1


if __name__ == "__main__":
    sys.exit(main())
