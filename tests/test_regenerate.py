"""Tests del regenerador: un médico que se cura y cura a otros (spec de la 0.2.0,
"El regenerador (#62)", decisiones 65 a 69).

Se cura a sí mismo: recupera la línea que le falta de índice menor cada `interval`, y
un golpe reinicia la cuenta. Entero, dona una línea al herido más cercano: la línea
suelta viaja hasta él, y un herido que la toca la absorbe.
"""

import math
import random
from collections.abc import Sequence
from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pygame.math import Vector2

from circlebh.balance import (
    BALANCE,
    EnemySpec,
    OrbitSpec,
    RegenerateSpec,
    StarPolygonShape,
)
from circlebh.pilot import pilot_intent
from circlebh.world.actions import (
    ActionContext,
    Deliver,
    Regenerate,
    step_actions,
    steps_of,
)
from circlebh.world.clock import STEP
from circlebh.world.enemy import Enemy
from circlebh.world.events import Death, Donate, Event, Regrow
from circlebh.world.game import World
from circlebh.world.player import Player
from circlebh.world.regrowth import absorb
from circlebh.world.swarm import lattice, step_swarm


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


# --- 13.B: el médico dona, y la línea suelta (decisiones 67 a 69) ---

SIN_APARICIONES = replace(
    BALANCE,
    director=replace(
        BALANCE.director,
        sections=(replace(BALANCE.director.sections[0], deck=()),),
    ),
)
"""El balance real con un director que no compra: los tests ponen a mano a los
enemigos."""


def quieto(spec: EnemySpec) -> EnemySpec:
    """`spec` sin rapidez ni patrones: no se mueve solo, y así el test no depende de
    hacia dónde lo llevarían."""
    return replace(spec, speed=0.0, patterns=())


def hexagono(posicion: Vector2, quitar: Sequence[int] = ()) -> Enemy:
    enemy = Enemy(quieto(BALANCE.enemies["hexagon"]), posicion)
    for k in quitar:
        enemy.remove_edge(k)
    return enemy


def suelta(
    posicion: Vector2,
    paciente: Enemy | None = None,
    angulo: float = 0.0,
    radio: float | None = None,
) -> Enemy:
    """Una línea suelta en `posicion`, con su `angulo` y yendo a `paciente`."""
    spec = BALANCE.enemies["stray_line"]
    enemy = Enemy(replace(spec, radius=radio or spec.radius), posicion)
    enemy.angle = enemy.previous_angle = angulo
    [entrega] = enemy.actions
    assert isinstance(entrega, Deliver)
    entrega.patient = paciente
    return enemy


def encima(enemy: Enemy, lado: int = 1) -> Vector2:
    """Dónde poner una línea suelta para que toque a `enemy` por el lado `lado` (±1 en
    x): montada 4 unidades sobre su envolvente, como queda tras el empuje de su
    entrega. Justo tangente, su Coulomb la alejaría en el mismo paso."""
    return enemy.position + Vector2(lado * (enemy.radius + 12 - 4), 0)


def mundo(*enemies: Enemy, lethal: bool = False) -> World:
    world = World(SIN_APARICIONES, random.Random(0), lethal=lethal, armed=False)
    world.enemies = list(enemies)
    return world


def donaciones(events: Sequence[Event]) -> list[Donate]:
    return [e for e in events if isinstance(e, Donate)]


def test_entero_dona_al_herido_mas_cercano() -> None:
    enemy = medico()
    cerca = hexagono(Vector2(150, 0), quitar=[0])
    lejos = hexagono(Vector2(300, 0), quitar=[0])
    events = avanzar([enemy, lejos, cerca], intervalo())
    [donacion] = donaciones(events)
    assert donacion.enemy is enemy
    assert donacion.patient is cerca
    assert len(enemy.edges) == enemy.spec.shape.line_count - 1


