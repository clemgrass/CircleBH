"""Tests de la mano: las tarjetas, el reparto y la elección al subir de nivel (spec de
la 0.3.0, "La mano", y ADR 0029).

Los tests de `available`, `deal` y `apply` usan un catálogo propio, para no depender de
las tarjetas del balance. Los del mundo usan el balance real.
"""

import random
from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pygame.math import Vector2

from circlebh.balance import (
    BALANCE,
    Balance,
    CardSpec,
    KnobChange,
    LevelUpSpec,
    NewWeaponChange,
    PlayerChange,
)
from circlebh.pilot import choose_at_random, pilot_intent
from circlebh.world.cards import Loadout, Offer, apply, available, check_cards, deal
from circlebh.world.enemy import Enemy
from circlebh.world.events import CardChosen, Shot
from circlebh.world.experience import Orb, level_cost
from circlebh.world.game import World
from circlebh.world.weapons import ProjectileWeapon

PUNTO = BALANCE.weapon
MANO = LevelUpSpec(freeze_steps=12, hand_size=3, max_weapons=4, rerolls=1, banishes=1)


def perilla(
    field: str,
    op: str = "mul",
    values: tuple[float, ...] = (2.0,),
    weapons: tuple[str, ...] = (),
    *,
    shape: bool = False,
) -> CardSpec:
    """Una tarjeta de perilla de ejemplo."""
    change = KnobChange(kind="knob", field=field, op=op, values=values)  # type: ignore[arg-type]
    return CardSpec(
        title=field,
        symbol=field,
        family="knob",
        weapons=weapons,
        change=change,
        shape=shape,
    )


def del_jugador(field: str, values: tuple[float, ...] = (2.0,)) -> CardSpec:
    """Una tarjeta de ejemplo que cambia al jugador."""
    change = PlayerChange(kind="player", field=field, op="mul", values=values)  # type: ignore[arg-type]
    return CardSpec(
        title=field,
        symbol=field,
        family="player",
        weapons=(),
        change=change,
        shape=False,
    )


def arma_nueva() -> CardSpec:
    """Una tarjeta de ejemplo que suma otra `fₖ`, igual a la base."""
    return CardSpec(
        title="otra",
        symbol="otra",
        family="weapon",
        weapons=(),
        change=NewWeaponChange(kind="weapon"),
        shape=True,
    )


def equipo(*armas: str) -> Loadout:
    """Lo que tiene un jugador con las armas `armas`, todas iguales al punto."""
    return Loadout(
        weapons=dict.fromkeys(armas, PUNTO),
        player=BALANCE.player,
        rerolls=1,
        banishes=1,
    )


# --- apply ---


def test_perilla_multiplica_su_campo() -> None:
    cartas = {"seguido": perilla("cooldown", values=(0.8,))}
    nuevo = apply(Offer("seguido", "a", 0.8), equipo("a"), cartas, PUNTO)
    assert nuevo.weapons["a"].cooldown == pytest.approx(PUNTO.cooldown * 0.8)


def test_perilla_llega_a_un_campo_anidado() -> None:
    cartas = {"rapido": perilla("advance.coefficient", op="add", values=(50.0,))}
    nuevo = apply(Offer("rapido", "a", 50.0), equipo("a"), cartas, PUNTO)
    assert nuevo.weapons["a"].advance.coefficient == PUNTO.advance.coefficient + 50
    assert nuevo.weapons["a"].advance.degree == PUNTO.advance.degree


def test_perilla_solo_cambia_su_arma() -> None:
    cartas = {"seguido": perilla("cooldown")}
    nuevo = apply(Offer("seguido", "a", 2.0), equipo("a", "b"), cartas, PUNTO)
    assert nuevo.weapons["b"] == PUNTO


def test_perilla_entera_queda_entera() -> None:
    # Borde: `copies` es un entero, y multiplicarlo no lo deja en 1.5.
    cartas = {"copias": perilla("copies", values=(1.5,))}
    nuevo = apply(Offer("copias", "a", 1.5), equipo("a"), cartas, PUNTO)
    assert nuevo.weapons["a"].copies == 2
    assert isinstance(nuevo.weapons["a"].copies, int)


def test_tarjeta_del_jugador_cambia_su_spec() -> None:
    cartas = {"chico": del_jugador("radius", (0.9,))}
    nuevo = apply(Offer("chico", "", 0.9), equipo("a"), cartas, PUNTO)
    assert nuevo.player.radius == pytest.approx(BALANCE.player.radius * 0.9)
    assert nuevo.weapons == equipo("a").weapons


