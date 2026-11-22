"""Tests de la partida: `World` avanza un paso por `update`."""

import itertools
import math
import random
from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pygame.math import Vector2

from circlebh.balance import (
    BALANCE,
    Balance,
    DeckEntry,
    DirectorSpec,
    EnemySpec,
    SectionSpec,
)
from circlebh.world.clock import STEP
from circlebh.world.director import bar_at
from circlebh.world.enemy import Enemy
from circlebh.world.game import World
from circlebh.world.polygon import polygon_edge
from circlebh.world.spawning import quadrant
from circlebh.world.swarm import lattice
from circlebh.world.weapons import PointWeapon

SIN_APARICIONES = replace(
    BALANCE,
    director=replace(
        BALANCE.director,
        sections=(replace(BALANCE.director.sections[0], deck=()),),
    ),
)
"""El balance real con un director sin mazo, que no compra: los tests ponen a mano a
los enemigos."""
HEXAGON_REAL = BALANCE.enemies["hexagon"]


def mundo_con_hexagono(
    position: Vector2, balance: Balance = SIN_APARICIONES, **kwargs: bool
) -> World:
    """Un mundo sin apariciones, con un hexágono en `position`."""
    world = World(balance, random.Random(1), **kwargs)
    world.enemies = [Enemy(balance.enemies["hexagon"], position)]
    return world


def test_world_mueve_al_jugador() -> None:
    world = World(BALANCE, random.Random(1))
    world.update(Vector2(0, 1))
    assert world.player.position.y == pytest.approx(BALANCE.player.speed * STEP)


def test_world_empieza_sin_enemigos() -> None:
    # La intro parte en silencio: el presupuesto de su primer paso no alcanza para nada.
    world = World(BALANCE, random.Random(1))
    assert world.enemies == []


def test_mundo_parte_con_el_arma_punto() -> None:
    world = World(BALANCE, random.Random(1))
    [weapon] = world.weapons
    assert isinstance(weapon, PointWeapon)
    assert weapon.spec == BALANCE.point_weapon


def test_la_bala_nace_donde_quedo_el_jugador() -> None:
    world = mundo_con_hexagono(Vector2(BALANCE.spawning.distance, 0))
    world.update(Vector2(1, 0))
    [weapon] = world.weapons
    assert isinstance(weapon, PointWeapon)
    [bullet] = weapon.bullets
    assert bullet.position == world.player.position


def test_el_enemigo_persigue_la_posicion_nueva_del_jugador() -> None:
    world = mundo_con_hexagono(Vector2(100, 0))
    [enemy] = world.enemies
    # El jugador se mueve hacia arriba; el enemigo apunta a donde quedó, no al origen.
    world.update(Vector2(0, 1))
    hacia_el_jugador = world.player.position - Vector2(100, 0)
    avance = enemy.position - Vector2(100, 0)
    # La misma dirección, no los mismos bits.
    assert tuple(avance.normalize()) == pytest.approx(
        tuple(hacia_el_jugador.normalize())
    )


def test_world_empieza_sin_terminar_y_en_cero() -> None:
    world = World(BALANCE, random.Random(1))
    assert world.game_over is False
    assert world.elapsed == 0


def test_elapsed_cuenta_un_step_por_update() -> None:
    world = World(BALANCE, random.Random(1))
    for _ in range(90):
        world.update(Vector2())
    assert world.steps == 90
    assert world.elapsed == pytest.approx(1.5)


# --- Morir ---


def mundo_con_hexagono_quieto(x: float) -> World:
    """Un mundo con el hexágono quieto (`speed = 0`) en `(x, 0)`, a la derecha del jugador.

    Quieto, la geometría queda exacta y no depende del redondeo de su paso. La línea
    que mira al jugador es la arista 1, la vertical izquierda del hexágono.
    """
    hexagon = replace(BALANCE.enemies["hexagon"], speed=0.0)
    balance = replace(SIN_APARICIONES, enemies={**BALANCE.enemies, "hexagon": hexagon})
    return mundo_con_hexagono(Vector2(x, 0), balance)


def tangente() -> float:
    """El centro del hexágono al que su arista 1 queda tangente al jugador."""
    a, _ = polygon_edge(BALANCE.enemies["hexagon"].radius, 6, 1)
    return BALANCE.player.radius - a.x


def test_tocar_una_linea_termina_la_partida() -> None:
    world = mundo_con_hexagono_quieto(tangente() - 5)
    world.update(Vector2())
    assert world.game_over is True


def test_tangente_a_una_linea_termina_la_partida() -> None:
    world = mundo_con_hexagono_quieto(tangente())
    world.update(Vector2())
    assert world.game_over is True


def test_a_una_unidad_de_la_linea_no_muere() -> None:
    world = mundo_con_hexagono_quieto(tangente() + 1)
    world.update(Vector2())
    assert world.game_over is False


