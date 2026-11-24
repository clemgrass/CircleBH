"""Tests de los patrones de movimiento: seek, coulomb y orbit (ADR 0021)."""

import math
from dataclasses import replace

import pytest
from pygame.math import Vector2

from circlebh.balance import BALANCE, CoulombSpec, EnemySpec, OrbitSpec, SeekSpec
from circlebh.world.clock import STEP
from circlebh.world.danger import Danger
from circlebh.world.enemy import Enemy
from circlebh.world.patterns import Context, Coulomb, Orbit, Seek, make_pattern

HEXAGON = BALANCE.enemies["hexagon"]
SOLO_COULOMB = replace(HEXAGON, patterns=(CoulombSpec(),))


def contexto(
    neighbors: list[Enemy] | None = None,
    player_charge: float = 0.0,
    player_velocity: Vector2 | None = None,
) -> Context:
    return Context(
        player_position=Vector2(),
        player_velocity=player_velocity or Vector2(),
        player_charge=player_charge,
        charges=BALANCE.charges,
        neighbors=neighbors or [],
    )


def test_make_pattern_elige_la_clase_por_su_spec() -> None:
    assert isinstance(make_pattern(SeekSpec(strength=1.0)), Seek)
    assert isinstance(make_pattern(CoulombSpec()), Coulomb)


# --- seek ---


def test_seek_apunta_al_jugador_con_strength() -> None:
    enemy = Enemy(HEXAGON, Vector2(300, 0))
    a = Seek(SeekSpec(strength=240.0)).acceleration(enemy, contexto())
    assert tuple(a) == pytest.approx((-240.0, 0.0))


def test_seek_encima_del_jugador_es_cero() -> None:
    enemy = Enemy(HEXAGON, Vector2())
    assert Seek(SeekSpec(strength=240.0)).acceleration(enemy, contexto()) == Vector2()


def test_seek_no_depende_de_la_velocidad() -> None:
    quieto = Enemy(HEXAGON, Vector2(0, 300))
    rapido = Enemy(HEXAGON, Vector2(0, 300))
    rapido.velocity = Vector2(100, 0)
    seek = Seek(SeekSpec(strength=240.0))
    assert seek.acceleration(quieto, contexto()) == seek.acceleration(
        rapido, contexto()
    )


# --- coulomb ---


def test_herido_empuja_menos() -> None:
    a = Enemy(SOLO_COULOMB, Vector2(0, 0))
    sano = Enemy(SOLO_COULOMB, Vector2(100, 0))
    herido = Enemy(SOLO_COULOMB, Vector2(100, 0))
    for k in range(3):
        herido.remove_edge(k)
    coulomb = Coulomb()
    por_el_sano = coulomb.acceleration(a, contexto([sano])).length()
    por_el_herido = coulomb.acceleration(a, contexto([herido])).length()
    assert por_el_herido < por_el_sano


def test_lo_que_recibe_no_depende_de_sus_lineas() -> None:
    # A 100 unidades el núcleo no alcanza (d₀ = 57,6), y el jugador no tiene carga: solo
    # queda Coulomb, k·qₐ·q_b / mₐ, y qₐ / mₐ = charge_per_line.
    vecino = Enemy(SOLO_COULOMB, Vector2(100, 0))
    sano = Enemy(SOLO_COULOMB, Vector2(0, 0))
    herido = Enemy(SOLO_COULOMB, Vector2(0, 0))
    for k in range(3):
        herido.remove_edge(k)
    coulomb = Coulomb()
    assert tuple(coulomb.acceleration(herido, contexto([vecino]))) == pytest.approx(
        tuple(coulomb.acceleration(sano, contexto([vecino])))
    )


def test_no_se_repele_a_si_mismo() -> None:
    enemy = Enemy(SOLO_COULOMB, Vector2(50, 0))
    assert Coulomb().acceleration(enemy, contexto([enemy])) == Vector2()


def test_la_carga_del_jugador_lo_atrae() -> None:
    enemy = Enemy(SOLO_COULOMB, Vector2(100, 0))
    assert Coulomb().acceleration(enemy, contexto(player_charge=-14.0)).x < 0


def test_hexagono_sobre_el_jugador_quieto_se_mantiene_finito() -> None:
    # Foco de revisión 2: el hexágono real parte encima del jugador quieto, con seek y
    # su carga tirando al centro. Oscila, pero nunca da nan ni pasa `speed`.
    enemy = Enemy(HEXAGON, Vector2())
    ctx = contexto(player_charge=BALANCE.player.charge)
    for _ in range(600):
        enemy.step(enemy.acceleration(ctx))
        assert math.isfinite(enemy.position.x) and math.isfinite(enemy.position.y)
        assert enemy.velocity.length() <= HEXAGON.speed + 1e-9


