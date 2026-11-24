"""Tests del enjambre: el paso simultáneo, la red de seguridad y la red triangular
(ADR 0021)."""

import math
import random
from dataclasses import replace
from itertools import combinations, pairwise

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st
from pygame.math import Vector2

from circlebh.balance import BALANCE, CoulombSpec, EnemySpec, OrbitSpec
from circlebh.world.actions import Spiral, SpiralState, step_actions
from circlebh.world.clock import STEP
from circlebh.world.enemy import Enemy
from circlebh.world.swarm import lattice, separate, step_swarm

HEXAGON = BALANCE.enemies["hexagon"]
SOLO_COULOMB = replace(HEXAGON, patterns=(CoulombSpec(),))
QUIETO = replace(HEXAGON, speed=0.0, patterns=())
"""No se mueve por sí mismo: solo la red de seguridad lo corre."""
CONTACTO = 2 * HEXAGON.radius
CELDA = BALANCE.charges.cutoff


def paso(enemies: list[Enemy], player_charge: float = 0.0) -> int:
    return step_swarm(enemies, Vector2(), Vector2(), player_charge, BALANCE.charges)


# --- El paso simultáneo ---


def test_dos_sueltos_se_alejan() -> None:
    a, b = Enemy(SOLO_COULOMB, Vector2(0, 0)), Enemy(SOLO_COULOMB, Vector2(80, 0))
    for _ in range(30):
        paso([a, b])
    assert a.position.distance_to(b.position) > 80


coordenada = st.floats(min_value=-150, max_value=150)


@given(
    puntos=st.lists(st.tuples(coordenada, coordenada), min_size=2, max_size=12),
    data=st.data(),
)
def test_orden_de_la_lista_no_importa(
    puntos: list[tuple[float, float]], data: st.DataObject
) -> None:
    # Dos en el mismo punto exacto quedan fuera: ahí la dirección fija sí depende del
    # orden (spec, "La red de seguridad").
    posiciones = [Vector2(p) for p in puntos]
    for p, q in combinations(posiciones, 2):
        assume(p.distance_to(q) > 1e-3)
    originales = [Enemy(HEXAGON, p) for p in posiciones]
    copias = [Enemy(HEXAGON, p) for p in posiciones]
    orden = data.draw(st.permutations(range(len(copias))))
    paso(originales, BALANCE.player.charge)
    paso([copias[i] for i in orden], BALANCE.player.charge)
    for original, copia in zip(originales, copias, strict=True):
        assert tuple(copia.position) == pytest.approx(
            tuple(original.position), abs=1e-9
        )


def test_solo_entran_los_vivos() -> None:
    # Foco de revisión 1: un muerto tiene masa 0; si entrara, dividiría por cero.
    vivo = Enemy(HEXAGON, Vector2(100, 0))
    muerto = Enemy(HEXAGON, Vector2(150, 0))
    for k in range(HEXAGON.shape.line_count):
        muerto.remove_edge(k)
    paso([vivo, muerto])
    assert muerto.position == Vector2(150, 0)


# --- La red de seguridad ---


def test_superpuestos_quedan_tangentes_y_sin_acercarse() -> None:
    a, b = Enemy(QUIETO, Vector2(0, 0)), Enemy(QUIETO, Vector2(30, 0))
    a.velocity, b.velocity = Vector2(10, 0), Vector2(-10, 0)
    assert separate([a, b], CELDA) == 1
    assert a.position.distance_to(b.position) == pytest.approx(CONTACTO)
    assert (b.velocity - a.velocity).x >= 0


def test_misma_posicion_no_divide_por_cero() -> None:
    a, b = Enemy(QUIETO, Vector2(5, 5)), Enemy(QUIETO, Vector2(5, 5))
    separate([a, b], CELDA)
    assert a.position.distance_to(b.position) == pytest.approx(CONTACTO)
    assert all(math.isfinite(c) for c in (*a.position, *b.position))


