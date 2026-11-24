"""La pantalla de muerte: un efecto corto al tocarte y, después, la semilla y el tiempo,
con el del modo infinito si llegaste.

El efecto es solo visual: `world` ya se detuvo. Desde el jugador sale un anillo que
crece y se desvanece mientras la escena se oscurece. Al terminar, aparece el texto.
"""

import pygame
from pygame.math import Vector2

from circlebh.render.palette import Palette
from circlebh.viewport import Viewport
from circlebh.world.clock import STEP

EFFECT_STEPS = round(0.6 / STEP)
"""Cuántos pasos dura el efecto: 0,6 s."""
RING_GROWTH = 8.0
"""Al terminar el efecto, el anillo mide esta cantidad de veces el radio del jugador."""
RING_WIDTH = 2.0
"""Grosor del anillo, en unidades del plano: escala con la cámara."""
SHADE_ALPHA = 180
"""Cuánto se desvanece la escena hacia el fondo detrás del texto, de 0 a 255."""
TITLE_SIZE = 64.0
TEXT_SIZE = 28.0
"""Tamaños de letra, en unidades del plano: escalan con la cámara."""
TEXT_CENTER = 0.7
"""A qué altura del área útil va el centro del texto: 0 es arriba y 1, abajo."""


class DeathScreen:
    """Dibuja la muerte encima de la partida congelada.

    Reusa lo que es caro de crear en cada frame: la capa con transparencia y las
    fuentes. Las dos dependen del tamaño del área útil, así que se rehacen solo cuando
    cambia. Vive con la escena, que se crea después de `pygame.init()`.
    """

    def __init__(self, palette: Palette) -> None:
        self._palette = palette
        self._size = (0, 0)
        self._layer = pygame.Surface(self._size, pygame.SRCALPHA)
        self._fonts: dict[int, pygame.font.Font] = {}

    def draw(
        self,
        screen: pygame.Surface,
        viewport: Viewport,
        player: tuple[Vector2, float],
        dead_steps: int,
        seed: int,
        elapsed: float,
        endless: float,
        *,
        show_hint: bool,
    ) -> None:
        """El efecto según los pasos desde la muerte, y el texto cuando termina.

        `player` es la posición y el radio del jugador al morir. `elapsed` es el tiempo
        total y `endless`, el del modo infinito, que solo se escribe si llegaste. Con
        `show_hint`, el texto dice cómo reiniciar.
        """
        progress = min(dead_steps / EFFECT_STEPS, 1.0)
        left, top, width, height = viewport.rect
        self._resize((width, height))
        # La capa del tamaño del área útil lleva la sombra y el anillo.
        layer = self._layer
        layer.fill((*self._palette.background.rgb, round(SHADE_ALPHA * progress)))

        if progress < 1:
            position, radius = player
            x, y = viewport.to_screen(position)
            ring = radius * (1 + (RING_GROWTH - 1) * progress)
            fade = round(255 * (1 - progress))
            pygame.draw.circle(
                layer,
                (*self._palette.foreground.rgb, fade),
                (x - left, y - top),
                ring * viewport.scale,
                viewport.width(RING_WIDTH),
            )
        screen.blit(layer, (left, top))

        if progress == 1:
            lines = [(f"duraste {elapsed:.1f} s".replace(".", ","), TITLE_SIZE)]
            if endless > 0:
                text = f"en el infinito: {endless:.1f} s".replace(".", ",")
                lines.append((text, TEXT_SIZE))
            lines.append((f"semilla: {seed}", TEXT_SIZE))
            if show_hint:
                lines.append(("R o X para reiniciar", TEXT_SIZE))
            self._draw_lines(screen, viewport, lines)

    def _resize(self, size: tuple[int, int]) -> None:
        """Si cambió el tamaño del área útil, una capa nueva y fuentes nuevas.

        Las fuentes viejas se sueltan: con la ventana arrastrada de a poco, guardarlas
        todas sumaría una por cada alto que pasó.
        """
        if size != self._size:
            self._size = size
            self._layer = pygame.Surface(size, pygame.SRCALPHA)
            self._fonts.clear()

    def _draw_lines(
        self, screen: pygame.Surface, viewport: Viewport, lines: list[tuple[str, float]]
    ) -> None:
        """Escribe las líneas una bajo otra, centradas a lo ancho y bajo el jugador.

        El bloque se centra en `TEXT_CENTER` del alto: el jugador queda al centro de la
        pantalla, y así el texto no tapa dónde moriste.
        """
        left, top, width, height = viewport.rect
        surfaces = [
            self._font(viewport.width(size)).render(
                text, True, self._palette.foreground
            )
            for text, size in lines
        ]
        y = top + height * TEXT_CENTER - sum(s.get_height() for s in surfaces) / 2
        for surface in surfaces:
            screen.blit(surface, (left + (width - surface.get_width()) / 2, y))
            y += surface.get_height()

    def _font(self, size: int) -> pygame.font.Font:
        """La fuente que trae pygame-ce, en `size` píxeles."""
        if size not in self._fonts:
            self._fonts[size] = pygame.font.Font(None, size)
        return self._fonts[size]
