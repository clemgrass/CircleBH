"""Punto de entrada: `uv run circlebh`.

Hay dos modos:
- Con ventana: el tiempo real (× `--speed`) pasa por el reloj de pasos fijos.
- Captura (`--demo --capture t1,t2,…`): sin ventana y sin esperar. Avanza paso a paso
  y guarda un PNG en el paso de cada tiempo. La misma semilla da los mismos PNG.
"""

import os
from collections.abc import Sequence
from pathlib import Path

import pygame

from circlebh.cli import RunOptions, parse_args
from circlebh.render.plane import draw_empty_plane
from circlebh.world.clock import STEP, FixedStepClock, capture_steps

WINDOW_SIZE = (1280, 720)
FPS = 60
CAPTURE_DIR = Path(".capturas")


def main(argv: Sequence[str] | None = None) -> None:
    options = parse_args(argv)
    print(f"semilla: {options.seed}")
    try:
        if options.capture:
            run_capture(options)
        else:
            run_window(options)
    finally:
        pygame.quit()


def capture_path(scenario: str, seed: int, t: float) -> Path:
    """`.capturas/<escenario>-seed<N>-t<segundos con 2 decimales>.png`."""
    return CAPTURE_DIR / f"{scenario}-seed{seed}-t{t:.2f}.png"


def run_capture(options: RunOptions) -> None:
    """Avanza paso a paso, sin reloj real, y guarda un PNG en cada tiempo pedido."""
    # El driver sin ventana de SDL; tiene que fijarse antes de pygame.init().
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE)
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)

    # Varios tiempos pueden caer en el mismo paso: ese paso se captura una sola vez.
    steps = set(capture_steps(options.capture))

    for step in range(max(steps) + 1):
        if step in steps:
            draw_empty_plane(screen)
            # El nombre lleva el tiempo del paso capturado, no el pedido: como un paso
            # (1/60 s) es más que 0,01 s, dos pasos distintos nunca comparten nombre.
            path = capture_path(options.scenario, options.seed, step * STEP)
            pygame.image.save(screen, path)
            print(path)
        # Cuando exista `world`, aquí va `world.update(STEP)`, después de capturar:
        # así el paso 0 es el estado inicial.


def run_window(options: RunOptions) -> None:
    """Abre la ventana y la mantiene hasta que el jugador la cierra o presiona Escape."""
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE, pygame.RESIZABLE)
    pygame.display.set_caption("CircleBH")
    clock = pygame.time.Clock()
    step_clock = FixedStepClock()

    running = True
    while running:
        real_dt = clock.tick(FPS) / 1000
        # Todavía no hay `world` que actualizar, así que los pasos se descartan.
        step_clock.advance(real_dt, options.speed)
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                running = False
        draw_empty_plane(screen)
        pygame.display.flip()


if __name__ == "__main__":
    main()
