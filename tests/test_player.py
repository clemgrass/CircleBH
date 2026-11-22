"""Tests del jugador: avanza según la intención, a velocidad fija por paso."""

import pytest
from pygame.math import Vector2

from circlebh.balance import PlayerSpec
from circlebh.world.clock import STEP
from circlebh.world.player import Player

SPEC = PlayerSpec(speed=240.0, radius=12.0, charge=-14.0)


def test_jugador_nace_en_el_origen() -> None:
    player = Player(SPEC)
    assert player.position == Vector2(0, 0)
    assert player.radius == SPEC.radius


def test_previous_es_donde_estaba_antes_del_paso() -> None:
    # Lo usa el tramo de una bala enemiga, en el marco del jugador.
    player = Player(SPEC)
    assert player.previous == Vector2(0, 0)
    player.step(Vector2(1, 0))
    before = Vector2(player.position)
    player.step(Vector2(0, 1))
    assert player.previous == before
    assert player.previous is not player.position


def test_jugador_avanza_speed_por_paso() -> None:
    player = Player(SPEC)
    player.step(Vector2(1, 0))
    assert player.position.x == pytest.approx(240 / 60)
    assert player.position.y == 0


def test_intencion_larga_se_recorta() -> None:
    player = Player(SPEC)
    player.step(Vector2(3, 4))
    assert player.position.length() == pytest.approx(SPEC.speed * STEP)


def test_intencion_corta_avanza_menos() -> None:
    # El stick a medias mueve a media velocidad: solo se recorta lo que pasa de 1.
    player = Player(SPEC)
    player.step(Vector2(0, 0.5))
    assert player.position.y == pytest.approx(0.5 * SPEC.speed * STEP)


def test_intencion_cero_no_mueve() -> None:
    player = Player(SPEC)
    player.step(Vector2(0, 0))
    assert player.position == Vector2(0, 0)


def test_step_no_modifica_la_intencion() -> None:
    intent = Vector2(3, 4)
    Player(SPEC).step(intent)
    assert intent == Vector2(3, 4)
