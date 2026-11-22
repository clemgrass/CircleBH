"""Los colores del juego: un fondo, un trazo y un acento para el peligro.

Todo lo que se dibuja usa el trazo, salvo el peligro que los enemigos atraviesan, que usa
el acento: las balas enemigas y la gran estrella roja, con su aviso y su apagarse. Lo que
tapa o desvanece la escena usa el fondo. Así, invertir los colores es invertir el fondo
y el trazo (ADR 0023).
"""

from dataclasses import dataclass

import pygame


@dataclass(frozen=True)
class Palette:
    background: pygame.Color
    foreground: pygame.Color
    letterbox: pygame.Color
    """Las franjas fuera del área útil: apenas distintas del fondo."""
    accent: pygame.Color
    """El peligro. Es el mismo en las dos paletas: tiene que leerse sobre el negro y
    sobre el blanco."""

    def inverted(self) -> Palette:
        """El negativo de cada color: el fondo negro pasa a blanco, y el trazo, a negro.

        El acento no se invierte: su negativo cambia de tono (el rojo pasa a cian), y el
        peligro dejaría de verse igual (ADR 0023)."""
        return Palette(
            negative(self.background),
            negative(self.foreground),
            negative(self.letterbox),
            self.accent,
        )


def negative(color: pygame.Color) -> pygame.Color:
    """Cada canal pasa de `c` a `255 - c`; la opacidad no cambia."""
    return pygame.Color(255 - color.r, 255 - color.g, 255 - color.b, color.a)


DARK = Palette(
    background=pygame.Color("black"),
    foreground=pygame.Color("white"),
    letterbox=pygame.Color("#202020"),
    accent=pygame.Color("#ff3b30"),
)
"""La paleta de fábrica: fondo negro y trazo blanco."""
