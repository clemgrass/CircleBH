"""Tests del secuenciador: avanza con los pasos de la escena y entrega bloques (ADR 0022).

Para mirar adentro sin escuchar, el secuenciador anota en `decisions` lo que decidió en
cada semicorchea: la capa, las notas de los enemigos, los golpes del arma y los acentos.
"""

import random
from dataclasses import replace

from pygame.math import Vector2

from circlebh.audio import sounds
from circlebh.audio.harmony import chord_at, variation_for
from circlebh.audio.intensity import PHRASE_BARS
from circlebh.audio.rhythm import SIXTEENTHS
from circlebh.audio.sequencer import SAMPLES_PER_STEP, Sequencer
from circlebh.balance import BALANCE, EnemySpec, SectionSpec
from circlebh.pilot import pilot_intent
from circlebh.world.enemy import Enemy
from circlebh.world.events import Death, Hit
from circlebh.world.game import World

# Sin apariciones: los tests ponen a los enemigos a mano. Un director sin mazo no compra.
SIN_APARICIONES = replace(
    BALANCE,
    director=replace(
        BALANCE.director,
        sections=(replace(BALANCE.director.sections[0], deck=()),),
    ),
)
# Sin patrones ni carga: el enemigo se queda donde lo ponen.
QUIETO = EnemySpec(
    sides=6,
    radius=24.0,
    speed=120.0,
    friction=0.0,
    charge_per_line=0.0,
    patterns=(),
    threat=1.0,
)


def mundo(*enemigos: Enemy, armed: bool = True, lethal: bool = True) -> World:
    world = World(SIN_APARICIONES, random.Random(1), armed=armed, lethal=lethal)
    world.enemies = list(enemigos)
    return world


def tocar(
    sequencer: Sequencer, world: World, pasos: int, *, piloto: bool = False
) -> list[list]:
    """Avanza el mundo y el secuenciador `pasos` veces, como la escena: con la partida
    perdida, el mundo ya no se actualiza, pero el secuenciador sigue. Devuelve los
    eventos de cada paso."""
    eventos = []
    for _ in range(pasos):
        if not world.game_over:
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


def test_con_enemigos_cerca_la_base_sube_hasta_la_capa_3() -> None:
    # Diez hexágonos quietos a 150 unidades llevan la intensidad cerca de 0,9: en dos
    # frases sube hasta la capa 3, con su riser, y suenan el bombo, el bajo y el sidechain.
    enemigos = [Enemy(QUIETO, Vector2(150, 0).rotate(36 * i)) for i in range(10)]
    sequencer = Sequencer(1)
    tocar(sequencer, mundo(*enemigos, armed=False, lethal=False), 620)
    niveles = [d.level for d in sequencer.decisions]
    assert max(niveles) == 3
    assert any("riser" in d.cues for d in sequencer.decisions)
    # Con la base completa, el audio pesa más que en la calma del principio.
    calma, fuerte = sequencer.ready[2], sequencer.ready[-1]
    assert sum(map(abs, memoryview(fuerte).cast("h"))) > sum(
        map(abs, memoryview(calma).cast("h"))
    )


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


def test_al_crearse_deja_lista_la_bateria() -> None:
    # Generar un sonido la primera vez cuesta hasta 70 ms: no puede pasar a mitad de
    # partida, donde se notaría como un tirón.
    for sonido in (sounds.kick, sounds.clap, sounds.impact, sounds.riser):
        sonido.cache_clear()
    sequencer = Sequencer(1)
    for sonido in (sounds.kick, sounds.closed_hat, sounds.open_hat, sounds.clap):
        assert sonido.cache_info().currsize == 1
    assert sounds.impact.cache_info().currsize == 1
    assert sounds.rim.cache_info().currsize == 1
    # El de un compás y el de la subida de una frase (ADR 0026).
    assert sounds.riser.cache_info().currsize == 2
    sounds.riser(sequencer.grid.bar_seconds)
    sounds.riser(PHRASE_BARS * sequencer.grid.bar_seconds)
    assert sounds.riser.cache_info().hits >= 2


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
    # A 124 BPM, el segundo compás empieza en el paso 117.
    tocar(sequencer, world, 140)
    assert any(d.g >= SIXTEENTHS for d in sequencer.decisions)
    nueva = variation_for(7)
    for decision in sequencer.decisions:
        if decision.g < SIXTEENTHS:
            assert decision.variation == variation_for(1)
        else:
            assert decision.variation == nueva
    # Al reiniciar, el tempo no cambia.
    assert sequencer.grid.bpm == BALANCE.director.bpm


def test_musica_toma_el_tempo_del_balance() -> None:
    # ADR 0025: el tempo es del tema, no de la semilla.
    tempos = {Sequencer(seed).grid.bpm for seed in range(8)}
    assert tempos == {BALANCE.director.bpm}


def test_al_reiniciar_tonalidad_acorde_inicial_e_impacto_caen_juntos() -> None:
    # Como `GameScene.restart`: mundo nuevo y `start_game` a mitad del compás 0. En el
    # compás 1 entran juntos el impacto, la tonalidad nueva y su acorde inicial, que dura
    # sus dos compases completos (1 y 2); en el 3 sigue el acorde siguiente.
    sequencer = Sequencer(1)
    tocar(sequencer, mundo(armed=False), 20)
    sequencer.start_game(7)
    tocar(sequencer, mundo(armed=False), 480)
    nueva = variation_for(7)
    por_g = {d.g: d for d in sequencer.decisions}
    [impacto] = [d.g for d in sequencer.decisions if "impact" in d.cues]
    assert impacto == SIXTEENTHS
    assert por_g[SIXTEENTHS].variation == nueva
    for g in range(SIXTEENTHS, 3 * SIXTEENTHS):
        assert por_g[g].chord == chord_at(0, nueva)
    assert por_g[3 * SIXTEENTHS].chord == chord_at(2, nueva)


