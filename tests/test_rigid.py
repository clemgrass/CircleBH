"""Tests del cuerpo rígido: el giro del enemigo y los golpes en su marco (ADR 0027).

El cuadrado de radio 24 sin girar es un rombo: su vértice 3 está en (24, 0), y la
arista 3 va de ahí al vértice 0, en (0, 24). Girado en `π/4`, sus lados quedan
horizontales y verticales, y la arista 2 es la vertical derecha, en `x ≈ 16,97`.
"""

import math
from dataclasses import replace
from itertools import pairwise

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st
from pygame.math import Vector2

from circlebh.balance import BALANCE, EnemySpec
from circlebh.world.clock import STEP
from circlebh.world.collisions import closest_point_on_segment
from circlebh.world.enemy import Enemy
from circlebh.world.polygon import first_hit, polygon_edge, vertex
from circlebh.world.rigid import to_local, to_world

# Sin patrones ni carga, y rápido, para poder darle cualquier velocidad.
CUADRADO = EnemySpec(
    sides=4,
    radius=24.0,
    speed=1000.0,
    friction=0.0,
    spin=0.0,
    charge_per_line=0.0,
    patterns=(),
    threat=1.0,
)
HEXAGONO = replace(CUADRADO, sides=6)

SUBPASOS = 16
"""Los subpasos del cálculo de referencia."""

MAX_SPIN = 0.1 / STEP
"""El giro más rápido que cubre el test de referencia: `|ω·dt| ≤ 0,1`."""

angulos = st.floats(-math.pi, math.pi)


def polar(largo: float, angulo: float) -> Vector2:
    return largo * Vector2(math.cos(angulo), math.sin(angulo))


def girado(angulo: float, spec: EnemySpec = CUADRADO) -> Enemy:
    """Un enemigo quieto en el origen, girado en `angulo` desde antes del paso."""
    enemy = Enemy(spec, Vector2())
    enemy.angle = enemy.previous_angle = angulo
    return enemy


# --- El ángulo ---


def test_angulo_avanza_omega_por_paso() -> None:
    enemy = Enemy(replace(CUADRADO, spin=2.0), Vector2())
    assert (enemy.angle, enemy.omega) == (0.0, 2.0)
    enemy.step(Vector2())
    enemy.step(Vector2())
    assert enemy.previous_angle == pytest.approx(2.0 * STEP)
    assert enemy.angle == pytest.approx(2 * 2.0 * STEP)


def test_giro_negativo_es_horario() -> None:
    # Borde: ángulos antihorarios (ADR 0003), así que `spin < 0` resta.
    enemy = Enemy(replace(CUADRADO, spin=-3.0), Vector2())
    enemy.step(Vector2())
    assert enemy.angle == pytest.approx(-3.0 * STEP)


def test_sin_giro_el_angulo_no_cambia() -> None:
    # Negativo: el hexágono de la 0.1.0 no gira.
    enemy = Enemy(BALANCE.enemies["hexagon"], Vector2())
    for _ in range(10):
        enemy.step(Vector2(50, 0))
    assert (enemy.angle, enemy.previous_angle, enemy.omega) == (0.0, 0.0, 0.0)


@given(
    punto=st.builds(Vector2, st.floats(-1e3, 1e3), st.floats(-1e3, 1e3)),
    centro=st.builds(Vector2, st.floats(-1e3, 1e3), st.floats(-1e3, 1e3)),
    angulo=angulos,
)
def test_marco_local_y_del_plano_son_inversos(
    punto: Vector2, centro: Vector2, angulo: float
) -> None:
    vuelta = to_world(to_local(punto, centro, angulo), centro, angulo)
    assert vuelta.distance_to(punto) < 1e-9


# --- Las líneas y el jugador ---


def test_lineas_giradas() -> None:
    enemy = girado(math.pi / 4)
    enemy.position = Vector2(100, 0)
    # La arista 2 queda vertical, a la derecha del centro.
    a, b = enemy.lines()[2]
    lado = 24 / math.sqrt(2)
    assert a.x == pytest.approx(100 + lado)
    assert b.x == pytest.approx(100 + lado)
    assert sorted([a.y, b.y]) == pytest.approx([-lado, lado])


def test_jugador_toca_linea_rotada() -> None:
    # En (19, 0) con radio 2,5: el rombo queda a 3,5 y el cuadrado girado, a 2,0.
    centro, radio = Vector2(19, 0), 2.5
    assert girado(0.0).touches(centro, radio) is False
    assert girado(math.pi / 4).touches(centro, radio) is True


# --- Los golpes ---


def test_golpe_con_giro_usa_la_linea_rotada() -> None:
    # Una bala horizontal por y = 5, desde la derecha: al rombo le quita la arista 3
    # y al cuadrado girado, la vertical derecha.
    start, end = Vector2(30, 5), Vector2(10, 5)
    hit_rombo = girado(0.0).hit_by(start, end)
    hit_girado = girado(math.pi / 4).hit_by(start, end)
    assert hit_rombo is not None and hit_rombo[1] == 3
    assert hit_girado is not None and hit_girado[1] == 2


def test_bala_que_pasa_por_fuera_no_golpea_al_girado() -> None:
    # Negativo: la envolvente sigue descartando, gire o no.
    enemy = girado(1.0)
    assert enemy.hit_by(Vector2(30, 30), Vector2(30, -30)) is None


