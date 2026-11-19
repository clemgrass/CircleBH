"""Tests del arma círculo: un anillo que nace en el jugador, crece y revienta."""

from dataclasses import replace

import pytest
from pygame.math import Vector2

from circlebh.balance import CircleWeaponSpec
from circlebh.world.clock import STEP
from circlebh.world.weapons import CircleWeapon, Ring

# 260 / 300 = 52 pasos de vida justos, y 1,5 s = 90 pasos entre anillos.
SPEC = CircleWeaponSpec(
    cooldown=1.5, growth_speed=300.0, max_radius=260.0, thickness=6.0
)
VIDA = 52
COOLDOWN = 90


# --- El anillo ---


@pytest.mark.parametrize("pasos", [0, 1, 30])
def test_radio_crece_con_el_tiempo(pasos: int) -> None:
    ring = Ring(Vector2(0, 0), SPEC)
    for _ in range(pasos):
        ring.step()
    assert ring.radius == pytest.approx(SPEC.growth_speed * pasos * STEP)


def test_revienta_al_llegar_al_maximo() -> None:
    ring = Ring(Vector2(0, 0), SPEC)
    for _ in range(VIDA - 1):
        ring.step()
    assert not ring.expired
    ring.step()
    assert ring.expired


# --- El arma ---


def test_el_primer_anillo_nace_en_el_primer_paso() -> None:
    weapon = CircleWeapon(SPEC)
    assert weapon.rings == []
    weapon.update(Vector2(3, 4))
    [ring] = weapon.rings
    assert ring.center == Vector2(3, 4)
    assert ring.radius == 0


def test_el_anillo_reventado_desaparece() -> None:
    weapon = CircleWeapon(SPEC)
    weapon.update(Vector2(0, 0))
    for _ in range(VIDA - 1):
        weapon.update(Vector2(0, 0))
    assert len(weapon.rings) == 1
    weapon.update(Vector2(0, 0))
    assert weapon.rings == []


def test_nace_uno_cada_cooldown() -> None:
    weapon = CircleWeapon(SPEC)
    centros: set[float] = set()
    # El origen cambia en cada paso: el centro de cada anillo dice en qué paso nació.
    for paso in range(1, 3 * COOLDOWN + 1):
        weapon.update(Vector2(paso, 0))
        centros |= {ring.center.x for ring in weapon.rings}
    assert centros == {1, 1 + COOLDOWN, 1 + 2 * COOLDOWN}


def test_el_anillo_no_sigue_al_jugador() -> None:
    weapon = CircleWeapon(SPEC)
    # El mismo objeto, movido en el lugar: así se mueve `Player.position` (`+=`).
    jugador = Vector2(0, 0)
    weapon.update(jugador)
    for _ in range(10):
        jugador += Vector2(5, -2)
        weapon.update(jugador)
    [ring] = weapon.rings
    assert ring.center == Vector2(0, 0)


def test_anillo_lanzado_conserva_su_spec() -> None:
    weapon = CircleWeapon(SPEC)
    weapon.update(Vector2(0, 0))
    # Una mejora cambia el spec del arma, no los anillos que ya van en el aire.
    weapon.spec = replace(SPEC, growth_speed=2 * SPEC.growth_speed)
    weapon.update(Vector2(0, 0))
    [ring] = weapon.rings
    assert ring.radius == pytest.approx(SPEC.growth_speed * STEP)
