"""Tests de las acciones: lo que un enemigo hace y no es una fuerza (ADR 0021).

Por ahora, la embestida del triángulo: observa, avisa, embiste y se recupera.
"""

import math
import random
from collections.abc import Sequence
from dataclasses import replace
from itertools import groupby

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pygame.math import Vector2

from circlebh.balance import BALANCE, ChargeSpec
from circlebh.pilot import pilot_intent
from circlebh.settings import load_settings
from circlebh.world.actions import (
    ActionContext,
    Charge,
    ChargeState,
    clear_line,
    make_action,
    step_actions,
)
from circlebh.world.clock import STEP
from circlebh.world.enemy import Enemy
from circlebh.world.events import Telegraph
from circlebh.world.game import World
from circlebh.world.patterns import Context

TRIANGLE = BALANCE.enemies["triangle"]
HEXAGON = BALANCE.enemies["hexagon"]
CHARGE = TRIANGLE.actions[0]
assert isinstance(CHARGE, ChargeSpec)

SIN_APARICIONES = replace(
    BALANCE,
    director=replace(
        BALANCE.director,
        sections=(replace(BALANCE.director.sections[0], deck=()),),
    ),
)
"""El balance real con un director que no compra: los tests ponen a mano a los
enemigos."""


def pasos(seconds: float) -> int:
    return round(seconds / STEP)


def contexto(enemies: Sequence[Enemy], player: Vector2 | None = None) -> ActionContext:
    return ActionContext(player_position=player or Vector2(), enemies=enemies)


def embestida(enemy: Enemy) -> Charge:
    action = enemy.actions[0]
    assert isinstance(action, Charge)
    return action


def estados(enemy: Enemy, enemies: Sequence[Enemy], steps: int) -> list[ChargeState]:
    """El estado de la embestida en cada paso, sin mover a nadie."""
    charge = embestida(enemy)
    result = []
    for _ in range(steps):
        charge.update(enemy, contexto(enemies))
        result.append(charge.state)
    return result


def tramos(states: list[ChargeState]) -> list[tuple[ChargeState, int]]:
    """Cada estado seguido, con cuántos pasos duró."""
    return [(state, len(list(run))) for state, run in groupby(states)]


def test_make_action_elige_la_clase_por_su_spec() -> None:
    assert isinstance(make_action(CHARGE), Charge)


def test_cada_enemigo_tiene_su_propia_embestida() -> None:
    a = Enemy(TRIANGLE, Vector2(100, 0))
    b = Enemy(TRIANGLE, Vector2(-100, 0))
    assert a.actions[0] is not b.actions[0]


def test_parte_observando() -> None:
    assert embestida(Enemy(TRIANGLE, Vector2(100, 0))).state is ChargeState.WATCHING


# --- La recta libre ---


def test_recta_sin_nadie_esta_libre() -> None:
    assert clear_line(Vector2(200, 0), Vector2(), 14.0, [])


def test_recta_que_cruza_a_otro_no_esta_libre() -> None:
    otro = Enemy(HEXAGON, Vector2(100, 0))
    assert not clear_line(Vector2(200, 0), Vector2(), 14.0, [otro])


def test_recta_cuenta_el_ancho_del_que_embiste() -> None:
    # Borde: a 30 de la recta, el hexágono (24) no toca la recta, pero el triángulo
    # (14) sí lo tocaría al pasar: 24 + 14 = 38 > 30.
    otro = Enemy(HEXAGON, Vector2(100, 30))
    assert not clear_line(Vector2(200, 0), Vector2(), 14.0, [otro])


def test_recta_que_pasa_al_lado_esta_libre() -> None:
    otro = Enemy(HEXAGON, Vector2(100, 50))
    assert clear_line(Vector2(200, 0), Vector2(), 14.0, [otro])


def test_otro_detras_del_que_embiste_no_tapa() -> None:
    # Negativo: lo que está detrás no corta el camino hacia el jugador.
    otro = Enemy(HEXAGON, Vector2(300, 0))
    assert clear_line(Vector2(200, 0), Vector2(), 14.0, [otro])


# --- Las etapas ---


def test_etapas_en_orden_y_con_su_duracion() -> None:
    triangle = Enemy(TRIANGLE, Vector2(200, 0))
    total = pasos(CHARGE.telegraph + CHARGE.duration + CHARGE.cooldown) + 1
    assert tramos(estados(triangle, [triangle], total)) == [
        (ChargeState.TELEGRAPHING, pasos(CHARGE.telegraph)),
        (ChargeState.CHARGING, pasos(CHARGE.duration)),
        (ChargeState.RECOVERING, pasos(CHARGE.cooldown)),
        (ChargeState.TELEGRAPHING, 1),
    ]


