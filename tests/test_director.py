"""Tests del director: cuenta compases y compra enemigos por secciones (ADR 0025)."""

import itertools
import math
import random
from collections import defaultdict
from dataclasses import replace
from fractions import Fraction

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pygame.math import Vector2

from circlebh.balance import BALANCE, DeckEntry, DirectorSpec, SectionSpec
from circlebh.world.clock import STEP
from circlebh.world.director import Director, bar_at
from circlebh.world.game import World

HEXAGONO = BALANCE.enemies["hexagon"]
LIGERO, PESADO = 1.0, 3.0
ENEMIGOS = {"hexagon": HEXAGONO} | {
    f"{seccion}-{tipo}": replace(HEXAGONO, threat=threat)
    for seccion in ("intro", "drop", "respiro")
    for tipo, threat in (("ligero", LIGERO), ("pesado", PESADO))
}
"""Cada sección del tema corto tiene sus propios tipos. Así, lo que compra una sección
en el paso en que termina se le atribuye a ella por el nombre, y no a la siguiente."""


def mazo(seccion: str) -> tuple[DeckEntry, ...]:
    return (DeckEntry(f"{seccion}-ligero", 1.0), DeckEntry(f"{seccion}-pesado", 1.0))


def seccion(
    name: str, bars: float, start: float, end: float, deck: tuple[DeckEntry, ...]
) -> SectionSpec:
    return SectionSpec(
        name=name,
        kind="build",
        bars=bars,
        budget_start=start,
        budget_end=end,
        deck=deck,
        formations=("single",),
    )


def tema(*secciones: SectionSpec, bpm: float = 124.0) -> DirectorSpec:
    return DirectorSpec(bpm=bpm, max_alive=300, sections=secciones)


# Un tema corto, con presupuestos que suben, se mantienen y bajan. El silencio del final
# no compra: así las tres primeras secciones quedan completas.
CORTO = tema(
    seccion("intro", 2.0, 1.0, 3.0, mazo("intro")),
    seccion("drop", 3.0, 4.0, 4.0, mazo("drop")),
    seccion("respiro", 2.0, 2.0, 0.5, mazo("respiro")),
    seccion("silencio", 1.0, 0.0, 0.0, ()),
)


def primer_paso(bar: float, bpm: float) -> int:
    """El primer paso que llega al compás `bar`, con fracciones exactas.

    Un compás son 4 pulsos, y un minuto, 60 / STEP = 3600 pasos:
    `pasos · bpm / (4 · 3600) ≥ bar`.
    """
    return math.ceil(Fraction(bar) * 4 * 3600 / Fraction(bpm))


def inicios(spec: DirectorSpec) -> list[float]:
    """El compás en que empieza cada sección."""
    return list(itertools.accumulate((s.bars for s in spec.sections), initial=0.0))[:-1]


def correr(director: Director, pasos: int) -> list[tuple[int, list[str]]]:
    """Avanza `pasos` pasos y devuelve, por paso, la sección y lo comprado."""
    return [
        (director.section_index, compras)
        for compras in (director.update(paso) for paso in range(1, pasos + 1))
    ]


# --- El reloj en compases ---


def test_compas_desde_los_pasos() -> None:
    pasos = round(240 / 124 / STEP * 10)
    assert bar_at(pasos, 124) == pytest.approx(10, abs=124 * STEP / 240)


def test_compas_sin_error_acumulado() -> None:
    pasos = round(5 * 60 / STEP)
    exacto = Fraction(pasos) * 124 / (4 * 3600)
    assert abs(bar_at(pasos, 124) - float(exacto)) < 124 * STEP / 240


def test_paso_cero_es_compas_cero() -> None:
    assert bar_at(0, 124) == 0


# --- Las secciones ---


def test_seccion_empieza_en_su_compas() -> None:
    # Borde: a 124 BPM un compás dura 116,13 pasos, así que ningún límite cae en un
    # paso entero. Cada sección tiene que empezar en el primer paso que llega a él.
    spec = BALANCE.director
    director = Director(spec, BALANCE.enemies, random.Random(1))
    ultimo = primer_paso(inicios(spec)[-1], spec.bpm)
    secciones = [director.section_index] + [s for s, _ in correr(director, ultimo)]
    cambios = [p for p in range(1, ultimo + 1) if secciones[p] != secciones[p - 1]]
    assert cambios == [primer_paso(b, spec.bpm) for b in inicios(spec)[1:]]


