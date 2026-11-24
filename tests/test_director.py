"""Tests del director: cuenta compases y compra enemigos por secciones (ADR 0025)."""

import itertools
import math
import random
from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import replace
from fractions import Fraction
from typing import Literal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pygame.math import Vector2

from circlebh.balance import (
    BALANCE,
    DeckEntry,
    DirectorSpec,
    EndlessSpec,
    EnemySpec,
    SectionSpec,
    SeekSpec,
    SpawningSpec,
)
from circlebh.world.clock import STEP
from circlebh.world.director import (
    PHRASE_BARS,
    Director,
    Purchase,
    bar_at,
    body_weight,
    deck_weights,
    endless_earned,
    start_from,
)
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
    kind: Literal["build", "wave", "endless"] = "build",
) -> SectionSpec:
    return SectionSpec(
        name=name,
        kind=kind,
        bars=bars,
        budget_start=start,
        budget_end=end,
        burst=burst,
        layers=(0, 3),
        deck=deck,
        formations=formations,
    )


ESPEC_INFINITO = EndlessSpec(
    doubling=4.0, step=0.5, speed_cap=1.5, cadence_cap=2.0, sides_cap=2.0
)
"""Se duplica cada 4 compases, para que los tests del infinito sean cortos."""


def tema(
    *secciones: SectionSpec,
    bpm: float = 124.0,
    max_alive: int = 300,
    endless: EndlessSpec = ESPEC_INFINITO,
) -> DirectorSpec:
    return DirectorSpec(
        bpm=bpm, max_alive=max_alive, sections=secciones, endless=endless
    )


# Un tema corto, con presupuestos que suben, se mantienen y bajan, y un drop con ráfaga.
# El silencio del final no compra: así las tres primeras secciones quedan completas.
CORTO = tema(
    seccion("intro", 2.0, 1.0, 3.0, mazo("intro")),
    seccion("drop", 3.0, 4.0, 4.0, mazo("drop"), burst=7.0),
    seccion("respiro", 2.0, 2.0, 0.5, mazo("respiro")),
    seccion("silencio", 1.0, 0.0, 0.0, ()),
)


def infinito(
    start: float = 1.0,
    deck: tuple[DeckEntry, ...] = (DeckEntry("hexagon", 1.0),),
    formations: tuple[str, ...] = ("single",),
) -> SectionSpec:
    """Un infinito con `B₀ = start`."""
    return seccion(
        "infinito", 4.0, start, 0.0, deck, formations=formations, kind="endless"
    )


INFINITO = tema(
    seccion("intro", 4.0, 1.0, 1.0, mazo("intro")), infinito(), max_alive=10
)
"""4 compases de intro y el infinito, con un tope de 10 cuerpos. El infinito compra
hexágonos, y la intro, sus propios tipos: así se sabe quién compró qué."""

DIVISORES = ENEMIGOS | {name: BALANCE.enemies[name] for name in ("divider", "shard")}
"""Con el divisor y sus fragmentos."""


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
        for compras in (
            director.update(paso, wave_alive=False, bodies=0)
            for paso in range(1, pasos + 1)
        )
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
    # Borde: en un tema sin infinito, la última sección no termina.
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


# --- Las oleadas (decisión 72) ---

OLEADA = tema(
    seccion("intro", 4.0, 1.0, 1.0, mazo("intro")),
    seccion("drop", 8.0, 0.0, 0.0, mazo("drop"), burst=7.0, kind="wave"),
    seccion("respiro", 4.0, 1.0, 1.0, mazo("respiro")),
)
"""El drop es una oleada de 8 compases, del 4 al 12, que compra 7 de amenaza."""


