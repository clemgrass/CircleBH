"""Tests de los sonidos de la música: la batería y el timbre de un polígono (ADR 0022).

El timbre de un polígono es la `x` de un punto que recorre sus aristas. Su serie de
Fourier es la del contorno: el hexágono cerrado solo tiene armónicos en k = 1 ± 6m, con
magnitud 1/k², y el cuadrado da una onda triangular.
"""

import cmath
import math
from collections.abc import Sequence

import pytest

from circlebh.audio import sounds
from circlebh.balance import StarPolygonShape


def regular(n: int) -> StarPolygonShape:
    """El polígono regular de `n` lados, `{n/1}`."""
    return StarPolygonShape(vertices=n, steps=(1,))


def armonicos(ciclo: Sequence[float], hasta: int) -> list[float]:
    """Magnitud de los armónicos 1..hasta (DFT directa), relativa al primero."""
    n = len(ciclo)
    mags = [
        abs(sum(v * cmath.exp(-2j * math.pi * k * i / n) for i, v in enumerate(ciclo)))
        for k in range(1, hasta + 1)
    ]
    return [m / mags[0] for m in mags]


def test_hexagono_cerrado_tiene_armonicos_1_5_7_11_13() -> None:
    h = armonicos(sounds.shape_table(regular(6), (0, 1, 2, 3, 4, 5)), 13)
    for k in (2, 3, 4, 6, 8, 9, 10, 12):
        assert h[k - 1] < 1e-3
    for k in (5, 7, 11, 13):
        assert h[k - 1] == pytest.approx(1 / k**2, rel=0.05)


def test_cuadrado_es_onda_triangular() -> None:
    h = armonicos(sounds.shape_table(regular(4), (0, 1, 2, 3)), 9)
    for k in (3, 5, 7, 9):
        assert h[k - 1] == pytest.approx(1 / k**2, rel=0.05)
    for k in (2, 4, 6, 8):
        assert h[k - 1] < 1e-3


def test_una_sola_arista_es_diente_de_sierra() -> None:
    # El punto recorre la arista y salta al inicio: los armónicos pares aparecen.
    h = armonicos(sounds.shape_table(regular(6), (0,)), 3)
    assert h[1] > 0.1
    assert h[2] > 0.05


def test_tabla_sin_aristas_da_error() -> None:
    with pytest.raises(ValueError, match="sin líneas"):
        sounds.shape_table(regular(6), ())


def todos_los_sonidos() -> list[Sequence[float]]:
    return [
        sounds.kick(),
        sounds.closed_hat(),
        sounds.open_hat(),
        sounds.clap(),
        sounds.impact(),
        sounds.rim(),
        sounds.riser(1.9),
        sounds.stab((0, 3, 7, 10, 14)),
        sounds.poly_note(regular(6), (0, 2, 3), 220.0),
        # La estrella herida: solo le quedan sus diagonales.
        sounds.poly_note(
            StarPolygonShape(vertices=5, steps=(1, 2)), (5, 6, 7, 8, 9), 220.0
        ),
        sounds.blip(440.0),
    ]


def test_sonidos_finitos_y_acotados() -> None:
    for sonido in todos_los_sonidos():
        assert len(sonido) > 0
        assert all(math.isfinite(x) and abs(x) <= 1.5 for x in sonido)


def test_mismo_sonido_dos_veces_es_igual_aunque_cambie_el_orden() -> None:
    # Sin la caché: cada sonido con ruido usa su propia Random, así que el orden en que
    # se generan no cambia el resultado.
    antes = list(sounds.clap.__wrapped__())
    sounds.kick.__wrapped__()
    sounds.closed_hat.__wrapped__()
    assert list(sounds.clap.__wrapped__()) == antes
