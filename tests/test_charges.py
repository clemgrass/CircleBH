"""Tests de la ley de cargas: Coulomb con corte y núcleo duro entre enemigos, y la
atracción del jugador (ADR 0021)."""

import math

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st
from pygame.math import Vector2

from circlebh.balance import BALANCE
from circlebh.world.charges import pair_force, player_force

SPEC = BALANCE.charges
CONTACTO = 48.0
"""La suma de los radios envolventes de dos hexágonos. El núcleo empieza en 1,2 × 48."""

coordenada = st.floats(min_value=-200, max_value=200)
carga = st.floats(min_value=-12, max_value=12)


@given(
    x=coordenada,
    y=coordenada,
    qi=carga,
    qj=carga,
    contacto=st.floats(min_value=1, max_value=60),
)
def test_tercera_ley(x: float, y: float, qi: float, qj: float, contacto: float) -> None:
    # La fuerza de j sobre i es la contraria de la de i sobre j: con masas mᵢ y mⱼ,
    # mᵢ·aᵢ + mⱼ·aⱼ = 0, y la cantidad de movimiento se conserva.
    offset = Vector2(x, y)
    assume(offset.length() > 1e-3)
    sobre_i = pair_force(offset, qi, qj, contacto, SPEC)
    sobre_j = pair_force(-offset, qj, qi, contacto, SPEC)
    assert sobre_i.x == pytest.approx(-sobre_j.x, rel=1e-12, abs=1e-9)
    assert sobre_i.y == pytest.approx(-sobre_j.y, rel=1e-12, abs=1e-9)


def test_cargas_iguales_se_repelen() -> None:
    assert pair_force(Vector2(80, 0), 6, 6, CONTACTO, SPEC).x > 0


def test_cargas_contrarias_se_atraen_de_lejos() -> None:
    assert pair_force(Vector2(100, 0), 6, -6, CONTACTO, SPEC).x < 0


def test_nucleo_repele_aunque_se_atraigan() -> None:
    # 50 está dentro de d₀ = 57,6: el núcleo gana a la atracción.
    assert pair_force(Vector2(50, 0), 6, -6, CONTACTO, SPEC).x > 0


def test_cero_en_el_corte_y_mas_alla() -> None:
    assert pair_force(Vector2(SPEC.cutoff, 0), 6, 6, CONTACTO, SPEC) == Vector2()
    assert pair_force(Vector2(SPEC.cutoff + 1, 0), 6, 6, CONTACTO, SPEC) == Vector2()


def test_casi_en_el_corte_es_casi_cero() -> None:
    # Con la fuerza del corte restada, no salta de golpe a cero en el borde. La pendiente
    # ahí es ≈ 2·k·36 / 150³ ≈ 3,6 por unidad: a 1e-6 del corte vale unos 3,6e-6. Sin
    # restar, valdría k·36 / 150² ≈ 274.
    cerca = pair_force(Vector2(SPEC.cutoff - 1e-6, 0), 6, 6, CONTACTO, SPEC)
    assert cerca.x == pytest.approx(0, abs=1e-4)


def test_mismo_punto_no_divide_por_cero() -> None:
    assert pair_force(Vector2(), 6, 6, CONTACTO, SPEC) == Vector2()


def test_el_jugador_atrae() -> None:
    assert player_force(Vector2(100, 0), 6, -14, SPEC).x < 0


def test_el_jugador_atrae_sin_corte() -> None:
    assert player_force(Vector2(800, 0), 6, -14, SPEC).x < 0


def test_jugador_encima_es_finito() -> None:
    assert player_force(Vector2(), 6, -14, SPEC) == Vector2()
    casi = player_force(Vector2(1e-9, 0), 6, -14, SPEC)
    assert math.isfinite(casi.x) and math.isfinite(casi.y)
