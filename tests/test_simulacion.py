"""Las simulaciones largas sin ventana (ADR 0007).

Corren en `poe check` y en la CI, no en `poe fast`.
"""

import random
from itertools import combinations

import pytest
from pygame.math import Vector2

from circlebh.balance import BALANCE
from circlebh.pilot import simulate_worlds
from circlebh.world.enemy import Enemy
from circlebh.world.game import World
from circlebh.world.swarm import lattice


@pytest.mark.simulacion
def test_simulacion_de_60_s_sin_errores() -> None:
    # Lo que se exige es que no haya excepciones. Las duraciones confirman que jugó los
    # 60 s completos. Y en una partida normal la red de seguridad no actúa: la ley de
    # cargas basta para que no se superpongan (foco de revisión 5 del plan del #27).
    worlds = simulate_worlds(BALANCE, seconds=60.0, seed=1)
    assert sum(world.elapsed for world in worlds) == pytest.approx(60.0)
    assert [world.separations for world in worlds] == [0] * len(worlds)


@pytest.mark.simulacion
def test_300_hexagonos_nunca_se_tocan() -> None:
    # 300 hexágonos en una red triangular apretada contra el jugador quieto, sin contacto
    # ni armas. `seek` y la carga del jugador los aprietan; el núcleo duro los sostiene
    # (ADR 0021). Ningún paso necesita la red de seguridad.
    world = World(BALANCE, random.Random(1), lethal=False, armed=False)
    hexagon = BALANCE.enemies["hexagon"]
    world.enemies = [Enemy(hexagon, p) for p in lattice(Vector2(), 300, 60)]
    for _ in range(600):
        world.update(Vector2())
    assert world.separations == 0
    for a, b in combinations(world.enemies, 2):
        assert a.position.distance_to(b.position) >= a.radius + b.radius
