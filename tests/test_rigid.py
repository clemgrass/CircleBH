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

from circlebh.balance import BALANCE, EnemySpec, StarPolygonShape
from circlebh.world.clock import STEP
from circlebh.world.collisions import closest_point_on_segment
from circlebh.world.enemy import Enemy
from circlebh.world.polygon import first_hit, polygon_edge, vertex
from circlebh.world.rigid import center_of_mass, rotate, to_local, to_world

# Sin patrones ni carga, y rápido, para poder darle cualquier velocidad.
CUADRADO = EnemySpec(
    shape=StarPolygonShape(vertices=4, steps=(1,)),
    radius=24.0,
    speed=1000.0,
    friction=0.0,
    spin=0.0,
    anchored=False,
    charge_per_line=0.0,
    patterns=(),
    threat=1.0,
    actions=(),
)
HEXAGONO = replace(CUADRADO, shape=StarPolygonShape(vertices=6, steps=(1,)))

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


@pytest.mark.parametrize("angulo", [1e-6, -1e-6, math.pi / 2 - 1e-7])
def test_rotar_un_angulo_casi_recto_no_se_redondea(angulo: float) -> None:
    # Borde: pygame-ce 2.5.8 redondea `rotate_rad` cerca de los múltiplos de 90°, y no
    # igual hacia los dos lados. `R(θ)·(0, −1) = (sen θ, −cos θ)`.
    girado = rotate(Vector2(0, -1), angulo)
    assert girado.x == pytest.approx(math.sin(angulo), rel=1e-12)
    assert girado.y == pytest.approx(-math.cos(angulo), rel=1e-12)


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
        # Del marco del cuerpo, centrado en su centro de masa, al del polígono.
        camino.append(to_local(start.lerp(end, s), centro, angulo) - enemy.offset)
    sides = enemy.spec.shape.vertices
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
    radius, sides = enemy.spec.radius, enemy.spec.shape.vertices
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
    unas 0,6 unidades. Vale también herido, girando en torno a su nuevo centro.
    """
    enemy = Enemy(replace(CUADRADO, spin=spin), Vector2())
    enemy.angle = angulo
    for k in set(range(4)) - otras - {linea}:
        enemy.remove_edge(k)
    enemy.velocity = velocidad
    enemy.step(Vector2())
    # La bala pasa por un punto de `linea` en la fracción `s` del paso. Así casi
    # siempre hay golpe, y el filtro descarta poco.
    a, b = polygon_edge(CUADRADO.radius, 4, linea)
    centro = enemy.previous.lerp(enemy.position, s)
    pose = enemy.previous_angle + s * (enemy.angle - enemy.previous_angle)
    cruce = to_world(a.lerp(b, u) + enemy.offset, centro, pose)
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


# --- Perder una línea: mismo giro, nuevo centro (L2 del ADR 0027) ---

giros = st.one_of(st.floats(0.1, MAX_SPIN), st.floats(-MAX_SPIN, -0.1))
lineas_del_cuadrado = st.sets(st.integers(0, 3), min_size=1, max_size=3)
"""Las líneas que se quitan: al menos una, y siempre queda una."""


def cuadrado_local(edges: set[int] | range) -> list[tuple[Vector2, Vector2]]:
    """Las líneas del cuadrado, medidas desde el centro del polígono."""
    return [polygon_edge(CUADRADO.radius, 4, k) for k in sorted(edges)]


def punto_medio(k: int) -> Vector2:
    a, b = polygon_edge(CUADRADO.radius, 4, k)
    return (a + b) / 2


def herido(spin: float, angulo: float, velocidad: Vector2) -> Enemy:
    """Un cuadrado que gira, a medio camino: ya dio un paso, así que la pose de antes
    y la de ahora difieren."""
    enemy = Enemy(replace(CUADRADO, spin=spin), Vector2(50, -20))
    enemy.angle = angulo
    enemy.velocity = velocidad
    enemy.step(Vector2())
    return enemy


def pose_de_antes(enemy: Enemy) -> list[tuple[Vector2, Vector2]]:
    """Sus líneas con la pose de antes del paso, la que usa `hit_by` para `start`."""
    return [
        (
            to_world(a + enemy.offset, enemy.previous, enemy.previous_angle),
            to_world(b + enemy.offset, enemy.previous, enemy.previous_angle),
        )
        for a, b in cuadrado_local(set(enemy.edges))
    ]


def test_centro_de_masa_del_cuadrado_entero_es_su_centro() -> None:
    assert center_of_mass(cuadrado_local(range(4))).length() < 1e-12


@pytest.mark.parametrize("quitada", range(4))
def test_centro_de_masa_se_corre_hacia_las_que_quedan(quitada: int) -> None:
    # Los cuatro puntos medios suman 0. Sin uno, `m`, el centro queda en `−m/3`: un
    # tercio de la apotema hacia el lado opuesto a la línea perdida.
    centro = center_of_mass(cuadrado_local(set(range(4)) - {quitada}))
    assert centro.distance_to(-punto_medio(quitada) / 3) < 1e-9


def test_centro_de_masa_pesa_cada_linea_por_su_largo() -> None:
    # Borde: líneas de largos distintos. La de largo 3 pesa el triple.
    corta = (Vector2(0, 0), Vector2(1, 0))
    larga = (Vector2(0, 10), Vector2(3, 10))
    centro = center_of_mass([corta, larga])
    assert centro.distance_to(Vector2((0.5 + 3 * 1.5) / 4, 30 / 4)) < 1e-12


def test_centro_de_masa_sin_lineas_falla() -> None:
    # Negativo: sin masa no hay centro.
    with pytest.raises(ValueError, match="sin líneas"):
        center_of_mass([])


@given(
    spin=giros,
    angulo=angulos,
    velocidad=st.builds(polar, st.floats(0, 120), angulos),
    quitadas=lineas_del_cuadrado,
)
def test_perder_linea_no_mueve_las_que_quedan(
    spin: float, angulo: float, velocidad: Vector2, quitadas: set[int]
) -> None:
    # Ni con la pose de ahora, que se dibuja, ni con la de antes, que usa `hit_by`.
    enemy = herido(spin, angulo, velocidad)
    quedan = sorted(set(range(4)) - quitadas)
    ahora = dict(zip(enemy.edges, enemy.lines(), strict=True))
    antes = dict(zip(enemy.edges, pose_de_antes(enemy), strict=True))
    for k in sorted(quitadas):
        enemy.remove_edge(k)
    for k, (a, b) in zip(quedan, enemy.lines(), strict=True):
        assert a.distance_to(ahora[k][0]) < 1e-9
        assert b.distance_to(ahora[k][1]) < 1e-9
    for k, (a, b) in zip(quedan, pose_de_antes(enemy), strict=True):
        assert a.distance_to(antes[k][0]) < 1e-9
        assert b.distance_to(antes[k][1]) < 1e-9


@given(
    spin=giros,
    angulo=angulos,
    velocidad=st.builds(polar, st.floats(0, 120), angulos),
    quitada=st.integers(0, 3),
)
def test_centro_nuevo_hereda_la_velocidad_de_su_punto(
    spin: float, angulo: float, velocidad: Vector2, quitada: int
) -> None:
    # Un punto `r` de un cuerpo que gira va a `v + ω × r`, con `ω × r = ω·(−r.y, r.x)`.
    enemy = herido(spin, angulo, velocidad)
    antes = Vector2(enemy.position)
    v = Vector2(enemy.velocity)
    enemy.remove_edge(quitada)
    r = enemy.position - antes
    assert r.length() == pytest.approx(CUADRADO.radius * math.sqrt(2) / 2 / 3)
    assert enemy.velocity.distance_to(v + spin * Vector2(-r.y, r.x)) < 1e-9
    assert enemy.omega == spin


@given(spin=giros, angulo=angulos, quitadas=lineas_del_cuadrado)
def test_la_envolvente_del_herido_contiene_sus_lineas(
    spin: float, angulo: float, quitadas: set[int]
) -> None:
    # La envolvente, medida desde el centro nuevo, es la justa: toca el extremo más
    # lejano.
    enemy = herido(spin, angulo, Vector2())
    for k in sorted(quitadas):
        enemy.remove_edge(k)
    distancias = [
        enemy.position.distance_to(p) for linea in enemy.lines() for p in linea
    ]
    assert max(distancias) == pytest.approx(enemy.radius)


def test_una_sola_linea_gira_en_su_punto_medio() -> None:
    # Borde: con una sola línea, el centro de masa es su punto medio, y la línea gira
    # en torno a él sin moverlo.
    enemy = Enemy(replace(CUADRADO, spin=1.5), Vector2(100, 0))
    for k in (0, 1, 2):
        enemy.remove_edge(k)
    assert enemy.position.distance_to(Vector2(100, 0) + punto_medio(3)) < 1e-9
    assert enemy.radius == pytest.approx(CUADRADO.radius * math.sqrt(2) / 2)
    enemy.velocity = Vector2()
    for _ in range(30):
        enemy.step(Vector2())
    [(a, b)] = enemy.lines()
    assert ((a + b) / 2).distance_to(enemy.position) < 1e-9


def test_perder_la_ultima_linea_lo_mata_sin_dividir_por_cero() -> None:
    enemy = Enemy(replace(CUADRADO, spin=1.5), Vector2())
    for k in range(4):
        enemy.remove_edge(k)
    assert enemy.alive is False


def test_sin_giro_perder_linea_no_mueve_nada() -> None:
    # Negativo: la regla de la 0.1.0 (decisión 15) para los que no giran.
    enemy = Enemy(BALANCE.enemies["hexagon"], Vector2(100, 0))
    enemy.velocity = Vector2(10, 0)
    lineas = enemy.lines()
    enemy.remove_edge(2)
    assert enemy.position == Vector2(100, 0)
    assert enemy.velocity == Vector2(10, 0)
    assert enemy.offset == Vector2()
    assert enemy.radius == BALANCE.enemies["hexagon"].radius
    assert enemy.lines() == [linea for k, linea in enumerate(lineas) if k != 2]
