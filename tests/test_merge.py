"""Tests de la gran estrella roja: cinco estrellas vivas se juntan en una trampa que te
encierra (spec de la 0.2.0, decisiones 37 a 41).

La gran estrella es el pentagrama `{5/2}`. Su línea más cercana al centro está a
`R·cos(2π/5)`: con `R = 150`, a unas 46 unidades, y el jugador tiene radio 12.
"""

import random
from dataclasses import replace

import pytest

from circlebh.balance import BALANCE
from circlebh.world.game import World

# --- El balance ---


def test_el_mundo_rechaza_un_merge_que_tocaria_al_jugador() -> None:
    # Con radio 30, la línea más cercana queda a 30·cos 72° ≈ 9,3, dentro del jugador.
    chica = replace(BALANCE.enemies["red_star"], radius=30.0)
    balance = replace(BALANCE, enemies={**BALANCE.enemies, "red_star": chica})
    with pytest.raises(ValueError, match=r"merge\.into"):
        World(balance, random.Random(0))


def test_el_mundo_rechaza_un_merge_de_un_enemigo_que_no_existe() -> None:
    balance = replace(BALANCE, merge=replace(BALANCE.merge, enemy="nadie"))
    with pytest.raises(ValueError, match=r"merge\.enemy"):
        World(balance, random.Random(0))


def test_el_balance_real_cumple_el_merge() -> None:
    World(BALANCE, random.Random(0))
