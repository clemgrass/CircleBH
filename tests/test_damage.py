"""Tests del daño: cada bala quita la línea que golpea (ADR 0020).

En el hexágono, la arista 1 es la vertical izquierda y la 4, la derecha. Una bala que
llega por la izquierda, en horizontal, golpea primero la 1.
"""

import random
from dataclasses import replace

from pygame.math import Vector2

from circlebh.balance import BALANCE, EnemySpec, PointWeaponSpec
from circlebh.world.enemy import Enemy
from circlebh.world.game import World
from circlebh.world.polygon import vertex
from circlebh.world.weapons import PointWeapon

SPEC = PointWeaponSpec(cooldown=0.5, speed=600.0, range=700.0)
# Sin patrones ni carga: aquí solo importa dónde está.
HEXAGON = EnemySpec(
    sides=6,
    radius=24.0,
    speed=120.0,
    friction=0.0,
    spin=0.0,
    charge_per_line=0.0,
    patterns=(),
    threat=1.0,
)
ORIGEN = Vector2(0, 0)


def disparar(enemy: Enemy, pasos: int) -> PointWeapon:
    """Un arma en el origen que dispara `pasos` veces al enemigo, que no se mueve."""
    weapon = PointWeapon(SPEC)
    for _ in range(pasos):
        weapon.update(ORIGEN, [enemy])
    return weapon


def test_bala_que_cruza_una_linea_la_quita_y_desaparece() -> None:
    enemy = Enemy(HEXAGON, Vector2(100, 0))
    # La arista 1 está en x ≈ 79,2; a 10 unidades por paso, la bala llega en el paso 8.
    weapon = disparar(enemy, 10)
    assert enemy.edges == [0, 2, 3, 4, 5]
    assert weapon.bullets == []


def test_una_bala_quita_una_sola_linea() -> None:
    # Negativo: tras golpear, la bala no sigue hasta la arista de atrás (x ≈ 120,8).
    enemy = Enemy(HEXAGON, Vector2(100, 0))
    disparar(enemy, 25)
    assert len(enemy.edges) == 5


def test_tres_balas_al_centro_quitan_solo_dos_lineas() -> None:
    # Decisión 18: desde el mismo ángulo, la tercera pasa por los dos huecos.
    enemy = Enemy(HEXAGON, Vector2(100, 0))
    # Disparos en los pasos 0, 30 y 60; el cuarto sería en el 90.
    weapon = disparar(enemy, 80)
    assert enemy.edges == [0, 2, 3, 5]
    assert len(weapon.bullets) == 1
    assert weapon.bullets[0].position.x > 130


def test_bala_que_entra_por_un_hueco_golpea_desde_adentro() -> None:
    enemy = Enemy(HEXAGON, Vector2(100, 0))
    enemy.remove_edge(1)
    disparar(enemy, 15)
    assert enemy.edges == [0, 2, 3, 5]


def test_bala_dentro_de_la_envolvente_sin_cruzar_no_golpea() -> None:
    # Entre la arista 4 (x ≈ 20,8) y la envolvente (x = 24): adentro del círculo,
    # afuera del polígono, sin cruzar ninguna línea.
    enemy = Enemy(HEXAGON, Vector2(0, 0))
    assert enemy.hit_by(Vector2(23, -1), Vector2(23, 1)) is None


def test_tramo_que_termina_en_un_vertice_golpea() -> None:
    # Lo encontró Hypothesis: el vértice 7 de un polígono de 20 lados queda, por
    # redondeo, a 24,000000000000004 del centro, y la envolvente de radio 24 descartaba
    # un golpe que la prueba exacta sí encuentra.
    veinte = replace(HEXAGON, sides=20, speed=0.0)
    enemy = Enemy(veinte, Vector2(0, 0))
    v = vertex(veinte.radius, veinte.sides, 7)
    assert enemy.hit_by(Vector2(-29, -1), v) is not None


def test_hit_by_da_t_y_arista() -> None:
    enemy = Enemy(HEXAGON, Vector2(0, 0))
    hit = enemy.hit_by(Vector2(50, 0), Vector2(10, 0))
    assert hit is not None
    assert hit[1] == 4


def test_enemigo_que_avanza_no_deja_pasar_la_bala() -> None:
    # Un enemigo muy rápido (50 por paso) contra una bala de 10 por paso: sin el tramo
    # relativo, la arista de enfrente saltaría por encima de la bala.
    rapido = replace(HEXAGON, speed=3000.0)
    enemy = Enemy(rapido, Vector2(300, 0))
    # Sin roce ni patrones, avanza a velocidad fija hacia el origen.
    enemy.velocity = Vector2(-3000, 0)
    weapon = PointWeapon(SPEC)
    for _ in range(10):
        enemy.step(Vector2())
        weapon.update(ORIGEN, [enemy])
        if len(enemy.edges) < 6:
            break
    assert enemy.edges == [0, 2, 3, 4, 5]


def test_enemigo_sin_lineas_desaparece_del_mundo() -> None:
    world = World(BALANCE, random.Random(1))
    enemy = Enemy(BALANCE.enemies["hexagon"], Vector2(-150, 0))
    world.enemies = [enemy]
    for k in [0, 2, 3, 4, 5]:
        enemy.remove_edge(k)
    # Solo le queda la arista 4, la que mira al jugador.
    for _ in range(30):
        world.update(Vector2())
        if not world.enemies:
            break
    assert world.enemies == []
    assert world.game_over is False
