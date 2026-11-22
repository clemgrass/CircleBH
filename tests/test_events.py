"""Tests de los eventos del mundo: lo que pasó en cada paso, para la música (ADR 0022).

En el hexágono, la arista 1 es la vertical izquierda: una bala que sale del origen hacia
un enemigo en +x la golpea primero.
"""

import random
from collections.abc import Callable

from pygame.math import Vector2

from circlebh.balance import BALANCE, EnemySpec, StarPolygonShape
from circlebh.world.enemy import Enemy
from circlebh.world.events import Death, Hit, Shot
from circlebh.world.game import World

# Sin patrones ni carga: el enemigo se queda donde lo ponen.
QUIETO = EnemySpec(
    shape=StarPolygonShape(vertices=6, steps=(1,)),
    radius=24.0,
    speed=120.0,
    friction=0.0,
    spin=0.0,
    anchored=False,
    charge_per_line=0.0,
    patterns=(),
    threat=1.0,
    actions=(),
)


def mundo_con(enemy: Enemy, *, armed: bool = True, lethal: bool = True) -> World:
    world = World(BALANCE, random.Random(1), armed=armed, lethal=lethal)
    world.enemies = [enemy]
    return world


def avanzar_hasta(world: World, listo: Callable[[], bool], pasos: int = 300) -> None:
    """Avanza con el jugador quieto hasta que `listo()` sea verdadero."""
    for _ in range(pasos):
        world.update(Vector2())
        if listo():
            return
    raise AssertionError("no pasó en los pasos dados")


def test_disparo_deja_shot() -> None:
    world = mundo_con(Enemy(QUIETO, Vector2(100, 0)))
    world.update(Vector2())
    assert world.events == [Shot(world.weapons[0])]


def test_bala_que_golpea_deja_hit_con_la_arista() -> None:
    enemy = Enemy(QUIETO, Vector2(100, 0))
    world = mundo_con(enemy)
    avanzar_hasta(world, lambda: len(enemy.edges) < 6)
    [perdida] = set(range(6)) - set(enemy.edges)
    assert perdida == 1
    assert Hit(enemy, 1) in world.events


def test_ultima_linea_deja_hit_y_death_en_el_mismo_paso() -> None:
    enemy = Enemy(QUIETO, Vector2(100, 0))
    enemy.edges = [1]
    world = mundo_con(enemy)
    avanzar_hasta(world, lambda: enemy not in world.enemies)
    assert Hit(enemy, 1) in world.events
    assert Death(enemy) in world.events


def test_events_se_vacia_en_el_paso_siguiente() -> None:
    world = mundo_con(Enemy(QUIETO, Vector2(100, 0)))
    world.update(Vector2())
    assert world.events
    # La bala va en camino y el arma está recargando: no pasa nada.
    world.update(Vector2())
    assert world.events == []


def test_paso_sin_nada_deja_events_vacio() -> None:
    world = mundo_con(Enemy(QUIETO, Vector2(100, 0)), armed=False)
    world.update(Vector2())
    assert world.events == []


def test_despues_de_game_over_events_queda_vacio() -> None:
    # La arista 1 queda a 4,2 del jugador, dentro de su radio de 12: lo toca.
    world = mundo_con(Enemy(QUIETO, Vector2(25, 0)))
    world.update(Vector2())
    assert world.game_over
    world.update(Vector2())
    assert world.events == []
