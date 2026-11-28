"""Tests de los escenarios del benchmark: que midan lo que dicen medir (ADR 0006 y 0020).

El tiempo no se testea: en la CI sería inestable. Se corre a mano con `tools/benchmark.py`.
"""

from benchmark import boss_world, endless_world, swarm_world
from pygame.math import Vector2

from circlebh.balance import BALANCE
from circlebh.world.danger import NEUTRAL, Danger


def test_el_infinito_tiene_el_tope_de_cuerpos_del_mazo() -> None:
    # Decisión 73: el tope se mide con el mazo del infinito, no solo con hexágonos.
    world = endless_world(NEUTRAL)
    [infinito] = [s for s in BALANCE.director.sections if s.kind == "endless"]
    mazo = [BALANCE.enemies[entry.enemy] for entry in infinito.deck]
    assert world.bodies == BALANCE.director.max_alive
    assert all(enemy.spec in mazo for enemy in world.enemies)
    assert len({id(enemy.spec) for enemy in world.enemies}) > 1


def test_el_infinito_en_su_tope_nace_con_el_peligro() -> None:
    endless = BALANCE.director.endless
    tope = Danger(endless.speed_cap, endless.cadence_cap, 1.0)
    world = endless_world(tope)
    assert all(enemy.danger == tope for enemy in world.enemies)


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
