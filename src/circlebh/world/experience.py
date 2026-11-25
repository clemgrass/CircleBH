"""La experiencia: el punto que deja cada enemigo y lo que cuesta cada nivel (spec de la
0.3.0, decisiones 3, 12 y 13)."""

import math

from pygame.math import Vector2

from circlebh.balance import ChargesSpec, ExperienceSpec
from circlebh.world.charges import player_force
from circlebh.world.clock import STEP
from circlebh.world.collisions import segment_touches_circle
from circlebh.world.player import Player


class Orb:
    """Un punto de experiencia, en coordenadas del plano."""

    def __init__(self, position: Vector2, value: float) -> None:
        self.position = Vector2(position)
        self.value = value
        """Cuánta experiencia da al recogerlo: el `threat` del enemigo que lo dejó."""
        self.velocity = Vector2()
        """Unidades del plano por segundo. Nace quieto."""


def step_orbs(
    orbs: list[Orb],
    player: Player,
    player_charge: float,
    spec: ExperienceSpec,
    charges: ChargesSpec,
) -> tuple[list[Orb], float]:
    """Avanza un paso a los puntos, y devuelve los que quedan y la experiencia
    recogida. El jugador ya dio su paso.

    Cada punto siente solo al jugador: `a = F_jugador(p − P) − γ·v`, con la fuerza de
    `charges.py` y masa 1, y avanza con Euler semi-implícito, como un enemigo. Se recoge
    si su tramo del paso toca el círculo del jugador, medido en el marco del jugador
    como una bala enemiga: así no lo salta aunque vaya rápido, ni se escapa porque el
    jugador también se movió.
    """
    remaining: list[Orb] = []
    collected = 0.0
    for orb in orbs:
        start = orb.position - player.previous
        force = player_force(
            orb.position - player.position, spec.charge, player_charge, charges
        )
        orb.velocity += (force - orb.velocity * spec.friction) * STEP
        orb.position += orb.velocity * STEP
        end = orb.position - player.position
        if segment_touches_circle(start, end, Vector2(), player.radius):
            collected += orb.value
        else:
            remaining.append(orb)
    return remaining, collected


def level_cost(level: int, spec: ExperienceSpec) -> float:
    """La experiencia que pide subir del nivel `level`: `a·nᵇ`."""
    return spec.base * math.pow(level, spec.exponent)


def check_experience(spec: ExperienceSpec) -> None:
    """Rechaza al crear el mundo un costo de nivel que no sea positivo: con `a ≤ 0`, un
    solo punto subiría infinitos niveles."""
    if spec.base <= 0:
        raise ValueError(f"experience.base: tiene que ser mayor que 0, no {spec.base}")
