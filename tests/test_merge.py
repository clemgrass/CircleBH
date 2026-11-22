"""Tests de la gran estrella roja: cinco estrellas vivas se juntan en una trampa que te
encierra (spec de la 0.2.0, decisiones 37 a 41).

La gran estrella es el pentagrama `{5/2}`. Su línea más cercana al centro está a
`R·cos(2π/5)`: con `R = 150`, a unas 46 unidades, y el jugador tiene radio 12.
"""

import math
import random
from dataclasses import replace
from itertools import groupby

import pytest
from pygame.math import Vector2

from circlebh.balance import BALANCE, CircleShape
from circlebh.world.enemy import Enemy
from circlebh.world.events import Death
from circlebh.world.game import World
from circlebh.world.merge import MergeState, beat_at

STAR = BALANCE.enemies["star"]
RED_STAR = BALANCE.enemies["red_star"]
MERGE = BALANCE.merge
BPM = BALANCE.director.bpm
QUIETO = Vector2()
SIN_APARICIONES = replace(
    BALANCE,
    director=replace(
        BALANCE.director,
        sections=(replace(BALANCE.director.sections[0], deck=()),),
    ),
)


def mundo_con_estrellas(cuantas: int, *, lethal: bool = True) -> World:
    """El jugador en el origen, sin armas, y `cuantas` estrellas a 300 de él."""
    world = World(SIN_APARICIONES, random.Random(1), lethal=lethal, armed=False)
    world.enemies += [
        Enemy(STAR, 300 * Vector2(math.cos(a), math.sin(a)))
        for a in (math.tau * k / cuantas for k in range(cuantas))
    ]
    return world


def grandes(world: World) -> list[Enemy]:
    return [e for e in world.enemies if e.spec == RED_STAR]


def hasta_que_aparezca(world: World, intent: Vector2 = QUIETO) -> None:
    """Avanza, con `intent`, hasta que la gran estrella aparece."""
    for _ in range(1000):
        world.update(intent)
        if world.merge.state is MergeState.PRESENT:
            return
    raise AssertionError("la gran estrella no apareció")


# --- La fusión ---


def test_cinco_estrellas_se_juntan_sin_death() -> None:
    world = mundo_con_estrellas(5)
    world.update(QUIETO)
    assert world.merge.state is MergeState.WARNING
    assert not [e for e in world.enemies if e.spec == STAR]
    assert not [e for e in world.events if isinstance(e, Death)]


def test_cuatro_estrellas_no_hacen_nada() -> None:
    world = mundo_con_estrellas(4)
    for _ in range(200):
        world.update(QUIETO)
    assert world.merge.state is MergeState.CALM
    assert len([e for e in world.enemies if e.spec == STAR]) == 4


def test_aparece_en_el_cuarto_pulso_donde_esta_el_jugador() -> None:
    # El jugador se mueve durante el aviso: la estrella lo sigue y nace donde está.
    world = mundo_con_estrellas(5)
    world.update(QUIETO)
    primer_pulso = math.floor(beat_at(world.steps, BPM)) + 1
    hasta_que_aparezca(world, Vector2(1, 0))
    assert beat_at(world.steps - 1, BPM) < primer_pulso + MERGE.beats
    assert beat_at(world.steps, BPM) >= primer_pulso + MERGE.beats
    [grande] = grandes(world)
    assert grande.position == world.player.position
    assert world.player.position.x > 0


def test_al_aparecer_ninguna_linea_toca_al_jugador() -> None:
    world = mundo_con_estrellas(5)
    hasta_que_aparezca(world, Vector2(0.6, 0.8))
    [grande] = grandes(world)
    assert not grande.touches(world.player.position, world.player.radius)
    assert not world.game_over


def test_titila_en_la_primera_mitad_de_tres_pulsos() -> None:
    world = mundo_con_estrellas(5)
    visibles = []
    while world.merge.state is not MergeState.PRESENT:
        world.update(QUIETO)
        visibles.append((world.steps, world.merge.blink(world.steps)))
    tramos = [list(grupo) for vista, grupo in groupby(visibles, key=lambda v: v[1])]
    encendidos = [t for t in tramos if t[0][1]]
    assert len(encendidos) == MERGE.beats
    for tramo in encendidos:
        for paso, _ in tramo:
            assert beat_at(paso, BPM) % 1 < 0.5


def test_al_alejarse_se_desvanece_y_vuelve_la_calma() -> None:
    world = mundo_con_estrellas(5, lethal=False)
    hasta_que_aparezca(world)
    [grande] = grandes(world)
    while world.merge.state is MergeState.PRESENT:
        world.update(Vector2(1, 0))
    assert world.merge.state is MergeState.FADING
    assert world.player.position.distance_to(grande.position) > (
        MERGE.release * RED_STAR.radius
    )
    assert grande not in world.enemies
    assert world.merge.fading is grande
    inicio = beat_at(world.steps, BPM)
    while world.merge.state is MergeState.FADING:
        world.update(QUIETO)
    assert world.merge.state is MergeState.CALM
    assert world.merge.fading is None
    assert beat_at(world.steps, BPM) >= inicio + MERGE.fade_beats