@given(
    lineas=st.sets(st.integers(0, 5), min_size=1),
    velocidad=st.builds(polar, st.floats(0, 120), angulos),
    start=st.builds(polar, st.floats(0, 40), angulos),
    tramo=st.builds(polar, st.floats(0, 20), angulos),
)
def test_sin_giro_golpea_igual_que_antes(
    lineas: set[int], velocidad: Vector2, start: Vector2, tramo: Vector2
) -> None:
    # El tramo relativo de la 0.1.0 (ADR 0020): de `start − previous` a
    # `end − position`, contra todas las líneas que quedan.
    enemy = Enemy(HEXAGONO, Vector2())
    enemy.edges = sorted(lineas)
    enemy.velocity = velocidad
    enemy.step(Vector2())
    end = start + tramo
    antes = first_hit(
        start - enemy.previous, end - enemy.position, 24.0, 6, enemy.edges
    )
    assert enemy.hit_by(start, end) == antes


def golpe_en_subpasos(
    enemy: Enemy, start: Vector2, end: Vector2
) -> tuple[int, Vector2, Vector2, list[Vector2]] | None:
    """El cálculo de referencia: parte el paso en `SUBPASOS`, con la pose y la bala
    interpoladas, y busca la primera línea que cruza el camino en el marco del enemigo.

    Devuelve la línea, el punto del cruce, la dirección del subpaso que la cruza y el
    camino entero, en el marco del enemigo.
    """
    camino = []
    for i in range(SUBPASOS + 1):
        s = i / SUBPASOS
        centro = enemy.previous.lerp(enemy.position, s)
        angulo = enemy.previous_angle + s * (enemy.angle - enemy.previous_angle)
        camino.append(to_local(start.lerp(end, s), centro, angulo))
    sides = enemy.spec.sides
    for p, q in pairwise(camino):
        hit = first_hit(p, q, enemy.spec.radius, sides, enemy.edges)
        if hit is not None:
            t, k = hit
            return k, p.lerp(q, t), q - p, camino
    return None


def tolerancia(enemy: Enemy, start: Vector2, end: Vector2) -> float:
    """Cuánto se aparta el tramo recto del camino curvo de la bala en el marco del
    enemigo: `(2·|w|·|Δr| + w²·|r|) / 8`, con `w = ω·dt` y `r` la bala vista desde el
    centro del enemigo. Es la cota del error de interpolar lineal, `max|q''| / 8`."""
    w = enemy.omega * STEP
    r0, r1 = start - enemy.previous, end - enemy.position
    return (2 * abs(w) * (r1 - r0).length() + w**2 * max(r0.length(), r1.length())) / 8


def ambiguo(camino: list[Vector2], enemy: Enemy, margen: float) -> bool:
    """Si el camino pasa a `margen` o menos de un vértice de las líneas que quedan, o
    si empieza o termina a esa distancia de una línea. Ahí, un error del tamaño del
    margen puede cambiar qué línea se golpea, o si se golpea en este paso o el que
    sigue."""
    radius, sides = enemy.spec.radius, enemy.spec.sides
    vertices = {k for edge in enemy.edges for k in (edge, (edge + 1) % sides)}
    cerca_de_un_vertice = any(
        v.distance_to(closest_point_on_segment(v, p, q)) <= margen
        for k in vertices
        for v in [vertex(radius, sides, k)]
        for p, q in pairwise(camino)
    )
    extremo_sobre_una_linea = any(
        punto.distance_to(closest_point_on_segment(punto, a, b)) <= margen
        for punto in (camino[0], camino[-1])
        for a, b in (polygon_edge(radius, sides, k) for k in enemy.edges)
    )
    return cerca_de_un_vertice or extremo_sobre_una_linea


@given(
    spin=st.floats(-MAX_SPIN, MAX_SPIN),
    angulo=angulos,
    velocidad=st.builds(polar, st.floats(0, 120), angulos),
    linea=st.integers(0, 3),
    otras=st.sets(st.integers(0, 3)),
    u=st.floats(0.1, 0.9),
    s=st.floats(0.0, 1.0),
    tramo=st.builds(polar, st.floats(1, 6), angulos),
)
def test_golpe_con_giro_coincide_con_subpasos(
    spin: float,
    angulo: float,
    velocidad: Vector2,
    linea: int,
    otras: set[int],
    u: float,
    s: float,
    tramo: Vector2,
) -> None:
    """Con `|ω·dt| ≤ 0,1`, el tramo recto en el marco del enemigo le quita la misma
    línea que 16 subpasos, salvo en los casos ambiguos (`ambiguo`) o si la cruza casi
    rasante. El margen es el doble de la `tolerancia`: con estos números, a lo más
    unas 0,6 unidades.
    """
    enemy = Enemy(replace(CUADRADO, spin=spin), Vector2())
    enemy.angle = angulo
    enemy.velocity = velocidad
    enemy.step(Vector2())
    enemy.edges = sorted(otras | {linea})
    # La bala pasa por un punto de `linea` en la fracción `s` del paso. Así casi
    # siempre hay golpe, y el filtro descarta poco.
    a, b = polygon_edge(CUADRADO.radius, 4, linea)
    centro = enemy.previous.lerp(enemy.position, s)
    pose = enemy.previous_angle + s * (enemy.angle - enemy.previous_angle)
    cruce = to_world(a.lerp(b, u), centro, pose)
    start, end = cruce - tramo * s, cruce + tramo * (1 - s)

    referencia = golpe_en_subpasos(enemy, start, end)
    assume(referencia is not None)
    assert referencia is not None
    k, _, direccion, camino = referencia
    a, b = polygon_edge(CUADRADO.radius, 4, k)
    rasante = abs(direccion.normalize().cross((b - a).normalize())) < 0.3
    margen = 2 * tolerancia(enemy, start, end) + 1e-6
    assume(not rasante and not ambiguo(camino, enemy, margen))

    hit = enemy.hit_by(start, end)
    assert hit is not None
    assert hit[1] == k