def test_tarjeta_de_rerolls_suma_usos() -> None:
    cartas = {"otra": del_jugador("rerolls", (2.0,))}
    nuevo = apply(Offer("otra", "", 2.0), equipo("a"), cartas, PUNTO)
    assert nuevo.rerolls == 2
    assert nuevo.player == BALANCE.player


def test_arma_nueva_suma_otra_funcion_igual_a_la_base() -> None:
    # ADR 0033: `f₂` parte igual al punto del inicio, aunque `f₁` ya esté mejorada.
    mejorada = replace(PUNTO, cooldown=0.1)
    estado = Loadout({"f1": mejorada}, BALANCE.player, rerolls=1, banishes=1)
    cartas = {"otra": arma_nueva()}
    nuevo = apply(Offer("otra", "f2", 0.0), estado, cartas, PUNTO)
    assert nuevo.weapons == {"f1": mejorada, "f2": PUNTO}


# --- available ---


def test_tarjeta_sin_armas_sirve_para_todas() -> None:
    cartas = {"seguido": perilla("cooldown")}
    pares = available(equipo("a", "b"), cartas, MANO, set())
    assert pares == [("seguido", "a"), ("seguido", "b")]


def test_tarjeta_de_otra_arma_no_se_ofrece() -> None:
    # Negativo: la tarjeta es del arma "c", y no la tienes.
    cartas = {"seguido": perilla("cooldown", weapons=("c",))}
    assert available(equipo("a"), cartas, MANO, set()) == []


def test_tarjeta_sin_efecto_no_se_ofrece() -> None:
    # Negativo: multiplicar un avance de 0 lo deja en 0.
    quieto = replace(PUNTO, advance=replace(PUNTO.advance, coefficient=0.0))
    estado = Loadout({"a": quieto}, BALANCE.player, rerolls=1, banishes=1)
    cartas = {"rapido": perilla("advance.coefficient")}
    assert available(estado, cartas, MANO, set()) == []


def test_tarjeta_del_jugador_va_sin_arma() -> None:
    cartas = {"rapido": del_jugador("speed")}
    assert available(equipo("a", "b"), cartas, MANO, set()) == [("rapido", "")]


def test_ofrece_arma_nueva_con_menos_de_cuatro() -> None:
    # La tarjeta va a la `fₖ` que sigue.
    cartas = {"otra": arma_nueva()}
    estado = equipo("f1", "f2", "f3")
    assert available(estado, cartas, MANO, set()) == [("otra", "f4")]


def test_sin_armas_la_nueva_es_f1() -> None:
    # Borde: un jugador sin armas suma la primera.
    cartas = {"otra": arma_nueva()}
    assert available(equipo(), cartas, MANO, set()) == [("otra", "f1")]


def test_no_ofrece_arma_nueva_con_cuatro() -> None:
    # Negativo: con `max_weapons` armas, no cabe otra.
    cartas = {"otra": arma_nueva()}
    estado = equipo("f1", "f2", "f3", "f4")
    assert available(estado, cartas, MANO, set()) == []


def test_tarjeta_desterrada_no_se_ofrece() -> None:
    cartas = {"seguido": perilla("cooldown"), "rapido": del_jugador("speed")}
    pares = available(equipo("a"), cartas, MANO, {"seguido"})
    assert pares == [("rapido", "")]


# --- deal ---

CINCO = {f"c{i}": perilla("cooldown", values=(0.5, 0.8)) for i in range(5)}
"""Cinco tarjetas con efecto sobre cualquier arma, sin cambiar la forma."""


@given(seed=st.integers(min_value=0, max_value=10**6))
def test_mano_trae_tres_distintas(seed: int) -> None:
    mano = deal(equipo("a"), CINCO, MANO, set(), random.Random(seed))
    assert len(mano) == 3
    assert len({oferta.card for oferta in mano}) == 3


@given(seed=st.integers(min_value=0, max_value=10**6))
def test_valor_sale_de_su_lista(seed: int) -> None:
    mano = deal(equipo("a"), CINCO, MANO, set(), random.Random(seed))
    assert all(oferta.value in (0.5, 0.8) for oferta in mano)


@given(seed=st.integers(min_value=0, max_value=10**6))
def test_misma_semilla_misma_mano(seed: int) -> None:
    una = deal(equipo("a"), CINCO, MANO, set(), random.Random(seed))
    otra = deal(equipo("a"), CINCO, MANO, set(), random.Random(seed))
    assert una == otra


