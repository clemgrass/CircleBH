"""Tests de la intensidad de la partida y de las capas por frases (ADR 0022)."""

from itertools import pairwise

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pygame.math import Vector2

from circlebh.audio.intensity import PHRASE_BARS, Arrangement, raw_intensity
from circlebh.audio.rhythm import SIXTEENTHS
from circlebh.balance import BALANCE
from circlebh.world.enemy import Enemy

HEXAGON = BALANCE.enemies["hexagon"]
SEMICORCHEA = 60 / 124 / 4
"""Segundos de una semicorchea a 124 BPM."""
FRASE = PHRASE_BARS * SIXTEENTHS
"""Semicorcheas de una frase."""


def hexagono(x: float, lineas: int = 6) -> Enemy:
    enemy = Enemy(HEXAGON, Vector2(x, 0))
    enemy.edges = list(range(lineas))
    return enemy


def tocar(arrangement: Arrangement, raws: list[float], desde: int = 0) -> list[tuple]:
    """Avanza una semicorchea por cada `raw`. Devuelve `(g, capa, cues)` de cada una."""
    out = []
    for g, raw in enumerate(raws, start=desde):
        cues = arrangement.advance(raw, g, SEMICORCHEA)
        out.append((g, arrangement.level, cues))
    return out


def cambios(pasos: list[tuple]) -> list[tuple[int, int, int]]:
    """`(g, capa antes, capa después)` de cada semicorchea en que cambió la capa."""
    return [
        (g, antes, capa)
        for (_, antes, _), (g, capa, _) in pairwise(pasos)
        if capa != antes
    ]


# --- La intensidad cruda ---


def test_sin_enemigos_intensidad_cero() -> None:
    assert raw_intensity([], Vector2()) == 0


def test_intensidad_cruda_baja_con_la_distancia_y_las_lineas() -> None:
    cerca, lejos = hexagono(100), hexagono(800)
    herido = hexagono(100, lineas=3)
    jugador = Vector2()
    assert raw_intensity([cerca], jugador) > raw_intensity([lejos], jugador)
    assert raw_intensity([herido], jugador) == pytest.approx(
        raw_intensity([cerca], jugador) / 2
    )
    assert raw_intensity([cerca, lejos], jugador) == pytest.approx(
        raw_intensity([cerca], jugador) + raw_intensity([lejos], jugador)
    )


# --- Las capas ---


def test_con_muchos_enemigos_sube_al_empezar_una_frase_con_riser_antes() -> None:
    pasos = tocar(Arrangement(), [20.0] * (3 * FRASE))
    subidas = [g for g, antes, capa in cambios(pasos) if capa > antes]
    assert subidas
    for g in subidas:
        assert g % FRASE == 0
        assert "impact" in pasos[g][2]
        assert "riser" in pasos[g - SIXTEENTHS][2]
    assert pasos[-1][1] == 3


def test_con_pocos_baja_al_empezar_una_frase_sin_riser() -> None:
    arrangement = Arrangement()
    tocar(arrangement, [20.0] * (3 * FRASE))
    pasos = tocar(arrangement, [0.0] * (8 * FRASE), desde=3 * FRASE)
    bajadas = [g for g, antes, capa in cambios(pasos) if capa < antes]
    assert bajadas
    assert all(g % FRASE == 0 for g in bajadas)
    assert not any("riser" in cues for _, _, cues in pasos)
    assert pasos[-1][1] == 0


def test_reset_deja_la_capa_en_cero_con_un_impacto() -> None:
    arrangement = Arrangement()
    tocar(arrangement, [20.0] * (3 * FRASE))
    assert arrangement.reset() == ["impact"]
    assert arrangement.level == 0
    assert arrangement.smooth == 0


def test_rising_avisa_el_compas_antes_de_subir() -> None:
    arrangement = Arrangement()
    pasos = tocar(arrangement, [20.0] * (FRASE - SIXTEENTHS + 1))
    # La última semicorchea tocada es la primera del último compás de la frase.
    g = pasos[-1][0]
    assert arrangement.rising(g)
    assert not Arrangement().rising(g)


@given(st.lists(st.floats(0, 30), min_size=FRASE, max_size=4 * FRASE))
def test_la_capa_no_cambia_a_mitad_de_frase(raws: list[float]) -> None:
    for g, _, _ in cambios(tocar(Arrangement(), raws)):
        assert g % FRASE == 0


def test_la_intensidad_suavizada_sube_rapido_y_baja_lento() -> None:
    sube, baja = Arrangement(), Arrangement()
    baja.smooth = 1.0
    for g in range(8):  # ~1 s
        sube.advance(1e9, g, SEMICORCHEA)
        baja.advance(0.0, g, SEMICORCHEA)
    # En el mismo tiempo, recorre más camino al subir que al bajar.
    assert sube.smooth > 1 - baja.smooth
