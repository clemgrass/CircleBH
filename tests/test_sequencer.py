"""Tests del secuenciador: avanza con los pasos de la escena y entrega bloques (ADR 0022).

Para mirar adentro sin escuchar, el secuenciador anota en `decisions` lo que decidió en
cada semicorchea: la capa, las notas de los enemigos, los golpes del arma y los acentos.
"""

import random
from dataclasses import replace

from pygame.math import Vector2

from circlebh.audio.harmony import bpm_for, variation_for
from circlebh.audio.rhythm import SIXTEENTHS
from circlebh.audio.sequencer import SAMPLES_PER_STEP, Sequencer
from circlebh.balance import BALANCE, EnemySpec
from circlebh.pilot import pilot_intent
from circlebh.world.enemy import Enemy
from circlebh.world.events import Death, Hit
from circlebh.world.game import World

# Sin apariciones: los tests ponen a los enemigos a mano.
SIN_APARICIONES = replace(
    BALANCE, spawning=replace(BALANCE.spawning, interval=1e9, distance=5000.0)
)
# Sin patrones ni carga: el enemigo se queda donde lo ponen.
QUIETO = EnemySpec(
    sides=6, radius=24.0, speed=120.0, friction=0.0, charge_per_line=0.0, patterns=()
)


def mundo(*enemigos: Enemy, armed: bool = True, lethal: bool = True) -> World:
    world = World(SIN_APARICIONES, random.Random(1), armed=armed, lethal=lethal)
    world.enemies = list(enemigos)
    return world


def tocar(
    sequencer: Sequencer, world: World, pasos: int, *, piloto: bool = False
) -> list[list]:
    """Avanza el mundo y el secuenciador `pasos` veces, como la escena. Devuelve los
    eventos de cada paso."""
    eventos = []
    for _ in range(pasos):
        world.update(pilot_intent(world.steps) if piloto else Vector2())
        sequencer.step(world)
        eventos.append(list(world.events))
    return eventos


def demo(segundos: float) -> bytes:
    """Unos segundos de la demo con la semilla 1, como bytes de audio."""
    sequencer = Sequencer(1)
    tocar(
        sequencer, World(BALANCE, random.Random(1)), round(segundos * 60), piloto=True
    )
    return b"".join(sequencer.ready)


# --- Determinismo y bloques ---


def test_los_mismos_pasos_dan_los_mismos_bytes() -> None:
    a, b = demo(3), demo(3)
    assert len(a) > 0
    assert a == b


def test_cada_bloque_listo_mide_su_semicorchea() -> None:
    sequencer = Sequencer(1)
    pasos = 100
    tocar(sequencer, mundo(armed=False), pasos)
    grid = sequencer.grid
    # Un bloque queda listo cuando empieza el siguiente.
    ultimo_paso = (pasos - 1) * SAMPLES_PER_STEP
    listos = [g for g in range(1000) if grid.start(g + 1) <= ultimo_paso]
    assert len(sequencer.ready) == len(listos)
    for g, block in zip(listos, sequencer.ready, strict=True):
        assert len(block) == (grid.start(g + 1) - grid.start(g)) * 4  # estéreo, 16 bits


def test_sin_enemigos_ni_disparos_la_capa_del_juego_calla() -> None:
    sequencer = Sequencer(1)
    tocar(sequencer, mundo(), 120)
    assert sequencer.decisions
    for decision in sequencer.decisions:
        assert decision.level == 0
        assert decision.notes == ()
        assert decision.weapon_hits == 0
        assert decision.rims == 0
    # La base sigue sonando: el pad de la capa 0.
    assert any(any(block) for block in sequencer.ready)


def test_volumen_cero_en_las_dos_capas_es_silencio() -> None:
    sequencer = Sequencer(1, base_volume=0.0, game_volume=0.0)
    tocar(sequencer, mundo(Enemy(QUIETO, Vector2(100, 0))), 120)
    assert sequencer.ready
    assert not any(any(block) for block in sequencer.ready)


def bloques_con_enemigo_en(posicion: Vector2, game_volume: float) -> Sequencer:
    sequencer = Sequencer(1, game_volume=game_volume)
    tocar(sequencer, mundo(Enemy(QUIETO, posicion), armed=False), 120)
    return sequencer


