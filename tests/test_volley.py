"""Tests de la ráfaga del pentágono: observa, avisa congelándose, dispara y se recupera.

Dispara una bala por vértice, y una ráfaga de `shots` salvas mientras gira: cada punta
deja un brazo de la espiral de Arquímedes `r = (v/ω)·θ`. Solo dispara con el jugador
entre `min_distance` y `max_distance` (decisiones 31 a 33 de la spec de la 0.2.0).
"""

import math
import random
from collections.abc import Sequence
from itertools import groupby, pairwise

import pytest
from pygame.math import Vector2

from circlebh.balance import BALANCE, VolleySpec
from circlebh.settings import load_settings
from circlebh.world.actions import ActionContext, Volley, VolleyState, make_action
from circlebh.world.clock import STEP
from circlebh.world.enemy import Enemy
from circlebh.world.enemy_bullets import EnemyBullet
from circlebh.world.events import Telegraph

PENTAGON = BALANCE.enemies["pentagon"]
VOLLEY = PENTAGON.actions[0]
assert isinstance(VOLLEY, VolleySpec)
BULLET = BALANCE.enemy_bullet
DISTANCIA = (VOLLEY.min_distance + VOLLEY.max_distance) / 2
"""Una distancia al jugador desde la que dispara."""


def pasos(seconds: float) -> int:
    return round(seconds / STEP)


AVISO = pasos(VOLLEY.telegraph)
INTERVALO = pasos(VOLLEY.interval)
RAFAGA = VOLLEY.shots * INTERVALO
"""Los pasos que dura la ráfaga entera."""


def pentagono(distance: float = DISTANCIA) -> Enemy:
    """Un pentágono a `distance` del jugador, que está en el origen."""
    return Enemy(PENTAGON, Vector2(distance, 0))


def rafaga(enemy: Enemy) -> Volley:
    action = enemy.actions[0]
    assert isinstance(action, Volley)
    return action


def contexto(
    enemies: Sequence[Enemy],
    bullets: list[EnemyBullet],
    player: Vector2 | None = None,
) -> ActionContext:
    return ActionContext(
        player_position=player or Vector2(),
        enemies=enemies,
        rng=random.Random(1),
        bullets=bullets,
        bullet_spec=BULLET,
    )


def avanzar(
    enemy: Enemy,
    steps: int,
    bullets: list[EnemyBullet] | None = None,
    player: Vector2 | None = None,
) -> list[VolleyState]:
    """El estado de la ráfaga en cada paso. El pentágono gira, pero no se traslada."""
    bullets = [] if bullets is None else bullets
    volley = rafaga(enemy)
    states = []
    for _ in range(steps):
        volley.update(enemy, contexto([enemy], bullets, player))
        enemy.velocity = Vector2()
        enemy.step(Vector2())
        states.append(volley.state)
    return states


def tramos(states: list[VolleyState]) -> list[tuple[VolleyState, int]]:
    return [(state, len(list(run))) for state, run in groupby(states)]


def vertices(enemy: Enemy) -> set[tuple[float, float]]:
    """Los vértices que le quedan, como tuplas redondeadas para compararlos."""
    return {(round(p.x, 9), round(p.y, 9)) for line in enemy.lines() for p in line}


def test_make_action_elige_la_clase_por_su_spec() -> None:
    assert isinstance(make_action(VOLLEY), Volley)


def test_parte_observando() -> None:
    assert rafaga(pentagono()).state is VolleyState.WATCHING


# --- Las etapas ---


def test_etapas_en_orden_y_con_su_duracion() -> None:
    recuperacion = pasos(VOLLEY.cooldown)
    states = avanzar(pentagono(), AVISO + RAFAGA + recuperacion + 1)
    assert tramos(states) == [
        (VolleyState.TELEGRAPHING, AVISO),
        (VolleyState.FIRING, RAFAGA),
        (VolleyState.RECOVERING, recuperacion),
        # Al terminar la recuperación, ya mira en ese mismo paso.
        (VolleyState.TELEGRAPHING, 1),
    ]


