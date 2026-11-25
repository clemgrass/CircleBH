"""Tests de la experiencia: el punto que deja cada enemigo, la carga que lo atrae y los
niveles (spec de la 0.3.0, decisiones 3, 12 y 13).

En el hexágono, la arista 1 es la vertical izquierda: una bala que sale del origen hacia
un enemigo en +x la golpea primero.
"""

import math
import random
from collections.abc import Callable
from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pygame.math import Vector2

from circlebh.balance import BALANCE, Balance, EnemySpec, ExperienceSpec
from circlebh.world.actions import steps_of
from circlebh.world.director import start_from
from circlebh.world.enemy import Enemy
from circlebh.world.events import Death, Event, ExperienceDrop, LevelUp
from circlebh.world.experience import Orb, level_cost, step_orbs
from circlebh.world.game import World
from circlebh.world.merge import MergeState
from circlebh.world.player import Player

ESPEC = ExperienceSpec(charge=3.0, friction=3.0, base=10.0, exponent=1.5)
"""Una experiencia de ejemplo: los tests de `step_orbs` no dependen del balance."""

CARGAS = BALANCE.charges

SIN_APARICIONES = replace(
    BALANCE,
    director=replace(
        BALANCE.director,
        sections=(replace(BALANCE.director.sections[0], deck=()),),
    ),
)
"""El balance real con un director que no compra: los tests ponen a mano a los
enemigos."""


def quieto(name: str) -> EnemySpec:
    """El enemigo `name` del balance, sin moverse ni actuar: se queda donde lo ponen."""
    return replace(
        BALANCE.enemies[name], speed=0.0, patterns=(), actions=(), charge_per_line=0.0
    )


def con_una_linea(enemy: Enemy) -> Enemy:
    """Deja a `enemy` con la línea que mira al origen, para que una bala lo mate."""
    if len(enemy.edges) == 1:
        # El círculo: su única línea es curva.
        return enemy
    lines = dict(zip(enemy.edges, enemy.lines(), strict=True))
    frente = min(lines, key=lambda k: ((lines[k][0] + lines[k][1]) / 2).length())
    for k in [k for k in list(enemy.edges) if k != frente]:
        enemy.remove_edge(k)
    return enemy


def avanzar_juntando(
    world: World, listo: Callable[[], bool], pasos: int = 600
) -> list[Event]:
    """Avanza con el jugador quieto hasta que `listo()` sea verdadero, y devuelve todos
    los eventos del camino."""
    todos: list[Event] = []
    for _ in range(pasos):
        world.update(Vector2())
        todos += world.events
        if listo():
            return todos
    raise AssertionError("no pasó en los pasos dados")


def pasos_hasta_recoger(carga: float, distancia: float, pasos: int = 3000) -> int:
    """Cuántos pasos tarda un punto quieto a `distancia` del jugador quieto en llegar a
    él, con el jugador de carga `-carga`."""
    player = Player(BALANCE.player)
    orbs = [Orb(Vector2(distancia, 0), 1.0)]
    for paso in range(1, pasos + 1):
        orbs, recogida = step_orbs(orbs, player, -carga, ESPEC, CARGAS)
        if recogida:
            return paso
    raise AssertionError("no llegó en los pasos dados")


# --- El punto ---


def test_enemigo_deja_su_threat() -> None:
    enemy = con_una_linea(Enemy(quieto("pentagon"), Vector2(200, 0)))
    assert enemy.spec.threat == 2.0
    world = World(SIN_APARICIONES, random.Random(1))
    world.enemies = [enemy]
    eventos = avanzar_juntando(world, lambda: Death(enemy) in world.events)
    [orb] = world.orbs
    assert orb.value == 2.0
    assert ExperienceDrop(orb) in eventos