# --- El drop (ADR 0026) ---


def seccion_vacia(name: str, layers: tuple[int, int]) -> SectionSpec:
    """Una sección de 4 compases que no compra: solo importan sus capas."""
    return replace(
        BALANCE.director.sections[0],
        name=name,
        bars=4.0,
        deck=(),
        burst=0.0,
        layers=layers,
    )


TEMA_CORTO = replace(
    BALANCE,
    director=replace(
        BALANCE.director,
        sections=(seccion_vacia("intro", (0, 3)), seccion_vacia("drop", (3, 3))),
    ),
)
"""Una frase de intro y un drop en el compás 4 de la partida."""


def test_reinicio_espera_el_compas_y_el_drop_cae_en_el_golpe() -> None:
    # Como `GameScene` con R1: el jugador reinicia a mitad del compás 0. El mundo nuevo
    # queda congelado mientras la música espera el compás, y parte con él.
    sequencer = Sequencer(1)
    tocar(sequencer, mundo(armed=False), 20)
    sequencer.start_game(7)
    world = World(TEMA_CORTO, random.Random(7), armed=False, lethal=False)
    entra_al_drop = golpe_decidido = None
    golpe = (
        1 + 4
    ) * SIXTEENTHS  # la tonalidad entra en el compás 1; el drop, 4 después
    for paso in range(800):
        if not sequencer.waiting_for_bar:
            world.update(Vector2())
            if entra_al_drop is None and world.director.section.name == "drop":
                entra_al_drop = paso
        sequencer.step(world)
        if golpe_decidido is None and sequencer.decisions[-1].g >= golpe:
            golpe_decidido = paso
    assert entra_al_drop is not None and golpe_decidido is not None
    assert abs(entra_al_drop - golpe_decidido) <= 1
    por_g = {d.g: d for d in sequencer.decisions}
    assert "build" in por_g[1 * SIXTEENTHS].cues
    assert [g for g, d in por_g.items() if d.silent] == list(range(golpe - 4, golpe))
    assert "impact" in por_g[golpe].cues
    assert por_g[golpe].level == 3


def test_sin_reinicio_no_espera() -> None:
    # Negativo: sin `start_game` pendiente, la escena no frena al mundo.
    sequencer = Sequencer(1)
    tocar(sequencer, mundo(armed=False), 200)
    assert not sequencer.waiting_for_bar


def test_musica_apagada_misma_partida() -> None:
    # Negativo (ADR 0022 y 0025): la música lee al mundo, pero no lo cambia. Con una
    # intro que compra rápido, en 200 pasos ya aparecieron varios enemigos.
    intro = replace(BALANCE.director.sections[0], budget_start=8.0, budget_end=8.0)
    balance = replace(BALANCE, director=replace(BALANCE.director, sections=(intro,)))
    con, sin = World(balance, random.Random(3)), World(balance, random.Random(3))
    sequencer = Sequencer(3)
    for _ in range(200):
        con.update(pilot_intent(con.steps))
        sequencer.step(con)
        sin.update(pilot_intent(sin.steps))
        assert [e.position for e in con.enemies] == [e.position for e in sin.enemies]
    assert len(con.enemies) > 2
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


def test_los_eventos_del_paso_fatal_suenan_una_sola_vez() -> None:
    # Con la partida perdida, la escena no vuelve a llamar a `update`, así que
    # `world.events` se queda con los eventos del paso fatal. Si en ese paso una bala
    # golpeó, el rim tiene que sonar una vez, no en cada paso de la pantalla de muerte.
    enemy = Enemy(QUIETO, Vector2(25, 0))
    world = mundo(enemy)
    sequencer = Sequencer(1)
    world.update(Vector2())
    assert world.game_over
    world.events += [Hit(enemy, 1), Death(enemy)]  # como si el paso fatal los dejara
    sequencer.step(world)
    tocar(sequencer, world, 120)
    assert sum(d.rims for d in sequencer.decisions) == 1
    assert sum(d.death for d in sequencer.decisions) == 1


def test_un_golpe_de_la_partida_anterior_no_suena_en_la_nueva() -> None:
    # El golpe queda pendiente al final de un paso; si en el paso siguiente ya hay otro
    # mundo (el jugador reinició), es de la partida anterior y no suena.
    enemy = Enemy(QUIETO, Vector2(300, 0))
    viejo = mundo(enemy, armed=False)
    sequencer = Sequencer(1)
    viejo.update(Vector2())
    viejo.events += [Hit(enemy, 1), Death(enemy)]
    sequencer.step(viejo)
    tocar(sequencer, mundo(armed=False), 60)
    assert sum(d.rims for d in sequencer.decisions) == 0
    assert not any(d.death for d in sequencer.decisions)


def test_un_mundo_nuevo_vuelve_a_la_calma_con_un_impacto() -> None:
    sequencer = Sequencer(1)
    tocar(sequencer, mundo(armed=False), 30)
    tocar(sequencer, mundo(armed=False), 30)
    impactos = [d for d in sequencer.decisions if "impact" in d.cues]
    assert len(impactos) == 1
