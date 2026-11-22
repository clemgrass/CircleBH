"""El jugador: un círculo que avanza según la intención de movimiento."""

from pygame.math import Vector2

from circlebh.balance import PlayerSpec
from circlebh.world.clock import STEP


class Player:
    """El círculo del jugador, en coordenadas del plano."""

    def __init__(self, spec: PlayerSpec) -> None:
        self.spec = spec
        self.position = Vector2(0, 0)
        self.previous = Vector2(0, 0)
        """Dónde estaba antes del último `step`. Lo usa el tramo de una bala enemiga,
        medido en el marco del jugador (`bullet_hits_player`)."""

    @property
    def radius(self) -> float:
        """Radio del círculo de choque, en unidades del plano."""
        return self.spec.radius

    def step(self, intent: Vector2) -> None:
        """Avanza un paso: `intent · speed · STEP`, con `intent` recortada a largo 1.

        Una intención menor que 1 (el stick a medias) avanza menos. Solo se recorta lo
        que pasa de 1, para que nada mueva al jugador más rápido que `speed`.
        """
        self.previous = Vector2(self.position)
        self.position += intent.clamp_magnitude(1) * self.spec.speed * STEP