def test_avisar_emite_telegraph_una_vez() -> None:
    triangle = Enemy(TRIANGLE, Vector2(200, 0))
    charge = embestida(triangle)
    events = [
        charge.update(triangle, contexto([triangle]))
        for _ in range(pasos(CHARGE.telegraph))
    ]
    assert events[0] == [Telegraph(triangle)]
    assert all(e == [] for e in events[1:])


def test_no_embiste_sin_recta_libre() -> None:
    triangle = Enemy(TRIANGLE, Vector2(200, 0))
    otro = Enemy(HEXAGON, Vector2(100, 0))
    states = estados(triangle, [triangle, otro], pasos(5))
    assert set(states) == {ChargeState.WATCHING}


def test_no_avisa_desde_fuera_de_la_vista() -> None:
    # Foco 2: más allá de `watch_distance` sigue observando.
    triangle = Enemy(TRIANGLE, Vector2(CHARGE.watch_distance + 1, 0))
    assert set(estados(triangle, [triangle], pasos(5))) == {ChargeState.WATCHING}


def test_avisa_justo_en_watch_distance() -> None:
    # Borde: en el límite exacto, avisa.
    triangle = Enemy(TRIANGLE, Vector2(0, CHARGE.watch_distance))
    assert estados(triangle, [triangle], 1) == [ChargeState.TELEGRAPHING]


@pytest.mark.parametrize("nombre", sorted(BALANCE.enemies))
def test_watch_distance_cabe_en_la_vista(nombre: str) -> None:
    # Coherencia entre balance y configuración (Foco 2): el que avisa se ve entero.
    # Lo más cercano que deja de verse es el borde de arriba o de abajo, a `fov / 2`.
    camera = load_settings().camera
    spec = BALANCE.enemies[nombre]
    for action in spec.actions:
        reach = action.watch_distance + spec.radius
        assert reach <= camera.fov / 2 - Vector2(camera.offset).length()


def test_direccion_fija_durante_el_aviso() -> None:
    # Si el jugador se mueve durante el aviso, embiste hacia donde apuntó al avisar.
    triangle = Enemy(TRIANGLE, Vector2(200, 0))
    charge = embestida(triangle)
    charge.update(triangle, contexto([triangle]))
    for _ in range(pasos(CHARGE.telegraph)):
        charge.update(triangle, contexto([triangle], player=Vector2(0, 150)))
    assert charge.state is ChargeState.CHARGING
    assert charge.velocity == Vector2(-CHARGE.speed, 0)


def test_enemigo_que_cruza_durante_el_aviso_no_lo_detiene() -> None:
    # Borde: la recta se mira solo al avisar. Después, embiste igual y el núcleo duro
    # del otro lo desvía.
    triangle = Enemy(TRIANGLE, Vector2(200, 0))
    charge = embestida(triangle)
    charge.update(triangle, contexto([triangle]))
    otro = Enemy(HEXAGON, Vector2(100, 0))
    for _ in range(pasos(CHARGE.telegraph)):
        charge.update(triangle, contexto([triangle, otro]))
    assert charge.state is ChargeState.CHARGING


def test_tras_recuperarse_vuelve_a_mirar_la_recta() -> None:
    # Negativo: si al terminar la recuperación la recta está tapada, no avisa.
    triangle = Enemy(TRIANGLE, Vector2(200, 0))
    otro = Enemy(HEXAGON, Vector2(100, 0))
    charge = embestida(triangle)
    charge.update(triangle, contexto([triangle]))
    ciclo = pasos(CHARGE.telegraph + CHARGE.duration + CHARGE.cooldown)
    for _ in range(ciclo + pasos(2)):
        charge.update(triangle, contexto([triangle, otro]))
    assert charge.state is ChargeState.WATCHING


# --- El movimiento ---


def test_observando_lo_mueven_sus_patrones() -> None:
    triangle = Enemy(TRIANGLE, Vector2(600, 0))
    charge = embestida(triangle)
    assert not charge.controls_motion
    assert charge.velocity is None


