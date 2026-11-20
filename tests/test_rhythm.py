"""Tests del ritmo de la música: el ritmo euclidiano y la grilla (ADR 0022)."""

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from circlebh.audio.rhythm import RATE, SIXTEENTHS, Grid, euclid


@st.composite
def k_y_n(draw: st.DrawFn) -> tuple[int, int]:
    n = draw(st.integers(1, 32))
    return draw(st.integers(1, n)), n


# --- euclid ---


@given(k_y_n())
def test_euclid_reparte_k_golpes_lo_mas_parejo_posible(kn: tuple[int, int]) -> None:
    k, n = kn
    pattern = euclid(k, n)
    assert len(pattern) == n
    assert sum(pattern) == k
    # Los intervalos entre golpes, contando la vuelta, difieren a lo más en 1.
    onsets = [i for i, hit in enumerate(pattern) if hit]
    gaps = [(onsets[(j + 1) % k] - onsets[j]) % n or n for j in range(k)]
    assert max(gaps) - min(gaps) <= 1


@pytest.mark.parametrize("n", [1, 6, 16])
def test_euclid_todos_golpes_y_uno_solo(n: int) -> None:
    assert euclid(n, n) == [True] * n
    assert euclid(1, n) == [True] + [False] * (n - 1)


def test_euclid_tresillo_de_toussaint() -> None:
    # E(3, 8) es el tresillo: x . . x . . x .
    assert euclid(3, 8) == [True, False, False, True, False, False, True, False]


@pytest.mark.parametrize(("k", "n"), [(0, 16), (17, 16), (-1, 4)])
def test_euclid_fuera_de_rango_da_error(k: int, n: int) -> None:
    with pytest.raises(ValueError, match="0 < k ≤ n"):
        euclid(k, n)


# --- La grilla ---


@pytest.mark.parametrize("bpm", range(120, 127))
def test_cada_semicorchea_mide_su_redondeo(bpm: int) -> None:
    grid = Grid(bpm)
    assert grid.samples == pytest.approx(RATE * 60 / bpm / 4)
    largos = {grid.start(g + 1) - grid.start(g) for g in range(500)}
    assert largos <= {math.floor(grid.samples), math.ceil(grid.samples)}


def test_swing_solo_atrasa_las_impares() -> None:
    grid = Grid(124)
    assert [grid.swing(g) for g in range(4)] == [0, 640, 0, 640]


def test_la_grilla_no_acumula_error() -> None:
    grid = Grid(124)
    for m in (1, 100, 10_000):
        assert grid.start(SIXTEENTHS * m) == round(SIXTEENTHS * m * grid.samples)


def test_un_compas_dura_cuatro_pulsos() -> None:
    assert Grid(120).bar_seconds == pytest.approx(2.0)