def test_avisar_emite_telegraph_una_vez() -> None:
    enemy = pentagono()
    volley = rafaga(enemy)
    events = []
    for _ in range(AVISO + RAFAGA):
        events += volley.update(enemy, contexto([enemy], []))
    assert events == [Telegraph(enemy)]


def test_no_avisa_desde_fuera_de_la_vista() -> None:
    states = avanzar(pentagono(VOLLEY.max_distance + 1), AVISO + RAFAGA)
    assert set(states) == {VolleyState.WATCHING}


def test_avisa_justo_en_max_distance() -> None:
    assert avanzar(pentagono(VOLLEY.max_distance), 1) == [VolleyState.TELEGRAPHING]


def test_no_dispara_a_quemarropa() -> None:
    # Foco 1: una bala que nace encima del jugador no se puede esquivar.
    bullets: list[EnemyBullet] = []
    states = avanzar(pentagono(VOLLEY.min_distance - 1), AVISO + RAFAGA, bullets)
    assert set(states) == {VolleyState.WATCHING}
    assert bullets == []


def test_avisa_justo_en_min_distance() -> None:
    assert avanzar(pentagono(VOLLEY.min_distance), 1) == [VolleyState.TELEGRAPHING]


def test_quemarropa_al_soltarse_no_dispara() -> None:
    # Borde: avisa de lejos, pero el jugador llega encima justo al terminar el aviso.
    enemy = pentagono()
    bullets: list[EnemyBullet] = []
    avanzar(enemy, AVISO, bullets)
    cerca = enemy.position + Vector2(0, VOLLEY.min_distance - 1)
    assert avanzar(enemy, 1, bullets, player=cerca) == [VolleyState.WATCHING]
    assert bullets == []


def test_rafaga_se_corta_si_el_jugador_se_acerca() -> None:
    # Cada salva vuelve a mirar la distancia: a quemarropa, la ráfaga termina.
    enemy = pentagono()
    bullets: list[EnemyBullet] = []
    avanzar(enemy, AVISO + 1, bullets)
    assert len(bullets) == PENTAGON.shape.vertices
    cerca = enemy.position + Vector2(0, VOLLEY.min_distance - 1)
    states = avanzar(enemy, RAFAGA, bullets, player=cerca)
    assert VolleyState.FIRING not in states[INTERVALO - 1 :]
    assert len(bullets) == PENTAGON.shape.vertices


# --- El giro ---


def test_durante_el_aviso_no_gira() -> None:
    # Decisión 31: se congela, y sus puntas muestran hacia dónde van a salir las balas.
    enemy = pentagono()
    volley = rafaga(enemy)
    angulos = []
    for _ in range(AVISO):
        volley.update(enemy, contexto([enemy], []))
        assert volley.omega == 0.0
        enemy.step(Vector2())
        angulos.append(enemy.angle)
    assert len(set(angulos)) == 1


def test_observando_y_disparando_gira_con_su_spin() -> None:
    enemy = pentagono()
    volley = rafaga(enemy)
    assert volley.omega is None
    avanzar(enemy, AVISO + 1)
    assert volley.state is VolleyState.FIRING
    assert volley.omega is None


# --- Las balas ---


def test_dispara_una_bala_por_vertice() -> None:
    enemy = pentagono()
    bullets: list[EnemyBullet] = []
    avanzar(enemy, AVISO, bullets)
    assert bullets == []
    rafaga(enemy).update(enemy, contexto([enemy], bullets))
    assert len(bullets) == PENTAGON.shape.vertices
    assert {(round(b.position.x, 9), round(b.position.y, 9)) for b in bullets} == (
        vertices(enemy)
    )


