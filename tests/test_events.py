"""Tests de los eventos del mundo: lo que pasó en cada paso, para la música (ADR 0022)
y para medir el balance (ADR 0030).

En el hexágono, la arista 1 es la vertical izquierda: una bala que sale del origen hacia
un enemigo en +x la golpea primero.
"""

import math
import random
from collections.abc import Callable
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from typing import Literal

from pygame.math import Vector2

from circlebh.balance import (
    BALANCE,
    DeckEntry,
    EnemySpec,
    SectionSpec,
    StarPolygonShape,
)
from circlebh.pilot import pilot_intent
from circlebh.world import events as events_module
from circlebh.world.actions import steps_of
from circlebh.world.clock import STEP
from circlebh.world.director import start_from
from circlebh.world.enemy import Enemy
from circlebh.world.enemy_bullets import EnemyBullet
from circlebh.world.events import (
    Death,
    Donate,
    Event,
    Hit,
    PlayerDeath,
    SectionStart,
    Shot,
    Spawn,
)
from circlebh.world.game import World
from circlebh.world.merge import MergeState
from circlebh.world.spawning import Queued

# Sin patrones ni carga: el enemigo se queda donde lo ponen.
QUIETO = EnemySpec(
    shape=StarPolygonShape(vertices=6, steps=(1,)),
    radius=24.0,
    speed=120.0,
    friction=0.0,
    spin=0.0,
    anchored=False,
    phantom=False,
    solitary=False,
    charge_per_line=0.0,
    mass_per_line=1.0,
    patterns=(),
    threat=1.0,
    actions=(),
    split_into="",
)


def mundo_con(enemy: Enemy, *, armed: bool = True, lethal: bool = True) -> World:
    world = World(BALANCE, random.Random(1), armed=armed, lethal=lethal)
    world.enemies = [enemy]
    return world


def avanzar_hasta(world: World, listo: Callable[[], bool], pasos: int = 300) -> None:
    """Avanza con el jugador quieto hasta que `listo()` sea verdadero."""
    for _ in range(pasos):
        world.update(Vector2())
        if listo():
            return
    raise AssertionError("no pasó en los pasos dados")


def sin_inicios(events: list[Event]) -> list[Event]:
    """Los eventos sin `SectionStart`: el primer paso de toda partida trae el de la
    intro."""
    return [e for e in events if not isinstance(e, SectionStart)]


def test_disparo_deja_shot() -> None:
    world = mundo_con(Enemy(QUIETO, Vector2(100, 0)))
    world.update(Vector2())
    assert sin_inicios(world.events) == [Shot(world.weapons[0])]


def test_bala_que_golpea_deja_hit_con_la_arista() -> None:
    enemy = Enemy(QUIETO, Vector2(100, 0))
    world = mundo_con(enemy)
    avanzar_hasta(world, lambda: len(enemy.edges) < 6)
    [perdida] = set(range(6)) - set(enemy.edges)
    assert perdida == 1
    assert Hit(enemy, 1) in world.events


def test_ultima_linea_deja_hit_y_death_en_el_mismo_paso() -> None:
    enemy = Enemy(QUIETO, Vector2(100, 0))
    enemy.edges = [1]
    world = mundo_con(enemy)
    avanzar_hasta(world, lambda: enemy not in world.enemies)
    assert Hit(enemy, 1) in world.events
    assert Death(enemy) in world.events


def test_events_se_vacia_en_el_paso_siguiente() -> None:
    world = mundo_con(Enemy(QUIETO, Vector2(100, 0)))
    world.update(Vector2())
    assert world.events
    # La bala va en camino y el arma está recargando: no pasa nada.
    world.update(Vector2())
    assert world.events == []


def test_paso_sin_nada_deja_events_vacio() -> None:
    world = mundo_con(Enemy(QUIETO, Vector2(100, 0)), armed=False)
    world.update(Vector2())
    assert sin_inicios(world.events) == []


def test_despues_de_game_over_events_queda_vacio() -> None:
    # La arista 1 queda a 4,2 del jugador, dentro de su radio de 12: lo toca.
    world = mundo_con(Enemy(QUIETO, Vector2(25, 0)))
    world.update(Vector2())
    assert world.game_over
    world.update(Vector2())
    assert world.events == []


# --- El contrato de medición (ADR 0030) ---


SIN_APARICIONES = replace(
    BALANCE,
    director=replace(
        BALANCE.director,
        sections=(replace(BALANCE.director.sections[0], deck=()),),
    ),
)
"""El balance real con un director que no compra: los tests ponen a mano a los
enemigos."""

BPM = BALANCE.director.bpm
HEXAGONOS = (DeckEntry("hexagon", 1.0),)


def seccion(
    name: str,
    kind: Literal["build", "wave", "endless"],
    bars: float,
    deck: tuple[DeckEntry, ...] = (),
    burst: float = 0.0,
    budget: float = 0.0,
) -> SectionSpec:
    return SectionSpec(
        name=name,
        kind=kind,
        bars=bars,
        budget_start=budget,
        budget_end=0.0,
        burst=burst,
        layers=(0, 3),
        deck=deck,
        formations=("single",),
    )