@given(
    cuerpos=st.lists(
        st.tuples(
            coordenada,
            coordenada,
            st.sampled_from([HEXAGON.radius, 10.0, 200.0]),
        ),
        max_size=20,
    )
)
def test_corrige_los_mismos_pares_que_la_fuerza_bruta(
    cuerpos: list[tuple[float, float, float]],
) -> None:
    # Con tamaños mezclados, como un jefe entre hexágonos: un cuerpo más grande que la
    # celda no puede quedar fuera de la red de seguridad.
    enemies = [Enemy(replace(QUIETO, radius=r), Vector2(x, y)) for x, y, r in cuerpos]
    superpuestos = sum(
        1
        for a, b in combinations(enemies, 2)
        if a.position.distance_to(b.position) < a.radius + b.radius
    )
    assert separate(enemies, CELDA) == superpuestos


def test_separados_no_se_tocan() -> None:
    a, b = Enemy(QUIETO, Vector2(0, 0)), Enemy(QUIETO, Vector2(100, 0))
    assert separate([a, b], CELDA) == 0
    assert (a.position, b.position) == (Vector2(0, 0), Vector2(100, 0))


def test_la_bala_golpea_al_que_movio_el_empujon() -> None:
    # A estaba en 115 al empezar el paso, y la red de seguridad lo corre a 105. Una bala
    # corta, de 88 a 89, solo cruza su arista izquierda si el tramo se mide de
    # `previous` (115) a `position` (105): de −27 a −16, con la arista en −20,8.
    a = Enemy(QUIETO, Vector2(115, 0))
    b = Enemy(QUIETO, Vector2(143, 0))
    separate([a, b], CELDA)
    assert a.position.x == pytest.approx(105)
    assert a.previous == Vector2(115, 0)
    assert a.hit_by(Vector2(88, 0), Vector2(89, 0)) is not None


# --- El anclado ---

ANCLADO = replace(QUIETO, radius=40.0, anchored=True)
"""Como la estrella: nada lo mueve, ni las fuerzas ni la red de seguridad."""


def test_red_de_seguridad_no_mueve_al_anclado() -> None:
    estrella = Enemy(ANCLADO, Vector2(0, 0))
    hexagono = Enemy(QUIETO, Vector2(50, 0))
    assert separate([estrella, hexagono], CELDA) == 1
    assert estrella.position == Vector2(0, 0)
    assert hexagono.position.x == pytest.approx(ANCLADO.radius + HEXAGON.radius)


def test_choque_contra_anclado_le_quita_toda_la_velocidad_de_acercamiento() -> None:
    estrella = Enemy(ANCLADO, Vector2(0, 0))
    hexagono = Enemy(QUIETO, Vector2(50, 0))
    hexagono.velocity = Vector2(-30, 12)
    separate([estrella, hexagono], CELDA)
    assert hexagono.velocity.x == pytest.approx(0)
    assert hexagono.velocity.y == pytest.approx(12)
    assert estrella.velocity == Vector2()


def test_dos_anclados_encimados_quedan_donde_estan() -> None:
    a, b = Enemy(ANCLADO, Vector2(0, 0)), Enemy(ANCLADO, Vector2(30, 0))
    assert separate([a, b], CELDA) == 0
    assert (a.position, b.position) == (Vector2(0, 0), Vector2(30, 0))


def test_anclado_con_giro_no_se_corre_al_perder_una_linea() -> None:
    # Un anclado no gira aunque el balance le dé `spin`, así que perder una línea no
    # lo pasa a su nuevo centro de masa (ADR 0027, L2): nada lo mueve.
    estrella = Enemy(replace(ANCLADO, spin=1.0), Vector2(0, 0))
    estrella.remove_edge(0)
    paso([estrella])
    assert estrella.position == Vector2(0, 0)
    assert estrella.velocity == Vector2()
    assert estrella.angle == 0.0