def test_dona_la_linea_mas_cercana_al_herido() -> None:
    enemy = Enemy(quieto(regenerador()), Vector2(0, 300))
    herido = hexagono(Vector2(0, 450), quitar=[0])
    lineas = dict(zip(enemy.edges, enemy.lines(), strict=True))
    esperada = min(
        lineas,
        key=lambda k: ((lineas[k][0] + lineas[k][1]) / 2).distance_to(herido.position),
    )
    world = mundo(enemy, herido)
    for _ in range(intervalo()):
        world.update(Vector2())
    [donacion] = donaciones(world.events)
    assert donacion.edge == esperada
    assert esperada not in enemy.edges
    [linea] = [e for e in world.enemies if e.stray]
    a, b = lineas[esperada]
    assert linea.position.distance_to((a + b) / 2) < 1e-6
    # Nace con el largo y la orientación de la línea donada, en cualquier sentido.
    [(c, d)] = linea.lines()
    directo = max(c.distance_to(a), d.distance_to(b))
    cruzado = max(c.distance_to(b), d.distance_to(a))
    assert min(directo, cruzado) < 1e-6


def test_entero_sin_heridos_no_dona() -> None:
    # Negativo: ni la gran estrella herida ni una línea suelta cuentan como heridos.
    enemy = medico()
    estrella = Enemy(BALANCE.enemies["red_star"], Vector2(0, 400))
    estrella.remove_edge(0)
    otros = [hexagono(Vector2(150, 0)), estrella, suelta(Vector2(-150, 0))]
    assert donaciones(avanzar([enemy, *otros], steps_of(10))) == []


def test_donar_no_cuenta_como_golpe() -> None:
    enemy = medico()
    herido = hexagono(Vector2(150, 0), quitar=[0])
    events = avanzar([enemy, herido], intervalo())
    [donacion] = donaciones(events)
    events = avanzar([enemy, herido], intervalo(), desde=intervalo())
    assert Regrow(enemy, donacion.edge) in events
    assert len(enemy.edges) == enemy.spec.shape.line_count


def test_el_medico_no_absorbe_la_linea_que_va_a_otro() -> None:
    # Al donar queda herido y tocando su línea: no la recupera de vuelta.
    enemy = Enemy(quieto(regenerador()), Vector2(0, 300))
    herido = hexagono(Vector2(0, 450), quitar=[0])
    world = mundo(enemy, herido)
    for _ in range(intervalo() + 1):
        world.update(Vector2())
    assert [e for e in world.enemies if e.stray]
    assert len(enemy.edges) == enemy.spec.shape.line_count - 1


def test_linea_suelta_va_a_su_paciente() -> None:
    herido = hexagono(Vector2(300, 0), quitar=[0])
    linea = suelta(Vector2(300, 250), herido)
    world = mundo(herido, linea)
    distancia = linea.position.distance_to(herido.position)
    for _ in range(steps_of(3)):
        world.update(Vector2())
        if linea not in world.enemies:
            break
        nueva = linea.position.distance_to(herido.position)
        assert nueva < distancia
        distancia = nueva
    assert linea not in world.enemies
    assert 0 in herido.edges


def test_herido_absorbe_linea_suelta() -> None:
    herido = hexagono(Vector2(300, 0), quitar=[0, 2])
    linea = suelta(encima(herido))
    world = mundo(herido, linea)
    world.update(Vector2())
    assert 0 in herido.edges
    assert 2 not in herido.edges
    assert linea not in world.enemies
    assert Regrow(herido, 0) in world.events
    assert not any(isinstance(e, Death) for e in world.events)
    assert len(world.ghosts) == 1


def test_dos_heridos_absorbe_el_mas_antiguo() -> None:
    # Borde: los dos la tocan en el mismo paso; solo el primero de la lista la absorbe.
    antiguo = hexagono(Vector2(260, 0), quitar=[0])
    nuevo = hexagono(Vector2(340, 0), quitar=[0])
    linea = suelta(Vector2(300, 0), radio=20.0)
    world = mundo(antiguo, nuevo, linea)
    world.update(Vector2())
    assert 0 in antiguo.edges
    assert 0 not in nuevo.edges
    assert linea not in world.enemies


def test_entero_no_absorbe() -> None:
    # Negativo: un enemigo entero choca con la línea suelta y nada más.
    entero = hexagono(Vector2(300, 0))
    linea = suelta(encima(entero))
    world = mundo(entero, linea)
    for _ in range(30):
        world.update(Vector2())
    assert linea in world.enemies
    assert len(entero.edges) == entero.spec.shape.line_count