def test_game_volume_cero_calla_solo_las_notas_del_juego() -> None:
    # A la misma distancia, la intensidad (y con ella la base) es la misma; el ángulo
    # solo rota el loop del enemigo, que es la capa del juego.
    este, norte = Vector2(300, 0), Vector2(0, 300)
    mudo_este = bloques_con_enemigo_en(este, 0.0)
    mudo_norte = bloques_con_enemigo_en(norte, 0.0)
    assert [d.notes for d in mudo_este.decisions] != [
        d.notes for d in mudo_norte.decisions
    ]
    assert list(mudo_este.ready) == list(mudo_norte.ready)
    assert list(bloques_con_enemigo_en(este, 1.0).ready) != list(
        bloques_con_enemigo_en(norte, 1.0).ready
    )


# --- La cuantización ---


def primer_paso_con(eventos: list[list], tipo: type) -> int:
    return next(
        n for n, paso in enumerate(eventos) if any(isinstance(e, tipo) for e in paso)
    )


def test_un_golpe_suena_en_la_primera_semicorchea_despues_de_su_paso() -> None:
    sequencer = Sequencer(1)
    eventos = tocar(sequencer, mundo(Enemy(QUIETO, Vector2(100, 0))), 60)
    n = primer_paso_con(eventos, Hit)
    [decision] = [d for d in sequencer.decisions if d.rims]
    grid = sequencer.grid
    assert grid.start(decision.g) > n * SAMPLES_PER_STEP
    assert grid.start(decision.g - 1) <= n * SAMPLES_PER_STEP


def test_una_muerte_cae_en_la_corchea_siguiente() -> None:
    enemy = Enemy(QUIETO, Vector2(100, 0))
    enemy.edges = [1]
    sequencer = Sequencer(1)
    eventos = tocar(sequencer, mundo(enemy), 60)
    n = primer_paso_con(eventos, Death)
    [decision] = [d for d in sequencer.decisions if d.death]
    assert decision.g % 2 == 0
    assert sequencer.grid.start(decision.g) > n * SAMPLES_PER_STEP


def test_el_arma_calla_si_no_disparo() -> None:
    # Armada, pero sin enemigos no tiene a quién disparar: su loop no suena.
    sequencer = Sequencer(1)
    tocar(sequencer, mundo(), 120)
    assert all(d.weapon_hits == 0 for d in sequencer.decisions)


def test_el_arma_suena_en_su_loop_cuando_dispara() -> None:
    sequencer = Sequencer(1)
    # Dispara cada 0,6 s (36 pasos): en 160 pasos alcanza a sonar al menos dos veces.
    tocar(sequencer, mundo(Enemy(QUIETO, Vector2(600, 0))), 160)
    assert sum(d.weapon_hits for d in sequencer.decisions) >= 2


# --- La variación y las partidas ---


def test_start_game_cambia_la_tonalidad_en_el_compas_siguiente() -> None:
    sequencer = Sequencer(1)
    world = mundo(armed=False)
    tocar(sequencer, world, 20)  # a mitad del primer compás
    sequencer.start_game(7)
    # El segundo compás empieza antes del paso 120 con cualquier tempo de 120 a 126.
    tocar(sequencer, world, 140)
    assert any(d.g >= SIXTEENTHS for d in sequencer.decisions)
    nueva = variation_for(7)
    for decision in sequencer.decisions:
        if decision.g < SIXTEENTHS:
            assert decision.variation == variation_for(1)
        else:
            assert decision.variation == nueva
    assert sequencer.grid.bpm == bpm_for(1)


def test_el_mundo_queda_identico_con_y_sin_la_musica() -> None:
    con, sin = World(BALANCE, random.Random(3)), World(BALANCE, random.Random(3))
    tocar(Sequencer(3), con, 200, piloto=True)
    for _ in range(200):
        sin.update(pilot_intent(sin.steps))
    assert [e.position for e in con.enemies] == [e.position for e in sin.enemies]
    assert con.rng.getstate() == sin.rng.getstate()


def test_mundo_muerto_sigue_sonando_con_un_solo_impacto() -> None:
    # La arista 1 queda dentro del radio del jugador: muere en el primer paso.
    sequencer = Sequencer(1)
    world = mundo(Enemy(QUIETO, Vector2(25, 0)))
    tocar(sequencer, world, 1)
    assert world.game_over
    listos = len(sequencer.ready)
    tocar(sequencer, world, 90)
    assert len(sequencer.ready) > listos
    impactos = [d for d in sequencer.decisions if "impact" in d.cues]
    assert len(impactos) == 1


def test_un_mundo_nuevo_vuelve_a_la_calma_con_un_impacto() -> None:
    sequencer = Sequencer(1)
    tocar(sequencer, mundo(armed=False), 30)
    tocar(sequencer, mundo(armed=False), 30)
    impactos = [d for d in sequencer.decisions if "impact" in d.cues]
    assert len(impactos) == 1
