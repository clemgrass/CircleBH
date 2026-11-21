"""Tests del arma punto: una bala que se dispara sola al centro del enemigo más cercano."""

import pytest
from pygame.math import Vector2

from circlebh.balance import EnemySpec, PointWeaponSpec
from circlebh.world.clock import STEP
from circlebh.world.enemy import Enemy
from circlebh.world.weapons import Bullet, PointWeapon, nearest

# 0,5 s = 30 pasos entre disparos; 600 / 60 = 10 unidades por paso; 700 / 10 = 70 pasos
# de vida.
SPEC = PointWeaponSpec(cooldown=0.5, speed=600.0, range=700.0)
COOLDOWN = 30
VIDA = 70
# Sin patrones ni carga: aquí solo importa dónde está.
HEXAGON = EnemySpec(
    sides=6,
    radius=24.0,
    speed=120.0,
    friction=0.0,
    spin=0.0,
    charge_per_line=0.0,
    patterns=(),
    threat=1.0,
)


def enemigo(x: float, y: float) -> Enemy:
    return Enemy(HEXAGON, Vector2(x, y))


# --- La bala ---


@pytest.mark.parametrize("pasos", [0, 1, 30])
def test_bala_avanza_en_linea_recta(pasos: int) -> None:
    origen, velocidad = Vector2(1, 2), Vector2(0, -SPEC.speed)
    bullet = Bullet(origen, velocidad, SPEC)
    for _ in range(pasos):
        bullet.step()
    # p(t) = p₀ + v·t
    assert tuple(bullet.position) == pytest.approx(
        tuple(origen + velocidad * pasos * STEP)
    )
    assert bullet.position.distance_to(origen) == pytest.approx(SPEC.speed / 60 * pasos)


def test_previous_es_la_posicion_un_paso_antes() -> None:
    bullet = Bullet(Vector2(0, 0), Vector2(SPEC.speed, 0), SPEC)
    assert bullet.previous == bullet.position
    bullet.step()
    antes = Vector2(bullet.position)
    bullet.step()
    assert tuple(bullet.previous) == pytest.approx(tuple(antes))


def test_bala_vence_al_recorrer_range() -> None:
    bullet = Bullet(Vector2(0, 0), Vector2(SPEC.speed, 0), SPEC)
    for _ in range(VIDA - 1):
        bullet.step()
    assert bullet.expired is False
    bullet.step()
    assert bullet.expired is True


# --- A quién apunta ---


def test_nearest_sin_enemigos_es_none() -> None:
    assert nearest(Vector2(0, 0), []) is None


def test_dispara_al_centro_del_mas_cercano() -> None:
    weapon = PointWeapon(SPEC)
    weapon.update(Vector2(0, 0), [enemigo(500, 0), enemigo(0, -100)])
    [bullet] = weapon.bullets
    assert bullet.velocity == Vector2(0, -SPEC.speed)


def test_empate_gana_el_primero() -> None:
    weapon = PointWeapon(SPEC)
    weapon.update(Vector2(0, 0), [enemigo(100, 0), enemigo(-100, 0)])
    [bullet] = weapon.bullets
    assert bullet.velocity == Vector2(SPEC.speed, 0)


def test_centro_sobre_el_jugador_no_dispara() -> None:
    # Negativo: la dirección es nula y no se puede normalizar.
    weapon = PointWeapon(SPEC)
    weapon.update(Vector2(5, 5), [enemigo(5, 5)])
    assert weapon.bullets == []


def test_centro_casi_sobre_el_jugador_no_falla() -> None:
    # Negativo: a 1e-200, la dirección no es nula, pero su largo al cuadrado se redondea
    # a 0 y `normalize` lanzaría ValueError.
    weapon = PointWeapon(SPEC)
    weapon.update(Vector2(0, 0), [enemigo(1e-200, 0)])
    assert weapon.bullets == []


def test_un_enemigo_a_una_millonesima_si_recibe_disparo() -> None:
    # Borde: la igualdad de Vector2 tiene tolerancia 1e-6; a 1e-7 el enemigo no está
    # "encima" y se le dispara.
    weapon = PointWeapon(SPEC)
    weapon.update(Vector2(0, 0), [enemigo(1e-7, 0)])
    [bullet] = weapon.bullets
    assert bullet.velocity == Vector2(SPEC.speed, 0)


def test_ignora_al_enemigo_sobre_el_jugador_y_apunta_al_siguiente() -> None:
    # Un enemigo abierto puede quedar estacionado sobre el jugador quieto. No debe
    # callar el arma contra los demás.
    weapon = PointWeapon(SPEC)
    weapon.update(Vector2(0, 0), [enemigo(0, 0), enemigo(0, 200)])
    [bullet] = weapon.bullets
    assert bullet.velocity == Vector2(0, SPEC.speed)


def test_no_apunta_a_un_enemigo_muerto() -> None:
    # Un enemigo que perdió su última línea en este mismo paso sigue en la lista hasta
    # que `World` lo quita.
    muerto = enemigo(50, 0)
    for k in range(HEXAGON.sides):
        muerto.remove_edge(k)
    weapon = PointWeapon(SPEC)
    weapon.update(Vector2(0, 0), [muerto, enemigo(0, -300)])
    [bullet] = weapon.bullets
    assert bullet.velocity == Vector2(0, -SPEC.speed)


# --- Cuándo dispara ---


def test_dispara_uno_cada_cooldown() -> None:
    weapon = PointWeapon(SPEC)
    lejos = [enemigo(10_000, 0)]
    disparos = []
    for paso in range(100):
        weapon.update(Vector2(0, 0), lejos)
        if any(bullet.age == 0 for bullet in weapon.bullets):
            disparos.append(paso)
    assert disparos == [0, COOLDOWN, 2 * COOLDOWN, 3 * COOLDOWN]


def test_las_balas_vencidas_se_quitan() -> None:
    weapon = PointWeapon(SPEC)
    lejos = [enemigo(10_000, 0)]
    for _ in range(VIDA + 1):
        weapon.update(Vector2(0, 0), lejos)
    # Nacieron en los pasos 0, 30 y 60; la del paso 0 ya recorrió `range`.
    assert len(weapon.bullets) == 2


def test_sin_enemigos_no_dispara_y_queda_lista() -> None:
    weapon = PointWeapon(SPEC)
    for _ in range(COOLDOWN * 3):
        weapon.update(Vector2(0, 0), [])
    assert weapon.bullets == []
    weapon.update(Vector2(0, 0), [enemigo(100, 0)])
    assert len(weapon.bullets) == 1


def test_la_bala_no_sigue_al_jugador() -> None:
    weapon = PointWeapon(SPEC)
    objetivo = [enemigo(10_000, 0)]
    weapon.update(Vector2(0, 0), objetivo)
    for _ in range(10):
        weapon.update(Vector2(0, 50), objetivo)
    bullet = weapon.bullets[0]
    assert bullet.position.y == 0
    assert bullet.position.x == pytest.approx(SPEC.speed * 10 * STEP)