def test_punto_nace_donde_murio_el_enemigo() -> None:
    # Borde: el punto aparece en la posición del enemigo, no en la del jugador.
    enemy = con_una_linea(Enemy(quieto("hexagon"), Vector2(200, 0)))
    world = World(SIN_APARICIONES, random.Random(1))
    world.enemies = [enemy]
    avanzar_juntando(world, lambda: Death(enemy) in world.events)
    [orb] = world.orbs
    # En su primer paso ya sintió la carga: se movió menos de un paso de jugador.
    assert orb.position.distance_to(Vector2(200, 0)) < 1.0


@given(
    st.floats(min_value=5.0, max_value=60.0), st.floats(min_value=0.0, max_value=60.0)
)
def test_mas_carga_llega_antes(carga: float, extra: float) -> None:
    assert pasos_hasta_recoger(carga + extra, 150.0) <= pasos_hasta_recoger(
        carga, 150.0
    )


def test_punto_encima_del_jugador_se_recoge() -> None:
    # Foco 2 del plan: en el mismo punto no hay dirección, y no se divide por 0.
    player = Player(BALANCE.player)
    orbs, recogida = step_orbs([Orb(Vector2(), 3.0)], player, -14.0, ESPEC, CARGAS)
    assert orbs == []
    assert recogida == 3.0


def test_punto_rapido_que_cruza_al_jugador_se_recoge() -> None:
    # Borde: en un paso va de un lado al otro del jugador sin quedar dentro de él.
    player = Player(BALANCE.player)
    orb = Orb(Vector2(30, 0), 1.0)
    orb.velocity = Vector2(-3600, 0)
    orbs, recogida = step_orbs([orb], player, 0.0, ESPEC, CARGAS)
    assert orbs == []
    assert recogida == 1.0


def test_punto_lejos_no_se_recoge() -> None:
    # Negativo: un paso no alcanza para llegar desde 150.
    player = Player(BALANCE.player)
    orb = Orb(Vector2(150, 0), 1.0)
    orbs, recogida = step_orbs([orb], player, -14.0, ESPEC, CARGAS)
    assert orbs == [orb]
    assert recogida == 0.0


def test_el_punto_no_siente_a_los_enemigos() -> None:
    # Sin carga del jugador, un punto quieto sigue quieto aunque haya enemigos cerca.
    sin_carga = replace(SIN_APARICIONES.player, charge=0.0)
    world = World(
        replace(SIN_APARICIONES, player=sin_carga), random.Random(1), armed=False
    )
    world.enemies = [Enemy(BALANCE.enemies["hexagon"], Vector2(130, 0))]
    world.orbs = [Orb(Vector2(100, 0), 1.0)]
    world.update(Vector2())
    assert world.orbs[0].position == Vector2(100, 0)


# --- Los niveles ---


def test_costo_del_nivel_sigue_su_formula() -> None:
    assert level_cost(1, ESPEC) == 10.0
    assert level_cost(4, ESPEC) == pytest.approx(10.0 * 4**1.5)


def mundo_con_punto(valor: float, balance: Balance = SIN_APARICIONES) -> World:
    """Un mundo sin armas, con un punto de `valor` encima del jugador."""
    world = World(balance, random.Random(1), armed=False)
    world.orbs = [Orb(Vector2(), valor)]
    return world


def test_recoger_suma_experiencia() -> None:
    world = mundo_con_punto(1.0)
    world.update(Vector2())
    assert world.experience == 1.0
    assert world.level == 1
    assert world.pending_levels == 0


def test_sobrante_pasa_al_siguiente_nivel() -> None:
    # Borde: lo que sobra del nivel 1 queda en el nivel 2.
    costo = level_cost(1, BALANCE.experience)
    world = mundo_con_punto(costo + 0.5)
    world.update(Vector2())
    assert world.level == 2
    assert world.experience == pytest.approx(0.5)
    assert world.pending_levels == 1
    assert LevelUp(2) in world.events


def test_dos_niveles_de_una_vez() -> None:
    # Borde: alcanza para dos niveles, y salen dos subidas en el mismo paso.
    spec = BALANCE.experience
    valor = level_cost(1, spec) + level_cost(2, spec)
    world = mundo_con_punto(valor)
    world.update(Vector2())
    assert world.level == 3
    assert world.experience == pytest.approx(0.0)
    assert world.pending_levels == 2
    assert [e for e in world.events if isinstance(e, LevelUp)] == [
        LevelUp(2),
        LevelUp(3),
    ]