def con_secciones(*secciones: SectionSpec) -> World:
    """Un mundo sin muerte ni armas, con el tema `secciones`."""
    director = replace(BALANCE.director, sections=secciones)
    balance = replace(BALANCE, director=director)
    return World(balance, random.Random(1), lethal=False, armed=False)


def primer_paso(bar: float) -> int:
    """El primer paso del mundo que llega al compás `bar`. El paso 1 es el primero que
    da `update`."""
    return max(1, math.ceil(Fraction(bar) * 4 * 3600 / Fraction(BPM)))


def inicios_hasta_el_infinito(
    world: World, segundos: float = 60
) -> list[tuple[int, SectionStart]]:
    """Avanza con el jugador quieto hasta la primera vez que el director entra al
    infinito, y devuelve cada `SectionStart` con su paso."""
    inicios: list[tuple[int, SectionStart]] = []
    for paso in range(1, round(segundos / STEP) + 1):
        world.update(Vector2())
        inicios += [(paso, e) for e in world.events if isinstance(e, SectionStart)]
        if world.director.section.kind == "endless":
            return inicios
    raise AssertionError("no llegó al infinito")


def test_cada_seccion_emite_su_inicio() -> None:
    world = con_secciones(
        seccion("a", "build", 4.0),
        seccion("b", "wave", 4.0),  # Sin mazo no compra, y no espera.
        seccion("c", "endless", 4.0, HEXAGONOS, budget=1.0),
    )
    inicios = inicios_hasta_el_infinito(world)
    secciones = world.balance.director.sections
    assert [e for _, e in inicios] == [
        SectionStart(k, s) for k, s in enumerate(secciones)
    ]
    assert [paso for paso, _ in inicios] == [1, primer_paso(4.0), primer_paso(8.0)]


def test_inicio_tras_una_oleada_sale_cuando_se_limpia() -> None:
    # Borde: la oleada corre a las que siguen. El inicio sale en el paso en que el
    # director cambia de sección, y no en el compás que decía el tema. El hexágono de
    # la oleada se limpia a mano en el compás 10, después del final que decía el tema.
    world = con_secciones(
        seccion("a", "build", 4.0),
        seccion("b", "wave", 4.0, HEXAGONOS, burst=1.0),
        seccion("c", "endless", 4.0, HEXAGONOS, budget=1.0),
    )
    cambios: list[int] = []
    inicios: list[tuple[int, SectionStart]] = []
    antes = -1
    for paso in range(1, round(60 / STEP) + 1):
        world.update(Vector2())
        inicios += [(paso, e) for e in world.events if isinstance(e, SectionStart)]
        if world.director.section_index != antes:
            cambios.append(paso)
            antes = world.director.section_index
        if world.director.section.kind == "endless":
            break
        if paso >= primer_paso(10.0):
            for enemy in world.enemies:
                for k in list(enemy.edges):
                    enemy.remove_edge(k)
    else:
        raise AssertionError("no llegó al infinito")
    assert [e.index for _, e in inicios] == [0, 1, 2]
    assert [paso for paso, _ in inicios] == cambios
    assert cambios[2] > primer_paso(8.0)


def test_sin_cambio_de_seccion_un_solo_inicio() -> None:
    # Negativo: la última sección sigue después de sus compases sin volver a empezar.
    world = con_secciones(seccion("a", "build", 1.0))
    inicios = []
    for _ in range(primer_paso(4.0)):
        world.update(Vector2())
        inicios += [e for e in world.events if isinstance(e, SectionStart)]
    assert inicios == [SectionStart(0, world.balance.director.sections[0])]


def test_eventos_no_usan_nombres_de_secciones() -> None:
    codigo = Path(events_module.__file__).read_text(encoding="utf-8")
    for name in ("intro", "drop_1"):
        assert name not in codigo


# --- Spawn ---


def spawns(events: list[Event]) -> list[Enemy]:
    return [e.enemy for e in events if isinstance(e, Spawn)]


def avanzar_juntando(
    world: World, listo: Callable[[], bool], pasos: int = 600
) -> list[Event]:
    """Como `avanzar_hasta`, pero devuelve todos los eventos del camino."""
    todos: list[Event] = []
    for _ in range(pasos):
        world.update(Vector2())
        todos += world.events
        if listo():
            return todos
    raise AssertionError("no pasó en los pasos dados")


def test_enemigo_de_la_cola_emite_spawn() -> None:
    world = World(SIN_APARICIONES, random.Random(1), armed=False)
    world.queue.push([Queued("hexagon", Vector2(300, 0), None)])
    world.update(Vector2())
    [nuevo] = world.enemies
    assert spawns(world.events) == [nuevo]