def test_dentro_de_un_enemigo_abierto_sin_tocar_no_muere() -> None:
    # Decisión 16: el jugador (radio 12) cabe dentro del hexágono (apotema ≈ 20,8) sin
    # tocar sus líneas. Solo llega ahí por un hueco.
    world = mundo_con_hexagono_quieto(0)
    world.enemies[0].remove_edge(1)
    world.update(Vector2())
    assert world.game_over is False


def test_la_envolvente_sola_no_mata() -> None:
    # Negativo: el jugador toca el círculo envolvente (a 24 + 12 = 36 del centro), pero
    # ninguna línea.
    world = mundo_con_hexagono_quieto(34)
    world.update(Vector2())
    assert world.game_over is False


def test_enemigo_lejos_no_termina_la_partida() -> None:
    world = mundo_con_hexagono(Vector2(BALANCE.spawning.distance, 0))
    for _ in range(60):
        world.update(Vector2())
    assert world.game_over is False


def test_tras_morir_update_no_avanza() -> None:
    world = mundo_con_hexagono(Vector2(tangente() - 5, 0))
    world.update(Vector2())
    assert world.game_over is True

    jugador, enemigo, tiempo = (
        Vector2(world.player.position),
        Vector2(world.enemies[0].position),
        world.elapsed,
    )
    for _ in range(10):
        world.update(Vector2(1, 0))
    assert world.player.position == jugador
    assert world.enemies[0].position == enemigo
    assert world.elapsed == tiempo
    assert world.game_over is True


# --- Las apariciones (ADR 0025) ---

TASA = 4.0
RAPIDO = replace(
    BALANCE,
    director=DirectorSpec(
        bpm=124.0,
        max_alive=300,
        sections=(
            SectionSpec(
                name="rapida",
                kind="build",
                bars=64.0,
                budget_start=TASA,
                budget_end=TASA,
                burst=0.0,
                layers=(0, 3),
                deck=(DeckEntry("hexagon", 1.0),),
                formations=("single",),
            ),
        ),
    ),
)
"""Un hexágono por cuarto de compás. Con la tasa constante, lo ganado es `4 · compás`."""


def mundo_sin_armas(seed: int) -> World:
    """Un mundo con `RAPIDO`, los hexágonos quietos (`speed = 0`) y sin armas.

    Así nadie muere ni mata, y la cuenta de enemigos solo cambia por las apariciones.
    """
    hexagon = replace(BALANCE.enemies["hexagon"], speed=0.0)
    balance = replace(RAPIDO, enemies={**BALANCE.enemies, "hexagon": hexagon})
    return World(balance, random.Random(seed), armed=False)


def avanzar_hasta_que_haya(world: World, n: int, intent: Vector2) -> None:
    while len(world.enemies) < n:
        world.update(intent)


def test_aparece_lo_que_gana_el_director() -> None:
    world = mundo_sin_armas(seed=1)
    for _ in range(300):
        world.update(Vector2())
        assert len(world.enemies) == math.floor(TASA * bar_at(world.steps, 124.0))


def test_aparece_a_la_distancia_del_jugador_donde_esta() -> None:
    world = mundo_sin_armas(seed=1)
    avanzar_hasta_que_haya(world, 1, Vector2(1, 0))
    nuevo = world.enemies[-1]
    assert nuevo.position.distance_to(world.player.position) == pytest.approx(
        BALANCE.spawning.distance
    )


@given(seed=st.integers(min_value=0, max_value=2**32 - 1))
def test_dos_apariciones_no_comparten_posicion(seed: int) -> None:
    # Propiedad: cada aparición sortea su ángulo. Que dos ángulos al azar coincidan
    # tiene probabilidad prácticamente nula, así que es un error y no azar.
    world = mundo_sin_armas(seed)
    avanzar_hasta_que_haya(world, 2, Vector2())
    primero, segundo = world.enemies
    assert primero.position != segundo.position


# --- La cola y los cuadrantes (ADR 0025, #53) ---


def mundo_con_rafaga(
    burst: float,
    formation: str,
    *,
    size: int = 1,
    max_per_step: int = 4,
    seed: int = 1,
) -> World:
    """Un mundo cuya única compra es una ráfaga de `burst` en el primer paso, con
    hexágonos quietos y sin armas. `size` fija el tamaño de las formaciones."""
    seccion = SectionSpec(
        name="rafaga",
        kind="build",
        bars=64.0,
        budget_start=0.0,
        budget_end=0.0,
        burst=burst,
        layers=(0, 3),
        deck=(DeckEntry("hexagon", 1.0),),
        formations=(formation,),
    )
    balance = replace(
        BALANCE,
        enemies={
            **BALANCE.enemies,
            "hexagon": replace(BALANCE.enemies["hexagon"], speed=0.0),
        },
        spawning=replace(
            BALANCE.spawning, max_per_step=max_per_step, formation_size=(size, size)
        ),
        director=replace(BALANCE.director, sections=(seccion,)),
    )
    return World(balance, random.Random(seed), armed=False)


