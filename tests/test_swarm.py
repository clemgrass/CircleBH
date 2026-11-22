"""Tests del enjambre: el paso simultáneo, la red de seguridad y la red triangular
(ADR 0021)."""

import math
from dataclasses import replace
from itertools import combinations

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st
from pygame.math import Vector2

from circlebh.balance import BALANCE, CoulombSpec
from circlebh.world.enemy import Enemy
from circlebh.world.swarm import lattice, separate, step_swarm

HEXAGON = BALANCE.enemies["hexagon"]
SOLO_COULOMB = replace(HEXAGON, patterns=(CoulombSpec(),))
QUIETO = replace(HEXAGON, speed=0.0, patterns=())
"""No se mueve por sí mismo: solo la red de seguridad lo corre."""
CONTACTO = 2 * HEXAGON.radius
CELDA = BALANCE.charges.cutoff


def paso(enemies: list[Enemy], player_charge: float = 0.0) -> int:
    return step_swarm(enemies, Vector2(), player_charge, BALANCE.charges)


# --- El paso simultáneo ---


def test_dos_sueltos_se_alejan() -> None:
    a, b = Enemy(SOLO_COULOMB, Vector2(0, 0)), Enemy(SOLO_COULOMB, Vector2(80, 0))
    for _ in range(30):
        paso([a, b])
    assert a.position.distance_to(b.position) > 80


coordenada = st.floats(min_value=-150, max_value=150)


@given(
    puntos=st.lists(st.tuples(coordenada, coordenada), min_size=2, max_size=12),
    data=st.data(),
)
def test_orden_de_la_lista_no_importa(
    puntos: list[tuple[float, float]], data: st.DataObject
) -> None:
    # Dos en el mismo punto exacto quedan fuera: ahí la dirección fija sí depende del
    # orden (spec, "La red de seguridad").
    posiciones = [Vector2(p) for p in puntos]
    for p, q in combinations(posiciones, 2):
        assume(p.distance_to(q) > 1e-3)
    originales = [Enemy(HEXAGON, p) for p in posiciones]
    copias = [Enemy(HEXAGON, p) for p in posiciones]
    orden = data.draw(st.permutations(range(len(copias))))
    paso(originales, BALANCE.player.charge)
    paso([copias[i] for i in orden], BALANCE.player.charge)
    for original, copia in zip(originales, copias, strict=True):
        assert tuple(copia.position) == pytest.approx(
            tuple(original.position), abs=1e-9
        )


def test_solo_entran_los_vivos() -> None:
    # Foco de revisión 1: un muerto tiene masa 0; si entrara, dividiría por cero.
    vivo = Enemy(HEXAGON, Vector2(100, 0))
    muerto = Enemy(HEXAGON, Vector2(150, 0))
    for k in range(HEXAGON.shape.line_count):
        muerto.remove_edge(k)
    paso([vivo, muerto])
    assert muerto.position == Vector2(150, 0)


# --- La red de seguridad ---


def test_superpuestos_quedan_tangentes_y_sin_acercarse() -> None:
    a, b = Enemy(QUIETO, Vector2(0, 0)), Enemy(QUIETO, Vector2(30, 0))
    a.velocity, b.velocity = Vector2(10, 0), Vector2(-10, 0)
    assert separate([a, b], CELDA) == 1
    assert a.position.distance_to(b.position) == pytest.approx(CONTACTO)
    assert (b.velocity - a.velocity).x >= 0


def test_misma_posicion_no_divide_por_cero() -> None:
    a, b = Enemy(QUIETO, Vector2(5, 5)), Enemy(QUIETO, Vector2(5, 5))
    separate([a, b], CELDA)
    assert a.position.distance_to(b.position) == pytest.approx(CONTACTO)
    assert all(math.isfinite(c) for c in (*a.position, *b.position))


@given(
    cuerpos=st.lists(
        st.tuples(
            coordenada,
            coordenada,
            st.sampled_from([HEXAGON.radius, 10.0, 200.0]),
        ),
        max_size=20,
    )
)
def test_corrige_los_mismos_pares_que_la_fuerza_bruta(
    cuerpos: list[tuple[float, float, float]],
) -> None:
    # Con tamaños mezclados, como un jefe entre hexágonos: un cuerpo más grande que la
    # celda no puede quedar fuera de la red de seguridad.
    enemies = [Enemy(replace(QUIETO, radius=r), Vector2(x, y)) for x, y, r in cuerpos]
    superpuestos = sum(
        1
        for a, b in combinations(enemies, 2)
        if a.position.distance_to(b.position) < a.radius + b.radius
    )
    assert separate(enemies, CELDA) == superpuestos


