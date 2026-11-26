"""Tests del barrido: cómo dañan los trazos (ADR 0029, spec de la 0.3.0).

Cada punto de muestra de la curva es una bala durante un paso, probada con
`Enemy.hit_by`. Una pasada dura mientras la curva toca al enemigo, y en ella le quita a
lo más `payload.lines`.

El hexágono parte con un vértice arriba, así que sus líneas 1 y 4 son verticales: la 1
a la izquierda y la 4 a la derecha. Con el jugador en el origen y el hexágono en
`(100, 0)`, la 1 es la cara que mira al jugador.
"""

import math
from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pygame.math import Vector2

from circlebh.balance import BALANCE, AdvanceSpec, EnemySpec, StarPolygonShape
from circlebh.world.enemy import Enemy
from circlebh.world.events import Event, Hit
from circlebh.world.sweep import Pass, PointGrid, query_radius, touching
from circlebh.world.weapons import TraceWeapon

SPACING = 4.0
WIDTH = 4.0
# Un solo anillo en toda la prueba: el `cooldown` no alcanza a lanzar otro.
RING = replace(
    BALANCE.weapons["point"],
    kind="trace",
    frame="polar",
    advance=AdvanceSpec(coefficient=90.0, degree=1),
    reach=320.0,
    cooldown=100.0,
    payload=replace(BALANCE.weapons["point"].payload, lines=1, width=WIDTH),
)
# Sin patrones ni carga ni roce: aquí solo importa dónde está.
HEXAGON = EnemySpec(
    shape=StarPolygonShape(vertices=6, steps=(1,)),
    radius=24.0,
    speed=120.0,
    friction=0.0,
    spin=0.0,
    anchored=False,
    phantom=False,
    solitary=False,
    charge_per_line=0.0,
    mass_per_line=1.0,
    patterns=(),
    threat=1.0,
    actions=(),
    split_into="",
)
FACE = 1
"""La línea del hexágono que mira al jugador cuando el hexágono está a su derecha."""


def hexagono(x: float, y: float = 0.0) -> Enemy:
    return Enemy(HEXAGON, Vector2(x, y))


def golpes(eventos: list[Event]) -> list[Hit]:
    return [e for e in eventos if isinstance(e, Hit)]


def jugar(arma: TraceWeapon, enemigos: list[Enemy], pasos: int) -> list[Hit]:
    """Avanza el arma `pasos` pasos con el jugador quieto en el origen."""
    eventos: list[Event] = []
    for _ in range(pasos):
        eventos += arma.update(Vector2(), enemigos)
    return golpes(eventos)


# --- Tocar ---


@pytest.mark.parametrize(
    ("x", "toca"),
    [
        (10.0, True),  # dentro del hexágono, sin tocar ninguna línea
        (25.9, True),  # fuera del envolvente, dentro del medio grosor
        (26.0, True),  # justo en el borde agrandado: tocar incluye la tangente
        (26.1, False),  # negativo: fuera del envolvente agrandado
    ],
)
def test_toca_dentro_del_envolvente_agrandado(x: float, toca: bool) -> None:
    # El envolvente del hexágono mide 24; con grosor 4, se agranda en 2.
    assert touching([Vector2(300, 0), Vector2(x, 0)], hexagono(0), WIDTH) is toca


# --- El anillo ---


def test_anillo_quita_la_linea_que_mira_al_jugador() -> None:
    # Feliz: el anillo crece desde el jugador y la primera línea que barre es la cara
    # de enfrente, a 100 − 24·cos 30° ≈ 79 del jugador, en el paso ~53.
    enemigo = hexagono(100)
    assert jugar(TraceWeapon(RING, SPACING), [enemigo], 70) == [Hit(enemigo, FACE)]


def test_anillo_dentro_del_hexagono_sigue_en_la_misma_pasada() -> None:
    # Borde: el anillo que ya entró sigue tocando al hexágono, así que la pasada no se
    # reinicia y no le quita la línea de atrás al salir por el otro lado.
    enemigo = hexagono(100)
    golpes_ = jugar(TraceWeapon(RING, SPACING), [enemigo], 120)
    assert golpes_ == [Hit(enemigo, FACE)]
    assert len(enemigo.edges) == 5


