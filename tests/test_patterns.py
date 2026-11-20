"""Tests de los patrones de movimiento: seek y coulomb (ADR 0021)."""

import math
from dataclasses import replace

import pytest
from pygame.math import Vector2

from circlebh.balance import BALANCE, CoulombSpec, SeekSpec
from circlebh.world.enemy import Enemy
from circlebh.world.patterns import Context, Coulomb, Seek, make_pattern

HEXAGON = BALANCE.enemies["hexagon"]
SOLO_COULOMB = replace(HEXAGON, patterns=(CoulombSpec(),))


def contexto(
    neighbors: list[Enemy] | None = None, player_charge: float = 0.0
) -> Context:
    return Context(
        player_position=Vector2(),
        player_charge=player_charge,
        charges=BALANCE.charges,
        neighbors=neighbors or [],
    )


def test_make_pattern_elige_la_clase_por_su_spec() -> None:
    assert isinstance(make_pattern(SeekSpec(strength=1.0)), Seek)
    assert isinstance(make_pattern(CoulombSpec()), Coulomb)


# --- seek ---


def test_seek_apunta_al_jugador_con_strength() -> None:
    enemy = Enemy(HEXAGON, Vector2(300, 0))
    a = Seek(SeekSpec(strength=240.0)).acceleration(enemy, contexto())
    assert tuple(a) == pytest.approx((-240.0, 0.0))


def test_seek_encima_del_jugador_es_cero() -> None:
    enemy = Enemy(HEXAGON, Vector2())
    assert Seek(SeekSpec(strength=240.0)).acceleration(enemy, contexto()) == Vector2()


def test_seek_no_depende_de_la_velocidad() -> None:
    quieto = Enemy(HEXAGON, Vector2(0, 300))
    rapido = Enemy(HEXAGON, Vector2(0, 300))
    rapido.velocity = Vector2(100, 0)
    seek = Seek(SeekSpec(strength=240.0))
    assert seek.acceleration(quieto, contexto()) == seek.acceleration(
        rapido, contexto()
    )


# --- coulomb ---


def test_herido_empuja_menos() -> None:
    a = Enemy(SOLO_COULOMB, Vector2(0, 0))
    sano = Enemy(SOLO_COULOMB, Vector2(100, 0))
    herido = Enemy(SOLO_COULOMB, Vector2(100, 0))
    for k in range(3):
        herido.remove_edge(k)
    coulomb = Coulomb()
    por_el_sano = coulomb.acceleration(a, contexto([sano])).length()
    por_el_herido = coulomb.acceleration(a, contexto([herido])).length()
    assert por_el_herido < por_el_sano


def test_lo_que_recibe_no_depende_de_sus_lineas() -> None:
    # A 100 unidades el núcleo no alcanza (d₀ = 57,6), y el jugador no tiene carga: solo
    # queda Coulomb, k·qₐ·q_b / mₐ, y qₐ / mₐ = charge_per_line.
    vecino = Enemy(SOLO_COULOMB, Vector2(100, 0))
    sano = Enemy(SOLO_COULOMB, Vector2(0, 0))
    herido = Enemy(SOLO_COULOMB, Vector2(0, 0))
    for k in range(3):
        herido.remove_edge(k)
    coulomb = Coulomb()
    assert tuple(coulomb.acceleration(herido, contexto([vecino]))) == pytest.approx(
        tuple(coulomb.acceleration(sano, contexto([vecino])))
    )


def test_no_se_repele_a_si_mismo() -> None:
    enemy = Enemy(SOLO_COULOMB, Vector2(50, 0))
    assert Coulomb().acceleration(enemy, contexto([enemy])) == Vector2()


def test_la_carga_del_jugador_lo_atrae() -> None:
    enemy = Enemy(SOLO_COULOMB, Vector2(100, 0))
    assert Coulomb().acceleration(enemy, contexto(player_charge=-14.0)).x < 0


def test_hexagono_sobre_el_jugador_quieto_se_mantiene_finito() -> None:
    # Foco de revisión 2: el hexágono real parte encima del jugador quieto, con seek y
    # su carga tirando al centro. Oscila, pero nunca da nan ni pasa `speed`.
    enemy = Enemy(HEXAGON, Vector2())
    ctx = contexto(player_charge=BALANCE.player.charge)
    for _ in range(600):
        enemy.step(enemy.acceleration(ctx))
        assert math.isfinite(enemy.position.x) and math.isfinite(enemy.position.y)
        assert enemy.velocity.length() <= HEXAGON.speed + 1e-9
