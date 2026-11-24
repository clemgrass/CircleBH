"""Tests de la espiral del círculo: primero cruza la masa crítica, se lleva a parte del
grupo al otro lado del jugador, y después lo persigue en espiral, mirando solo su
posición (spec de la 0.2.0, decisiones 53, 54 y 57)."""

import math
import random
from dataclasses import replace

import pytest
from pygame.math import Vector2

from circlebh.balance import BALANCE, CircleShape, CoulombSpec, SpiralSpec
from circlebh.world.actions import (
    ActionContext,
    Spiral,
    SpiralState,
    make_action,
    step_actions,
)
from circlebh.world.clock import STEP
from circlebh.world.critical_mass import heavy_direction
from circlebh.world.enemy import Enemy
from circlebh.world.game import World
from circlebh.world.swarm import lattice, step_swarm

ESPIRAL = SpiralSpec(
    angular_speed=0.8,
    decay=0.19,
    cross_speed=360.0,
    carry_speed=100.0,
    carry_radius=250.0,
)
CIRCULO = replace(
    BALANCE.enemies["hexagon"],
    shape=CircleShape(),
    radius=8.0,
    speed=0.0,
    friction=0.0,
    charge_per_line=60.0,
    patterns=(),
    actions=(ESPIRAL,),
)
"""Un círculo con números propios, para que afinar el balance no cambie estos tests."""
QUIETO = replace(BALANCE.enemies["hexagon"], speed=0.0, patterns=())
"""Un hexágono que no se mueve por sí mismo: el grupo que hay que cruzar."""
SOLO_CARGAS = replace(BALANCE.enemies["hexagon"], patterns=(CoulombSpec(),))
"""Un hexágono que solo siente la ley de cargas: el círculo se lo puede llevar."""


def pasos(seconds: float) -> int:
    return round(seconds / STEP)


def paso(enemies: list[Enemy], jugador: Vector2) -> None:
    """Un paso como el del mundo: primero las acciones, después el enjambre."""
    step_actions(enemies, jugador, random.Random(0), [], BALANCE.enemy_bullet)
    step_swarm(enemies, jugador, Vector2(), BALANCE.player.charge, BALANCE.charges)


def contexto(enemies: list[Enemy], jugador: Vector2) -> ActionContext:
    return ActionContext(jugador, enemies, random.Random(0), [], BALANCE.enemy_bullet)


def espiral_de(enemy: Enemy) -> Spiral:
    (action,) = enemy.actions
    assert isinstance(action, Spiral)
    return action


def centroide(enemies: list[Enemy]) -> Vector2:
    return sum((e.position for e in enemies), Vector2()) / len(enemies)


def test_make_action_elige_la_espiral() -> None:
    assert isinstance(make_action(ESPIRAL), Spiral)


def test_quieto_sigue_la_espiral_logaritmica() -> None:
    circulo = Enemy(CIRCULO, Vector2(800, 0))
    n = pasos(5)
    for _ in range(n):
        paso([circulo], Vector2())
    t = n * STEP
    assert circulo.position.length() == pytest.approx(800 * math.exp(-0.19 * t))
    angulo = math.atan2(circulo.position.y, circulo.position.x)
    assert angulo == pytest.approx(math.remainder(0.8 * t, math.tau))


def test_la_velocidad_no_depende_de_la_del_jugador() -> None:
    # La misma espiral ve al jugador venir corriendo desde x = −100 hasta el origen.
    # En el último paso tiene que dar lo mismo que una que lo ve quieto en el origen.
    circulo = Enemy(CIRCULO, Vector2(300, 0))
    corriendo, quieto = Spiral(ESPIRAL), Spiral(ESPIRAL)
    for x in range(-100, 0, 4):
        corriendo.update(circulo, contexto([circulo], Vector2(x, 0)))
    corriendo.update(circulo, contexto([circulo], Vector2()))
    quieto.update(circulo, contexto([circulo], Vector2()))
    assert corriendo.velocity == quieto.velocity


def etapas_con_grupo(
    segundos: float,
) -> tuple[Enemy, list[Enemy], list[tuple[SpiralState, Vector2, float]]]:
    """Un círculo bajo un grupo quieto de 7 hexágonos en `(300, 0)`, con el jugador quieto
    en el origen. Devuelve, por paso, la etapa, el offset desde el jugador y su carga."""
    grupo = [Enemy(QUIETO, p) for p in lattice(Vector2(300, 0), 7, 50)]
    circulo = Enemy(CIRCULO, Vector2(300, -700))
    enemies = [*grupo, circulo]
    registro = []
    for _ in range(pasos(segundos)):
        paso(enemies, Vector2())
        registro.append(
            (espiral_de(circulo).state, Vector2(circulo.position), circulo.charge)
        )
    return circulo, grupo, registro


