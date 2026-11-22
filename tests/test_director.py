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

from circlebh.audio.intensity import PHRASE_BARS
from circlebh.balance import (
    BALANCE,
    DeckEntry,
    DirectorSpec,
    SectionSpec,
    SpawningSpec,
)
from circlebh.world.clock import STEP
from circlebh.world.director import Director, bar_at
from circlebh.world.game import World
from circlebh.world.spawning import FORMATIONS

HEXAGONO = BALANCE.enemies["hexagon"]
SPAWNING = BALANCE.spawning
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
    name: str,
    bars: float,
    start: float,
    end: float,
    deck: tuple[DeckEntry, ...],
    burst: float = 0.0,
    formations: tuple[str, ...] = ("single",),
) -> SectionSpec:
    return SectionSpec(
        name=name,
        kind="build",
        bars=bars,
        budget_start=start,
        budget_end=end,
        burst=burst,
        layers=(0, 3),
        deck=deck,
        formations=formations,
    )


def tema(*secciones: SectionSpec, bpm: float = 124.0) -> DirectorSpec:
    return DirectorSpec(bpm=bpm, max_alive=300, sections=secciones)


# Un tema corto, con presupuestos que suben, se mantienen y bajan, y un drop con ráfaga.
# El silencio del final no compra: así las tres primeras secciones quedan completas.
CORTO = tema(
    seccion("intro", 2.0, 1.0, 3.0, mazo("intro")),
    seccion("drop", 3.0, 4.0, 4.0, mazo("drop"), burst=7.0),
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
    """Avanza `pasos` pasos y devuelve, por paso, la sección y lo comprado, un nombre
    por enemigo."""
    return [
        (director.section_index, [p.enemy for p in compras for _ in range(p.count)])
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
    director = Director(spec, BALANCE.enemies, SPAWNING, random.Random(1))
    ultimo = primer_paso(inicios(spec)[-1], spec.bpm)
    secciones = [director.section_index] + [s for s, _ in correr(director, ultimo)]
    cambios = [p for p in range(1, ultimo + 1) if secciones[p] != secciones[p - 1]]
    assert cambios == [primer_paso(b, spec.bpm) for b in inicios(spec)[1:]]


@given(seed=st.integers(0, 2**32 - 1))
def test_secciones_en_orden(seed: int) -> None:
    # ADR 0025: con cualquier semilla, las secciones van en orden, y cada una empieza
    # en el primer paso que llega a su compás.
    director = Director(CORTO, ENEMIGOS, SPAWNING, random.Random(seed))
    pasos = primer_paso(sum(s.bars for s in CORTO.sections), CORTO.bpm)
    secciones = [s for s, _ in correr(director, pasos)]
    assert [k for k, _ in itertools.groupby(secciones)] == list(
        range(len(CORTO.sections))
    )
    empieza = [secciones.index(k) + 1 for k in range(1, len(CORTO.sections))]
    assert empieza == [primer_paso(b, CORTO.bpm) for b in inicios(CORTO)[1:]]


def test_la_ultima_seccion_sigue_despues_de_sus_compases() -> None:
    # Borde: hasta que exista el modo infinito, la última sección no termina.
    spec = tema(seccion("unica", 2.0, 4.0, 4.0, (DeckEntry("hexagon", 1.0),)))
    director = Director(spec, ENEMIGOS, SPAWNING, random.Random(1))
    resultado = correr(director, primer_paso(6.0, spec.bpm))
    assert {s for s, _ in resultado} == {0}
    # Pasados sus 2 compases, sigue comprando con la tasa del final: 4 por compás.
    assert sum(len(c) for _, c in resultado) == 24


# --- Las compras ---


CORTO_EN_FORMACION = replace(
    CORTO,
    sections=tuple(replace(s, formations=FORMATIONS) for s in CORTO.sections),
)
"""`CORTO` con todas las formaciones: compras de 1 y de 3 a 6."""


@given(
    seed=st.integers(0, 2**32 - 1),
    spec=st.sampled_from([CORTO, CORTO_EN_FORMACION]),
)
def test_no_gasta_mas_que_el_presupuesto(seed: int, spec: DirectorSpec) -> None:
    # El presupuesto es una tasa, en amenaza por compás, que va de `budget_start` a
    # `budget_end`. Lo que gana una sección es su integral: el área de un trapecio.
    director = Director(spec, ENEMIGOS, SPAWNING, random.Random(seed))
    pasos = primer_paso(inicios(CORTO)[-1], CORTO.bpm)
    gastado: defaultdict[str, float] = defaultdict(float)
    for _, compras in correr(director, pasos):
        for nombre in compras:
            gastado[nombre.split("-")[0]] += ENEMIGOS[nombre].threat
    for s in CORTO.sections[:-1]:
        presupuesto = s.burst + (s.budget_start + s.budget_end) / 2 * s.bars
        assert gastado[s.name] <= presupuesto
        # Y no deja más sin gastar de lo que cuesta uno de la compra que espera: una
        # formación se recorta al cerrar la sección.
        assert gastado[s.name] > presupuesto - PESADO


def test_lo_caro_tambien_se_compra() -> None:
    # Si el director comprara solo lo que le alcanza en cada paso, el presupuesto se
    # iría siempre en lo barato. Elige primero y ahorra.
    spec = tema(seccion("unica", 16.0, 4.0, 4.0, mazo("intro")))
    director = Director(spec, ENEMIGOS, SPAWNING, random.Random(1))
    compras = [n for _, c in correr(director, primer_paso(16.0, spec.bpm)) for n in c]
    assert set(compras) == {"intro-ligero", "intro-pesado"}


CALMA_Y_RAFAGA = tema(
    seccion("calma", 1.0, 0.0, 0.0, (DeckEntry("hexagon", 1.0),)),
    seccion("drop", 4.0, 0.0, 0.0, (DeckEntry("hexagon", 1.0),), burst=5.0),
)
"""Sin tasa: lo único que se compra es la ráfaga del drop, que empieza en el compás 1."""


def test_rafaga_en_el_primer_paso() -> None:
    director = Director(CALMA_Y_RAFAGA, ENEMIGOS, SPAWNING, random.Random(1))
    golpe = primer_paso(1.0, CALMA_Y_RAFAGA.bpm)
    compras = {paso: c for paso, (_, c) in enumerate(correr(director, golpe), start=1)}
    assert compras[golpe] == ["hexagon"] * 5
    assert all(c == [] for paso, c in compras.items() if paso != golpe)


def test_rafaga_solo_al_empezar() -> None:
    # Negativo: la ráfaga se compra una vez, no en cada paso de la sección.
    director = Director(CALMA_Y_RAFAGA, ENEMIGOS, SPAWNING, random.Random(1))
    resultado = correr(director, primer_paso(5.0, CALMA_Y_RAFAGA.bpm))
    assert sum(len(c) for _, c in resultado) == 5


# --- Las formaciones (decisión 28) ---

ANILLOS_DE_5 = replace(SPAWNING, formation_size=(5, 5))
ANILLO_QUE_CIERRA = tema(
    seccion(
        "anillos", 2.0, 4.0, 4.0, (DeckEntry("hexagon", 1.0),), formations=("ring",)
    ),
    seccion("silencio", 4.0, 0.0, 0.0, ()),
)
"""8 de amenaza en 2 compases, en anillos de 5 hexágonos de amenaza 1."""


def compras_con_paso(spec: DirectorSpec, spawning: SpawningSpec, pasos: int) -> list:
    director = Director(spec, ENEMIGOS, spawning, random.Random(1))
    return [(paso, p) for paso in range(1, pasos + 1) for p in director.update(paso)]


def test_formacion_se_compra_entera() -> None:
    # A 4 por compás, el primer anillo de 5 se paga recién en el compás 1,25: antes no
    # sale ninguna parte.
    [(paso, anillo), _] = compras_con_paso(ANILLO_QUE_CIERRA, ANILLOS_DE_5, 1000)
    assert (anillo.formation, anillo.count) == ("ring", 5)
    assert paso == primer_paso(1.25, 124.0)


def test_al_cerrar_la_seccion_recorta_la_formacion() -> None:
    # Borde: al terminar la sección quedan 3 de amenaza. El anillo que esperaba sale
    # con 3, en vez de perderse.
    compras = compras_con_paso(ANILLO_QUE_CIERRA, ANILLOS_DE_5, 1000)
    assert [p.count for _, p in compras] == [5, 3]
    assert compras[1][0] == primer_paso(2.0, 124.0)


def test_single_es_de_a_uno() -> None:
    # Negativo: `formation_size` no se aplica a `single`.
    spec = tema(seccion("unica", 4.0, 4.0, 4.0, (DeckEntry("hexagon", 1.0),)))
    compras = compras_con_paso(spec, ANILLOS_DE_5, primer_paso(4.0, 124.0))
    assert {(p.formation, p.count) for _, p in compras} == {("single", 1)}
    assert len(compras) == 16


@given(seed=st.integers(0, 2**32 - 1))
def test_solitario_se_compra_siempre_single(seed: int) -> None:
    # Decisión 45: aunque la sección sortee un anillo, una fila o un grupo, el
    # solitario sale de a uno. El otro tipo del mazo sí forma.
    enemigos = {**ENEMIGOS, "estrella": BALANCE.enemies["star"]}
    mazo = (DeckEntry("estrella", 1.0), DeckEntry("hexagon", 1.0))
    formaciones = ("ring", "line", "cluster")
    spec = tema(seccion("unica", 8.0, 6.0, 6.0, mazo, formations=formaciones))
    director = Director(spec, enemigos, ANILLOS_DE_5, random.Random(seed))
    compras = [p for paso in range(1, 2000) for p in director.update(paso)]
    estrellas = [p for p in compras if p.enemy == "estrella"]
    assert estrellas
    assert all((p.formation, p.count) == ("single", 1) for p in estrellas)
    assert all(p.count == 5 for p in compras if p.enemy == "hexagon")


@pytest.mark.parametrize(
    ("spec", "spawning", "campo"),
    [
        (
            tema(
                seccion(
                    "x",
                    4.0,
                    1.0,
                    1.0,
                    (DeckEntry("hexagon", 1.0),),
                    formations=("rombo",),
                )
            ),
            SPAWNING,
            "rombo",
        ),
        (
            tema(
                seccion("x", 4.0, 1.0, 1.0, (DeckEntry("hexagon", 1.0),), formations=())
            ),
            SPAWNING,
            "formations",
        ),
        (CORTO, replace(SPAWNING, formation_size=(0, 3)), "formation_size"),
        (CORTO, replace(SPAWNING, formation_size=(4, 2)), "formation_size"),
        (CORTO, replace(SPAWNING, max_per_step=0), "max_per_step"),
        (CORTO, replace(SPAWNING, formation_gap=-1.0), "formation_gap"),
        # Con 0, los vecinos nacen justo en el borde del núcleo duro, no fuera.
        (CORTO, replace(SPAWNING, formation_gap=0.0), "formation_gap"),
        (CORTO, replace(SPAWNING, distance=0.0), "distance"),
    ],
)
def test_aparicion_invalida_se_rechaza(
    spec: DirectorSpec, spawning: SpawningSpec, campo: str
) -> None:
    # Negativo: una formación que no existe, una sección con mazo y sin formaciones, o
    # números de aparición sin sentido fallan al empezar, nombrando el campo.
    with pytest.raises(ValueError, match=campo):
        Director(spec, ENEMIGOS, spawning, random.Random(1))


def test_section_at() -> None:
    # Borde: antes del compás 0 da la primera, y después del final, la última.
    director = Director(CORTO, ENEMIGOS, SPAWNING, random.Random(1))
    nombres = [director.section_at(b).name for b in (-1.0, 0.0, 1.999, 2.0, 100.0)]
    assert nombres == ["intro", "intro", "intro", "drop", "silencio"]


def test_secciones_empiezan_en_una_frase() -> None:
    # Foco 6: la capa de la música solo cambia al empezar una frase. Una sección que
    # empieza a mitad de frase sonaría hasta 3 compases tarde.
    assert all(b % PHRASE_BARS == 0 for b in inicios(BALANCE.director))


@pytest.mark.parametrize(
    ("spec", "enemigos", "campo"),
    [
        # Con amenaza 0, el director compraría sin fin en un solo paso.
        (CALMA_Y_RAFAGA, {"hexagon": replace(HEXAGONO, threat=0.0)}, "threat"),
        (tema(seccion("x", 0.0, 1.0, 1.0, ())), ENEMIGOS, "bars"),
        (
            tema(seccion("x", 4.0, 1.0, 1.0, (DeckEntry("nadie", 1.0),))),
            ENEMIGOS,
            "nadie",
        ),
        (
            tema(seccion("x", 4.0, 1.0, 1.0, (DeckEntry("hexagon", 0.0),))),
            ENEMIGOS,
            "weight",
        ),
        (tema(), ENEMIGOS, "sections"),
    ],
)
def test_tema_invalido_se_rechaza_al_crear_el_director(
    spec: DirectorSpec, enemigos: dict, campo: str
) -> None:
    # Negativo: un tema que colgaría o rompería la partida a mitad de camino se
    # rechaza al empezar, nombrando el campo.
    with pytest.raises(ValueError, match=campo):
        Director(spec, enemigos, SPAWNING, random.Random(1))


def test_sin_mazo_no_compra() -> None:
    spec = tema(seccion("vacia", 8.0, 50.0, 50.0, ()))
    director = Director(spec, ENEMIGOS, SPAWNING, random.Random(1))
    assert all(c == [] for _, c in correr(director, primer_paso(8.0, spec.bpm)))


def test_no_usa_otro_azar() -> None:
    # Negativo: todo el azar sale de la `Random` que recibe (ADR 0005).
    random.seed(0)
    global_antes = random.getstate()
    director = Director(CORTO, ENEMIGOS, SPAWNING, random.Random(1))
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
