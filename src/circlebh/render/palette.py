"""Los colores del juego: un fondo y un trazo, y nada más hasta que llegue el acento.

Todo lo que se dibuja usa el trazo. Lo que tapa o desvanece la escena usa el fondo.
Así, invertir los colores es invertir la paleta y nada más (ADR 0023).
"""

from dataclasses import dataclass

import pygame


@dataclass(frozen=True)
class Palette:
    background: pygame.Color
    foreground: pygame.Color
    letterbox: pygame.Color
    """Las franjas fuera del área útil: apenas distintas del fondo."""

    def inverted(self) -> Palette:
        """El negativo de cada color: el fondo negro pasa a blanco, y el trazo, a negro."""
        return Palette(
            negative(self.background),
            negative(self.foreground),
            negative(self.letterbox),
        )


def negative(color: pygame.Color) -> pygame.Color:
    """Cada canal pasa de `c` a `255 - c`; la opacidad no cambia."""
    return pygame.Color(255 - color.r, 255 - color.g, 255 - color.b, color.a)


DARK = Palette(
    background=pygame.Color("black"),
    foreground=pygame.Color("white"),
    letterbox=pygame.Color("#202020"),
)
"""La paleta de fábrica: fondo negro y trazo blanco."""