def test_al_pasar_el_centroide_empieza_a_cargar() -> None:
    grupo = [Enemy(QUIETO, p) for p in lattice(Vector2(300, 0), 7, 50)]
    circulo = Enemy(CIRCULO, Vector2(300, -700))
    enemies = [*grupo, circulo]
    etapas = []
    for _ in range(pasos(4)):
        centro = centroide(grupo)
        paso(enemies, Vector2())
        etapa = espiral_de(circulo).state
        etapas.append(etapa)
        if etapa is SpiralState.CROSSING:
            # La que impone; la red de seguridad la corrige si choca con un hexágono.
            assert espiral_de(circulo).velocity.length() == pytest.approx(360)
        elif etapas.count(SpiralState.CARRYING) == 1:
            # Empieza a cargar recién cuando ya pasó el centro del grupo.
            assert circulo.position.y >= centro.y - 360 * STEP
    assert etapas[0] is SpiralState.CROSSING
    assert SpiralState.CARRYING in etapas


def test_atrae_al_cruzar_y_al_cargar_y_repele_al_girar() -> None:
    _, _, registro = etapas_con_grupo(15)
    signos = {etapa: carga > 0 for etapa, _, carga in registro}
    assert signos == {
        SpiralState.CROSSING: False,
        SpiralState.CARRYING: False,
        SpiralState.CIRCLING: True,
    }


def test_la_media_vuelta_suma_pi_y_no_se_acerca_al_jugador() -> None:
    _, _, registro = etapas_con_grupo(15)
    cargando = [
        offset for etapa, offset, _ in registro if etapa is SpiralState.CARRYING
    ]
    primero_girando = next(
        offset for etapa, offset, _ in registro if etapa is SpiralState.CIRCLING
    )
    assert min(o.length() for o in cargando) >= 250 - 100 * STEP
    # Del primer offset cargando al primero girando hay media vuelta, más un paso.
    giro = abs(cargando[0].angle_to(primero_girando))
    assert giro == pytest.approx(180, abs=2)


def test_el_cruce_nunca_entra_a_carry_radius() -> None:
    # Un grupo cerca del jugador y unos rezagados lejos al otro lado: el centroide de
    # las posiciones cae cerca del jugador, aunque Σû apunte al grupo. El círculo nace
    # detrás del grupo, como en el mundo, y nunca se acerca a menos de `carry_radius`.
    grupo = [Enemy(QUIETO, p) for p in lattice(Vector2(350, 0), 23, 55)]
    rezagados = [Enemy(QUIETO, Vector2(-1100, 60 * k - 180)) for k in range(7)]
    otros = [*grupo, *rezagados]
    direccion = heavy_direction([e.position for e in otros])
    assert direccion is not None
    circulo = Enemy(CIRCULO, direccion * BALANCE.spawning.distance)
    enemies = [*otros, circulo]
    for _ in range(pasos(10)):
        paso(enemies, Vector2())
        if espiral_de(circulo).state is not SpiralState.CIRCLING:
            assert circulo.position.length() >= 250 - 360 * STEP


def test_se_lleva_parte_del_grupo_al_otro_lado() -> None:
    # 14 hexágonos a la derecha del jugador quieto, y el círculo detrás de ellos. Al
    # terminar la media vuelta, una parte quedó a la izquierda del jugador.
    grupo = [Enemy(SOLO_CARGAS, p) for p in lattice(Vector2(300, 0), 14, 55)]
    circulo = Enemy(CIRCULO, Vector2(1100, 0))
    enemies = [*grupo, circulo]
    assert all(e.position.x > 0 for e in grupo)
    for _ in range(pasos(20)):
        paso(enemies, Vector2())
        if espiral_de(circulo).state is SpiralState.CIRCLING:
            break
    assert espiral_de(circulo).state is SpiralState.CIRCLING
    al_otro_lado = [e for e in grupo if e.position.x < 0]
    assert len(al_otro_lado) >= len(grupo) / 3


def test_sin_nadie_que_cruzar_gira_al_tiro() -> None:
    circulo = Enemy(CIRCULO, Vector2(300, 0))
    paso([circulo], Vector2())
    assert espiral_de(circulo).state is SpiralState.CIRCLING


def test_los_anclados_no_se_cruzan() -> None:
    estrella = Enemy(BALANCE.enemies["star"], Vector2(0, 300))
    circulo = Enemy(CIRCULO, Vector2(300, 0))
    paso([estrella, circulo], Vector2())
    assert espiral_de(circulo).state is SpiralState.CIRCLING


def test_encima_del_jugador_se_queda_quieto() -> None:
    circulo = Enemy(CIRCULO, Vector2())
    for _ in range(10):
        paso([circulo], Vector2())
    assert circulo.position == Vector2()
    assert circulo.velocity == Vector2()


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("decay", 0.0),
        ("decay", -0.1),
        ("angular_speed", 0.0),
        ("cross_speed", 0.0),
        ("carry_speed", 0.0),
        ("carry_radius", 0.0),
    ],
)
def test_rechaza_una_espiral_sin_sentido(campo: str, valor: float) -> None:
    mala = replace(ESPIRAL, **{campo: valor})
    circulo = replace(BALANCE.enemies["circle"], actions=(mala,))
    balance = replace(BALANCE, enemies={**BALANCE.enemies, "circle": circulo})
    with pytest.raises(ValueError, match=r"enemies\.circle\.actions"):
        World(balance, random.Random(0))


def test_el_circulo_del_balance_va_en_espiral() -> None:
    circulo = BALANCE.enemies["circle"]
    assert circulo.patterns == ()
    assert [type(a) for a in circulo.actions] == [SpiralSpec]