def test_mas_masa_acelera_menos_con_la_misma_carga() -> None:
    # La misma fuerza del mismo vecino, dividida por una masa 10 veces mayor.
    def empuje(spec: EnemySpec) -> Vector2:
        enemy = Enemy(spec, Vector2())
        vecino = Enemy(HEXAGON, Vector2(30, 0))
        return Coulomb().acceleration(enemy, contexto([vecino]))

    liviano = empuje(SOLO_COULOMB)
    pesado = empuje(replace(SOLO_COULOMB, mass_per_line=10.0))
    assert liviano.x < 0
    assert tuple(pesado) == pytest.approx((liviano.x / 10, 0.0))


# --- orbit ---

ORBITA = OrbitSpec(radius=200.0, stiffness=4.0, tangential=0.0, follow=False)
SOLO_ORBITA = replace(HEXAGON, friction=3.0, speed=1000.0, patterns=(ORBITA,))


def test_make_pattern_elige_orbit() -> None:
    assert isinstance(make_pattern(ORBITA), Orbit)


def test_orbit_fuera_del_radio_tira_hacia_el_jugador() -> None:
    # −stiffness·(r − R)·r̂ = −4·(300 − 200)·(1, 0).
    enemy = Enemy(HEXAGON, Vector2(300, 0))
    assert tuple(Orbit(ORBITA).acceleration(enemy, contexto())) == pytest.approx(
        (-400.0, 0.0)
    )


def test_orbit_dentro_del_radio_empuja_hacia_afuera() -> None:
    enemy = Enemy(HEXAGON, Vector2(0, 150))
    assert tuple(Orbit(ORBITA).acceleration(enemy, contexto())) == pytest.approx(
        (0.0, 200.0)
    )


def test_orbit_en_el_radio_y_sin_tangencial_es_cero() -> None:
    # Negativo: en `r = R` el resorte no tira, y sin tangencial no hay nada más.
    enemy = Enemy(HEXAGON, Vector2(0, -200))
    assert Orbit(ORBITA).acceleration(enemy, contexto()).length() == pytest.approx(0)


def test_orbit_encima_del_jugador_no_divide_por_cero() -> None:
    # Borde: en `r = 0` no hay dirección radial, y vale 0, como seek.
    enemy = Enemy(HEXAGON, Vector2())
    assert Orbit(ORBITA).acceleration(enemy, contexto()) == Vector2()


def test_orbit_sin_tangencial_converge_al_radio() -> None:
    # Un resorte con roce: oscila amortiguado hasta quedar en `r = R`.
    enemy = Enemy(SOLO_ORBITA, Vector2(600, 0))
    for _ in range(round(10 / STEP)):
        enemy.step(enemy.acceleration(contexto()))
    assert enemy.position.length() == pytest.approx(ORBITA.radius, abs=0.5)


# --- el octágono: orbit con empuje tangencial ---

CONVERGER = round(10 / STEP)
MEDIR = round(5 / STEP)


def octagono() -> EnemySpec:
    # Se lee en cada test, para que un balance sin octágono no rompa la colección.
    return BALANCE.enemies["octagon"]


def con_tangencial(spec: EnemySpec, tangential: float) -> EnemySpec:
    patterns = tuple(
        replace(p, tangential=tangential) if isinstance(p, OrbitSpec) else p
        for p in spec.patterns
    )
    return replace(spec, patterns=patterns)


type Pose = tuple[Vector2, Vector2]
"""La posición y la velocidad en un paso, con el jugador en el origen."""


def orbitar(spec: EnemySpec) -> list[Pose]:
    """Lo deja converger solo, y devuelve su pose en cada paso mientras mide."""
    enemy = Enemy(spec, Vector2(600, 0))
    context = contexto(player_charge=BALANCE.player.charge)
    for _ in range(CONVERGER):
        enemy.step(enemy.acceleration(context))
    poses = []
    for _ in range(MEDIR):
        enemy.step(enemy.acceleration(context))
        poses.append((Vector2(enemy.position), Vector2(enemy.velocity)))
    return poses


def giro(pose: Pose) -> float:
    """La velocidad angular alrededor del jugador: `p × v / |p|²`."""
    p, v = pose
    return p.cross(v) / p.length_squared()


def radio_del_orbit(spec: EnemySpec) -> float:
    return next(p.radius for p in spec.patterns if isinstance(p, OrbitSpec))


def test_octagono_se_mantiene_en_el_radio() -> None:
    spec = octagono()
    radio = radio_del_orbit(spec)
    assert all(abs(p.length() - radio) < 20 for p, _ in orbitar(spec))


def test_orbit_con_tangencial_gira_antihorario() -> None:
    assert all(giro(pose) > 0 for pose in orbitar(octagono()))