def test_angulos_de_las_balas() -> None:
    # La bala `k` sale del vértice `k`, en `θ + π/2 + 2πk/n` (`polygon.py`), a `speed`.
    enemy = pentagono()
    enemy.angle = 0.3
    avanzar(enemy, AVISO)
    bullets: list[EnemyBullet] = []
    rafaga(enemy).update(enemy, contexto([enemy], bullets))
    assert enemy.angle == 0.3
    n = PENTAGON.shape.vertices
    esperados = [enemy.angle + math.pi / 2 + math.tau * k / n for k in range(n)]
    for bullet, angle in zip(bullets, esperados, strict=True):
        esperado = Vector2(math.cos(angle), math.sin(angle)) * BULLET.speed
        assert tuple(bullet.velocity) == pytest.approx(tuple(esperado))


def test_rafaga_de_shots_salvas() -> None:
    enemy = pentagono()
    bullets: list[EnemyBullet] = []
    avanzar(enemy, AVISO, bullets)
    contadas = []
    for _ in range(RAFAGA):
        avanzar(enemy, 1, bullets)
        contadas.append(len(bullets) // PENTAGON.shape.vertices)
    # Una salva al empezar y otra cada `interval`.
    assert contadas == [1 + k // INTERVALO for k in range(RAFAGA)]
    assert len(bullets) == VOLLEY.shots * PENTAGON.shape.vertices


def test_salvas_siguen_el_giro() -> None:
    # Decisión 32: entre dos salvas gira `ω·interval`, y cada punta deja un brazo de
    # espiral.
    enemy = pentagono()
    bullets: list[EnemyBullet] = []
    avanzar(enemy, AVISO + RAFAGA, bullets)
    n = PENTAGON.shape.vertices
    primeras = [bullets[k * n].velocity for k in range(VOLLEY.shots)]
    giro = PENTAGON.spin * INTERVALO * STEP
    for a, b in pairwise(primeras):
        assert math.radians(a.angle_to(b)) == pytest.approx(giro)


def test_herido_dispara_solo_desde_sus_vertices() -> None:
    # Sin las aristas 0 y 1, el vértice 1 ya no existe: dispara 4 balas, no 5.
    enemy = pentagono()
    enemy.remove_edge(0)
    enemy.remove_edge(1)
    avanzar(enemy, AVISO)
    bullets: list[EnemyBullet] = []
    rafaga(enemy).update(enemy, contexto([enemy], bullets))
    assert len(bullets) == PENTAGON.shape.vertices - 1
    assert {(round(b.position.x, 9), round(b.position.y, 9)) for b in bullets} == (
        vertices(enemy)
    )


# --- Coherencia del balance ---


def rafagas() -> list[tuple[str, VolleySpec]]:
    return [
        (nombre, action)
        for nombre, spec in BALANCE.enemies.items()
        for action in spec.actions
        if isinstance(action, VolleySpec)
    ]


@pytest.mark.parametrize(("nombre", "volley"), rafagas())
def test_max_distance_cabe_en_la_vista(nombre: str, volley: VolleySpec) -> None:
    # Decisión 33: nunca dispara desde fuera de la pantalla.
    camera = load_settings().camera
    reach = volley.max_distance + BALANCE.enemies[nombre].radius
    assert reach <= camera.fov / 2 - Vector2(camera.offset).length()


@pytest.mark.parametrize(("nombre", "volley"), rafagas())
def test_la_bala_no_nace_encima_del_jugador(nombre: str, volley: VolleySpec) -> None:
    # Herido, el centro de masa se corre: un vértice queda a lo más a `2·radius` de él.
    reach = BALANCE.player.radius + BULLET.radius
    assert volley.min_distance > 2 * BALANCE.enemies[nombre].radius + reach
    assert volley.min_distance < volley.max_distance


@pytest.mark.parametrize(("nombre", "volley"), rafagas())
def test_cada_etapa_dura_al_menos_un_paso(nombre: str, volley: VolleySpec) -> None:
    for seconds in (volley.telegraph, volley.interval, volley.cooldown):
        assert pasos(seconds) >= 1
    assert volley.shots >= 1