def test_pasada_no_quita_mas_que_su_tope() -> None:
    # Borde: con dos líneas por pasada, quita la cara y una más, y nada después.
    dos = replace(RING, payload=replace(RING.payload, lines=2))
    enemigo = hexagono(100)
    golpes_ = jugar(TraceWeapon(dos, SPACING), [enemigo], 120)
    assert len(golpes_) == 2
    assert golpes_[0] == Hit(enemigo, FACE)


def test_anillo_sigue_al_jugador() -> None:
    # El marco polar se centra en el jugador de ahora: si se mueve, el anillo va con él.
    arma = TraceWeapon(RING, SPACING)
    for _ in range(10):
        arma.update(Vector2(), [])
    centro = Vector2(50, 20)
    arma.update(centro, [])
    # Nació en el primer paso: tiene 10 pasos, y su radio es 90 · 10/60 = 15.
    [curva] = arma.curves()
    assert all(p.distance_to(centro) == pytest.approx(15.0) for p in curva)


def test_anillo_revienta_en_su_alcance() -> None:
    # Borde: el anillo vive hasta que su avance llega a R, y entonces se quita.
    arma = TraceWeapon(RING, SPACING)
    # Nace en el primer paso. Con 213 pasos de edad va en 319,5; con 214 llega a R,
    # golpea por última vez con ese tramo y se quita.
    for _ in range(214):
        arma.update(Vector2(), [])
    assert arma.curves()
    arma.update(Vector2(), [])
    assert not arma.curves()


def test_lanza_un_anillo_cada_cooldown_aunque_no_haya_enemigos() -> None:
    # El anillo no apunta: sale cada `cooldown`, con o sin enemigos.
    seguido = replace(RING, cooldown=0.5)
    arma = TraceWeapon(seguido, SPACING)
    for _ in range(61):
        arma.update(Vector2(), [])
    # En los pasos 1, 31 y 61.
    assert len(arma.curves()) == 3


def test_escudo_quieto_dana_al_que_avanza() -> None:
    # Borde: un anillo de grado 0 queda quieto a `v·τ` del jugador. Sus puntos no se
    # mueven, pero el cruce se mide en el marco del enemigo, que sí avanza hacia él.
    escudo = replace(RING, advance=AdvanceSpec(coefficient=100.0, degree=0))
    arma = TraceWeapon(escudo, SPACING)
    enemigo = hexagono(120)
    enemigo.velocity = Vector2(-120, 0)
    eventos: list[Event] = []
    # 2 unidades por paso: en 40 pasos, de 120 a 40. La cara cruza el radio 50 cuando
    # el centro pasa por 50 + 24·cos 30° ≈ 71.
    for _ in range(40):
        enemigo.step(Vector2())
        eventos += arma.update(Vector2(), [enemigo])
    assert golpes(eventos) == [Hit(enemigo, FACE)]


# --- La pasada ---


def test_soltar_y_volver_empieza_otra_pasada() -> None:
    # Borde: cuando la curva deja de tocar al enemigo, la pasada termina, y al volver
    # empieza otra, que puede quitar otra línea.
    enemigo = hexagono(0)
    pasada = Pass()

    def paso(antes: Vector2, ahora: Vector2) -> list[Hit]:
        return pasada.strike([antes], [ahora], [enemigo], 1, WIDTH)

    # Entra por la izquierda y cruza la línea 1.
    assert paso(Vector2(-30, 0), Vector2(-15, 0)) == [Hit(enemigo, 1)]
    # Sale lejos: ya no toca.
    assert paso(Vector2(-15, 0), Vector2(-60, 0)) == []
    # Vuelve por arriba y cruza la línea 5.
    assert paso(Vector2(5, 40), Vector2(5, 15)) == [Hit(enemigo, 5)]


def test_sin_soltar_no_empieza_otra_pasada() -> None:
    # Negativo: lo mismo, pero sin salir del envolvente: la pasada sigue y no quita la
    # segunda línea.
    enemigo = hexagono(0)
    pasada = Pass()

    def paso(antes: Vector2, ahora: Vector2) -> list[Hit]:
        return pasada.strike([antes], [ahora], [enemigo], 1, WIDTH)

    assert paso(Vector2(-30, 0), Vector2(-15, 0)) == [Hit(enemigo, 1)]
    assert paso(Vector2(-15, 0), Vector2(-10, 0)) == []
    assert paso(Vector2(5, 40), Vector2(5, 15)) == []


