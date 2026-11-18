"""El plano cartesiano vacío: el fondo y los dos ejes."""

import pygame

# Provisorio: el fondo negro o blanco se decide con un prototipo (pregunta abierta).
BACKGROUND = pygame.Color("black")
AXIS_COLOR = pygame.Color("white")


def draw_empty_plane(screen: pygame.Surface) -> None:
    """Dibuja el fondo y los ejes X e Y, con el origen en el centro de la ventana."""
    screen.fill(BACKGROUND)
    width, height = screen.get_size()
    pygame.draw.line(screen, AXIS_COLOR, (0, height // 2), (width, height // 2))
    pygame.draw.line(screen, AXIS_COLOR, (width // 2, 0), (width // 2, height))