def limpiar_en(
    limpia: float, hasta: float, spec: DirectorSpec = OLEADA
) -> tuple[Director, list[tuple[int, list[Purchase]]]]:
    """Corre el director hasta el compás `hasta`, con la oleada viva antes del compás
    `limpia` y limpia desde ahí. Devuelve, por paso, la sección y lo comprado."""
    director = Director(spec, ENEMIGOS, SPAWNING, random.Random(1))
    resultado = []
    for paso in range(1, primer_paso(hasta, spec.bpm) + 1):
        compras = director.update(
            paso, wave_alive=bar_at(paso, spec.bpm) < limpia, bodies=0
        )
        resultado.append((director.section_index, compras))
    return director, resultado


def empieza(resultado: list[tuple[int, list[Purchase]]], seccion: int) -> int:
    """El paso en que empezó la sección de índice `seccion`."""
    return next(paso for paso, (s, _) in enumerate(resultado, 1) if s == seccion)


def test_oleada_compra_su_rafaga_al_empezar() -> None:
    director = Director(OLEADA, ENEMIGOS, SPAWNING, random.Random(1))
    golpe = primer_paso(4.0, OLEADA.bpm)
    for paso in range(1, golpe):
        director.update(paso, wave_alive=False, bodies=0)
    # En el paso en que se compra, el mundo todavía no ve a nadie de la oleada: no
    # cuenta como limpia.
    oleada = director.update(golpe, wave_alive=False, bodies=0)
    assert director.waiting
    assert oleada
    assert all(p.wave == 1 for p in oleada)
    gastado = sum(ENEMIGOS[p.enemy].threat * p.count for p in oleada)
    assert 7.0 - PESADO < gastado <= 7.0
    despues = [
        director.update(paso, wave_alive=True, bodies=0)
        for paso in range(golpe + 1, primer_paso(8.0, OLEADA.bpm))
    ]
    assert all(c == [] for c in despues)


def test_oleada_no_termina_con_uno_vivo() -> None:
    # Negativo: mientras quede uno, el director espera, aunque pasen muchos compases.
    director, resultado = limpiar_en(math.inf, 100.0)
    assert resultado[-1][0] == 1
    assert director.waiting
    # La música pregunta por compases futuros: mientras espera, todos son del drop.
    assert director.section_at(1000.0).name == "drop"


@pytest.mark.parametrize(
    ("limpia", "inicio"),
    [
        (13.5, 16.0),
        # El compás de margen: limpia a 1,1 compases de la frase, y alcanza.
        (14.9, 16.0),
        # Limpia en el último compás de la frase, cuando la música ya decidió la
        # siguiente: el respiro espera a la otra.
        (15.1, 20.0),
    ],
)
def test_oleada_termina_al_limpiarse(limpia: float, inicio: float) -> None:
    director, resultado = limpiar_en(limpia, 24.0)
    assert empieza(resultado, 2) == primer_paso(inicio, OLEADA.bpm)
    assert not director.waiting
    assert director.section_at(inicio).name == "respiro"
    assert director.section_at(inicio - 0.01).name == "drop"


def test_oleada_dura_al_menos_sus_compases() -> None:
    # Borde: limpia en el compás 5, pero la oleada dura 8 compases, hasta el 12.
    _, resultado = limpiar_en(5.0, 16.0)
    assert empieza(resultado, 2) == primer_paso(12.0, OLEADA.bpm)
    # Y no compra más que al empezar, aunque le sobre `burst`.
    golpe = primer_paso(4.0, OLEADA.bpm)
    del_drop = [paso for paso, (s, c) in enumerate(resultado, 1) if s == 1 and c]
    assert del_drop == [golpe]


def test_oleada_sin_compras_queda_limpia() -> None:
    # Borde: con menos `burst` que la amenaza más barata no compra, y no espera a
    # nadie aunque el mundo diga que hay alguien.
    pobre = replace(
        OLEADA,
        sections=tuple(
            replace(s, burst=0.5) if s.kind == "wave" else s for s in OLEADA.sections
        ),
    )
    director, resultado = limpiar_en(math.inf, 16.0, pobre)
    assert not any(c for s, c in resultado if s == 1)
    assert empieza(resultado, 2) == primer_paso(12.0, pobre.bpm)
    assert not director.waiting


