"""Tests del arma punto: una bala que se dispara sola al centro del enemigo más cercano."""

import random
from dataclasses import replace

import pytest
from pygame.math import Vector2

from circlebh.balance import (
    BALANCE,
    AdvanceSpec,
    EnemySpec,
    SamplingSpec,
    StarPolygonShape,
)
from circlebh.pilot import pilot_intent
from circlebh.world.clock import STEP
from circlebh.world.enemy import Enemy
from circlebh.world.events import Hit
from circlebh.world.game import World
from circlebh.world.weapons import (
    Bullet,
    ProjectileWeapon,
    check_weapons,
    intercept,
    nearest,
)

# 0,5 s = 30 pasos entre disparos; 600 / 60 = 10 unidades por paso; 700 / 10 = 70 pasos
# de vida.
POINT = BALANCE.weapons["point"]
SPEED = 600.0
SPEC = replace(
    POINT,
    cooldown=0.5,
    advance=AdvanceSpec(coefficient=SPEED, degree=1),
    reach=700.0,
)
COOLDOWN = 30
VIDA = 70
# Sin patrones ni carga: aquí solo importa dónde está.
HEXAGON = EnemySpec(
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


def enemigo(x: float, y: float) -> Enemy:
    return Enemy(HEXAGON, Vector2(x, y))


# --- La bala ---


@pytest.mark.parametrize("pasos", [0, 1, 30])
def test_bala_avanza_en_linea_recta(pasos: int) -> None:
    origen, direccion = Vector2(1, 2), Vector2(0, -1)
    bullet = Bullet(origen, direccion, SPEC)
    for _ in range(pasos):
        bullet.step()
    # p(t) = p₀ + v·t·û
    assert tuple(bullet.position) == pytest.approx(
        tuple(origen + direccion * SPEED * pasos * STEP)
    )
    assert bullet.position.distance_to(origen) == pytest.approx(SPEED / 60 * pasos)


def test_previous_es_la_posicion_un_paso_antes() -> None:
    bullet = Bullet(Vector2(0, 0), Vector2(1, 0), SPEC)
    assert bullet.previous == bullet.position
    bullet.step()
    antes = Vector2(bullet.position)
    bullet.step()
    assert tuple(bullet.previous) == pytest.approx(tuple(antes))


def test_bala_vence_al_recorrer_range() -> None:
    bullet = Bullet(Vector2(0, 0), Vector2(1, 0), SPEC)
    for _ in range(VIDA - 1):
        bullet.step()
    assert bullet.expired is False
    bullet.step()
    assert bullet.expired is True


# --- A quién apunta ---


def test_nearest_sin_enemigos_es_none() -> None:
    assert nearest(Vector2(0, 0), []) is None


def test_el_arma_no_le_apunta_al_fantasma() -> None:
    # Decisión 44: dentro de la gran estrella, el arma sigue apuntando al enjambre,
    # aunque el centro de la estrella esté más cerca.
    fantasma = Enemy(replace(HEXAGON, phantom=True, radius=150.0), Vector2(10, 0))
    hexagono = enemigo(0, -100)
    assert nearest(Vector2(0, 0), [fantasma, hexagono]) is hexagono
    assert nearest(Vector2(0, 0), [fantasma]) is None


def test_la_bala_le_quita_una_linea_al_fantasma() -> None:
    # Las balas del jugador sí lo golpean: así se rompe la trampa.
    fantasma = Enemy(replace(HEXAGON, phantom=True), Vector2(100, 0))
    weapon = ProjectileWeapon(SPEC)
    weapon.bullets.append(Bullet(Vector2(0, 0), Vector2(1, 0), SPEC))
    for _ in range(20):
        weapon.update(Vector2(0, 0), [fantasma])
    assert len(fantasma.edges) < HEXAGON.shape.line_count


def test_dispara_al_centro_del_mas_cercano() -> None:
    weapon = ProjectileWeapon(SPEC)
    weapon.update(Vector2(0, 0), [enemigo(500, 0), enemigo(0, -100)])
    [bullet] = weapon.bullets
    assert bullet.direction == Vector2(0, -1)


def test_empate_gana_el_primero() -> None:
    weapon = ProjectileWeapon(SPEC)
    weapon.update(Vector2(0, 0), [enemigo(100, 0), enemigo(-100, 0)])
    [bullet] = weapon.bullets
    assert bullet.direction == Vector2(1, 0)


def test_centro_sobre_el_jugador_no_dispara() -> None:
    # Negativo: la dirección es nula y no se puede normalizar.
    weapon = ProjectileWeapon(SPEC)
    weapon.update(Vector2(5, 5), [enemigo(5, 5)])
    assert weapon.bullets == []


def test_centro_casi_sobre_el_jugador_no_falla() -> None:
    # Negativo: a 1e-200, la dirección no es nula, pero su largo al cuadrado se redondea
    # a 0 y `normalize` lanzaría ValueError.
    weapon = ProjectileWeapon(SPEC)
    weapon.update(Vector2(0, 0), [enemigo(1e-200, 0)])
    assert weapon.bullets == []


def test_un_enemigo_a_una_millonesima_si_recibe_disparo() -> None:
    # Borde: la igualdad de Vector2 tiene tolerancia 1e-6; a 1e-7 el enemigo no está
    # "encima" y se le dispara.
    weapon = ProjectileWeapon(SPEC)
    weapon.update(Vector2(0, 0), [enemigo(1e-7, 0)])
    [bullet] = weapon.bullets
    assert bullet.direction == Vector2(1, 0)


def test_ignora_al_enemigo_sobre_el_jugador_y_apunta_al_siguiente() -> None:
    # Un enemigo abierto puede quedar estacionado sobre el jugador quieto. No debe
    # callar el arma contra los demás.
    weapon = ProjectileWeapon(SPEC)
    weapon.update(Vector2(0, 0), [enemigo(0, 0), enemigo(0, 200)])
    [bullet] = weapon.bullets
    assert bullet.direction == Vector2(0, 1)


def test_no_apunta_a_un_enemigo_muerto() -> None:
    # Un enemigo que perdió su última línea en este mismo paso sigue en la lista hasta
    # que `World` lo quita.
    muerto = enemigo(50, 0)
    for k in range(HEXAGON.shape.line_count):
        muerto.remove_edge(k)
    weapon = ProjectileWeapon(SPEC)
    weapon.update(Vector2(0, 0), [muerto, enemigo(0, -300)])
    [bullet] = weapon.bullets
    assert bullet.direction == Vector2(0, -1)


# --- Cuándo dispara ---


def test_dispara_uno_cada_cooldown() -> None:
    weapon = ProjectileWeapon(SPEC)
    lejos = [enemigo(10_000, 0)]
    disparos = []
    for paso in range(100):
        weapon.update(Vector2(0, 0), lejos)
        if any(bullet.age == 0 for bullet in weapon.bullets):
            disparos.append(paso)
    assert disparos == [0, COOLDOWN, 2 * COOLDOWN, 3 * COOLDOWN]


def test_las_balas_vencidas_se_quitan() -> None:
    weapon = ProjectileWeapon(SPEC)
    lejos = [enemigo(10_000, 0)]
    for _ in range(VIDA + 1):
        weapon.update(Vector2(0, 0), lejos)
    # Nacieron en los pasos 0, 30 y 60; la del paso 0 ya recorrió `range`.
    assert len(weapon.bullets) == 2


def test_sin_enemigos_no_dispara_y_queda_lista() -> None:
    weapon = ProjectileWeapon(SPEC)
    for _ in range(COOLDOWN * 3):
        weapon.update(Vector2(0, 0), [])
    assert weapon.bullets == []
    weapon.update(Vector2(0, 0), [enemigo(100, 0)])
    assert len(weapon.bullets) == 1


def test_la_bala_no_sigue_al_jugador() -> None:
    weapon = ProjectileWeapon(SPEC)
    objetivo = [enemigo(10_000, 0)]
    weapon.update(Vector2(0, 0), objetivo)
    for _ in range(10):
        weapon.update(Vector2(0, 50), objetivo)
    bullet = weapon.bullets[0]
    assert bullet.position.y == 0
    assert bullet.position.x == pytest.approx(SPEED * 10 * STEP)


# --- La puntería con anticipación (decisión 55) ---


def test_intercepta_un_objetivo_que_cruza() -> None:
    # El punto está a la vez a `s·t` del origen y a `v·t` del objetivo.
    objetivo, velocidad = Vector2(300, 0), Vector2(0, 120)
    punto = intercept(Vector2(), objetivo, velocidad, 300.0)
    t = punto.length() / 300.0
    assert tuple(punto) == pytest.approx(tuple(objetivo + velocidad * t))
    assert punto.y > 0


def test_objetivo_quieto_apunta_igual_que_antes() -> None:
    objetivo = Vector2(120, -50)
    assert intercept(Vector2(10, 10), objetivo, Vector2(), 300.0) == objetivo


def test_si_se_aleja_mas_rapido_apunta_a_donde_esta() -> None:
    objetivo = Vector2(100, 0)
    assert intercept(Vector2(), objetivo, Vector2(400, 0), 300.0) == objetivo


def test_le_acierta_al_que_cruza_de_lado() -> None:
    # Sin anticipar, la bala llega en 0,5 s y el hexágono ya avanzó 60, más que su
    # radio (24): fallaría.
    weapon = ProjectileWeapon(SPEC)
    objetivo = enemigo(300, 0)
    objetivo.velocity = Vector2(0, 120)
    golpes = []
    for _ in range(round(0.6 / STEP)):
        golpes += [
            e for e in weapon.update(Vector2(), [objetivo]) if isinstance(e, Hit)
        ]
        objetivo.step(Vector2())
    assert golpes


def test_al_circulo_le_acierta_lejos() -> None:
    # El círculo del balance, solo, gira alrededor del jugador quieto. Sin anticipar,
    # el primer golpe llegaba recién a r ≈ 45. La anticipación supone que va derecho y
    # él curva, así que no acierta desde cualquier distancia: medido, a r ≈ 104.
    sin_apariciones = replace(
        BALANCE,
        director=replace(
            BALANCE.director,
            sections=(replace(BALANCE.director.sections[0], deck=()),),
        ),
    )
    world = World(sin_apariciones, random.Random(1), lethal=False)
    circulo = Enemy(BALANCE.enemies["circle"], Vector2(400, 0))
    world.enemies = [circulo]
    while circulo.alive:
        distancia = circulo.position.distance_to(world.player.position)
        world.update(Vector2())
    assert distancia > 80


# --- El arma por términos (ADR 0029) ---

# Los golpes de la demo con la semilla 1, sin morir, en 60 s, grabados en `main` antes de
# que el punto se escribiera con términos (#95): `(paso, enemigo, línea)`, con cada
# enemigo numerado en el orden en que entró al plano. Si un cambio de las reglas o del
# balance los cambia a propósito, se graban de nuevo con este mismo test.
GOLPES_DE_LA_DEMO = [
    (394, 0, 0), (520, 0, 3), (520, 0, 1), (547, 0, 2), (624, 1, 2), (692, 0, 5),
    (749, 1, 5), (784, 1, 3), (854, 1, 0), (898, 1, 1), (929, 2, 5), (958, 2, 4),
    (1037, 0, 4), (1110, 1, 4), (1151, 2, 0), (1184, 2, 1), (1220, 2, 2),
    (1258, 2, 3), (1417, 4, 2), (1425, 4, 3), (1517, 4, 0), (1662, 5, 3),
    (1684, 4, 1), (1770, 6, 2), (1786, 6, 4), (1823, 5, 0), (1860, 5, 1),
    (1900, 5, 2), (2042, 6, 5), (2082, 6, 0), (2124, 5, 5), (2162, 6, 3),
    (2229, 5, 4), (2375, 6, 1), (2477, 9, 2), (2496, 9, 0), (2541, 9, 1),
    (2591, 9, 5), (2702, 9, 3), (2729, 10, 3), (2747, 10, 1), (2800, 10, 4),
    (2838, 10, 2), (2904, 11, 1), (2933, 11, 3), (3019, 10, 5), (3051, 10, 0),
    (3183, 13, 0), (3197, 11, 2), (3303, 13, 3), (3338, 13, 1), (3371, 14, 1),
    (3400, 14, 3), (3533, 14, 2), (3576, 14, 0),
]  # fmt: skip


def golpes_de_la_demo(seed: int, seconds: float) -> list[tuple[int, int, int]]:
    """Los golpes de la demo, sin morir, como `(paso, enemigo, línea)`.

    Sin subir de nivel: la lista se grabó antes de que hubiera mano, y la mano detiene
    al mundo hasta que alguien elige."""
    sin_niveles = replace(BALANCE, experience=replace(BALANCE.experience, base=1e9))
    world = World(sin_niveles, random.Random(seed), lethal=False)
    # Guardar a los enemigos, y no solo su `id`, evita que un muerto le preste su `id`
    # a uno nuevo.
    orden: dict[int, int] = {}
    vistos: list[Enemy] = []
    golpes = []
    for _ in range(round(seconds / STEP)):
        world.update(pilot_intent(world.steps))
        for enemy in world.enemies:
            if id(enemy) not in orden:
                orden[id(enemy)] = len(vistos)
                vistos.append(enemy)
        golpes += [
            (world.steps, orden[id(e.enemy)], e.edge)
            for e in world.events
            if isinstance(e, Hit)
        ]
    return golpes


def test_misma_semilla_mismos_golpes() -> None:
    # Escribir el punto con términos no cambia la partida (#95).
    assert golpes_de_la_demo(seed=1, seconds=60.0) == GOLPES_DE_LA_DEMO


def test_arma_inicial_que_no_existe() -> None:
    # Negativo: `start_weapon` tiene que ser una clave de `weapons`.
    sin_arma = replace(BALANCE, player=replace(BALANCE.player, start_weapon="laser"))
    with pytest.raises(ValueError, match=r"player\.start_weapon"):
        check_weapons(sin_arma)


@pytest.mark.parametrize(
    ("cambio", "campo"),
    [
        # Hoy se arman el proyectil cartesiano y el trazo polar; la recta y la
        # espiral llegan en las tareas 8 y 9.
        ({"kind": "trace"}, "frame"),
        ({"frame": "polar"}, "frame"),
        (
            {
                "kind": "trace",
                "frame": "polar",
                "payload": replace(POINT.payload, duration=1.0),
            },
            "payload.duration",
        ),
        ({"aim": "motion"}, "aim"),
        ({"advance": AdvanceSpec(coefficient=300.0, degree=0)}, "advance.degree"),
        ({"copies": 3}, "copies"),
        ({"mirror": True}, "mirror"),
        ({"parallel": 10.0}, "parallel"),
        ({"payload": replace(POINT.payload, size=4.0)}, "payload.size"),
        ({"payload": replace(POINT.payload, lines=2)}, "payload.lines"),
        ({"payload": replace(POINT.payload, pierce=1)}, "payload.pierce"),
    ],
)
def test_rechaza_lo_que_todavia_no_se_arma(
    cambio: dict[str, object], campo: str
) -> None:
    # Negativo: el balance solo puede pedir lo que el código sabe armar; lo demás llega
    # con su tarea. Así un dato no queda ignorado en silencio.
    arma = replace(POINT, **cambio)  # type: ignore[arg-type]
    balance = replace(BALANCE, weapons={"point": arma})
    with pytest.raises(ValueError, match=rf"weapons\.point\.{campo}"):
        check_weapons(balance)


def test_el_punto_del_balance_se_arma() -> None:
    check_weapons(BALANCE)


def test_el_circulo_del_balance_se_arma() -> None:
    # El círculo es un trazo polar, y el chequeo lo deja pasar.
    circulo = BALANCE.weapons["circle"]
    assert (circulo.kind, circulo.frame) == ("trace", "polar")
    check_weapons(replace(BALANCE, weapons={"point": POINT, "circle": circulo}))


@pytest.mark.parametrize("spacing", [0.0, -1.0])
def test_rechaza_un_espaciado_no_positivo(spacing: float) -> None:
    # Negativo: sin espaciado positivo, un trazo no sabe cuántas muestras tomar.
    balance = replace(BALANCE, sampling=SamplingSpec(spacing=spacing))
    with pytest.raises(ValueError, match=r"sampling\.spacing"):
        check_weapons(balance)
