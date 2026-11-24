"""Tests del regenerador: un médico que se cura y cura a otros (spec de la 0.2.0,
"El regenerador (#62)", decisiones 65 a 69).

Se cura a sí mismo: recupera la línea que le falta de índice menor cada `interval`, y
un golpe reinicia la cuenta.
"""

import math
import random
from collections.abc import Sequence
from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pygame.math import Vector2

from circlebh.balance import BALANCE, EnemySpec, RegenerateSpec, StarPolygonShape
from circlebh.world.actions import ActionContext, Regenerate, step_actions, steps_of
from circlebh.world.enemy import Enemy
from circlebh.world.events import Event, Regrow


def regenerador() -> EnemySpec:
    return BALANCE.enemies["regenerator"]


def intervalo() -> int:
    """Los pasos de la cuenta del médico."""
    [accion] = regenerador().actions
    assert isinstance(accion, RegenerateSpec)
    return steps_of(accion.interval)


def medico(posicion: Vector2 | None = None, quitar: Sequence[int] = ()) -> Enemy:
    """Un médico en `posicion` (el origen si no se da), sin las líneas `quitar`."""
    enemy = Enemy(regenerador(), posicion or Vector2())
    for k in quitar:
        enemy.remove_edge(k)
    return enemy


def avanzar(enemies: list[Enemy], steps: int, desde: int = 0) -> list[Event]:
    """`steps` pasos de las acciones, contando los pasos del mundo desde `desde`."""
    events: list[Event] = []
    for n in range(desde, desde + steps):
        events += step_actions(
            enemies, Vector2(), random.Random(1), [], BALANCE.enemy_bullet, n
        )
    return events


def test_recupera_una_linea_cada_intervalo() -> None:
    enemy = medico(quitar=[1, 3])
    events = avanzar([enemy], intervalo())
    assert events == [Regrow(enemy, 1)]
    assert enemy.edges == [k for k in range(enemy.spec.shape.line_count) if k != 3]
    events = avanzar([enemy], intervalo(), desde=intervalo())
    assert events == [Regrow(enemy, 3)]
    assert enemy.edges == list(range(enemy.spec.shape.line_count))


def test_golpe_reinicia_la_cuenta() -> None:
    # Borde: golpeado una y otra vez antes de que se cumpla la cuenta, nunca recupera.
    enemy = medico(quitar=[0])
    events: list[Event] = []
    for golpe in (1, 2, 3):
        events += avanzar([enemy], intervalo() - 1)
        enemy.remove_edge(golpe)
    events += avanzar([enemy], intervalo() - 1)
    assert events == []
    assert 0 not in enemy.edges


def test_nunca_pasa_de_sus_lados() -> None:
    enemy = medico()
    lados = enemy.spec.shape.line_count
    for n in range(steps_of(10)):
        assert avanzar([enemy], 1, desde=n) == []
        assert len(enemy.edges) == lados


def test_muerto_no_se_regenera() -> None:
    # Negativo: sin líneas está muerto, y no vuelve.
    enemy = medico(quitar=range(regenerador().shape.line_count))
    [accion] = enemy.actions
    assert isinstance(accion, Regenerate)
    context = ActionContext(
        Vector2(), [], random.Random(1), [], BALANCE.enemy_bullet, steps=0
    )
    for _ in range(3 * intervalo()):
        assert accion.update(enemy, context) == []
    assert enemy.edges == []


def figuras_con_lineas() -> list[EnemySpec]:
    """Los enemigos del balance hechos de segmentos, con y sin giro."""
    return [
        spec
        for spec in BALANCE.enemies.values()
        if isinstance(spec.shape, StarPolygonShape)
    ]


@given(
    indice=st.integers(0, len(figuras_con_lineas()) - 1),
    angulo=st.floats(-math.pi, math.pi),
    antes=st.floats(-math.pi, math.pi),
    linea=st.integers(0, 99),
    velocidad=st.builds(Vector2, st.floats(-200, 200), st.floats(-200, 200)),
)
def test_restore_edge_deshace_remove_edge(
    indice: int, angulo: float, antes: float, linea: int, velocidad: Vector2
) -> None:
    # Con giro, recibir una línea recentra al revés que perderla: la figura no se mueve
    # en el plano, ni con la pose de antes del paso (L2 del ADR 0027).
    spec = figuras_con_lineas()[indice]
    enemy = Enemy(replace(spec, spin=spec.spin or 1.5), Vector2(40, -30))
    enemy.angle, enemy.previous_angle, enemy.velocity = angulo, antes, velocidad
    k = linea % spec.shape.line_count
    lineas, v, radio = enemy.lines(), Vector2(enemy.velocity), enemy.radius
    enemy.remove_edge(k)
    enemy.restore_edge(k, 0)
    assert enemy.edges == sorted(enemy.edges)
    assert len(enemy.edges) == spec.shape.line_count
    for (a, b), (c, d) in zip(enemy.lines(), lineas, strict=True):
        assert a.distance_to(c) < 1e-6
        assert b.distance_to(d) < 1e-6
    assert enemy.velocity.distance_to(v) < 1e-6
    assert enemy.radius == pytest.approx(radio)


def test_restore_edge_de_linea_presente_falla() -> None:
    # Negativo: una línea que ya está no se recupera dos veces.
    enemy = medico(quitar=[2])
    with pytest.raises(ValueError, match="restore_edge"):
        enemy.restore_edge(0, 0)
    with pytest.raises(ValueError, match="restore_edge"):
        enemy.restore_edge(regenerador().shape.line_count, 0)


def test_restored_at_guarda_el_paso() -> None:
    enemy = medico(quitar=[2])
    enemy.restore_edge(2, 37)
    assert enemy.restored_at == {2: 37}


def test_herido_es_vivo_y_con_lineas_menos() -> None:
    assert not medico().wounded
    assert medico(quitar=[0]).wounded
    assert not medico(quitar=range(regenerador().shape.line_count)).wounded
