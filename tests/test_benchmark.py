"""Tests de los escenarios del benchmark: que midan lo que dicen medir (ADR 0006 y 0020).

El tiempo no se testea: en la CI sería inestable. Se corre a mano con `tools/benchmark.py`.
"""

from benchmark import boss_world, swarm_world
from pygame.math import Vector2


def test_el_enjambre_tiene_300_hexagonos() -> None:
    world = swarm_world()
    assert len(world.enemies) == 300
    assert {enemy.spec.shape.vertices for enemy in world.enemies} == {6}


def test_las_balas_le_pegan_al_jefe() -> None:
    # Lo encontró la revisión del #27: con el enemigo de 100 líneas fuera del alcance
    # del arma, el benchmark no medía las balas contra muchas líneas.
    world = boss_world()
    [boss] = world.enemies
    for _ in range(300):
        world.update(Vector2())
    assert len(boss.edges) < boss.spec.shape.line_count