def test_nunca_mas_de_max_per_step() -> None:
    world = mundo_con_rafaga(20, "single", max_per_step=4)
    cuentas = []
    for _ in range(7):
        world.update(Vector2())
        cuentas.append(len(world.enemies))
    assert cuentas == [4, 8, 12, 16, 20, 20, 20]


def test_formacion_grande_llega_completa_y_en_orden() -> None:
    # Borde: una fila de 6 con un tope de 4 llega en dos pasos, y en el orden de la
    # fila: cada uno queda a la misma separación del anterior.
    world = mundo_con_rafaga(6, "line", size=6, max_per_step=4)
    world.update(Vector2())
    assert len(world.enemies) == 4
    world.update(Vector2())
    fila = [e.position for e in world.enemies]
    assert len(fila) == 6
    pasos = [a.distance_to(b) for a, b in itertools.pairwise(fila)]
    assert pasos == pytest.approx([pasos[0]] * 5)


def test_rafaga_reparte_los_cuadrantes() -> None:
    # La cola cuenta para el cuadrante más vacío: 12 sueltos quedan 3 por cuadrante.
    world = mundo_con_rafaga(12, "single", max_per_step=12)
    world.update(Vector2())
    cuenta = [0, 0, 0, 0]
    for enemy in world.enemies:
        cuenta[quadrant(enemy.position - world.player.position)] += 1
    assert cuenta == [3, 3, 3, 3]


def test_la_gran_estrella_no_cuenta_en_los_cuadrantes() -> None:
    # Los enemigos la atraviesan (decisión 40): no ocupa un cuadrante. Si contara, su
    # centro sobre el jugador le quitaría un hexágono al cuadrante 0.
    world = mundo_con_rafaga(12, "single", max_per_step=12)
    grande = Enemy(BALANCE.enemies["red_star"], world.player.position)
    world.enemies.append(grande)
    world.update(Vector2())
    cuenta = [0, 0, 0, 0]
    for enemy in world.enemies:
        if enemy is not grande:
            cuenta[quadrant(enemy.position - world.player.position)] += 1
    assert cuenta == [3, 3, 3, 3]


def test_formacion_en_varios_pasos_se_deforma_poco() -> None:
    # La cola guarda posiciones relativas al jugador. Si avanza mientras una fila llega
    # de a uno, cada vecino nace corrido lo que el jugador avanzó en un paso: la fila
    # se deforma a lo más eso, y sigue fuera del núcleo duro.
    world = mundo_con_rafaga(6, "line", size=6, max_per_step=1)
    for _ in range(6):
        world.update(Vector2(1, 0))
    fila = [e.position for e in world.enemies]
    assert len(fila) == 6
    hexagon = BALANCE.enemies["hexagon"]
    nucleo = BALANCE.charges.core_reach * 2 * hexagon.radius
    separacion = nucleo + BALANCE.spawning.formation_gap
    avance = BALANCE.player.speed * STEP
    for a, b in itertools.pairwise(fila):
        assert abs(a.distance_to(b) - separacion) <= avance + 1e-9
        assert a.distance_to(b) > nucleo


def test_formacion_que_no_cabe_se_rechaza_al_crear_el_mundo() -> None:
    # Negativo: con hexágonos enormes, la fila de 6 de la subida no cabe en un
    # cuadrante. Falla al empezar, no a mitad de la partida.
    hexagon = replace(BALANCE.enemies["hexagon"], radius=300.0)
    balance = replace(BALANCE, enemies={**BALANCE.enemies, "hexagon": hexagon})
    with pytest.raises(ValueError, match="cuadrante"):
        World(balance, random.Random(1))


@given(seed=st.integers(0, 2**32 - 1))
def test_aparece_fuera_de_la_vista_aunque_el_jugador_avance(seed: int) -> None:
    # Negativo: lo que espera en la cola se ubica desde donde está el jugador al salir,
    # no desde donde estaba al comprarse.
    world = mundo_con_rafaga(24, "cluster", size=6, max_per_step=1, seed=seed)
    for _ in range(30):
        antes = set(map(id, world.enemies))
        world.update(Vector2(1, 0))
        for enemy in world.enemies:
            if id(enemy) not in antes:
                distancia = enemy.position.distance_to(world.player.position)
                assert distancia >= BALANCE.spawning.distance - 1e-9


def test_tras_morir_no_aparecen_mas() -> None:
    world = mundo_sin_armas(seed=1)
    world.enemies = [
        Enemy(world.balance.enemies["hexagon"], Vector2(tangente() - 5, 0))
    ]
    world.update(Vector2())
    assert world.game_over is True
    for _ in range(300):
        world.update(Vector2())
    assert len(world.enemies) == 1