def test_durante_el_aviso_solo_frena() -> None:
    triangle = Enemy(TRIANGLE, Vector2(200, 0))
    triangle.velocity = Vector2(0, 50)
    step_actions([triangle], Vector2())
    assert embestida(triangle).state is ChargeState.TELEGRAPHING
    # Sus patrones tirarían hacia el radio de su órbita: avisando, solo queda el roce.
    a = triangle.acceleration(
        Context(Vector2(), BALANCE.player.charge, BALANCE.charges, [triangle])
    )
    assert tuple(a) == pytest.approx((0.0, -50.0 * TRIANGLE.friction))


def test_embiste_a_speed_por_encima_de_su_tope() -> None:
    world = World(SIN_APARICIONES, random.Random(1), lethal=False, armed=False)
    triangle = Enemy(TRIANGLE, Vector2(200, 0))
    world.enemies = [triangle]
    for _ in range(pasos(CHARGE.telegraph) + 1):
        world.update(Vector2())
    assert embestida(triangle).state is ChargeState.CHARGING
    assert triangle.velocity == Vector2(-CHARGE.speed, 0)
    assert CHARGE.speed > TRIANGLE.speed


def test_world_anota_el_aviso() -> None:
    world = World(SIN_APARICIONES, random.Random(1), lethal=False, armed=False)
    triangle = Enemy(TRIANGLE, Vector2(200, 0))
    world.enemies = [triangle]
    world.update(Vector2())
    assert Telegraph(triangle) in world.events


def test_la_embestida_mata_al_jugador_quieto() -> None:
    world = World(SIN_APARICIONES, random.Random(1))
    world.enemies = [Enemy(TRIANGLE, Vector2(200, 0))]
    for _ in range(pasos(CHARGE.telegraph + CHARGE.duration)):
        world.update(Vector2())
    assert world.game_over


def test_se_esquiva_moviendose_de_lado() -> None:
    # Al avisar, el jugador se mueve hacia +y. Con `telegraph`, le alcanza para salir
    # de la recta.
    world = World(SIN_APARICIONES, random.Random(1))
    world.enemies = [Enemy(TRIANGLE, Vector2(200, 0))]
    for _ in range(pasos(CHARGE.telegraph + CHARGE.duration)):
        world.update(Vector2(0, 1))
    assert not world.game_over


@pytest.mark.parametrize("nombre", sorted(BALANCE.enemies))
def test_la_embestida_no_atraviesa_al_jugador(nombre: str) -> None:
    # Coherencia: como en `test_jugador_no_atraviesa_una_linea_en_un_paso`, pero con la
    # rapidez de la embestida, que pasa el tope del enemigo.
    player = BALANCE.player
    for action in BALANCE.enemies[nombre].actions:
        assert (player.speed + action.speed) * STEP < 2 * player.radius


@pytest.mark.parametrize("nombre", sorted(BALANCE.enemies))
def test_cada_etapa_dura_al_menos_un_paso(nombre: str) -> None:
    for action in BALANCE.enemies[nombre].actions:
        for seconds in (action.telegraph, action.duration, action.cooldown):
            assert pasos(seconds) >= 1


# --- La propiedad (Hypothesis) ---

lugares = st.builds(
    lambda r, a: Vector2(r * math.cos(a), r * math.sin(a)),
    st.floats(min_value=60, max_value=500),
    st.floats(min_value=0, max_value=math.tau),
)


@settings(max_examples=15, deadline=None)
@given(
    triangulos=st.lists(lugares, min_size=1, max_size=3),
    hexagonos=st.lists(lugares, max_size=4),
)
def test_nunca_embiste_sin_avisar(
    triangulos: list[Vector2], hexagonos: list[Vector2]
) -> None:
    # Con el piloto moviéndose, cada embestida va justo después de un aviso completo.
    world = World(SIN_APARICIONES, random.Random(1), lethal=False, armed=False)
    triangles = [Enemy(TRIANGLE, p) for p in triangulos]
    world.enemies = triangles + [Enemy(HEXAGON, p) for p in hexagonos]
    historia: dict[int, list[ChargeState]] = {id(t): [] for t in triangles}
    for _ in range(pasos(8)):
        world.update(pilot_intent(world.steps))
        for t in triangles:
            historia[id(t)].append(embestida(t).state)
    for states in historia.values():
        runs = tramos(states)
        for k, (state, _) in enumerate(runs):
            if state is ChargeState.CHARGING:
                assert k > 0
                assert runs[k - 1] == (
                    ChargeState.TELEGRAPHING,
                    pasos(CHARGE.telegraph),
                )
