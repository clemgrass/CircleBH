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
from circlebh.world.swarm import lattice, step_swarm


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


@pytest.mark.simulacion
def test_los_heridos_no_tiemblan_en_la_multitud() -> None:
    # Lo encontró la revisión del #27: un herido de 1 línea tiene masa 1, y el núcleo
    # (una fuerza que no depende de la masa) le da una rigidez seis veces mayor. Con
    # `ω·dt > 1`, Euler se pasa de un lado al otro en cada paso: tiembla a toda velocidad.
    # Aquí, 300 hexágonos con de 1 a 6 líneas al azar contra el jugador quieto. En los
    # últimos 2 s, ninguno puede invertir su velocidad de un paso al siguiente yendo a
    # más de 30 u/s, y la red de seguridad nunca actúa.
    rng = random.Random(1)
    hexagon = BALANCE.enemies["hexagon"]
    enemies = [Enemy(hexagon, p) for p in lattice(Vector2(), 300, 60)]
    for enemy in enemies:
        lines = hexagon.shape.line_count
        for k in rng.sample(range(lines), rng.randint(0, lines - 1)):
            enemy.remove_edge(k)
    separations = 0
    temblores = 0
    for paso in range(720):
        antes = [Vector2(enemy.velocity) for enemy in enemies]
        separations += step_swarm(
            enemies, Vector2(), BALANCE.player.charge, BALANCE.charges
        )
        if paso >= 600:
            temblores += sum(
                1
                for v, enemy in zip(antes, enemies, strict=True)
                if enemy.velocity.length() > 30 and v.dot(enemy.velocity) < 0
            )
    assert separations == 0
    assert temblores == 0
