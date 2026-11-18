"""Punto de entrada: `uv run circlebh` abre la ventana con el plano vacío."""

import pygame

WINDOW_SIZE = (1280, 720)
FPS = 60
# Provisorio: el fondo negro o blanco se decide con un prototipo (pregunta abierta).
BACKGROUND = pygame.Color("black")
AXIS_COLOR = pygame.Color("white")


def main() -> None:
    """Abre la ventana y la mantiene hasta que el jugador la cierra o presiona Escape."""
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE, pygame.RESIZABLE)
    pygame.display.set_caption("CircleBH")
    clock = pygame.time.Clock()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                running = False
        draw_empty_plane(screen)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


def draw_empty_plane(screen: pygame.Surface) -> None:
    """Dibuja el fondo y los ejes X e Y, con el origen en el centro de la ventana."""
    screen.fill(BACKGROUND)
    width, height = screen.get_size()
    pygame.draw.line(screen, AXIS_COLOR, (0, height // 2), (width, height // 2))
    pygame.draw.line(screen, AXIS_COLOR, (width // 2, 0), (width // 2, height))


if __name__ == "__main__":
    main()
