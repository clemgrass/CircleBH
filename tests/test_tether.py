"""Tests de la cuerda: el círculo gira atado al jugador en una espiral logarítmica,
`r = r₀·e^(−λt)` y `θ = θ₀ + ω·t` (spec de la 0.2.0, decisión 51)."""

import math
import random
from dataclasses import replace

import pytest
from pygame.math import Vector2

from circlebh.balance import BALANCE, CircleShape, TetherSpec
from circlebh.world.actions import Tether, make_action, step_actions
from circlebh.world.clock import STEP
from circlebh.world.enemy import Enemy
from circlebh.world.game import World
from circlebh.world.swarm import step_swarm

CUERDA = TetherSpec(angular_speed=0.8, decay=0.19)
CIRCULO = replace(
    BALANCE.enemies["hexagon"],
    shape=CircleShape(),
    radius=8.0,
    speed=0.0,
    friction=0.0,
    patterns=(),
    actions=(CUERDA,),
)
"""Un círculo con números propios, para que afinar el balance no cambie estos tests."""


def pasos(seconds: float) -> int:
    return round(seconds / STEP)


def paso(enemies: list[Enemy], jugador: Vector2) -> None:
    """Un paso como el del mundo: primero las acciones, después el enjambre."""
    step_actions(enemies, jugador, random.Random(0), [], BALANCE.enemy_bullet)
    step_swarm(enemies, jugador, BALANCE.player.charge, BALANCE.charges)


def test_make_action_elige_la_cuerda() -> None:
    assert isinstance(make_action(CUERDA), Tether)


def test_la_cuerda_sigue_la_espiral_logaritmica() -> None:
    circulo = Enemy(CIRCULO, Vector2(800, 0))
    n = pasos(5)
    for _ in range(n):
        paso([circulo], Vector2())
    t = n * STEP
    assert circulo.position.length() == pytest.approx(800 * math.exp(-0.19 * t))
    angulo = math.atan2(circulo.position.y, circulo.position.x)
    assert angulo == pytest.approx(math.remainder(0.8 * t, math.tau))


def test_la_espiral_no_se_deforma_si_el_jugador_se_mueve() -> None:
    # Los dos parten a (800, 0) del jugador, y uno de los jugadores avanza a 240.
    quieto = Enemy(CIRCULO, Vector2(800, 0))
    movido = Enemy(CIRCULO, Vector2(800, 0))
    jugador = Vector2()
    for i in range(pasos(5)):
        jugador = Vector2(240 * i * STEP, 0)
        paso([quieto], Vector2())
        paso([movido], jugador)
    assert tuple(movido.position - jugador) == pytest.approx(
        tuple(quieto.position), abs=1e-6
    )


def test_vuelve_a_la_curva_si_la_corren() -> None:
    circulo = Enemy(CIRCULO, Vector2(800, 0))
    paso([circulo], Vector2())
    circulo.position += Vector2(5, 5)
    paso([circulo], Vector2())
    assert circulo.position.length() == pytest.approx(800 * math.exp(-0.19 * 2 * STEP))


def test_encima_del_jugador_se_queda_encima() -> None:
    circulo = Enemy(CIRCULO, Vector2())
    for _ in range(10):
        paso([circulo], Vector2())
    assert circulo.position == Vector2()


@pytest.mark.parametrize(
    ("angular_speed", "decay"), [(0.8, 0.0), (0.8, -0.1), (0.0, 0.19)]
)
def test_rechaza_una_cuerda_que_no_se_acerca(
    angular_speed: float, decay: float
) -> None:
    mala = replace(
        BALANCE.enemies["circle"],
        actions=(TetherSpec(angular_speed=angular_speed, decay=decay),),
    )
    balance = replace(BALANCE, enemies={**BALANCE.enemies, "circle": mala})
    with pytest.raises(ValueError, match=r"enemies\.circle\.actions"):
        World(balance, random.Random(0))


def test_el_circulo_del_balance_va_atado() -> None:
    circulo = BALANCE.enemies["circle"]
    assert circulo.patterns == ()
    assert [type(a) for a in circulo.actions] == [TetherSpec]
