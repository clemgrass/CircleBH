"""Tests de las figuras: el polígono estrellado `{n/s}` (spec de la 0.2.0, "La estrella").

La estrella chica es `{5/1}` más `{5/2}`: primero sus 5 lados y después sus 5 diagonales.
"""

import math
import random
from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pygame.math import Vector2

from circlebh.balance import BALANCE, StarPolygonShape
from circlebh.world.collisions import crossing
from circlebh.world.enemy import Enemy
from circlebh.world.figures import check_shape, line_vertices, local_lines
from circlebh.world.game import World
from circlebh.world.polygon import TIE, polygon_edge

PHI = (1 + math.sqrt(5)) / 2
ESTRELLA = StarPolygonShape(vertices=5, steps=(1, 2))


def largo(linea: tuple[Vector2, Vector2]) -> float:
    a, b = linea
    return (b - a).length()


# --- La figura ---


@pytest.mark.parametrize("n", range(3, 13))
def test_regular_da_lo_mismo_que_antes(n: int) -> None:
    lineas = local_lines(StarPolygonShape(vertices=n, steps=(1,)), 24.0)
    assert lineas == [polygon_edge(24.0, n, k) for k in range(n)]


def test_estrella_tiene_diez_lineas() -> None:
    assert ESTRELLA.line_count == 10
    assert len(local_lines(ESTRELLA, 40.0)) == 10


def test_diagonal_mide_phi_veces_el_lado() -> None:
    lineas = local_lines(ESTRELLA, 40.0)
    lados, diagonales = lineas[:5], lineas[5:]
    for lado, diagonal in zip(lados, diagonales, strict=True):
        assert largo(diagonal) == pytest.approx(PHI * largo(lado))


def test_pentagrama_une_cada_vertice_con_el_que_esta_dos_mas_alla() -> None:
    pentagrama = StarPolygonShape(vertices=5, steps=(2,))
    assert line_vertices(pentagrama) == [(0, 2), (1, 3), (2, 4), (3, 0), (4, 1)]


# --- El chequeo al cargar ---


def test_rechaza_paso_de_media_vuelta() -> None:
    # En `{6/3}`, la línea 0 y la 3 son la misma: del vértice 0 al 3.
    with pytest.raises(ValueError, match=r"star\.shape"):
        check_shape(StarPolygonShape(vertices=6, steps=(3,)), "star")


def test_rechaza_pasos_repetidos() -> None:
    with pytest.raises(ValueError, match=r"star\.shape"):
        check_shape(StarPolygonShape(vertices=5, steps=(1, 1)), "star")


def test_rechaza_menos_de_tres_vertices() -> None:
    with pytest.raises(ValueError, match=r"star\.shape"):
        check_shape(StarPolygonShape(vertices=2, steps=(1,)), "star")


def test_acepta_la_estrella() -> None:
    check_shape(ESTRELLA, "star")


# --- El golpe (F1 del ADR 0027) ---


def estrella_en_el_origen() -> Enemy:
    """Una estrella quieta en el origen, sin girar: el marco del enemigo es el plano."""
    spec = replace(BALANCE.enemies["hexagon"], shape=ESTRELLA, radius=40.0)
    return Enemy(spec, Vector2())


def golpe_revisando_todas(
    enemy: Enemy, start: Vector2, end: Vector2
) -> tuple[float, int] | None:
    """La referencia: cruza el tramo con cada línea que queda, y gana el menor `t`. Si
    dos empatan (`TIE`), la de índice menor."""
    best: tuple[float, int] | None = None
    for k, (a, b) in zip(enemy.edges, enemy.lines(), strict=True):
        t = crossing(start, end, a, b)
        if t is not None and (best is None or t < best[0] - TIE):
            best = (t, k)
    return best


puntos = st.builds(Vector2, st.floats(-60, 60), st.floats(-60, 60))


@given(
    start=puntos,
    end=puntos,
    lineas=st.sets(st.integers(0, 9), min_size=1),
)
def test_estrella_golpe_igual_que_todas_las_lineas(
    start: Vector2, end: Vector2, lineas: set[int]
) -> None:
    enemy = estrella_en_el_origen()
    enemy.edges = sorted(lineas)
    assert enemy.hit_by(start, end) == golpe_revisando_todas(enemy, start, end)


def test_bala_desde_afuera_quita_un_lado_antes_que_una_diagonal() -> None:
    # A la altura y = 5, desde la izquierda, la bala cruza primero el lado 1, que va
    # del vértice en 162° al de 234°. Las diagonales quedan detrás.
    enemy = estrella_en_el_origen()
    hit = enemy.hit_by(Vector2(-60, 5), Vector2(60, 5))
    assert hit is not None
    assert hit[1] == 1


def test_sin_el_lado_la_bala_golpea_una_diagonal() -> None:
    enemy = estrella_en_el_origen()
    enemy.remove_edge(1)
    hit = enemy.hit_by(Vector2(-60, 5), Vector2(60, 5))
    assert hit is not None
    assert hit[1] >= 5


def test_el_mundo_rechaza_una_figura_invalida_nombrando_al_enemigo() -> None:
    malo = replace(
        BALANCE.enemies["hexagon"], shape=StarPolygonShape(vertices=6, steps=(3,))
    )
    balance = replace(BALANCE, enemies={**BALANCE.enemies, "malo": malo})
    with pytest.raises(ValueError, match=r"enemies\.malo\.shape"):
        World(balance, random.Random(0))