@given(seed=st.integers(0, 2**32 - 1))
def test_secciones_en_orden(seed: int) -> None:
    director = Director(CORTO, ENEMIGOS, random.Random(seed))
    pasos = primer_paso(sum(s.bars for s in CORTO.sections), CORTO.bpm)
    secciones = [s for s, _ in correr(director, pasos)]
    assert [k for k, _ in itertools.groupby(secciones)] == list(
        range(len(CORTO.sections))
    )


def test_la_ultima_seccion_sigue_despues_de_sus_compases() -> None:
    # Borde: hasta que exista el modo infinito, la última sección no termina.
    spec = tema(seccion("unica", 2.0, 4.0, 4.0, (DeckEntry("hexagon", 1.0),)))
    director = Director(spec, ENEMIGOS, random.Random(1))
    resultado = correr(director, primer_paso(6.0, spec.bpm))
    assert {s for s, _ in resultado} == {0}
    # Pasados sus 2 compases, sigue comprando con la tasa del final: 4 por compás.
    assert sum(len(c) for _, c in resultado) == 24


# --- Las compras ---


@given(seed=st.integers(0, 2**32 - 1))
def test_no_gasta_mas_que_el_presupuesto(seed: int) -> None:
    # El presupuesto es una tasa, en amenaza por compás, que va de `budget_start` a
    # `budget_end`. Lo que gana una sección es su integral: el área de un trapecio.
    director = Director(CORTO, ENEMIGOS, random.Random(seed))
    pasos = primer_paso(inicios(CORTO)[-1], CORTO.bpm)
    gastado: defaultdict[str, float] = defaultdict(float)
    for _, compras in correr(director, pasos):
        for nombre in compras:
            gastado[nombre.split("-")[0]] += ENEMIGOS[nombre].threat
    for s in CORTO.sections[:-1]:
        presupuesto = (s.budget_start + s.budget_end) / 2 * s.bars
        assert gastado[s.name] <= presupuesto
        # Y no deja más sin gastar de lo que cuesta la compra que está esperando.
        assert gastado[s.name] > presupuesto - PESADO


def test_lo_caro_tambien_se_compra() -> None:
    # Si el director comprara solo lo que le alcanza en cada paso, el presupuesto se
    # iría siempre en lo barato. Elige primero y ahorra.
    spec = tema(seccion("unica", 16.0, 4.0, 4.0, mazo("intro")))
    director = Director(spec, ENEMIGOS, random.Random(1))
    compras = [n for _, c in correr(director, primer_paso(16.0, spec.bpm)) for n in c]
    assert set(compras) == {"intro-ligero", "intro-pesado"}


def test_sin_mazo_no_compra() -> None:
    spec = tema(seccion("vacia", 8.0, 50.0, 50.0, ()))
    director = Director(spec, ENEMIGOS, random.Random(1))
    assert all(c == [] for _, c in correr(director, primer_paso(8.0, spec.bpm)))


def test_no_usa_otro_azar() -> None:
    # Negativo: todo el azar sale de la `Random` que recibe (ADR 0005).
    random.seed(0)
    global_antes = random.getstate()
    director = Director(CORTO, ENEMIGOS, random.Random(1))
    correr(director, primer_paso(7.0, CORTO.bpm))
    assert random.getstate() == global_antes


# --- El director en el mundo ---

RAPIDO = replace(
    BALANCE,
    director=tema(seccion("rapida", 8.0, 4.0, 4.0, (DeckEntry("hexagon", 1.0),))),
)
"""Un hexágono por cuarto de compás, desde el primer paso."""


def test_misma_semilla_mismas_compras() -> None:
    a = World(RAPIDO, random.Random(7), lethal=False)
    b = World(RAPIDO, random.Random(7), lethal=False)
    for _ in range(primer_paso(4.0, 124.0)):
        a.update(Vector2(1, 0))
        b.update(Vector2(1, 0))
        assert [e.position for e in a.enemies] == [e.position for e in b.enemies]
    assert len(a.enemies) > 4