@settings(max_examples=20, deadline=None)
@given(data=st.data())
def test_secciones_empiezan_en_una_frase_tras_la_oleada(data: st.DataObject) -> None:
    # Foco 6, después de esperar: limpie cuando limpie, cada sección sigue empezando en
    # una frase.
    spec = BALANCE.director
    drop = [s.name for s in spec.sections].index("drop_1")
    limpia = data.draw(st.floats(inicios(spec)[drop], 120.0))
    director = Director(spec, BALANCE.enemies, SPAWNING, random.Random(1))
    seccion = director.section_index
    for paso in range(1, primer_paso(160.0, spec.bpm) + 1):
        director.update(paso, wave_alive=bar_at(paso, spec.bpm) < limpia, bodies=0)
        if director.section_index != seccion:
            seccion = director.section_index
            frase = math.floor(bar_at(paso, spec.bpm) / PHRASE_BARS) * PHRASE_BARS
            assert frase > bar_at(paso - 1, spec.bpm)


def test_drops_del_balance_son_oleadas() -> None:
    kinds = {s.name: s.kind for s in BALANCE.director.sections}
    assert kinds["drop_1"] == kinds["drop_2"] == "wave"


def test_las_siguientes_se_corren_lo_mismo() -> None:
    spec = replace(
        OLEADA,
        sections=(*OLEADA.sections, seccion("final", 4.0, 1.0, 1.0, mazo("intro"))),
    )
    _, resultado = limpiar_en(13.5, 24.0, spec)
    assert empieza(resultado, 2) == primer_paso(16.0, spec.bpm)
    assert empieza(resultado, 3) == primer_paso(20.0, spec.bpm)


def test_oleada_de_compases_sueltos_termina_en_una_frase() -> None:
    # Borde (Foco 6): una oleada de 6 compases que se limpia al tiro no termina en el
    # compás 10, a mitad de frase, sino en el 12.
    spec = replace(
        OLEADA,
        sections=tuple(
            replace(s, bars=6.0) if s.kind == "wave" else s for s in OLEADA.sections
        ),
    )
    _, resultado = limpiar_en(5.0, 16.0, spec)
    assert empieza(resultado, 2) == primer_paso(12.0, spec.bpm)


def test_antes_de_una_seccion_que_exige_mas_deja_frase_para_la_subida() -> None:
    # Si lo que sigue exige más capas, la música necesita una frase entera de subida
    # que empiece después de limpiar: limpia en el 13,5 y el drop sigue hasta el 20.
    intensa = replace(OLEADA.sections[2], layers=(3, 3))
    spec = replace(OLEADA, sections=(*OLEADA.sections[:2], intensa))
    _, resultado = limpiar_en(13.5, 24.0, spec)
    assert empieza(resultado, 2) == primer_paso(20.0, spec.bpm)


def test_oleadas_seguidas() -> None:
    # La primera se limpia en el 5 y termina en el 8; la segunda compra con su
    # etiqueta y espera, aunque la primera ya no tenga a nadie.
    spec = tema(
        seccion("uno", 4.0, 0.0, 0.0, mazo("drop"), burst=7.0, kind="wave"),
        seccion("dos", 4.0, 0.0, 0.0, mazo("drop"), burst=7.0, kind="wave"),
    )
    director = Director(spec, ENEMIGOS, SPAWNING, random.Random(1))
    segunda = primer_paso(8.0, spec.bpm)
    compras = {}
    for paso in range(1, segunda + 100):
        viva = bar_at(paso, spec.bpm) < 5.0 or paso > segunda
        compras[paso] = director.update(paso, wave_alive=viva, bodies=0)
    assert {p.wave for p in compras[1]} == {0}
    assert {p.wave for p in compras[segunda]} == {1}
    assert director.section_index == 1
    assert director.waiting