@given(seed=st.integers(min_value=0, max_value=10**6))
def test_mano_favorece_las_formas(seed: int) -> None:
    # Con una sola tarjeta de forma entre seis, siempre sale.
    cartas = CINCO | {"forma": perilla("spin", op="add", shape=True)}
    mano = deal(equipo("a"), cartas, MANO, set(), random.Random(seed))
    assert "forma" in {oferta.card for oferta in mano}


def test_mano_corta_trae_las_que_hay() -> None:
    # Borde: dos tarjetas con efecto, y la mano es de tres.
    cartas = {"c0": CINCO["c0"], "c1": CINCO["c1"]}
    mano = deal(equipo("a"), cartas, MANO, set(), random.Random(1))
    assert sorted(oferta.card for oferta in mano) == ["c0", "c1"]


def test_sin_tarjetas_la_mano_queda_vacia() -> None:
    assert deal(equipo("a"), {}, MANO, set(), random.Random(1)) == ()


# --- check_cards ---


def test_rechaza_perilla_de_un_campo_que_no_existe() -> None:
    balance = replace(BALANCE, cards={"mala": perilla("advance.speed")})
    with pytest.raises(ValueError, match=r"cards\.mala\.change\.field"):
        check_cards(balance)


def test_rechaza_perilla_de_un_campo_que_no_es_numero() -> None:
    balance = replace(BALANCE, cards={"mala": perilla("mirror")})
    with pytest.raises(ValueError, match=r"cards\.mala\.change\.field"):
        check_cards(balance)


@pytest.mark.parametrize("arma", ["f5", "f0", "point"])
def test_rechaza_tarjeta_de_un_arma_que_no_puede_haber(arma: str) -> None:
    # Negativo: con `max_weapons = 4`, las armas son `f1` a `f4`.
    balance = replace(BALANCE, cards={"mala": perilla("cooldown", weapons=(arma,))})
    with pytest.raises(ValueError, match=r"cards\.mala\.weapons"):
        check_cards(balance)


def test_acepta_tarjeta_de_la_ultima_arma() -> None:
    # Borde: `f4` existe con `max_weapons = 4`.
    check_cards(replace(BALANCE, cards={"buena": perilla("cooldown", weapons=("f4",))}))


def test_rechaza_tarjeta_sin_valores() -> None:
    balance = replace(BALANCE, cards={"mala": perilla("cooldown", values=())})
    with pytest.raises(ValueError, match=r"cards\.mala\.change\.values"):
        check_cards(balance)


def test_las_tarjetas_del_balance_pasan_el_chequeo() -> None:
    check_cards(BALANCE)


# --- La mano en el mundo ---

SIN_APARICIONES = replace(
    BALANCE,
    director=replace(
        BALANCE.director,
        sections=(replace(BALANCE.director.sections[0], deck=()),),
    ),
)
"""El balance real con un director que no compra: los tests ponen a mano lo que haga
falta."""
FRENADO = BALANCE.level_up.freeze_steps


def mundo_que_sube(
    niveles: int = 1, balance: Balance = SIN_APARICIONES, **kwargs: bool
) -> World:
    """Un mundo con un punto encima del jugador que alcanza justo para `niveles`
    niveles: los sube en el primer `update`."""
    world = World(balance, random.Random(1), **kwargs)
    valor = sum(level_cost(n, balance.experience) for n in range(1, niveles + 1))
    world.orbs = [Orb(Vector2(), valor)]
    return world


def avanzar(world: World, pasos: int) -> None:
    for _ in range(pasos):
        world.update(Vector2())


def con_mano(niveles: int = 1, **kwargs: bool) -> World:
    """Un mundo con la mano abierta."""
    world = mundo_que_sube(niveles, **kwargs)
    avanzar(world, 1 + FRENADO)
    assert world.hand
    return world


def test_mano_despues_del_frenado() -> None:
    world = mundo_que_sube()
    world.update(Vector2())
    assert world.pending_levels == 1
    for _ in range(FRENADO - 1):
        world.update(Vector2())
        assert world.hand == ()
        assert world.freezing > 0
    world.update(Vector2())
    assert len(world.hand) == 3
    assert world.freezing == 0