def test_anclado_no_se_mueve_con_fuerzas() -> None:
    # Con carga y patrones, sus vecinos lo empujan por Coulomb y por el núcleo duro.
    cargado = replace(SOLO_COULOMB, radius=40.0, anchored=True)
    estrella = Enemy(cargado, Vector2(0, 0))
    vecinos = [Enemy(SOLO_COULOMB, p) for p in lattice(Vector2(20, 0), 6, 55)]
    for _ in range(60):
        paso([estrella, *vecinos], player_charge=-14.0)
    assert estrella.position == Vector2(0, 0)
    assert estrella.velocity == Vector2()


# --- El fantasma ---

FANTASMA = BALANCE.enemies["red_star"]
"""La gran estrella roja: los enemigos la atraviesan (decisión 40)."""


def test_fantasma_no_mueve_ni_frena_al_enjambre() -> None:
    # El hexágono está dentro de su envolvente: sin ser fantasma, la red de seguridad
    # lo sacaría a 174 y el núcleo duro lo empujaría. Va sin roce, para que su
    # velocidad solo pueda cambiar por la estrella.
    estrella = Enemy(FANTASMA, Vector2(0, 0))
    hexagono = Enemy(replace(SOLO_COULOMB, friction=0.0), Vector2(50, 0))
    hexagono.velocity = Vector2(-60, 0)
    assert paso([estrella, hexagono]) == 0
    assert hexagono.velocity == Vector2(-60, 0)
    assert hexagono.position == Vector2(50 - 60 * STEP, 0)


def test_el_fantasma_no_se_mueve() -> None:
    estrella = Enemy(FANTASMA, Vector2(0, 0))
    vecinos = [Enemy(SOLO_COULOMB, p) for p in lattice(Vector2(), 12, 55)]
    for _ in range(30):
        paso([estrella, *vecinos], player_charge=-14.0)
    assert estrella.position == Vector2(0, 0)


# --- La red triangular ---


def test_lattice_sin_superponerse() -> None:
    puntos = lattice(Vector2(), 300, 60)
    assert len(puntos) == 300
    assert Vector2() not in puntos
    assert min(p.distance_to(q) for p, q in combinations(puntos, 2)) >= 60 - 1e-9


def test_lattice_empieza_por_los_mas_cercanos() -> None:
    # Los 6 vecinos del centro, a una distancia `spacing`, van primero.
    puntos = lattice(Vector2(10, 10), 7, 60)
    assert [p.distance_to(Vector2(10, 10)) for p in puntos[:6]] == pytest.approx(
        [60] * 6
    )
    assert puntos[6].distance_to(Vector2(10, 10)) > 60


# --- El círculo (#59): cae en espiral y reparte al enjambre ---


def paso_real(enemies: list[Enemy]) -> None:
    """Un paso como el del mundo, con el jugador quieto en el origen y su carga real:
    primero las acciones, como la espiral del círculo, y después el enjambre."""
    step_actions(enemies, Vector2(), random.Random(0), [], BALANCE.enemy_bullet)
    step_swarm(enemies, Vector2(), Vector2(), BALANCE.player.charge, BALANCE.charges)


def dispersion(enemies: list[Enemy]) -> float:
    """La distancia media de cada uno al centroide del grupo."""
    centro = sum((e.position for e in enemies), Vector2()) / len(enemies)
    return sum(e.position.distance_to(centro) for e in enemies) / len(enemies)


