"""Las balas enemigas: puntos con radio que van en línea recta (spec de la 0.2.0).

No chocan con los enemigos ni entre ellas: los atraviesan sin quitarles líneas ni
moverlos, como en un bullet hell. Matan al jugador si su tramo toca su círculo, y se
borran al pasar `despawn` de él, que ya queda fuera de la vista.
"""

from pygame.math import Vector2

from circlebh.world.clock import STEP
from circlebh.world.collisions import segment_touches_circle
from circlebh.world.player import Player


class EnemyBullet:
    """Una bala enemiga: `p ← p + v·dt` en cada paso. Su dirección queda fija al nacer."""

    def __init__(self, position: Vector2, velocity: Vector2) -> None:
        # Copias: el vértice que la disparó sigue moviéndose, y la bala no lo sigue.
        self.position = Vector2(position)
        self.previous = Vector2(position)
        """Dónde estaba antes del último `step`. Al nacer, donde nació."""
        self.velocity = Vector2(velocity)
        """Unidades del plano por segundo."""

    def step(self) -> None:
        """Avanza un paso."""
        self.previous = Vector2(self.position)
        self.position += self.velocity * STEP


def step_bullets(
    bullets: list[EnemyBullet], player: Vector2, despawn: float
) -> list[EnemyBullet]:
    """Avanza un paso cada bala y devuelve las que siguen: las que quedan a `despawn` o
    menos de `player`.

    `despawn` es `spawning.distance`, que ya queda fuera de la vista. El mundo no conoce
    la pantalla: así, la misma semilla da la misma partida en cualquier ventana.
    """
    for bullet in bullets:
        bullet.step()
    return [b for b in bullets if b.position.distance_to(player) <= despawn]


def bullet_hits_player(
    bullet: EnemyBullet, player: Player, bullet_radius: float
) -> bool:
    """Si la bala tocó al jugador en el último paso.

    Los dos se movieron, así que el tramo se mide en el marco del jugador, como el golpe
    a un enemigo (ADR 0020): la bala va de `previous` menos donde estaba el jugador a
    `position` menos donde está ahora. Que una bala con radio toque al círculo del
    jugador es lo mismo que el tramo de su centro toque un círculo agrandado en ese
    radio (la suma de Minkowski).
    """
    start = bullet.previous - player.previous
    end = bullet.position - player.position
    return segment_touches_circle(start, end, Vector2(), player.radius + bullet_radius)