def test_fragmentos_emiten_spawn_al_morir_el_divisor() -> None:
    # Borde: nacen sin pasar por la cola, en el paso en que muere el padre.
    world = World(SIN_APARICIONES, random.Random(0), lethal=False)
    padre = Enemy(BALANCE.enemies["divider"], Vector2(150, 0))
    de_frente = min(
        range(len(padre.edges)),
        key=lambda k: ((padre.lines()[k][0] + padre.lines()[k][1]) / 2).length(),
    )
    for k in [k for k in list(padre.edges) if k != de_frente]:
        padre.remove_edge(k)
    world.enemies = [padre]
    avanzar_hasta(world, lambda: Death(padre) in world.events)
    hijos = [e for e in world.enemies if e.spec is BALANCE.enemies["shard"]]
    assert len(hijos) == 5
    assert spawns(world.events) == hijos


def test_linea_suelta_emite_spawn() -> None:
    # Borde: nace en medio del paso, cuando el médico dona.
    def quieto(name: str) -> EnemySpec:
        return replace(BALANCE.enemies[name], speed=0.0, patterns=())

    medico = Enemy(quieto("regenerator"), Vector2(0, 300))
    herido = Enemy(quieto("hexagon"), Vector2(0, 450))
    herido.remove_edge(0)
    world = World(SIN_APARICIONES, random.Random(0), lethal=False, armed=False)
    world.enemies = [medico, herido]
    avanzar_hasta(
        world, lambda: any(isinstance(e, Donate) for e in world.events), steps_of(10)
    )
    [linea] = [e for e in world.enemies if e.stray]
    assert spawns(world.events) == [linea]


def test_gran_estrella_emite_spawn() -> None:
    # Borde: nace de la fusión, sin pasar por la cola.
    world = World(SIN_APARICIONES, random.Random(1), lethal=False, armed=False)
    world.enemies = [
        Enemy(BALANCE.enemies["star"], 300 * Vector2(math.cos(a), math.sin(a)))
        for a in (math.tau * k / 5 for k in range(5))
    ]
    avanzar_hasta(world, lambda: world.merge.state is MergeState.PRESENT)
    assert spawns(world.events) == [world.merge.present]


def test_enemigo_puesto_a_mano_no_emite_spawn() -> None:
    # Negativo: lo que ya estaba en el plano no aparece.
    world = World(SIN_APARICIONES, random.Random(1), armed=False)
    world.enemies = [Enemy(QUIETO, Vector2(300, 0))]
    for _ in range(60):
        world.update(Vector2())
        assert spawns(world.events) == []


def test_cada_aparicion_emite_spawn() -> None:
    # 20 s del piloto desde la subida 2, que trae médicos. Todo enemigo que se ve en el
    # plano tuvo su `Spawn` en ese paso o antes, y ninguno tiene dos. Los fragmentos y
    # la gran estrella tienen sus propios tests: en una corrida corta casi no salen.
    director = start_from(BALANCE.director, "subida_2")
    world = World(replace(BALANCE, director=director), random.Random(1), lethal=False)
    vistos: set[int] = set()
    aparecidos: list[Enemy] = []
    for _ in range(round(20 / STEP)):
        world.update(pilot_intent(world.steps))
        aparecidos += spawns(world.events)
        vistos |= {id(e) for e in world.enemies}
        assert vistos <= {id(e) for e in aparecidos}
    assert len({id(e) for e in aparecidos}) == len(aparecidos)
    # La corrida cubre la cola y las líneas sueltas.
    assert any(e.stray for e in aparecidos)
    assert any(not e.stray for e in aparecidos)


# --- PlayerDeath ---


def muertes(events: list[Event]) -> list[PlayerDeath]:
    return [e for e in events if isinstance(e, PlayerDeath)]


def test_la_muerte_nombra_lo_que_toco() -> None:
    # La arista 1 queda a 4,2 del jugador, dentro de su radio de 12: lo toca.
    enemy = Enemy(QUIETO, Vector2(25, 0))
    world = mundo_con(enemy, armed=False)
    world.update(Vector2())
    assert muertes(world.events) == [PlayerDeath(enemy)]


def test_la_muerte_nombra_la_bala_que_toco() -> None:
    # En un paso, la bala va de x = 15 a x = 5: cruza el círculo del jugador.
    world = World(SIN_APARICIONES, random.Random(1), armed=False)
    bala = EnemyBullet(Vector2(15, 0), Vector2(-600, 0))
    world.enemy_bullets = [bala]
    world.update(Vector2())
    assert muertes(world.events) == [PlayerDeath(bala)]


def test_bala_y_enemigo_a_la_vez_nombra_la_bala() -> None:
    # Borde: la bala mata al empezar el paso; el contacto se revisa al final.
    world = World(SIN_APARICIONES, random.Random(1), armed=False)
    world.enemies = [Enemy(QUIETO, Vector2(25, 0))]
    bala = EnemyBullet(Vector2(15, 0), Vector2(-600, 0))
    world.enemy_bullets = [bala]
    world.update(Vector2())
    assert muertes(world.events) == [PlayerDeath(bala)]


def test_sin_muerte_no_hay_player_death() -> None:
    # Negativo: con `lethal=False`, el contacto no termina la partida.
    world = mundo_con(Enemy(QUIETO, Vector2(25, 0)), armed=False, lethal=False)
    world.enemy_bullets = [EnemyBullet(Vector2(15, 0), Vector2(-600, 0))]
    for _ in range(60):
        world.update(Vector2())
        assert muertes(world.events) == []
