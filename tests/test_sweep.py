"""Tests del barrido: cómo dañan los trazos (ADR 0029 y 0032).

Cada punto de muestra de la curva es una bala durante un paso, probada con
`Enemy.hit_by`. Al pegarle a un enemigo, el trazo le quita a lo más `payload.lines`, y
el arco que lo cubre visto desde el jugador desaparece: el trazo se gasta donde pega.

El hexágono parte con un vértice arriba, así que sus líneas 1 y 4 son verticales: la 1
a la izquierda y la 4 a la derecha. Con el jugador en el origen y el hexágono en
`(100, 0)`, la 1 es la cara que mira al jugador, a 100 − 24·cos 30° ≈ 79.
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
from circlebh.world.sweep import PointGrid, query_radius, strike
from circlebh.world.weapons import TraceWeapon

SPACING = 4.0
# El anillo crece a 200 por segundo hasta 200: vive 60 pasos. Un solo anillo en toda
# la prueba: el `cooldown` no alcanza a lanzar otro.
RING = replace(
    BALANCE.weapons["point"],
    kind="trace",
    frame="polar",
    advance=AdvanceSpec(coefficient=200.0, degree=1),
    reach=200.0,
    cooldown=100.0,
    payload=replace(BALANCE.weapons["point"].payload, lines=1, width=2.0),
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


# --- El anillo se gasta donde pega ---


def test_anillo_quita_la_linea_que_mira_al_jugador() -> None:
    # Feliz: la primera línea que barre el anillo es la cara de enfrente, en el paso 25.
    enemigo = hexagono(100)
    assert jugar(TraceWeapon(RING, SPACING), [enemigo], 40) == [Hit(enemigo, FACE)]


def test_anillo_deja_un_hueco_sobre_el_enemigo() -> None:
    # El arco que cubre al hexágono desaparece: ningún punto del anillo queda sobre él.
    # El hexágono está en θ = 0, así que el hueco pasa por 0 y el anillo queda en un
    # solo tramo abierto.
    enemigo = hexagono(100)
    arma = TraceWeapon(RING, SPACING)
    jugar(arma, [enemigo], 40)
    [tramo] = arma.curves()
    medio_hueco = math.degrees(math.asin(24 / 100))
    assert all(abs(p.as_polar()[1]) >= medio_hueco for p in tramo)
    assert tramo[0] != tramo[-1]


def test_anillo_no_le_quita_la_linea_de_atras() -> None:
    # Con toda la vida del anillo, el hexágono golpeado no recibe otro golpe: el anillo
    # ya no está sobre él.
    enemigo = hexagono(100)
    assert jugar(TraceWeapon(RING, SPACING), [enemigo], 61) == [Hit(enemigo, FACE)]
    assert len(enemigo.edges) == 5


def test_otro_enemigo_en_otra_direccion_tambien_recibe() -> None:
    # El resto del anillo sigue: el mismo anillo le quita la cara a dos hexágonos.
    uno, otro = hexagono(100), hexagono(-100)
    golpes_ = jugar(TraceWeapon(RING, SPACING), [uno, otro], 40)
    assert sorted(golpes_, key=lambda h: h.enemy.position.x) == [
        Hit(otro, 4),
        Hit(uno, FACE),
    ]


def test_enemigo_detras_dentro_del_hueco_no_recibe() -> None:
    # Negativo: el hueco del primero, ±asin(24/100) ≈ ±13,9°, tapa entero al de atrás,
    # que ocupa ±asin(24/160) ≈ ±8,6°.
    uno, atras = hexagono(100), hexagono(160)
    assert jugar(TraceWeapon(RING, SPACING), [uno, atras], 61) == [Hit(uno, FACE)]
    assert len(atras.edges) == 6


def test_enemigo_sobre_el_jugador_se_lleva_el_anillo() -> None:
    # Borde: con el hexágono encima del jugador, `d ≤ r`, y el hueco es el anillo
    # entero. Recibe un golpe, y el anillo ya no se dibuja.
    enemigo = hexagono(0)
    arma = TraceWeapon(RING, SPACING)
    assert len(jugar(arma, [enemigo], 30)) == 1
    assert arma.curves() == []


def test_anillo_sigue_al_jugador() -> None:
    # El marco polar se centra en el jugador de ahora: si se mueve, el anillo va con él.
    arma = TraceWeapon(RING, SPACING)
    for _ in range(10):
        arma.update(Vector2(), [])
    centro = Vector2(50, 20)
    arma.update(centro, [])
    # Nació en el primer paso: tiene 10 pasos, y su radio es 200 · 10/60. Sin huecos,
    # es un solo tramo cerrado: repite su primer punto al final.
    [curva] = arma.curves()
    assert all(p.distance_to(centro) == pytest.approx(2000 / 60) for p in curva)
    assert curva[0] == curva[-1]


def test_anillo_revienta_en_su_alcance() -> None:
    # Borde: el anillo vive hasta que su avance llega a R, y entonces se quita.
    arma = TraceWeapon(RING, SPACING)
    # Nace en el primer paso. Con 59 pasos de edad va en 196,7; con 60 llega a R,
    # golpea por última vez con ese tramo y se quita.
    for _ in range(60):
        arma.update(Vector2(), [])
    assert arma.curves()
    arma.update(Vector2(), [])
    assert not arma.curves()


def test_lanza_un_anillo_cada_cooldown_aunque_no_haya_enemigos() -> None:
    # El anillo no apunta: sale cada `cooldown`, con o sin enemigos.
    seguido = replace(RING, cooldown=0.5)
    arma = TraceWeapon(seguido, SPACING)
    for _ in range(40):
        arma.update(Vector2(), [])
    # En los pasos 1 y 31.
    assert len(arma.curves()) == 2


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
    golpes_ = golpes(eventos)
    assert golpes_[0] == Hit(enemigo, FACE)
    # Al acercarse, el hexágono crece visto desde el jugador, y sus lados vuelven a
    # tocar el escudo fuera del hueco. Cada contacto pega y abre su propio hueco: el
    # escudo nunca queda encima sin dañar (ADR 0032).
    [anillo] = arma.traces
    assert len(anillo.gaps) == len(golpes_)


# --- Un paso del barrido ---


@pytest.mark.parametrize(("lines", "lineas"), [(1, [1]), (2, [1, 4])])
def test_un_contacto_quita_a_lo_mas_lines(lines: int, lineas: list[int]) -> None:
    # Borde: en el mismo paso, un punto cruza la línea 1 y otro, un poco después, la 4.
    # Cada punto quita a lo más una, como la bala; el contacto, a lo más `lines`, en el
    # orden en que las cruza.
    enemigo = hexagono(0)
    antes = [Vector2(-30, 0), Vector2(35, 0)]
    ahora = [Vector2(-15, 0), Vector2(15, 0)]
    golpes_ = strike(antes, ahora, [enemigo], lines)
    assert golpes_ == [Hit(enemigo, k) for k in lineas]


def test_varios_puntos_un_solo_golpe() -> None:
    # Tres puntos cruzan la línea 1 en el mismo paso: es un solo contacto.
    enemigo = hexagono(0)
    antes = [Vector2(-30, y) for y in (-4, 0, 4)]
    ahora = [Vector2(-15, y) for y in (-4, 0, 4)]
    assert strike(antes, ahora, [enemigo], 1) == [Hit(enemigo, 1)]


def test_curva_por_un_hueco_no_dana() -> None:
    # Negativo: un trazo corto y vertical cruza de izquierda a derecha un hexágono sin
    # sus líneas verticales. Pasa por los huecos, entre las líneas inclinadas, sin tocar
    # ninguna.
    enemigo = hexagono(0)
    enemigo.remove_edge(1)
    enemigo.remove_edge(4)
    alturas = [-6.0, -4.0, -2.0, 0.0, 2.0, 4.0, 6.0]
    golpes_: list[Hit] = []
    for x in range(-40, 40, 4):
        antes = [Vector2(x, y) for y in alturas]
        ahora = [Vector2(x + 4, y) for y in alturas]
        golpes_ += strike(antes, ahora, [enemigo], 1)
    assert golpes_ == []
    assert enemigo.edges == [0, 2, 3, 5]


# --- El filtro ---


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
    # punto que golpea al enemigo queda entre los cercanos. Con giro, movimiento y una
    # línea perdida, que corre el centro de masa (ADR 0027).
    spec = replace(HEXAGON, spin=giro, speed=1e9)
    enemigo = Enemy(spec, Vector2(3, -2))
    enemigo.velocity = velocidad * 60
    if perdida is not None:
        enemigo.remove_edge(perdida)
    enemigo.step(Vector2())
    antes = [a for a, _ in tramos]
    ahora = [b for _, b in tramos]
    largo = max(a.distance_to(b) for a, b in tramos)
    cercanos = PointGrid(ahora).near(enemigo.position, query_radius(enemigo, largo))
    for i in range(len(tramos)):
        if enemigo.hit_by(antes[i], ahora[i]) is not None:
            assert i in cercanos


def test_con_un_giro_de_un_radian_el_filtro_no_descarta() -> None:
    # Borde: si el enemigo gira un radián o más en un paso, la cota no existe, y el
    # filtro deja pasar a todos los puntos.
    enemigo = Enemy(replace(HEXAGON, spin=60.0), Vector2())
    enemigo.step(Vector2())
    assert query_radius(enemigo, 0.0) == math.inf


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
    # la distancia al cuadrado.
    todos = [
        i for i, p in enumerate(puntos) if p.distance_squared_to(centro) <= radio**2
    ]
    assert PointGrid(puntos).near(centro, radio) == todos
