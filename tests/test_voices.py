"""Tests de las voces: cada enemigo es un loop euclidiano y cada arma, su ritmo (ADR 0022).

El enemigo de n lados toca E(n, 16), rotado por su ángulo alrededor del jugador. El
golpe i del loop es la arista i: si la arista no está, ese golpe calla.
"""

import math
from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pygame.math import Vector2

from circlebh.audio.harmony import CHORDS, Variation, chord_at
from circlebh.audio.rhythm import SIXTEENTHS, euclid
from circlebh.audio.voices import (
    EnemyView,
    enemy_notes,
    nearest_views,
    rotation,
    weapon_note,
    weapon_pattern,
)
from circlebh.balance import BALANCE, StarPolygonShape, WeaponSpec
from circlebh.world.enemy import Enemy

VOICING = CHORDS[0][1]
COMPAS = 60 / 124 * 4


def regular(n: int) -> StarPolygonShape:
    """El polígono regular de `n` lados, `{n/1}`."""
    return StarPolygonShape(vertices=n, steps=(1,))


def vista(
    edges: tuple[int, ...] = (0, 1, 2, 3, 4, 5), angle: float = 0.0, sides: int = 6
) -> EnemyView:
    return EnemyView(angle=angle, distance=100.0, shape=regular(sides), edges=edges)


def semicorcheas_que_suenan(view: EnemyView) -> list[int]:
    return [s for s in range(SIXTEENTHS) if enemy_notes([view], s, VOICING)]


# --- La voz de un enemigo ---


def test_hexagono_entero_suena_en_los_6_golpes_de_e_6_16() -> None:
    esperado = [s for s, golpe in enumerate(euclid(6, 16)) if golpe]
    assert semicorcheas_que_suenan(vista()) == esperado


def test_el_angulo_rota_el_loop() -> None:
    base = semicorcheas_que_suenan(vista())
    rotado = semicorcheas_que_suenan(vista(angle=math.tau * 4 / 16))
    assert rotado == sorted((s + 4) % 16 for s in base)


def test_si_pierde_la_arista_i_calla_el_golpe_i() -> None:
    golpes = [s for s, golpe in enumerate(euclid(6, 16)) if golpe]
    sin_la_2 = semicorcheas_que_suenan(vista(edges=(0, 1, 3, 4, 5)))
    assert sin_la_2 == [s for i, s in enumerate(golpes) if i != 2]


def test_la_nota_del_golpe_i_es_la_nota_i_del_acorde() -> None:
    golpes = [s for s, golpe in enumerate(euclid(6, 16)) if golpe]
    lejos = [
        vista(),
        EnemyView(
            angle=0.0, distance=500.0, shape=regular(6), edges=(0, 1, 2, 3, 4, 5)
        ),
    ]
    # El segundo más cercano no sube de octava.
    for i, s in enumerate(golpes):
        [primero, segundo] = enemy_notes(lejos, s, VOICING)
        assert segundo.semitones == VOICING[i % len(VOICING)]
        assert primero.semitones == segundo.semitones + 12


def test_el_mas_cercano_suena_mas_fuerte() -> None:
    cerca = EnemyView(angle=0.0, distance=50.0, shape=regular(6), edges=(0,))
    lejos = EnemyView(angle=0.0, distance=600.0, shape=regular(6), edges=(0,))
    [a, b] = enemy_notes([cerca, lejos], 0, VOICING)
    assert a.gain > b.gain > 0


def test_angulo_casi_una_vuelta_rota_cero() -> None:
    assert rotation(math.tau - 1e-9) == 0
    assert rotation(0.0) == 0


def test_solo_los_3_mas_cercanos_tienen_loop() -> None:
    hexagon = BALANCE.enemies["hexagon"]
    enemies = [Enemy(hexagon, Vector2(x, 0)) for x in (500, 100, 400, 200, 300)]
    views = nearest_views(enemies, Vector2())
    assert [round(v.distance) for v in views] == [100, 200, 300]


def test_enemigo_sobre_el_jugador_tiene_angulo_cero() -> None:
    enemy = Enemy(BALANCE.enemies["hexagon"], Vector2(3, 4))
    [view] = nearest_views([enemy], Vector2(3, 4))
    assert view.angle == 0
    assert view.distance == 0


def test_estrella_suena_en_e_10_16_y_calla_los_golpes_de_sus_lados() -> None:
    # 10 líneas: el loop es E(10, 16). El golpe j es la línea j, así que sin sus 5
    # lados solo suenan los golpes de las diagonales, del 5 al 9.
    estrella = BALANCE.enemies["star"].shape
    golpes = [s for s, golpe in enumerate(euclid(10, 16)) if golpe]
    entera = EnemyView(0.0, 100.0, estrella, tuple(range(10)))
    assert semicorcheas_que_suenan(entera) == golpes
    diagonales = EnemyView(0.0, 100.0, estrella, tuple(range(5, 10)))
    assert semicorcheas_que_suenan(diagonales) == golpes[5:]


def test_enemigo_de_100_lados_suena_sin_error() -> None:
    entero = vista(edges=tuple(range(100)), sides=100)
    assert semicorcheas_que_suenan(entero) == list(range(16))
    # Las aristas 0 a 6 son el sector 0 (k·16 // 100 = 0): sin ellas, calla el golpe 0.
    sin_sector_0 = vista(edges=tuple(range(7, 100)), sides=100)
    assert semicorcheas_que_suenan(sin_sector_0) == list(range(1, 16))


@given(
    angle=st.floats(0, math.tau, exclude_max=True),
    sides=st.integers(3, 40),
    data=st.data(),
    s=st.integers(0, 15),
    transpose=st.integers(-5, 2),
    bar=st.integers(0, 7),
)
def test_toda_nota_de_un_enemigo_esta_en_el_acorde(
    angle: float, sides: int, data: st.DataObject, s: int, transpose: int, bar: int
) -> None:
    edges = data.draw(
        st.lists(st.integers(0, sides - 1), min_size=1, unique=True).map(
            lambda e: tuple(sorted(e))
        )
    )
    _, voicing = chord_at(bar, Variation(transpose=transpose, first_chord=0))
    views = [EnemyView(angle, 10.0 * r, regular(sides), edges) for r in range(3)]
    for note in enemy_notes(views, s, voicing):
        assert note.semitones in voicing or note.semitones - 12 in voicing


# --- La voz del arma ---


def arma(cooldown: float) -> WeaponSpec:
    return replace(BALANCE.weapons["point"], cooldown=cooldown)


def test_arma_punto_con_cooldown_06_es_e_3_16() -> None:
    assert weapon_pattern(arma(0.6), COMPAS) == euclid(3, 16)


@pytest.mark.parametrize(
    ("cooldown", "golpes"), [(0.3, 6), (0.1, 16), (0.01, 16), (10.0, 1)]
)
def test_el_loop_del_arma_sigue_su_cooldown(cooldown: float, golpes: int) -> None:
    assert sum(weapon_pattern(arma(cooldown), COMPAS)) == golpes


@pytest.mark.parametrize("s", range(16))
def test_la_nota_del_arma_esta_en_el_acorde(s: int) -> None:
    assert weapon_note(s, VOICING) - 12 in VOICING