def test_oleada_unica_no_compra_mas_al_limpiarse() -> None:
    # Borde: una oleada que es la primera y la última sección compra en el primer
    # paso y, limpia, ya no compra nada: el tema no tiene infinito.
    spec = tema(seccion("unica", 4.0, 0.0, 0.0, mazo("drop"), burst=7.0, kind="wave"))
    director, resultado = limpiar_en(1.0, 40.0, spec)
    assert resultado[0][1]
    assert all(p.wave == 0 for p in resultado[0][1])
    assert not any(c for _, c in resultado[1:])
    assert not director.waiting


def test_un_salto_se_detiene_en_la_oleada() -> None:
    # Borde: si un paso salta varias secciones, se detiene en la oleada, compra y
    # espera.
    spec = tema(
        seccion("intro", 4.0, 1.0, 1.0, mazo("intro")),
        seccion("subida", 4.0, 1.0, 1.0, mazo("intro")),
        seccion("drop", 4.0, 0.0, 0.0, mazo("drop"), burst=7.0, kind="wave"),
        seccion("respiro", 4.0, 1.0, 1.0, mazo("respiro")),
    )
    director = Director(spec, ENEMIGOS, SPAWNING, random.Random(1))
    compras = director.update(primer_paso(100.0, spec.bpm), wave_alive=True, bodies=0)
    assert director.section.name == "drop"
    assert director.waiting
    assert {p.wave for p in compras if p.enemy.startswith("drop")} == {2}


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
    return [
        (paso, p)
        for paso in range(1, pasos + 1)
        for p in director.update(paso, wave_alive=False, bodies=0)
    ]


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
    compras = [
        p
        for paso in range(1, 2000)
        for p in director.update(paso, wave_alive=False, bodies=0)
    ]
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
        # Foco 4: una estrella quieta y lejos dejaría el drop sin limpiar nunca.
        (
            tema(
                seccion("x", 4.0, 0.0, 0.0, (DeckEntry("estrella", 1.0),), kind="wave")
            ),
            {"estrella": BALANCE.enemies["star"]},
            r"deck\[estrella\]",
        ),
        # Una oleada compra solo al empezar: esa tasa no se usaría.
        (
            tema(seccion("x", 4.0, 1.0, 0.0, mazo("drop"), kind="wave")),
            ENEMIGOS,
            "budget_start",
        ),
        (
            tema(seccion("x", 4.0, 0.0, 1.0, mazo("drop"), kind="wave")),
            ENEMIGOS,
            "budget_end",
        ),
        (
            tema(seccion("x", 4.0, 0.0, 0.0, (DeckEntry("nadie", 1.0),), kind="wave")),
            ENEMIGOS,
            "nadie",
        ),
        # Foco 4, un nivel más abajo: el que se parte en un anclado deja fragmentos que
        # no te siguen.
        (
            tema(seccion("x", 4.0, 0.0, 0.0, (DeckEntry("padre", 1.0),), kind="wave")),
            {
                "padre": replace(HEXAGONO, split_into="ancla"),
                "ancla": replace(HEXAGONO, anchored=True, threat=0.0),
            },
            r"deck\[padre\]",
        ),
        # El infinito sigue para siempre: después de él no se llega a nada.
        (
            tema(infinito(), seccion("x", 4.0, 1.0, 1.0, mazo("intro"))),
            ENEMIGOS,
            "kind",
        ),
        (tema(infinito(), infinito()), ENEMIGOS, "kind"),
        (tema(infinito(deck=())), ENEMIGOS, "deck"),
        (tema(infinito(start=0.0)), ENEMIGOS, "budget_start"),
        (tema(replace(infinito(), budget_end=1.0)), ENEMIGOS, "budget_end"),
        (tema(replace(infinito(), burst=1.0)), ENEMIGOS, "burst"),
        # El peso de los lados necesita vértices.
        (
            tema(infinito(deck=(DeckEntry("circulo", 1.0),))),
            {"circulo": replace(BALANCE.enemies["circle"], threat=1.0)},
            r"deck\[circulo\]",
        ),
        (
            tema(infinito(), endless=replace(ESPEC_INFINITO, doubling=0.0)),
            ENEMIGOS,
            "endless.doubling",
        ),
        (
            tema(infinito(), endless=replace(ESPEC_INFINITO, step=-1.0)),
            ENEMIGOS,
            "endless.step",
        ),
        (
            tema(infinito(), endless=replace(ESPEC_INFINITO, speed_cap=0.5)),
            ENEMIGOS,
            "endless.speed_cap",
        ),
        # Una formación que nunca cabe bajo el tope dejaría al infinito sin comprar.
        (
            tema(
                infinito(deck=(DeckEntry("divider", 1.0),), formations=("ring",)),
                max_alive=4,
            ),
            DIVISORES,
            "max_alive",
        ),
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