def test_rechaza_costo_que_no_es_positivo() -> None:
    # Negativo: con base 0, un nivel no costaría nada y subirían infinitos.
    balance = replace(BALANCE, experience=replace(BALANCE.experience, base=0.0))
    with pytest.raises(ValueError, match=r"experience\.base"):
        World(balance, random.Random(1))


# --- Lo que no deja experiencia (decisión 13 y spec, "La experiencia") ---


def muere_por_bala(name: str) -> tuple[World, list[Event]]:
    enemy = con_una_linea(Enemy(quieto(name), Vector2(200, 0)))
    world = World(SIN_APARICIONES, random.Random(1), lethal=False)
    world.enemies = [enemy]
    return world, avanzar_juntando(world, lambda: Death(enemy) in world.events)


def circulo() -> tuple[World, list[Event]]:
    return muere_por_bala("circle")


def fragmento() -> tuple[World, list[Event]]:
    return muere_por_bala("shard")


def estrellas_fusionadas() -> tuple[World, list[Event]]:
    # Las cinco estrellas se quitan sin morir: su `threat` no cuenta.
    world = World(SIN_APARICIONES, random.Random(1), lethal=False, armed=False)
    world.enemies = [
        Enemy(BALANCE.enemies["star"], 300 * Vector2(math.cos(a), math.sin(a)))
        for a in (math.tau * k / 5 for k in range(5))
    ]
    eventos = avanzar_juntando(world, lambda: world.merge.state is MergeState.WARNING)
    assert world.enemies == []
    return world, eventos


def linea_suelta_absorbida() -> tuple[World, list[Event]]:
    # El médico conserva su acción: es la que dona.
    medico = Enemy(
        replace(BALANCE.enemies["regenerator"], speed=0.0, patterns=()), Vector2(0, 300)
    )
    herido = Enemy(quieto("hexagon"), Vector2(0, 450))
    herido.remove_edge(0)
    world = World(SIN_APARICIONES, random.Random(0), lethal=False, armed=False)
    world.enemies = [medico, herido]
    eventos = avanzar_juntando(world, lambda: bool(world.ghosts), steps_of(20))
    return world, eventos


def muerte_en_el_infinito() -> tuple[World, list[Event]]:
    director = start_from(BALANCE.director, "infinito")
    world = World(replace(BALANCE, director=director), random.Random(1), lethal=False)
    enemy = con_una_linea(Enemy(quieto("hexagon"), Vector2(200, 0)))
    world.enemies = [enemy]
    eventos = avanzar_juntando(world, lambda: Death(enemy) in world.events)
    assert world.director.section.kind == "endless"
    return world, eventos


@pytest.mark.parametrize(
    "caso",
    [
        circulo,
        fragmento,
        estrellas_fusionadas,
        linea_suelta_absorbida,
        muerte_en_el_infinito,
    ],
)
def test_sin_experiencia_de(caso: Callable[[], tuple[World, list[Event]]]) -> None:
    world, eventos = caso()
    assert world.orbs == []
    assert not any(isinstance(e, ExperienceDrop) for e in eventos)


def test_al_entrar_al_infinito_se_van_los_puntos() -> None:
    # El borde queda quieto en el infinito (decisión 13): los puntos que quedaban se van
    # sin recogerse.
    previa = replace(BALANCE.director.sections[0], bars=1.0, deck=())
    infinito = replace(BALANCE.director.sections[-1], kind="endless")
    director = replace(BALANCE.director, sections=(previa, infinito))
    world = World(
        replace(BALANCE, director=director), random.Random(1), lethal=False, armed=False
    )
    world.orbs = [Orb(Vector2(500, 0), 5.0)]
    avanzar_juntando(world, lambda: world.director.section.kind == "endless", 600)
    assert world.orbs == []
    assert world.experience == 0.0
