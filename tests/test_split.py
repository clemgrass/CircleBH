"""Tests del divisor: al morir se parte en fragmentos (spec de la 0.2.0, "El divisor
(#63)", decisión 71).

Un heptágono se triangula en abanico en 5 triángulos, y en el centroide de cada uno nace
un fragmento: un triángulo chico que embiste. Nacen dentro de su figura, sin tocarse, y
ninguno encima del jugador.
"""

import math
import random
from dataclasses import replace
from itertools import combinations

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pygame.math import Vector2

from circlebh.balance import BALANCE, Balance, EnemySpec, StarPolygonShape
from circlebh.world.clock import STEP
from circlebh.world.collisions import circles_touch
from circlebh.world.enemy import Enemy
from circlebh.world.events import Death
from circlebh.world.figures import triangulation_centroids
from circlebh.world.game import World
from circlebh.world.polygon import vertex
from circlebh.world.rigid import to_world
from circlebh.world.split import fragments

LEJOS = Vector2(1e6, 0)
"""Un jugador que no toca a ningún fragmento."""


def divisor() -> EnemySpec:
    return BALANCE.enemies["divider"]


def fragmento() -> EnemySpec:
    return BALANCE.enemies["shard"]


def centroides() -> list[Vector2]:
    shape = divisor().shape
    assert isinstance(shape, StarPolygonShape)
    return triangulation_centroids(shape, divisor().radius)


def con_una_linea_de_frente(spec: EnemySpec, posicion: Vector2) -> Enemy:
    """Un enemigo en `posicion` al que solo le queda la línea más cercana al origen,
    donde está el jugador: la primera bala del arma la golpea."""
    enemy = Enemy(spec, posicion)
    de_frente = min(
        range(len(enemy.edges)),
        key=lambda k: ((enemy.lines()[k][0] + enemy.lines()[k][1]) / 2).length(),
    )
    for k in [k for k in list(enemy.edges) if k != de_frente]:
        enemy.remove_edge(k)
    return enemy


def con_enemigo(balance: Balance, name: str, **campos: object) -> Balance:
    """El balance con los `campos` de `name` cambiados."""
    spec = replace(balance.enemies[name], **campos)  # type: ignore[arg-type]
    return replace(balance, enemies={**balance.enemies, name: spec})


def matar(world: World, enemy: Enemy) -> list[Enemy]:
    """Corre el mundo hasta que muere `enemy`, a lo más 5 s, y devuelve los enemigos
    que quedan en ese paso."""
    for _ in range(round(5 / STEP)):
        world.update(Vector2())
        if any(isinstance(e, Death) and e.enemy is enemy for e in world.events):
            return world.enemies
    pytest.fail("el enemigo no murió en 5 s")


# --- La geometría ---


def test_fragmentos_caben_en_el_divisor() -> None:
    # Sin tocarse entre ellos (núcleo duro) y con su envolvente dentro del heptágono.
    r = fragmento().radius
    for a, b in combinations(centroides(), 2):
        assert a.distance_to(b) >= BALANCE.charges.core_reach * 2 * r
    n, radio = 7, divisor().radius
    for c in centroides():
        for k in range(n):
            a, b = vertex(radio, n, k), vertex(radio, n, k + 1)
            assert abs((b - a).cross(c - a)) / (b - a).length() >= r


# --- El reparto ---


@given(
    x=st.floats(-500, 500),
    y=st.floats(-500, 500),
    angulo=st.floats(-math.tau, math.tau),
    vx=st.floats(-120, 120),
    vy=st.floats(-120, 120),
)
def test_fragmentos_en_la_pose_del_padre(
    x: float, y: float, angulo: float, vx: float, vy: float
) -> None:
    padre = Enemy(divisor(), Vector2(x, y))
    padre.angle = angulo
    padre.velocity = Vector2(vx, vy)
    hijos = fragments(padre, fragmento(), LEJOS, BALANCE.player.radius)
    assert len(hijos) == 5
    for hijo, c in zip(hijos, centroides(), strict=True):
        assert hijo.spec is fragmento()
        assert hijo.position.distance_to(to_world(c, padre.position, angulo)) < 1e-6
        assert hijo.angle == angulo
        assert hijo.velocity == padre.velocity


def test_hijo_que_tocaria_al_jugador_no_nace() -> None:
    # Foco 3: el jugador se metió por un hueco del divisor herido, justo encima del
    # centroide 2. Ese fragmento no nace, y tampoco los de los centroides 1 y 3: quedan
    # a 18,8, y el envolvente del fragmento más el jugador suman 7 + 12 = 19. Los de las
    # puntas sí nacen.
    padre = Enemy(divisor(), Vector2(40, -10))
    padre.angle = 0.3
    jugador = to_world(centroides()[2], padre.position, padre.angle)
    radio = BALANCE.player.radius
    hijos = fragments(padre, fragmento(), jugador, radio)
    puntas = [to_world(centroides()[k], padre.position, padre.angle) for k in (0, 4)]
    assert [hijo.position for hijo in hijos] == puntas
    for hijo in hijos:
        assert not circles_touch(hijo.position, hijo.radius, jugador, radio)


# --- En el mundo ---


def test_heptagono_suelta_cinco() -> None:
    world = World(BALANCE, random.Random(0), lethal=False)
    padre = con_una_linea_de_frente(divisor(), Vector2(150, 0))
    world.enemies = [padre]
    quedan = matar(world, padre)
    hijos = [e for e in quedan if e.spec is fragmento()]
    assert len(hijos) == 5
    for hijo in hijos:
        assert hijo.position.distance_to(padre.position) < divisor().radius


def test_sin_split_into_no_suelta_nada() -> None:
    world = World(BALANCE, random.Random(0), lethal=False)
    hexagono = con_una_linea_de_frente(BALANCE.enemies["hexagon"], Vector2(150, 0))
    world.enemies = [hexagono]
    quedan = matar(world, hexagono)
    assert not any(e.spec is fragmento() for e in quedan)


# --- El chequeo ---


def test_split_into_desconocido_se_rechaza() -> None:
    balance = con_enemigo(BALANCE, "divider", split_into="nada")
    with pytest.raises(ValueError, match=r"enemies\.divider\.split_into"):
        World(balance, random.Random(0))


@pytest.mark.parametrize(
    "cadena",
    [
        {"hexagon": "square", "square": "hexagon"},
        # Un triángulo se parte en un solo triángulo: tampoco termina.
        {"shard": "shard"},
    ],
)
def test_ciclo_se_rechaza(cadena: dict[str, str]) -> None:
    balance = BALANCE
    for name, into in cadena.items():
        balance = con_enemigo(balance, name, split_into=into)
    with pytest.raises(ValueError, match=r"split_into.*ciclo"):
        World(balance, random.Random(0))


def test_padre_no_regular_se_rechaza() -> None:
    # El abanico de la estrella no triangula su figura: sus diagonales se cruzan.
    balance = con_enemigo(BALANCE, "star", split_into="shard")
    with pytest.raises(ValueError, match=r"enemies\.star\.split_into"):
        World(balance, random.Random(0))