def test_world_sin_intencion_deja_al_jugador_quieto() -> None:
    world = World(BALANCE, random.Random(1))
    for _ in range(10):
        world.update(Vector2(0, 0))
    assert world.player.position == Vector2(0, 0)


# --- El enjambre (ADR 0021) ---


def test_el_jugador_se_mueve_igual_con_enemigos_cerca() -> None:
    # La carga del jugador atrae, pero ninguna fuerza lo mueve: su control es exacto.
    solo = World(BALANCE, random.Random(1), lethal=False, armed=False)
    rodeado = World(BALANCE, random.Random(1), lethal=False, armed=False)
    hexagon = BALANCE.enemies["hexagon"]
    rodeado.enemies += [Enemy(hexagon, p) for p in lattice(Vector2(), 12, 60)]
    for paso in range(60):
        intent = Vector2(1, 0).rotate(paso * 6)
        solo.update(intent)
        rodeado.update(intent)
    assert rodeado.player.position == solo.player.position


def test_enemigo_muerto_no_divide_por_cero() -> None:
    # Foco de revisión 1: una bala le quita la última línea en el paso, y el paso
    # siguiente no puede calcular con masa 0.
    world = mundo_con_hexagono(Vector2(-150, 0))
    [enemy] = world.enemies
    for k in [0, 1, 2, 3, 5]:
        enemy.remove_edge(k)
    for _ in range(40):
        world.update(Vector2())
    assert enemy not in world.enemies


def test_aparecer_encima_de_otro_los_separa() -> None:
    # Foco de revisión 4: el próximo enemigo aparece justo donde ya hay uno. Un mundo
    # gemelo, con la misma semilla, dice dónde y en qué paso va a aparecer.
    gemelo = mundo_sin_armas(seed=1)
    avanzar_hasta_que_haya(gemelo, 1, Vector2())
    world = mundo_sin_armas(seed=1)
    world.enemies = [
        Enemy(world.balance.enemies["hexagon"], gemelo.enemies[0].position)
    ]
    for _ in range(gemelo.steps + 1):
        world.update(Vector2())
    a, b = world.enemies
    assert a.position.distance_to(b.position) >= a.radius + b.radius - 1e-9


def test_sin_letalidad_no_termina() -> None:
    world = mundo_con_hexagono(Vector2(tangente() - 5, 0), lethal=False)
    world.update(Vector2())
    assert world.game_over is False


def test_desarmado_no_dispara() -> None:
    world = World(BALANCE, random.Random(1), armed=False)
    assert world.weapons == []


def test_cuenta_las_separaciones() -> None:
    world = mundo_sin_armas(seed=1)
    hexagon = world.balance.enemies["hexagon"]
    world.enemies = [Enemy(hexagon, Vector2(300, 0)), Enemy(hexagon, Vector2(320, 0))]
    world.update(Vector2())
    assert world.separations == 1


# --- La masa (#59, ADR 0027) ---


def test_el_mundo_rechaza_una_masa_que_no_es_positiva() -> None:
    sin_masa = replace(HEXAGON_REAL, mass_per_line=0.0)
    balance = replace(BALANCE, enemies={**BALANCE.enemies, "hexagon": sin_masa})
    with pytest.raises(ValueError, match=r"enemies\.hexagon\.mass_per_line"):
        World(balance, random.Random(1))


# --- La masa crítica trae al círculo (#59) ---


def mundo_cargado(spec: EnemySpec) -> World:
    """Un mundo sin apariciones ni armas, con 30 enemigos `spec` en una red a la
    derecha del jugador: la masa crítica del balance, todos del mismo lado."""
    world = World(SIN_APARICIONES, random.Random(1), armed=False)
    world.enemies = [
        Enemy(spec, Vector2(300 + 60 * (i % 6), 60 * (i // 6) - 120))
        for i in range(BALANCE.critical_mass.count)
    ]
    return world


def circulos_en_la_cola(world: World) -> int:
    return sum(1 for name, _ in world.queue if name == "circle")


def test_el_mundo_trae_un_circulo_con_masa_critica() -> None:
    world = mundo_cargado(HEXAGON_REAL)
    world.update(Vector2())
    assert circulos_en_la_cola(world) == 1


@pytest.mark.parametrize("campo", ["anchored", "phantom"])
def test_los_anclados_y_los_fantasmas_no_cuentan(campo: str) -> None:
    # Copias del hexágono, no estrellas: 30 estrellas se fusionarían.
    world = mundo_cargado(replace(HEXAGON_REAL, **{campo: True}))
    world.update(Vector2())
    assert circulos_en_la_cola(world) == 0
