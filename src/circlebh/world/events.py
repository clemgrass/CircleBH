"""Los eventos del mundo: lo que pasó en un paso (ADR 0022).

`World.events` guarda los del último `update`. Son datos puros: el mundo no sabe quién
los lee. Los lee la música, para sonar con lo que pasa en el plano, y la medición del
balance, que sale solo de ellos y del reloj (ADR 0030).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pygame.math import Vector2

    from circlebh.balance import SectionSpec
    from circlebh.world.enemy import Enemy
    from circlebh.world.enemy_bullets import EnemyBullet
    from circlebh.world.weapons import Weapon


@dataclass(frozen=True)
class Shot:
    """`weapon` disparó en este paso."""

    weapon: Weapon


@dataclass(frozen=True)
class Hit:
    """Una bala quitó la línea `edge` a `enemy`."""

    enemy: Enemy
    edge: int


@dataclass(frozen=True)
class Death:
    """`enemy` perdió su última línea en este paso."""

    enemy: Enemy


@dataclass(frozen=True)
class Telegraph:
    """`enemy` empezó a avisar un ataque en este paso: después del aviso, ataca."""

    enemy: Enemy


@dataclass(frozen=True)
class Regrow:
    """`enemy` recuperó la línea `edge` en este paso."""

    enemy: Enemy
    edge: int


@dataclass(frozen=True)
class Donate:
    """`enemy` soltó su línea `edge`, que en el plano es `line`, para `patient`. El mundo
    la convierte en una línea suelta (decisión 67 de la spec de la 0.2.0)."""

    enemy: Enemy
    edge: int
    line: tuple[Vector2, Vector2]
    patient: Enemy


@dataclass(frozen=True)
class Spawn:
    """`enemy` entró al plano en este paso: de la cola, como fragmento, como línea suelta
    o de la fusión."""

    enemy: Enemy


@dataclass(frozen=True)
class SectionStart:
    """Empezó la sección `index` del tema, que es `section`. La primera, en el primer
    paso."""

    index: int
    section: SectionSpec


@dataclass(frozen=True)
class PlayerDeath:
    """El jugador murió en este paso, tocado por `cause`. Si una bala y un enemigo lo
    tocan a la vez, es la bala."""

    cause: Enemy | EnemyBullet


type Event = (
    Shot
    | Hit
    | Death
    | Telegraph
    | Regrow
    | Donate
    | Spawn
    | SectionStart
    | PlayerDeath
)