def test_con_la_mano_el_mundo_no_avanza() -> None:
    world = con_mano()
    pasos = world.steps
    avanzar(world, 30)
    assert world.steps == pasos
    world.choose(0)
    world.update(Vector2())
    assert world.steps == pasos + 1
    assert world.hand == ()
    assert world.pending_levels == 0


def test_elegir_cambia_el_arma() -> None:
    world = con_mano()
    # La mano se fija para no depender del sorteo.
    world.hand = (Offer("point_cooldown", "f1", 0.8),)
    world.choose(0)
    [arma] = world.weapons
    assert arma.spec.cooldown == pytest.approx(PUNTO.cooldown * 0.8)


def test_elegir_arma_nueva_suma_f2() -> None:
    # La tarjeta de arma nueva del balance suma otro punto, que apunta al segundo.
    world = con_mano()
    world.hand = (Offer("new_weapon", "f2", 0.0),)
    world.choose(0)
    assert list(world.arsenal) == ["f1", "f2"]
    nueva = world.arsenal["f2"]
    assert (nueva.spec, nueva.rank) == (BALANCE.weapon, 1)


def test_mejorar_f2_no_cambia_f1() -> None:
    # Negativo: cada arma se mejora por su lado. Dos niveles: dos manos seguidas.
    world = con_mano(niveles=2)
    world.hand = (Offer("new_weapon", "f2", 0.0),)
    world.choose(0)
    world.hand = (Offer("point_cooldown", "f2", 0.8),)
    world.choose(0)
    assert world.arsenal["f1"].spec == BALANCE.weapon
    assert world.arsenal["f2"].spec.cooldown == pytest.approx(PUNTO.cooldown * 0.8)


def test_elegir_emite_card_chosen_en_el_paso_siguiente() -> None:
    world = con_mano()
    oferta = world.hand[0]
    world.choose(0)
    world.update(Vector2())
    assert CardChosen(oferta) in world.events


def test_elegir_cambia_al_jugador() -> None:
    world = con_mano()
    world.hand = (Offer("player_speed", "", 2.0),)
    world.choose(0)
    world.update(Vector2(1, 0))
    assert world.player.position.x == pytest.approx(BALANCE.player.speed * 2 / 60)


def test_la_carga_elegida_atrae_la_experiencia() -> None:
    # El mundo lee la carga del jugador de su spec de ahora, no la del balance.
    def pasos_hasta_juntar(world: World) -> int:
        world.orbs = [Orb(Vector2(300, 0), 1.0)]
        for paso in range(1, 2000):
            world.update(Vector2())
            if not world.orbs:
                return paso
        raise AssertionError("no llegó")

    normal = con_mano(armed=False)
    normal.hand = (Offer("player_speed", "", 1.5),)
    normal.choose(0)
    cargado = con_mano(armed=False)
    cargado.hand = (Offer("player_charge", "", 4.0),)
    cargado.choose(0)
    assert pasos_hasta_juntar(cargado) < pasos_hasta_juntar(normal)


def test_dos_niveles_dos_manos_seguidas() -> None:
    # Borde: al elegir la primera, la segunda sale sin otro frenado.
    world = con_mano(niveles=2)
    pasos = world.steps
    world.choose(0)
    assert len(world.hand) == 3
    assert world.pending_levels == 1
    world.choose(0)
    assert world.hand == ()
    world.update(Vector2())
    assert world.steps == pasos + 1


def test_morir_al_frenar_no_muestra_la_mano() -> None:
    # Foco 1: si algo te toca en el frenado, mueres como siempre.
    world = mundo_que_sube(armed=False)
    world.update(Vector2())
    hexagono = replace(BALANCE.enemies["hexagon"], speed=0.0, patterns=(), actions=())
    world.enemies.append(Enemy(hexagono, Vector2(30, 0)))
    avanzar(world, FRENADO + 5)
    assert world.game_over
    assert world.hand == ()


def test_sin_tarjetas_no_se_detiene() -> None:
    # Borde: sin ninguna tarjeta con efecto, el nivel sube y el mundo sigue.
    balance = replace(SIN_APARICIONES, cards={})
    world = mundo_que_sube(balance=balance)
    avanzar(world, 1 + FRENADO + 10)
    assert world.steps == 1 + FRENADO + 10
    assert world.hand == ()
    assert world.pending_levels == 0


def test_mano_corta_en_el_mundo() -> None:
    # Borde: sin armas, y con el arma nueva sacada de la partida, quedan solo las tres
    # del jugador.
    world = mundo_que_sube(armed=False)
    world.banished.add("new_weapon")
    avanzar(world, 1 + FRENADO)
    assert {o.card for o in world.hand} == {
        "player_speed",
        "player_radius",
        "player_charge",
    }


