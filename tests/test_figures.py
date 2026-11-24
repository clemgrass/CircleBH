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

from circlebh.balance import BALANCE, CircleShape, SegmentShape, StarPolygonShape
from circlebh.world.collisions import crossing
from circlebh.world.enemy import Enemy
from circlebh.world.figures import (
    check_shape,
    line_vertices,
    local_lines,
    triangulation_centroids,
)
from circlebh.world.game import World
from circlebh.world.polygon import TIE, polygon_edge, vertex

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


def test_segmento_tiene_una_linea_de_largo_2r() -> None:
    # La línea suelta del regenerador (#62): un diámetro sobre el eje x.
    [(a, b)] = local_lines(SegmentShape(), 12.0)
    assert (a, b) == (Vector2(-12, 0), Vector2(12, 0))
    assert SegmentShape().line_count == 1


def test_volley_en_segmento_se_rechaza() -> None:
    # Negativo: un segmento solo no tiene puntas desde donde disparar una salva.
    pentagono = BALANCE.enemies["pentagon"]
    malo = replace(pentagono, shape=SegmentShape())
    balance = replace(BALANCE, enemies={**BALANCE.enemies, "pentagon": malo})
    with pytest.raises(ValueError, match=r"enemies\.pentagon\.actions"):
        World(balance, random.Random(0))


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


# --- El círculo (#59) ---


def test_circulo_tiene_una_linea_y_ningun_segmento() -> None:
    assert CircleShape().line_count == 1
    assert local_lines(CircleShape(), 8.0) == []


def test_rechaza_un_circulo_con_volley() -> None:
    # La salva sale de los vértices, y el círculo no tiene.
    malo = replace(BALANCE.enemies["pentagon"], shape=CircleShape())
    balance = replace(BALANCE, enemies={**BALANCE.enemies, "malo": malo})
    with pytest.raises(ValueError, match=r"enemies\.malo\.actions"):
        World(balance, random.Random(0))


def test_acepta_el_circulo() -> None:
    circulo = replace(BALANCE.enemies["hexagon"], shape=CircleShape(), radius=8.0)
    balance = replace(BALANCE, enemies={**BALANCE.enemies, "circulo": circulo})
    World(balance, random.Random(0))


# --- La triangulación del divisor (#63) ---


@given(n=st.integers(3, 12))
def test_triangulacion_da_n_menos_2_centroides(n: int) -> None:
    # El abanico desde el vértice 0: el triángulo k une v₀, vₖ y vₖ₊₁.
    r = 30.0
    centroides = triangulation_centroids(StarPolygonShape(vertices=n, steps=(1,)), r)
    assert len(centroides) == n - 2
    for k, c in enumerate(centroides, start=1):
        esperado = (vertex(r, n, 0) + vertex(r, n, k) + vertex(r, n, k + 1)) / 3
        assert c.distance_to(esperado) < 1e-9


@given(n=st.integers(3, 12), r=st.floats(1, 100))
def test_centroides_dentro_del_padre(n: int, r: float) -> None:
    # Dentro de un polígono convexo antihorario: a la izquierda de cada arista.
    for c in triangulation_centroids(StarPolygonShape(vertices=n, steps=(1,)), r):
        for k in range(n):
            a, b = vertex(r, n, k), vertex(r, n, k + 1)
            assert (b - a).cross(c - a) > 0