# --- El modo infinito ---


def infinito_con(
    spec: DirectorSpec,
    cuerpos: Callable[[int], int],
    hasta: float,
    *,
    enemigos: Mapping[str, EnemySpec] = ENEMIGOS,
    spawning: SpawningSpec = SPAWNING,
) -> tuple[Director, dict[int, list[Purchase]]]:
    """Avanza hasta el compás `hasta` con `cuerpos(paso)` cuerpos, y devuelve por paso
    lo que compró el infinito."""
    director = Director(spec, enemigos, spawning, random.Random(1))
    compras = {}
    for paso in range(1, primer_paso(hasta, spec.bpm) + 1):
        hechas = director.update(paso, wave_alive=False, bodies=cuerpos(paso))
        # La intro compra sus propios tipos: lo que queda es del infinito.
        compras[paso] = [p for p in hechas if not p.enemy.startswith("intro")]
    return director, compras


def test_infinito_compra_bajo_el_tope() -> None:
    _, compras = infinito_con(INFINITO, lambda _: 0, 12.0)
    total = sum(p.count for c in compras.values() for p in c)
    ganado = endless_earned(bar_at(primer_paso(12.0, 124.0), 124.0) - 4, 1.0, 4.0)
    # Cada hexágono cuesta 1: compra todo lo ganado, salvo lo que no alcanza para uno.
    assert ganado - 1 < total <= ganado


def test_tope_de_cuerpos() -> None:
    # Negativo: con el tope lleno no compra cuerpos, y lo ganado sube el peligro.
    director, compras = infinito_con(INFINITO, lambda _: 10, 12.0)
    assert not any(compras.values())
    assert director.excess > 0
    assert director.danger.speed > 1


def test_peligro_no_baja() -> None:
    # Matar abre espacio, pero no devuelve el peligro.
    spec = INFINITO
    director = Director(spec, ENEMIGOS, SPAWNING, random.Random(1))
    antes = director.danger.speed
    for paso in range(1, primer_paso(30.0, spec.bpm) + 1):
        lleno = math.floor(bar_at(paso, spec.bpm)) % 2 == 0
        director.update(paso, wave_alive=False, bodies=10 if lleno else 0)
        assert director.danger.speed >= antes
        antes = director.danger.speed
    assert antes > 1


def test_compra_que_espera_se_paga_al_abrir_espacio() -> None:
    abre = primer_paso(12.0, INFINITO.bpm) + 1
    _, compras = infinito_con(INFINITO, lambda paso: 0 if paso >= abre else 10, 12.1)
    assert not any(compras[p] for p in range(1, abre))
    assert compras[abre]


def test_formacion_que_no_cabe_espera() -> None:
    # Borde: un anillo de 3 no cabe en 2 lugares. Una formación se compra entera
    # (decisión 28), así que espera, y lo ganado va al peligro.
    spec = tema(
        seccion("intro", 4.0, 1.0, 1.0, mazo("intro")),
        infinito(formations=("ring",)),
        max_alive=10,
    )
    spawning = replace(SPAWNING, formation_size=(3, 3))
    director, compras = infinito_con(spec, lambda _: 8, 12.0, spawning=spawning)
    assert not any(compras.values())
    assert director.excess > 0