def test_rota_entera_vuelve_la_calma() -> None:
    world = mundo_con_estrellas(5)
    hasta_que_aparezca(world)
    [grande] = grandes(world)
    for k in list(grande.edges):
        grande.remove_edge(k)
    world.update(QUIETO)
    assert world.merge.state is MergeState.CALM
    assert not grandes(world)


def test_con_mas_de_cinco_se_quitan_todas() -> None:
    # Borde: si hay 6, no queda una suelta mientras las estrellas están prohibidas.
    world = mundo_con_estrellas(6)
    world.update(QUIETO)
    assert world.merge.state is MergeState.WARNING
    assert not [e for e in world.enemies if e.spec == STAR]


def test_rota_en_el_mismo_paso_en_que_sale_no_se_desvanece() -> None:
    # Borde: el mundo quita a los muertos antes del paso de la fusión, así que gana la
    # muerte. Vuelve la calma sin pasar por el desvanecerse.
    world = mundo_con_estrellas(5, lethal=False)
    hasta_que_aparezca(world)
    [grande] = grandes(world)
    afuera = MERGE.release * RED_STAR.radius + 1
    world.player.position = grande.position + Vector2(afuera, 0)
    for k in list(grande.edges):
        grande.remove_edge(k)
    world.update(QUIETO)
    assert world.merge.state is MergeState.CALM
    assert world.merge.fading is None


def test_una_estrella_con_otro_nombre_tampoco_nace() -> None:
    # La fusión reconoce a sus estrellas por su spec, también al prohibir: un tipo con
    # otro nombre y el mismo spec es una estrella.
    gemela = replace(
        SIN_APARICIONES,
        enemies={**SIN_APARICIONES.enemies, "gemela": STAR},
    )
    world = World(gemela, random.Random(1), armed=False)
    world.enemies += [Enemy(STAR, Vector2(300, 0).rotate(72 * k)) for k in range(5)]
    world.update(QUIETO)
    assert world.merge.state is MergeState.WARNING
    assert not world.merge.allows("gemela")
    assert world.merge.allows("hexagon")


def test_fuera_de_la_calma_no_nacen_estrellas() -> None:
    world = mundo_con_estrellas(5)
    world.update(QUIETO)
    world.queue.push([("star", Vector2(400, 0))])
    world.update(QUIETO)
    assert not [e for e in world.enemies if e.spec == STAR]
    assert not list(world.queue)


def test_en_calma_nacen_estrellas() -> None:
    # Negativo del anterior: sin fusión en curso, la estrella de la cola nace.
    world = mundo_con_estrellas(0)
    world.queue.push([("star", Vector2(400, 0))])
    world.update(QUIETO)
    assert len([e for e in world.enemies if e.spec == STAR]) == 1


# --- El balance ---


def test_el_mundo_rechaza_un_merge_que_tocaria_al_jugador() -> None:
    # Con radio 30, la línea más cercana queda a 30·cos 72° ≈ 9,3, dentro del jugador.
    chica = replace(BALANCE.enemies["red_star"], radius=30.0)
    balance = replace(BALANCE, enemies={**BALANCE.enemies, "red_star": chica})
    with pytest.raises(ValueError, match=r"merge\.into"):
        World(balance, random.Random(0))


def test_el_mundo_rechaza_un_merge_hacia_un_circulo() -> None:
    # La gran estrella es un polígono estrellado: un círculo no tiene línea más
    # cercana al centro que medir.
    redonda = replace(BALANCE.enemies["red_star"], shape=CircleShape())
    balance = replace(BALANCE, enemies={**BALANCE.enemies, "red_star": redonda})
    with pytest.raises(ValueError, match=r"merge\.into"):
        World(balance, random.Random(0))


def test_el_mundo_rechaza_un_merge_de_un_enemigo_que_no_existe() -> None:
    balance = replace(BALANCE, merge=replace(BALANCE.merge, enemy="nadie"))
    with pytest.raises(ValueError, match=r"merge\.enemy"):
        World(balance, random.Random(0))


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("count", 0),
        ("beats", 0),
        ("fade_beats", 0.0),
        ("fade_beats", -1.0),
        ("release", 1.0),
    ],
)
def test_el_mundo_rechaza_numeros_de_merge_sin_sentido(
    campo: str, valor: float
) -> None:
    # Sin pulsos de aviso, la trampa se cierra sin avisar (anti-meta). Con
    # `release ≤ 1`, el jugador saldría sin romper ninguna línea. Con `fade_beats ≤ 0`,
    # apagarse no tiene duración. Con `count < 1`, toda partida empieza encerrada.
    balance = replace(BALANCE, merge=replace(BALANCE.merge, **{campo: valor}))
    with pytest.raises(ValueError, match=rf"merge\.{campo}"):
        World(balance, random.Random(0))


def test_el_balance_real_cumple_el_merge() -> None:
    World(BALANCE, random.Random(0))
