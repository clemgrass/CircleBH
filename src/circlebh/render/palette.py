"""Los colores del juego: un fondo, un trazo, un acento para el peligro y una luz para lo
que es tuyo.

Todo lo que se dibuja usa el trazo, salvo el peligro que los enemigos atraviesan, que usa
el acento: las balas enemigas y la gran estrella roja, con su aviso y su apagarse. Lo que
tapa o desvanece la escena usa el fondo. Así, invertir los colores es invertir el fondo
y el trazo (ADR 0023).

La luz es el segundo color, y no es peligro: la experiencia, el borde que se carga y la
tarjeta elegida (ADR 0031). Va de verde azulado a azul.
"""

from dataclasses import dataclass

import pygame


@dataclass(frozen=True)
class Light:
    """La luz de lo que es tuyo, para un fondo (ADR 0031)."""

    low: pygame.Color
    """El punto que menos vale: verde azulado."""
    high: pygame.Color
    """El punto que más vale: azul."""
    selection: pygame.Color
    """El color intermedio: el borde de la experiencia y la tarjeta elegida."""

    def at(self, t: float) -> pygame.Color:
        """El color en `t` ∈ [0, 1], de `low` a `high`."""
        return self.low.lerp(self.high, min(1.0, max(0.0, t)))


ON_BLACK = Light(
    low=pygame.Color("#3ad2c2"),
    high=pygame.Color("#5e9afe"),
    selection=pygame.Color("#4cb6e0"),
)
"""La luz sobre el fondo negro: clara, para que brille."""

ON_WHITE = Light(
    low=pygame.Color("#0e8c82"),
    high=pygame.Color("#1e5ad2"),
    selection=pygame.Color("#1673aa"),
)
"""La luz sobre el fondo blanco: el mismo tono, más oscuro, porque una luz clara casi no
se ve sobre el blanco."""


@dataclass(frozen=True)
class Palette:
    background: pygame.Color
    foreground: pygame.Color
    letterbox: pygame.Color
    """Las franjas fuera del área útil: apenas distintas del fondo."""
    accent: pygame.Color
    """El peligro. Es el mismo en las dos paletas: tiene que leerse sobre el negro y
    sobre el blanco."""
    light: Light
    """Lo que es tuyo. Cada fondo tiene la suya."""

    def inverted(self) -> Palette:
        """El negativo de cada color: el fondo negro pasa a blanco, y el trazo, a negro.

        El acento no se invierte: su negativo cambia de tono (el rojo pasa a cian), y el
        peligro dejaría de verse igual (ADR 0023). La luz tampoco: su negativo sería
        rojizo, el color del peligro. Pasa a la luz del otro fondo (ADR 0031)."""
        return Palette(
            negative(self.background),
            negative(self.foreground),
            negative(self.letterbox),
            self.accent,
            ON_WHITE if self.light == ON_BLACK else ON_BLACK,
        )


def negative(color: pygame.Color) -> pygame.Color:
    """Cada canal pasa de `c` a `255 - c`; la opacidad no cambia."""
    return pygame.Color(255 - color.r, 255 - color.g, 255 - color.b, color.a)


DARK = Palette(
    background=pygame.Color("black"),
    foreground=pygame.Color("white"),
    letterbox=pygame.Color("#202020"),
    accent=pygame.Color("#ff3b30"),
    light=ON_BLACK,
)
"""La paleta de fábrica: fondo negro y trazo blanco."""