@pytest.mark.parametrize(("cuerpos", "compra"), [(6, False), (5, True)])
def test_divisor_cuenta_por_sus_fragmentos(cuerpos: int, compra: bool) -> None:
    # Borde (Foco): un divisor deja 5 fragmentos. Si contara como 1, con el tope lleno
    # cada divisor que muere lo pasaría en 4.
    assert body_weight(DIVISORES["divider"], DIVISORES) == 5
    spec = tema(
        seccion("intro", 4.0, 1.0, 1.0, mazo("intro")),
        infinito(start=4.0, deck=(DeckEntry("divider", 1.0),)),
        max_alive=10,
    )
    _, compras = infinito_con(spec, lambda _: cuerpos, 12.0, enemigos=DIVISORES)
    assert any(compras.values()) == compra


def test_lados_cargan_el_mazo() -> None:
    seccion_ = infinito(deck=(DeckEntry("triangle", 1.0), DeckEntry("octagon", 1.0)))
    enemigos = BALANCE.enemies
    triangulo, octagono = deck_weights(seccion_, enemigos, 2.0)
    assert octagono / triangulo == pytest.approx(8 / 3)
    # Negativo: con el multiplicador en 1, los pesos quedan tal cual.
    assert deck_weights(seccion_, enemigos, 1.0) == [1.0, 1.0]


def test_infinito_empieza_al_limpiar_el_drop_2() -> None:
    spec = BALANCE.director
    director = Director(spec, BALANCE.enemies, SPAWNING, random.Random(1))
    drop_2 = [s.name for s in spec.sections].index("drop_2")
    paso = 0
    while director.section.kind != "endless":
        paso += 1
        assert bar_at(paso, spec.bpm) < 200
        director.update(paso, wave_alive=False, bodies=0)
    assert director.section_index == drop_2 + 1
    assert director.section.name == "infinito"
    # Foco 6: empieza en una frase.
    frase = math.floor(bar_at(paso, spec.bpm) / PHRASE_BARS) * PHRASE_BARS
    assert frase > bar_at(paso - 1, spec.bpm)


def test_tope_de_velocidad_deja_a_los_que_persiguen_mas_lentos() -> None:
    # Foco: en su tope, nadie que te persigue corre más que tú.
    [infinito_] = [s for s in BALANCE.director.sections if s.kind == "endless"]
    tope = BALANCE.director.endless.speed_cap
    for entry in infinito_.deck:
        spec = BALANCE.enemies[entry.enemy]
        if any(isinstance(p, SeekSpec) for p in spec.patterns):
            assert spec.speed * tope < BALANCE.player.speed, entry.enemy


def test_start_from() -> None:
    spec = BALANCE.director
    assert start_from(spec, "") == spec
    assert start_from(spec, "infinito").sections[0].name == "infinito"
    # Negativo: una sección que no está en el tema.
    with pytest.raises(ValueError, match="start_section"):
        start_from(spec, "nadie")


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


def test_oleada_en_la_cola_no_esta_limpia() -> None:
    # Borde: la oleada sale de la cola de a uno. Aunque mueran todos los que ya
    # aparecieron, no está limpia mientras quede alguien esperando.
    oleada = tema(
        seccion("intro", 4.0, 0.0, 0.0, ()),
        seccion(
            "drop", 4.0, 0.0, 0.0, (DeckEntry("hexagon", 1.0),), burst=5.0, kind="wave"
        ),
        seccion("respiro", 4.0, 0.0, 0.0, ()),
    )
    balance = replace(
        BALANCE, director=oleada, spawning=replace(SPAWNING, max_per_step=1)
    )
    world = World(balance, random.Random(1), lethal=False, armed=False)
    while world.director.section_index == 0:
        world.update(Vector2())
    salieron = []
    while list(world.queue):
        assert world.director.waiting
        salieron += world.enemies
        world.enemies = []
        world.update(Vector2())
    salieron += world.enemies
    world.enemies = []
    world.update(Vector2())
    assert not world.director.waiting
    assert len(salieron) == 5
    assert all(e.wave == 1 for e in salieron)
