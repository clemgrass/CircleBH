"""Los eventos del mundo: lo que pasó en un paso (ADR 0022).

`World.events` guarda los del último `update`. Son datos puros: el mundo no sabe quién
los lee. Hoy los lee la música, para sonar con lo que pasa en el plano.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from circlebh.world.enemy import Enemy
    from circlebh.world.weapons import Weapon


@dataclass(frozen=True)
class Shot:
    """`weapon` disparó en este paso."""

    weapon: Weapon


@dataclass(frozen=True)
class Hit:
    """Una bala quitó la arista `edge` a `enemy`."""

    enemy: Enemy
    edge: int


@dataclass(frozen=True)
class Death:
    """`enemy` perdió su última línea en este paso."""

    enemy: Enemy


type Event = Shot | Hit | Death