def test_separados_no_se_tocan() -> None:
    a, b = Enemy(QUIETO, Vector2(0, 0)), Enemy(QUIETO, Vector2(100, 0))
    assert separate([a, b], CELDA) == 0
    assert (a.position, b.position) == (Vector2(0, 0), Vector2(100, 0))


def test_la_bala_golpea_al_que_movio_el_empujon() -> None:
    # A estaba en 115 al empezar el paso, y la red de seguridad lo corre a 105. Una bala
    # corta, de 88 a 89, solo cruza su arista izquierda si el tramo se mide de
    # `previous` (115) a `position` (105): de −27 a −16, con la arista en −20,8.
    a = Enemy(QUIETO, Vector2(115, 0))
    b = Enemy(QUIETO, Vector2(143, 0))
    separate([a, b], CELDA)
    assert a.position.x == pytest.approx(105)
    assert a.previous == Vector2(115, 0)
    assert a.hit_by(Vector2(88, 0), Vector2(89, 0)) is not None


# --- El anclado ---

ANCLADO = replace(QUIETO, radius=40.0, anchored=True)
"""Como la estrella: nada lo mueve, ni las fuerzas ni la red de seguridad."""


def test_red_de_seguridad_no_mueve_al_anclado() -> None:
    estrella = Enemy(ANCLADO, Vector2(0, 0))
    hexagono = Enemy(QUIETO, Vector2(50, 0))
    assert separate([estrella, hexagono], CELDA) == 1
    assert estrella.position == Vector2(0, 0)
    assert hexagono.position.x == pytest.approx(ANCLADO.radius + HEXAGON.radius)


def test_choque_contra_anclado_le_quita_toda_la_velocidad_de_acercamiento() -> None:
    estrella = Enemy(ANCLADO, Vector2(0, 0))
    hexagono = Enemy(QUIETO, Vector2(50, 0))
    hexagono.velocity = Vector2(-30, 12)
    separate([estrella, hexagono], CELDA)
    assert hexagono.velocity.x == pytest.approx(0)
    assert hexagono.velocity.y == pytest.approx(12)
    assert estrella.velocity == Vector2()


def test_dos_anclados_encimados_quedan_donde_estan() -> None:
    a, b = Enemy(ANCLADO, Vector2(0, 0)), Enemy(ANCLADO, Vector2(30, 0))
    assert separate([a, b], CELDA) == 0
    assert (a.position, b.position) == (Vector2(0, 0), Vector2(30, 0))


def test_anclado_no_se_mueve_con_fuerzas() -> None:
    # Con carga y patrones, sus vecinos lo empujan por Coulomb y por el núcleo duro.
    cargado = replace(SOLO_COULOMB, radius=40.0, anchored=True)
    estrella = Enemy(cargado, Vector2(0, 0))
    vecinos = [Enemy(SOLO_COULOMB, p) for p in lattice(Vector2(20, 0), 6, 55)]
    for _ in range(60):
        paso([estrella, *vecinos], player_charge=-14.0)
    assert estrella.position == Vector2(0, 0)
    assert estrella.velocity == Vector2()


# --- La red triangular ---


def test_lattice_sin_superponerse() -> None:
    puntos = lattice(Vector2(), 300, 60)
    assert len(puntos) == 300
    assert Vector2() not in puntos
    assert min(p.distance_to(q) for p, q in combinations(puntos, 2)) >= 60 - 1e-9


def test_lattice_empieza_por_los_mas_cercanos() -> None:
    # Los 6 vecinos del centro, a una distancia `spacing`, van primero.
    puntos = lattice(Vector2(10, 10), 7, 60)
    assert [p.distance_to(Vector2(10, 10)) for p in puntos[:6]] == pytest.approx(
        [60] * 6
    )
    assert puntos[6].distance_to(Vector2(10, 10)) > 60