def test_segunda_linea_no_pasa_de_los_lados() -> None:
    # Borde: dos líneas sueltas para un herido al que le falta una sola.
    herido = hexagono(Vector2(300, 0), quitar=[0])
    una = suelta(encima(herido))
    otra = suelta(encima(herido, -1))
    world = mundo(herido, una, otra)
    world.update(Vector2())
    assert len(herido.edges) == herido.spec.shape.line_count
    assert una not in world.enemies
    assert otra in world.enemies


def test_muerto_en_el_paso_no_absorbe() -> None:
    # Un herido sin líneas no absorbe: las balas van antes que la absorción.
    herido = hexagono(Vector2(300, 0), quitar=[0])
    linea = suelta(encima(herido))
    for k in list(herido.edges):
        herido.remove_edge(k)
    assert absorb([herido, linea], 0) == ([], [])


def test_sin_paciente_frena_y_queda_quieta() -> None:
    herido = hexagono(Vector2(300, 0), quitar=[0])
    linea = suelta(Vector2(300, 400), herido)
    world = mundo(herido, linea)
    for _ in range(10):
        world.update(Vector2())
    world.enemies.remove(herido)
    for k in list(herido.edges):
        herido.remove_edge(k)
    for _ in range(steps_of(5)):
        world.update(Vector2())
    assert linea in world.enemies
    assert linea.velocity.length() < 1


def test_linea_suelta_mata_al_jugador() -> None:
    linea = suelta(Vector2(0, 0))
    world = mundo(linea, lethal=True)
    world.update(Vector2())
    assert world.game_over


def test_bala_le_quita_la_linea_suelta() -> None:
    linea = suelta(Vector2(100, 0))
    hit = linea.hit_by(Vector2(100, -50), Vector2(100, 50))
    assert hit is not None
    assert hit[1] == 0


def test_stray_desconocido_se_rechaza() -> None:
    # Negativo: el médico tiene que soltar un segmento que exista y que tenga deliver.
    malo = replace(
        regenerador(),
        actions=(RegenerateSpec(interval=2.0, stray="nada"),),
    )
    balance = replace(BALANCE, enemies={**BALANCE.enemies, "regenerator": malo})
    with pytest.raises(ValueError, match=r"enemies\.regenerator\.actions"):
        World(balance, random.Random(0))
    sin_entrega = replace(
        regenerador(),
        actions=(RegenerateSpec(interval=2.0, stray="hexagon"),),
    )
    balance = replace(BALANCE, enemies={**BALANCE.enemies, "regenerator": sin_entrega})
    with pytest.raises(ValueError, match=r"enemies\.regenerator\.actions"):
        World(balance, random.Random(0))


# --- 13.C: apoya desde lejos (decisión 65) ---


def test_medico_se_mantiene_lejos() -> None:
    # Con 16 hexágonos detrás y el jugador dando vueltas como el piloto, en los últimos
    # 10 s de 30: lejos del jugador, a la distancia de su órbita, y fuera del enjambre.
    [orbita] = [p for p in regenerador().patterns if isinstance(p, OrbitSpec)]
    jugador = Player(BALANCE.player)
    enemy = Enemy(regenerador(), Vector2(-300, 80))
    hexagonos = [
        Enemy(BALANCE.enemies["hexagon"], p)
        for p in lattice(Vector2(-300, 0), 17, 70)[1:]
    ]
    al_jugador, al_enjambre = [], []
    for k in range(steps_of(30)):
        jugador.step(pilot_intent(k))
        velocidad = (jugador.position - jugador.previous) / STEP
        step_swarm(
            [enemy, *hexagonos],
            jugador.position,
            velocidad,
            BALANCE.player.charge,
            BALANCE.charges,
        )
        if k >= steps_of(20):
            al_jugador.append(enemy.position.distance_to(jugador.position))
            al_enjambre.append(
                min(h.position.distance_to(enemy.position) for h in hexagonos)
            )
    assert sum(al_jugador) / len(al_jugador) >= 0.8 * orbita.radius
    assert sum(al_enjambre) / len(al_enjambre) >= 120
