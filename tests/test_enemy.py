"""Tests del enemigo: aparece lejos del jugador y lo persigue en línea recta."""

import math
import random

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pygame.math import Vector2

from circlebh.balance import BALANCE, EnemySpec
from circlebh.settings import load_settings
from circlebh.viewport import ASPECT_HEIGHT, ASPECT_WIDTH
from circlebh.world.clock import STEP
from circlebh.world.enemy import Enemy, spawn_position
from circlebh.world.polygon import polygon_edge

SPEC = EnemySpec(
    sides=6, radius=24.0, speed=120.0, friction=0.0, charge_per_line=0.0, patterns=()
)

coordenadas = st.floats(min_value=-1e4, max_value=1e4)
puntos = st.builds(Vector2, coordenadas, coordenadas)


# --- Perseguir ---


def test_enemigo_se_acerca_cada_paso() -> None:
    enemy = Enemy(SPEC, Vector2(300, 400))
    target = Vector2(0, 0)
    distancias = []
    for _ in range(10):
        enemy.step(target)
        distancias.append(enemy.position.distance_to(target))
    assert distancias == sorted(distancias, reverse=True)
    assert distancias[0] == pytest.approx(500 - SPEC.speed * STEP)


@given(inicio=puntos, target=puntos)
def test_avanza_speed_por_paso_sin_pasarse(inicio: Vector2, target: Vector2) -> None:
    enemy = Enemy(SPEC, inicio)
    antes = inicio.distance_to(target)
    enemy.step(target)
    despues = enemy.position.distance_to(target)
    assert despues == pytest.approx(max(0.0, antes - SPEC.speed * STEP), abs=1e-6)


def test_objetivo_a_menos_de_un_paso_llega_justo() -> None:
    target = Vector2(1, 0)
    enemy = Enemy(SPEC, Vector2(0, 0))
    enemy.step(target)
    assert enemy.position == target


def test_enemigo_encima_del_jugador_no_se_vuelve_inestable() -> None:
    target = Vector2(5, -3)
    enemy = Enemy(SPEC, Vector2(target))
    for _ in range(60):
        enemy.step(target)
        assert enemy.position == target


def test_step_no_modifica_el_objetivo() -> None:
    target = Vector2(100, 0)
    Enemy(SPEC, Vector2(0, 0)).step(target)
    assert target == Vector2(100, 0)


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
    for k in range(SPEC.sides):
        enemy.remove_edge(k)
    assert enemy.alive is False


def test_lineas_en_coordenadas_del_plano() -> None:
    enemy = Enemy(SPEC, Vector2(100, -50))
    enemy.remove_edge(0)
    lineas = enemy.lines()
    assert len(lineas) == 5
    # La arista 4, la vertical derecha, queda a la derecha del centro.
    a, b = polygon_edge(SPEC.radius, SPEC.sides, 4)
    assert (a + enemy.position, b + enemy.position) in lineas


def test_previous_es_la_posicion_antes_del_paso() -> None:
    enemy = Enemy(SPEC, Vector2(300, 0))
    assert enemy.previous == enemy.position
    enemy.step(Vector2(0, 0))
    assert enemy.previous == Vector2(300, 0)
    assert enemy.position.x == pytest.approx(300 - SPEC.speed * STEP)


# --- Aparecer ---


@given(centro=puntos, seed=st.integers(min_value=0))
def test_aparece_a_la_distancia_pedida(centro: Vector2, seed: int) -> None:
    posicion = spawn_position(centro, 800.0, random.Random(seed))
    assert posicion.distance_to(centro) == pytest.approx(800.0)


@given(seed=st.integers(min_value=0))
def test_misma_semilla_mismo_lugar(seed: int) -> None:
    centro = Vector2(10, -20)
    a = spawn_position(centro, 800.0, random.Random(seed))
    b = spawn_position(centro, 800.0, random.Random(seed))
    assert a == b


def test_semillas_distintas_dan_angulos_distintos() -> None:
    # Negativo: el ángulo sale del azar, no es fijo. 20 semillas en el mismo punto
    # tendrían una probabilidad nula con un ángulo continuo.
    posiciones = {
        tuple(spawn_position(Vector2(), 800.0, random.Random(seed)))
        for seed in range(20)
    }
    assert len(posiciones) == 20


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
