"""La cámara: pasa un punto del plano a un píxel de la pantalla (ADR 0003 y 0005).

La pantalla muestra siempre la misma altura del plano, `fov`, en un área de 16:9. Si la
ventana tiene otra proporción, el área queda centrada y lo que sobra son franjas. Es la
única pieza que invierte la Y: en el plano, Y crece hacia arriba; en pantalla, hacia abajo.
"""

from pygame.math import Vector2

ASPECT_WIDTH, ASPECT_HEIGHT = 16, 9


def camera_center(target: Vector2, offset: tuple[float, float]) -> Vector2:
    """El centro de la cámara: el jugador, más el desplazamiento de la configuración."""
    return target + Vector2(offset)


class Viewport:
    """La cámara de un frame: el tamaño de la ventana, el FOV y el centro, ya resueltos."""

    def __init__(self, window: tuple[int, int], fov: float, center: Vector2) -> None:
        width, height = window
        if width * ASPECT_HEIGHT >= height * ASPECT_WIDTH:
            # Más ancha que 16:9, o justa: manda el alto, y las franjas van a los lados.
            area_height = height
            area_width = round(height * ASPECT_WIDTH / ASPECT_HEIGHT)
        else:
            # Más alta: manda el ancho, y las franjas van arriba y abajo.
            area_width = width
            area_height = round(width * ASPECT_HEIGHT / ASPECT_WIDTH)
        left = (width - area_width) // 2
        top = (height - area_height) // 2

        self.rect = (left, top, area_width, area_height)
        """El área útil: `(left, top, width, height)` en píxeles, sin las franjas."""
        self.scale = area_height / fov
        """Píxeles por unidad del plano. Con la ventana minimizada, 0."""
        self.center = Vector2(center)
        """El punto del plano que cae en el centro del área útil."""
        self._screen_center = (left + area_width / 2, top + area_height / 2)

    def to_screen(self, p: Vector2) -> tuple[float, float]:
        """El píxel donde se dibuja el punto `p` del plano."""
        cx, cy = self._screen_center
        return (
            cx + (p.x - self.center.x) * self.scale,
            # El signo menos invierte la Y: más arriba en el plano es más arriba en pantalla.
            cy - (p.y - self.center.y) * self.scale,
        )

    def width(self, units: float) -> int:
        """Un grosor del plano en píxeles, nunca menor que 1.

        Con 0, `pygame.draw.circle` rellena el círculo en vez de dibujar su borde, y
        `pygame.draw.line` no dibuja nada.
        """
        return max(1, round(units * self.scale))
