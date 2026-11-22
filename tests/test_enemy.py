"""Tests del enemigo: aparece lejos del jugador y se mueve con inercia y roce."""

import math
from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pygame.math import Vector2

from circlebh.balance import BALANCE, EnemySpec, StarPolygonShape
from circlebh.settings import load_settings
from circlebh.viewport import ASPECT_HEIGHT, ASPECT_WIDTH
from circlebh.world.clock import STEP
from circlebh.world.enemy import Enemy
from circlebh.world.patterns import Context
from circlebh.world.polygon import polygon_edge

SPEC = EnemySpec(
    shape=StarPolygonShape(vertices=6, steps=(1,)),
    radius=24.0,
    speed=120.0,
    friction=0.0,
    spin=0.0,
    anchored=False,
    charge_per_line=0.0,
    patterns=(),
    threat=1.0,
    actions=(),
)

coordenadas = st.floats(min_value=-1e4, max_value=1e4)
puntos = st.builds(Vector2, coordenadas, coordenadas)


# --- Inercia y roce (ADR 0021) ---


def contexto() -> Context:
    """Un contexto sin vecinos y con el jugador sin carga."""
    return Context(
        player_position=Vector2(),
        player_charge=0.0,
        charges=BALANCE.charges,
        neighbors=[],
    )


def test_con_seek_se_acerca_al_jugador() -> None:
    enemy = Enemy(BALANCE.enemies["hexagon"], Vector2(300, 400))
    distancias = []
    for _ in range(10):
        enemy.step(enemy.acceleration(contexto()))
        distancias.append(enemy.position.length())
    assert distancias == sorted(distancias, reverse=True)


def test_sin_fuerzas_el_roce_frena() -> None:
    con_roce = replace(SPEC, friction=2.0)
    enemy = Enemy(con_roce, Vector2())
    enemy.velocity = Vector2(100, 0)
    rapideces = []
    for _ in range(5):
        enemy.step(enemy.acceleration(contexto()))
        rapideces.append(enemy.velocity.length())
    assert rapideces == sorted(rapideces, reverse=True)
    assert rapideces[0] == pytest.approx(100 * (1 - 2.0 * STEP))


@given(x=coordenadas, y=coordenadas)
def test_nunca_pasa_speed(x: float, y: float) -> None:
    enemy = Enemy(SPEC, Vector2())
    for _ in range(3):
        enemy.step(Vector2(x, y) * 1000)
    assert enemy.velocity.length() <= SPEC.speed + 1e-9


def test_en_reposo_sin_fuerzas_no_se_mueve() -> None:
    enemy = Enemy(SPEC, Vector2(5, -3))
    for _ in range(60):
        enemy.step(enemy.acceleration(contexto()))
    assert enemy.position == Vector2(5, -3)


def test_avanza_con_euler_semi_implicito() -> None:
    # Primero la velocidad, después la posición con la velocidad nueva.
    enemy = Enemy(SPEC, Vector2())
    enemy.step(Vector2(600, 0))
    assert enemy.velocity.x == pytest.approx(600 * STEP)
    assert enemy.position.x == pytest.approx(600 * STEP * STEP)


def test_step_no_modifica_la_aceleracion() -> None:
    aceleracion = Vector2(100, 0)
    Enemy(SPEC, Vector2()).step(aceleracion)
    assert aceleracion == Vector2(100, 0)


def test_carga_y_masa_bajan_al_perder_lineas() -> None:
    hexagon = BALANCE.enemies["hexagon"]
    enemy = Enemy(hexagon, Vector2())
    assert enemy.mass == 6
    enemy.remove_edge(0)
    assert enemy.mass == 5
    assert enemy.charge == pytest.approx(5 * hexagon.charge_per_line)


def test_cada_enemigo_tiene_sus_propios_patrones() -> None:
    hexagon = BALANCE.enemies["hexagon"]
    a, b = Enemy(hexagon, Vector2()), Enemy(hexagon, Vector2())
    assert len(a.patterns) == len(hexagon.patterns)
    assert all(pa is not pb for pa, pb in zip(a.patterns, b.patterns, strict=True))


# --- Líneas (ADR 0020) ---


def test_parte_con_todas_sus_lineas() -> None:
    enemy = Enemy(SPEC, Vector2(0, 0))
    assert enemy.edges == [0, 1, 2, 3, 4, 5]
    assert enemy.alive is True


def test_la_envolvente_no_se_achica() -> None:
    # Las líneas que quedan no se mueven: el círculo que las contiene es el mismo.
    enemy = Enemy(SPEC, Vector2(0, 0))
    enemy.remove_edge(2)
    enemy.remove_edge(5)
    assert enemy.radius == SPEC.radius
    assert enemy.edges == [0, 1, 3, 4]


def test_sin_lineas_no_esta_vivo() -> None:
    enemy = Enemy(SPEC, Vector2(0, 0))
    for k in range(SPEC.shape.line_count):
        enemy.remove_edge(k)
    assert enemy.alive is False


def test_lineas_en_coordenadas_del_plano() -> None:
    enemy = Enemy(SPEC, Vector2(100, -50))
    enemy.remove_edge(0)
    lineas = enemy.lines()
    assert len(lineas) == 5
    # La arista 4, la vertical derecha, queda a la derecha del centro.
    a, b = polygon_edge(SPEC.radius, SPEC.shape.vertices, 4)
    assert (a + enemy.position, b + enemy.position) in lineas


def test_previous_es_la_posicion_antes_del_paso() -> None:
    enemy = Enemy(SPEC, Vector2(300, 0))
    assert enemy.previous == enemy.position
    enemy.velocity = Vector2(-SPEC.speed, 0)
    enemy.step(Vector2())
    assert enemy.previous == Vector2(300, 0)
    assert enemy.position.x == pytest.approx(300 - SPEC.speed * STEP)


# --- Aparecer (dónde, en `test_spawning.py`) ---


def test_balance_aparece_fuera_de_la_vista() -> None:
    # Coherencia entre balance y configuración: el enemigo entero queda fuera de la
    # vista al aparecer, en cualquier ángulo. Lo más lejano que se ve es una esquina.
    camera = load_settings().camera
    alto = camera.fov
    ancho = alto * ASPECT_WIDTH / ASPECT_HEIGHT
    esquina = math.hypot(ancho / 2, alto / 2) + Vector2(camera.offset).length()
    hexagon = BALANCE.enemies["hexagon"]
    assert BALANCE.spawning.distance - hexagon.radius > esquina


@pytest.mark.parametrize("nombre", sorted(BALANCE.enemies))
def test_jugador_no_atraviesa_una_linea_en_un_paso(nombre: str) -> None:
    # Coherencia del balance: el contacto se revisa una vez por paso. Si el jugador y el
    # enemigo se acercan más que el diámetro del jugador en un paso, una línea podría
    # pasarle por encima sin que ningún paso la vea tocándolo.
    player = BALANCE.player
    enemy = BALANCE.enemies[nombre]
    assert (player.speed + enemy.speed) * STEP < 2 * player.radius