def test_dispersa_un_grupo() -> None:
    # El círculo nace bajo el grupo. Al cruzarlo y llevárselo, lo atrae y lo junta
    # (decisión 57); al soltarlo, lo repele. Por eso se mide 2 s después de que empieza
    # a girar, y se compara contra el mismo tiempo sin círculo y con uno sin carga. El
    # choque solo ya los corre un poco: lo que los abre es la carga.
    real = BALANCE.enemies["circle"]

    def simular(circulo: EnemySpec | None, pasos: int) -> float:
        grupo = [Enemy(HEXAGON, p) for p in lattice(Vector2(250, 0), 7, 50)]
        enemies = list(grupo)
        if circulo is not None:
            enemies.append(Enemy(circulo, Vector2(250, -160)))
        for _ in range(pasos):
            paso_real(enemies)
        return dispersion(grupo)

    def hasta_soltarlos() -> int:
        grupo = [Enemy(HEXAGON, p) for p in lattice(Vector2(250, 0), 7, 50)]
        circulo = Enemy(real, Vector2(250, -160))
        (espiral,) = circulo.actions
        assert isinstance(espiral, Spiral)
        for n in range(round(30 / STEP)):
            if espiral.state is SpiralState.CIRCLING:
                return n
            paso_real([*grupo, circulo])
        raise AssertionError("el círculo nunca los soltó")

    pasos = hasta_soltarlos() + round(2 / STEP)
    con_carga = simular(real, pasos)
    assert con_carga > simular(None, pasos)
    assert con_carga > simular(replace(real, charge_per_line=0.0), pasos)


# --- el cerco del octágono (decisión 61) ---


def sin_follow(spec: EnemySpec) -> EnemySpec:
    patterns = tuple(
        replace(p, follow=False) if isinstance(p, OrbitSpec) else p
        for p in spec.patterns
    )
    return replace(spec, patterns=patterns)


def cerco_corriendo(spec: EnemySpec) -> tuple[float, float]:
    """10 octágonos y el jugador a toda velocidad en línea recta durante 30 s. Devuelve,
    desde los 10 s, el menor arco que cubren alrededor del jugador, en grados, y la menor
    distancia de uno al jugador."""
    enemies = [Enemy(spec, p) for p in lattice(Vector2(), 10, 90.0)]
    velocidad = Vector2(BALANCE.player.speed, 0)
    arco, cerca = 360.0, math.inf
    for k in range(round(30 / STEP)):
        jugador = velocidad * (k * STEP)
        step_swarm(enemies, jugador, velocidad, BALANCE.player.charge, BALANCE.charges)
        if k * STEP < 10:
            continue
        angulos = sorted(
            math.atan2(e.position.y - jugador.y, e.position.x - jugador.x) % math.tau
            for e in enemies
        )
        huecos = [b - a for a, b in pairwise(angulos)]
        huecos.append(angulos[0] + math.tau - angulos[-1])
        arco = min(arco, math.degrees(math.tau - max(huecos)))
        cerca = min(cerca, min(e.position.distance_to(jugador) for e in enemies))
    return arco, cerca


def test_cerco_aguanta_con_el_jugador_corriendo() -> None:
    octagono = BALANCE.enemies["octagon"]
    arco, cerca = cerco_corriendo(octagono)
    assert arco >= 240
    assert cerca > BALANCE.player.radius + octagono.radius


def test_cerco_no_toca_al_jugador_que_da_media_vuelta() -> None:
    # Bug: al dar media vuelta, el de adelante se le viene encima a `2·u`. Con un
    # resorte blando, pasaba de largo, caía en el pozo de la carga del jugador y `follow`
    # lo llevaba pegado: en la partida, te mataba por esquivar.
    octagono = BALANCE.enemies["octagon"]
    u = Vector2(BALANCE.player.speed, 0)
    enemies = []
    for k in range(10):
        enemy = Enemy(octagono, Vector2(200, 0).rotate_rad(math.tau * k / 10))
        enemy.velocity = Vector2(u)
        enemies.append(enemy)
    jugador = Vector2()
    for paso in range(round(30 / STEP)):
        velocidad = u if paso * STEP % 4 < 2 else -u
        jugador += velocidad * STEP
        step_swarm(enemies, jugador, velocidad, BALANCE.player.charge, BALANCE.charges)
        assert all(
            e.position.distance_to(jugador) > BALANCE.player.radius + octagono.radius
            for e in enemies
        )


def test_sin_follow_el_cerco_se_queda_atras() -> None:
    # Negativo: con el roce contra el suelo, el resorte radial no arrastra a los de los
    # costados, y el cerco se aplasta detrás del jugador.
    arco, _ = cerco_corriendo(sin_follow(BALANCE.enemies["octagon"]))
    assert arco < 90
