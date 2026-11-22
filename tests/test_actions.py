"""Tests de las acciones: lo que un enemigo hace y no es una fuerza (ADR 0021).

Por ahora, la embestida del triángulo: observa, avisa, embiste y se recupera. Te mira
siempre con una punta, salvo al embestir, y avisa retrocediendo como un resorte
(decisión 30 de la spec de la 0.2.0).
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
from circlebh.world.polygon import vertex

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


def contexto(
    enemies: Sequence[Enemy],
    player: Vector2 | None = None,
    rng: random.Random | None = None,
) -> ActionContext:
    return ActionContext(
        player_position=player or Vector2(),
        enemies=enemies,
        rng=rng or random.Random(1),
        bullets=[],
        bullet_spec=BALANCE.enemy_bullet,
    )


def embestidas(nombre: str) -> list[ChargeSpec]:
    """Las embestidas de un tipo de enemigo. Las otras acciones tienen sus propios tests
    de coherencia."""
    return [a for a in BALANCE.enemies[nombre].actions if isinstance(a, ChargeSpec)]


def triangulo(position: Vector2, **cambios: float) -> Enemy:
    """Un triángulo con su embestida cambiada: `lead_chance=0` nunca se desvía, y
    `lead_chance=1` siempre."""
    return Enemy(replace(TRIANGLE, actions=(replace(CHARGE, **cambios),)), position)


def hasta_soltarse(triangle: Enemy, enemies: Sequence[Enemy], player: Vector2) -> None:
    """Avisa con el jugador en el origen, y se suelta con el jugador en `player`."""
    charge = embestida(triangle)
    charge.update(triangle, contexto(enemies))
    for _ in range(pasos(CHARGE.telegraph)):
        charge.update(triangle, contexto(enemies, player=player))


def punta(enemy: Enemy) -> Vector2:
    """Hacia dónde apunta su primera punta, como vector unitario."""
    tip = vertex(enemy.spec.radius, enemy.spec.shape.vertices, 0).rotate_rad(
        enemy.angle
    )
    return tip.normalize()


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
    for action in embestidas(nombre):
        reach = action.watch_distance + spec.radius
        assert reach <= camera.fov / 2 - Vector2(camera.offset).length()


def test_embiste_hacia_donde_esta_el_jugador_al_soltarse() -> None:
    # Decisión 30: si el jugador se mueve durante el aviso, lo sigue y se suelta hacia
    # donde está en ese momento.
    triangle = triangulo(Vector2(200, 0), lead_chance=0.0)
    objetivo = Vector2(0, 150)
    hasta_soltarse(triangle, [triangle], objetivo)
    charge = embestida(triangle)
    assert charge.state is ChargeState.CHARGING
    assert charge.velocity is not None
    esperado = (objetivo - triangle.position).normalize() * CHARGE.speed
    assert tuple(charge.velocity) == pytest.approx(tuple(esperado))


def test_recta_tapada_al_soltarse_no_embiste() -> None:
    # Negativo: la recta se mira otra vez al soltarse. Si está tapada, vuelve a observar.
    triangle = triangulo(Vector2(200, 0), lead_chance=0.0)
    charge = embestida(triangle)
    charge.update(triangle, contexto([triangle]))
    otro = Enemy(HEXAGON, Vector2(100, 0))
    states = []
    for _ in range(pasos(CHARGE.telegraph) + pasos(1)):
        charge.update(triangle, contexto([triangle, otro]))
        states.append(charge.state)
    assert ChargeState.CHARGING not in states
    assert charge.state is ChargeState.WATCHING


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


def test_durante_el_aviso_retrocede_recoil() -> None:
    # El aviso es un resorte que se comprime: se aleja del jugador justo `recoil`.
    world = World(SIN_APARICIONES, random.Random(1), lethal=False, armed=False)
    triangle = triangulo(Vector2(200, 0), lead_chance=0.0)
    world.enemies = [triangle]
    for _ in range(pasos(CHARGE.telegraph)):
        world.update(Vector2())
    assert embestida(triangle).state is ChargeState.TELEGRAPHING
    assert triangle.position.length() == pytest.approx(200 + CHARGE.recoil)


def test_el_retroceso_frena_al_final_del_aviso() -> None:
    # Como `sen`: rápido al empezar y casi quieto justo antes de soltarse.
    triangle = triangulo(Vector2(200, 0), lead_chance=0.0)
    charge = embestida(triangle)
    rapideces = []
    for _ in range(pasos(CHARGE.telegraph)):
        charge.update(triangle, contexto([triangle]))
        assert charge.velocity is not None
        rapideces.append(charge.velocity.length())
    assert rapideces == sorted(rapideces, reverse=True)
    assert rapideces[-1] < rapideces[0] / 10


def test_al_retroceder_se_aleja_del_jugador() -> None:
    triangle = triangulo(Vector2(0, -200), lead_chance=0.0)
    charge = embestida(triangle)
    charge.update(triangle, contexto([triangle]))
    assert charge.velocity is not None
    assert tuple(charge.velocity.normalize()) == pytest.approx((0.0, -1.0))


def test_embiste_a_speed_por_encima_de_su_tope() -> None:
    world = World(SIN_APARICIONES, random.Random(1), lethal=False, armed=False)
    triangle = triangulo(Vector2(200, 0), lead_chance=0.0)
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
    world.enemies = [triangulo(Vector2(200, 0), lead_chance=0.0)]
    for _ in range(pasos(CHARGE.telegraph + CHARGE.duration)):
        world.update(Vector2())
    assert world.game_over


def test_se_esquiva_moviendose_de_lado() -> None:
    # El jugador se mueve hacia +y sin parar. El triángulo se suelta hacia donde está,
    # pero mientras embiste, el jugador sigue avanzando y sale de la recta.
    world = World(SIN_APARICIONES, random.Random(1))
    world.enemies = [triangulo(Vector2(200, 0), lead_chance=0.0)]
    for _ in range(pasos(CHARGE.telegraph + CHARGE.duration)):
        world.update(Vector2(0, 1))
    assert not world.game_over


@pytest.mark.parametrize("nombre", sorted(BALANCE.enemies))
def test_la_embestida_no_atraviesa_al_jugador(nombre: str) -> None:
    # Coherencia: como en `test_jugador_no_atraviesa_una_linea_en_un_paso`, pero con la
    # rapidez de la embestida, que pasa el tope del enemigo.
    player = BALANCE.player
    for action in embestidas(nombre):
        assert (player.speed + action.speed) * STEP < 2 * player.radius


@pytest.mark.parametrize("nombre", sorted(BALANCE.enemies))
def test_la_mirada_cabe_en_la_cota_del_golpe(nombre: str) -> None:
    # Coherencia (ADR 0027): como `spin`, el giro de la mirada cumple `|ω·dt| ≤ 0,1`,
    # para que `hit_by` siga coincidiendo con los subpasos.
    for action in embestidas(nombre):
        assert action.turn_rate * STEP <= 0.1


@pytest.mark.parametrize("nombre", sorted(BALANCE.enemies))
def test_cada_etapa_dura_al_menos_un_paso(nombre: str) -> None:
    for action in embestidas(nombre):
        for seconds in (action.telegraph, action.duration, action.cooldown):
            assert pasos(seconds) >= 1


# --- La mirada ---


def mirar(triangle: Enemy, seconds: float) -> list[float]:
    """Los ángulos de `triangle` paso a paso, sin moverlo, con el jugador en el origen."""
    angles = []
    for _ in range(pasos(seconds)):
        step_actions([triangle], Vector2(), random.Random(1), [], BALANCE.enemy_bullet)
        triangle.velocity = Vector2()
        triangle.step(Vector2())
        angles.append(triangle.angle)
    return angles


def test_mira_al_jugador_con_una_punta() -> None:
    # Más allá de `watch_distance`, observa: se da vuelta hasta apuntarle.
    triangle = triangulo(Vector2(0, 600))
    mirar(triangle, 1.0)
    assert tuple(punta(triangle)) == pytest.approx((0.0, -1.0))


def test_gira_a_lo_mas_turn_rate() -> None:
    triangle = triangulo(Vector2(0, 600))
    angles = mirar(triangle, 1.0)
    giros = [abs(b - a) for a, b in zip([0.0, *angles], angles, strict=False)]
    assert max(giros) <= CHARGE.turn_rate * STEP + 1e-12
    assert max(giros) == pytest.approx(CHARGE.turn_rate * STEP)


def test_ya_mirandolo_no_gira() -> None:
    # Negativo: con la punta hacia el jugador, el ángulo no cambia.
    triangle = triangulo(Vector2(0, 600))
    mirar(triangle, 1.0)
    antes = triangle.angle
    mirar(triangle, 0.5)
    assert triangle.angle == pytest.approx(antes)


def test_gira_por_el_lado_mas_corto() -> None:
    # Borde: del ángulo 0 (punta arriba) a mirar a +x hay −π/2 o +3π/2: va por −π/2.
    triangle = triangulo(Vector2(-600, 0))
    angles = mirar(triangle, 1.0)
    assert all(b <= a for a, b in zip([0.0, *angles], angles, strict=False))
    assert triangle.angle == pytest.approx(-math.pi / 2)


def test_no_gira_al_embestir() -> None:
    world = World(SIN_APARICIONES, random.Random(1), lethal=False, armed=False)
    triangle = triangulo(Vector2(200, 0), lead_chance=0.0)
    world.enemies = [triangle]
    angles = []
    for _ in range(pasos(CHARGE.telegraph + CHARGE.duration)):
        world.update(Vector2(0, 1))
        if embestida(triangle).state is ChargeState.CHARGING:
            angles.append(triangle.angle)
    assert len(angles) == pasos(CHARGE.duration)
    assert len(set(angles)) == 1


# --- El desvío ---


def test_desvio_va_al_lado_con_menos_enemigos() -> None:
    # Dos enemigos al lado +y del jugador: adivina que escapará hacia −y.
    triangle = triangulo(Vector2(200, 0), lead_chance=1.0)
    otros = [Enemy(HEXAGON, Vector2(-50, 120)), Enemy(HEXAGON, Vector2(50, 150))]
    hasta_soltarse(triangle, [triangle, *otros], Vector2())
    charge = embestida(triangle)
    assert charge.state is ChargeState.CHARGING
    assert charge.velocity is not None
    lead = CHARGE.lead_angle
    esperado = Vector2(-math.cos(lead), -math.sin(lead)) * CHARGE.speed
    assert tuple(charge.velocity) == pytest.approx(tuple(esperado))


def test_desvio_tapado_apunta_directo() -> None:
    # Borde: el desvío iría hacia −y, pero ahí hay otro en la recta: apunta directo.
    triangle = triangulo(Vector2(200, 0), lead_chance=1.0)
    otros = [
        Enemy(HEXAGON, Vector2(-50, 120)),
        Enemy(HEXAGON, Vector2(50, 150)),
        Enemy(HEXAGON, Vector2(57, -44)),
    ]
    hasta_soltarse(triangle, [triangle, *otros], Vector2())
    charge = embestida(triangle)
    assert charge.state is ChargeState.CHARGING
    assert charge.velocity == Vector2(-CHARGE.speed, 0)


def test_sin_suerte_no_se_desvia() -> None:
    # Negativo: con `lead_chance = 0`, apunta directo aunque un lado esté lleno.
    triangle = triangulo(Vector2(200, 0), lead_chance=0.0)
    otros = [Enemy(HEXAGON, Vector2(-50, 120)), Enemy(HEXAGON, Vector2(50, 150))]
    hasta_soltarse(triangle, [triangle, *otros], Vector2())
    assert embestida(triangle).velocity == Vector2(-CHARGE.speed, 0)


@given(
    semilla=st.integers(min_value=0, max_value=2**32),
    chance=st.sampled_from([0.0, 0.1, 1.0]),
    otros=st.lists(
        st.builds(
            Vector2,
            st.floats(min_value=-300, max_value=300),
            st.floats(min_value=40, max_value=300) | st.floats(-300, -40),
        ),
        max_size=5,
    ),
)
def test_al_soltarse_va_directo_o_a_lead_angle(
    semilla: int, chance: float, otros: list[Vector2]
) -> None:
    # Con cualquier azar, una embestida sale hacia el jugador o a `±lead_angle` de él.
    triangle = triangulo(Vector2(200, 0), lead_chance=chance)
    enemies = [triangle, *(Enemy(HEXAGON, p) for p in otros)]
    charge = embestida(triangle)
    rng = random.Random(semilla)
    charge.update(triangle, contexto(enemies, rng=rng))
    for _ in range(pasos(CHARGE.telegraph)):
        charge.update(triangle, contexto(enemies, rng=rng))
    if charge.state is not ChargeState.CHARGING:
        return
    assert charge.velocity is not None
    # `angle_to` da grados entre −360 y 360: se lleva a [−180, 180].
    desvio = abs(math.remainder(Vector2(-1, 0).angle_to(charge.velocity), 360))
    assert desvio == pytest.approx(0, abs=1e-9) or desvio == pytest.approx(
        math.degrees(CHARGE.lead_angle)
    )
    if chance == 0.0:
        assert desvio == pytest.approx(0, abs=1e-9)


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