def test_elegir_sin_mano_falla() -> None:
    # Negativo: no hay nada que elegir.
    world = mundo_que_sube()
    with pytest.raises(IndexError):
        world.choose(0)


def test_elegir_fuera_de_la_mano_falla() -> None:
    world = con_mano()
    with pytest.raises(IndexError):
        world.choose(3)


def test_reroll_cambia_la_mano_y_gasta_un_uso() -> None:
    world = con_mano()
    estado = world.rng.getstate()
    world.reroll()
    assert world.rerolls == BALANCE.level_up.rerolls - 1
    assert len(world.hand) == 3
    assert world.rng.getstate() != estado


def test_banish_saca_la_tarjeta_de_las_manos_siguientes() -> None:
    world = con_mano(niveles=2)
    desterrada = world.hand[0].card
    world.banish(0)
    assert world.banishes == BALANCE.level_up.banishes - 1
    assert desterrada not in {o.card for o in world.hand}
    assert len(world.hand) == 2
    world.choose(0)
    assert desterrada not in {o.card for o in world.hand}


def test_banish_de_la_ultima_tarjeta_cierra_la_mano() -> None:
    # Borde: si la mano queda vacía, el nivel se pierde y el mundo sigue.
    world = con_mano()
    world.hand = world.hand[:1]
    world.banish(0)
    assert world.hand == ()
    assert world.pending_levels == 0


def test_reroll_y_banish_sin_usos_no_hacen_nada() -> None:
    # Negativo.
    world = con_mano()
    world.rerolls = 0
    world.banishes = 0
    mano, estado = world.hand, world.rng.getstate()
    world.reroll()
    world.banish(0)
    assert world.hand == mano
    assert world.rng.getstate() == estado
    assert world.rerolls == 0
    assert world.banishes == 0


def test_reroll_y_banish_sin_mano_no_hacen_nada() -> None:
    world = mundo_que_sube()
    world.reroll()
    world.banish(0)
    assert world.rerolls == BALANCE.level_up.rerolls
    assert world.banishes == BALANCE.level_up.banishes


def test_cooldown_no_baja_de_un_paso() -> None:
    # Foco 4: un cooldown menor que un paso dispara una vez por paso, nunca más.
    hexagono = replace(BALANCE.enemies["hexagon"], speed=0.0, patterns=(), actions=())
    arma = ProjectileWeapon(replace(PUNTO, cooldown=0.001), 0)
    enemigos = [Enemy(hexagono, Vector2(10_000, 0))]
    disparos = [
        sum(isinstance(e, Shot) for e in arma.update(Vector2(), enemigos))
        for _ in range(30)
    ]
    assert disparos == [1] * 30


def jugar(seed: int, pasos: int) -> list[tuple[object, ...]]:
    """Una partida con el piloto, eligiendo siempre la tarjeta `nivel % largo`. Devuelve
    un resumen de cada paso: lo que pasó, dónde está todo y la mano."""
    balance = replace(BALANCE, experience=replace(BALANCE.experience, base=1.0))
    world = World(balance, random.Random(seed), lethal=False)
    resumen: list[tuple[object, ...]] = []
    for _ in range(pasos):
        if world.hand:
            world.choose(world.level % len(world.hand))
        world.update(pilot_intent(world.steps))
        resumen.append(
            (
                world.steps,
                tuple(type(e).__name__ for e in world.events),
                tuple(world.player.position),
                tuple(tuple(e.position) for e in world.enemies),
                world.hand,
            )
        )
    return resumen


def test_misma_semilla_mismas_elecciones_misma_partida() -> None:
    una, otra = jugar(3, 3000), jugar(3, 3000)
    assert any("CardChosen" in paso[1] for paso in una)
    assert una == otra


# --- La elección al azar de la demo ---


def test_eleccion_al_azar_no_usa_la_random_del_mundo() -> None:
    world = con_mano()
    estado = world.rng.getstate()
    choose_at_random(world, random.Random(7))
    assert world.hand == ()
    assert world.rng.getstate() == estado


def test_eleccion_al_azar_sin_mano_no_hace_nada() -> None:
    world = mundo_que_sube()
    azar = random.Random(7)
    estado = azar.getstate()
    choose_at_random(world, azar)
    assert azar.getstate() == estado