def test_tangencial_negativo_gira_horario() -> None:
    # Borde: el signo del empuje decide el sentido, nada más.
    assert all(giro(pose) < 0 for pose in orbitar(con_tangencial(octagono(), -120.0)))


def test_tangencial_cero_no_gira() -> None:
    # Negativo: en el anillo, sin empuje tangencial, el roce lo deja quieto.
    assert all(abs(giro(pose)) < 1e-3 for pose in orbitar(SOLO_ORBITA))


def test_octagono_alcanza_a_seguir_al_jugador() -> None:
    # Decisión 61: para girar mientras te sigue necesita tu rapidez más la de su giro,
    # `tangential / friction`. Con menos, el cerco queda detrás de ti (Foco 10).
    spec = octagono()
    orbit = next(p for p in spec.patterns if isinstance(p, OrbitSpec))
    assert spec.speed >= BALANCE.player.speed + orbit.tangential / spec.friction


# --- follow: el roce medido desde el jugador ---

SIGUE = replace(ORBITA, follow=True)
CORRIENDO = Vector2(100, 0)


def test_orbit_follow_suma_el_roce_por_la_velocidad_del_jugador() -> None:
    # En `r = R` y sin tangencial, solo queda `friction · u`: el roce total pasa a ser
    # `−friction · (v − u)`.
    enemy = Enemy(SOLO_ORBITA, Vector2(0, -200))
    a = Orbit(SIGUE).acceleration(enemy, contexto(player_velocity=CORRIENDO))
    assert tuple(a) == pytest.approx((SOLO_ORBITA.friction * 100, 0.0))


def test_orbit_follow_con_el_jugador_quieto_da_lo_mismo() -> None:
    # Borde: con `u = 0`, seguir al jugador no agrega nada.
    enemy = Enemy(SOLO_ORBITA, Vector2(300, 40))
    assert Orbit(SIGUE).acceleration(enemy, contexto()) == Orbit(ORBITA).acceleration(
        enemy, contexto()
    )


def test_orbit_sin_follow_ignora_la_velocidad_del_jugador() -> None:
    # Negativo: el triángulo y el pentágono no cambian.
    enemy = Enemy(SOLO_ORBITA, Vector2(300, 40))
    assert Orbit(ORBITA).acceleration(
        enemy, contexto(player_velocity=CORRIENDO)
    ) == Orbit(ORBITA).acceleration(enemy, contexto())


# --- El peligro del infinito (#65) ---


def test_hexagono_con_peligro_llega_a_m_veces_su_velocidad() -> None:
    # `seek` escala con el peligro, y su tope también: sin eso, el hexágono ya va
    # justo a su tope (240/2 = 120) y no se apuraría.
    spec = replace(HEXAGON, patterns=(SeekSpec(strength=240.0),))
    rapido = Enemy(spec, Vector2(10_000, 0), Danger(speed=1.5))
    normal = Enemy(spec, Vector2(10_000, 0))
    for _ in range(round(5 / STEP)):
        for enemy in (rapido, normal):
            enemy.step(enemy.acceleration(contexto()))
    assert rapido.velocity.length() == pytest.approx(180, rel=0.01)
    assert normal.velocity.length() == pytest.approx(120, rel=0.01)


def test_orbit_escala_el_resorte_con_el_peligro() -> None:
    # A 100 del anillo, el resorte tira con `stiffness · 100`, y con el doble de peligro,
    # con el doble.
    enemy = Enemy(SOLO_ORBITA, Vector2(300, 0), Danger(speed=2.0))
    a = Orbit(ORBITA).acceleration(enemy, contexto())
    assert tuple(a) == pytest.approx((-2 * ORBITA.stiffness * 100, 0.0))


def test_orbita_no_escala_el_arrastre() -> None:
    # Borde: el arrastre `friction · u` sigue al jugador. Si escalara, el cerco
    # correría más que él.
    enemy = Enemy(SOLO_ORBITA, Vector2(0, -200), Danger(speed=2.0))
    a = Orbit(SIGUE).acceleration(enemy, contexto(player_velocity=CORRIENDO))
    assert tuple(a) == pytest.approx((SOLO_ORBITA.friction * 100, 0.0))


def test_coulomb_no_cambia_con_el_peligro() -> None:
    # Negativo: la ley de cargas es una sola (ADR 0021). Si un enemigo nuevo cargara
    # más, la fuerza entre uno nuevo y uno viejo dejaría de ser pareja.
    vecino = Enemy(SOLO_COULOMB, Vector2(60, 0))
    rapido = Enemy(SOLO_COULOMB, Vector2(), Danger(speed=2.0))
    normal = Enemy(SOLO_COULOMB, Vector2())
    coulomb = Coulomb()
    assert coulomb.acceleration(rapido, contexto([vecino])) == coulomb.acceleration(
        normal, contexto([vecino])
    )