def test_curva_por_un_hueco_no_dana() -> None:
    # Negativo: un trazo corto y vertical cruza de izquierda a derecha un hexágono sin
    # sus líneas verticales. Pasa por los huecos, entre las líneas inclinadas, sin tocar
    # ninguna.
    enemigo = hexagono(0)
    enemigo.remove_edge(1)
    enemigo.remove_edge(4)
    pasada = Pass()
    alturas = [-6.0, -4.0, -2.0, 0.0, 2.0, 4.0, 6.0]
    golpes_: list[Hit] = []
    for x in range(-40, 40, 4):
        antes = [Vector2(x, y) for y in alturas]
        ahora = [Vector2(x + 4, y) for y in alturas]
        golpes_ += pasada.strike(antes, ahora, [enemigo], 1, WIDTH)
    assert golpes_ == []
    assert enemigo.edges == [0, 2, 3, 5]


COORDENADAS = st.floats(min_value=-80, max_value=80)
PUNTOS = st.builds(Vector2, COORDENADAS, COORDENADAS)


@given(
    tramos=st.lists(st.tuples(PUNTOS, PUNTOS), min_size=1, max_size=30),
    velocidad=st.builds(Vector2, COORDENADAS, COORDENADAS),
    giro=st.floats(min_value=-30, max_value=30),
    perdida=st.sampled_from([None, 0, 3]),
)
def test_el_filtro_no_deja_fuera_ningun_golpe(
    tramos: list[tuple[Vector2, Vector2]],
    velocidad: Vector2,
    giro: float,
    perdida: int | None,
) -> None:
    # La grilla de puntos tiene que dar lo mismo que probar todos los puntos: todo
    # punto que golpea o toca al enemigo queda entre los cercanos. Con giro, movimiento
    # y una línea perdida, que corre el centro de masa (ADR 0027).
    spec = replace(HEXAGON, spin=giro, speed=1e9)
    enemigo = Enemy(spec, Vector2(3, -2))
    enemigo.velocity = velocidad * 60
    if perdida is not None:
        enemigo.remove_edge(perdida)
    enemigo.step(Vector2())
    antes = [a for a, _ in tramos]
    ahora = [b for _, b in tramos]
    largo = max(a.distance_to(b) for a, b in tramos)
    cercanos = PointGrid(ahora).near(
        enemigo.position, query_radius(enemigo, largo, WIDTH)
    )
    for i in range(len(tramos)):
        golpea = enemigo.hit_by(antes[i], ahora[i]) is not None
        if golpea or touching([ahora[i]], enemigo, WIDTH):
            assert i in cercanos


def en_anillo(centro: Vector2, radio: float, n: int) -> list[Vector2]:
    return [centro + Vector2(radio, 0).rotate_rad(math.tau * i / n) for i in range(n)]


NUBES = st.one_of(
    st.lists(PUNTOS, max_size=40),
    st.builds(
        en_anillo,
        PUNTOS,
        st.floats(min_value=0, max_value=300),
        st.integers(min_value=1, max_value=200),
    ),
)


@given(NUBES, PUNTOS, st.floats(min_value=0, max_value=100))
def test_near_da_lo_mismo_que_revisar_todos(
    puntos: list[Vector2], centro: Vector2, radio: float
) -> None:
    # La grilla y la franja solo descartan: encuentran lo mismo que revisar todos, con
    # la distancia al cuadrado, como `touching`.
    todos = [
        i for i, p in enumerate(puntos) if p.distance_squared_to(centro) <= radio**2
    ]
    assert PointGrid(puntos).near(centro, radio) == todos


def test_una_pasada_por_enemigo() -> None:
    # El tope es por enemigo: el mismo anillo le quita la cara a dos hexágonos.
    uno, otro = hexagono(100), hexagono(-100)
    golpes_ = jugar(TraceWeapon(RING, SPACING), [uno, otro], 70)
    assert sorted(golpes_, key=lambda h: h.enemy.position.x) == [
        Hit(otro, 4),
        Hit(uno, FACE),
    ]
