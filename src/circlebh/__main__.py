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
from circlebh.world.clock import FixedStepClock, capture_steps

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

    # Varios tiempos pueden caer en el mismo paso: se guardan todos.
    times_by_step: dict[int, list[float]] = {}
    for t, step in zip(options.capture, capture_steps(options.capture), strict=True):
        times_by_step.setdefault(step, []).append(t)

    for step in range(max(times_by_step) + 1):
        # Cuando exista `world`, aquí va `world.update(STEP)`, antes de dibujar.
        if step in times_by_step:
            draw_empty_plane(screen)
            for t in times_by_step[step]:
                path = capture_path(options.scenario, options.seed, t)
                pygame.image.save(screen, path)
                print(path)


def run_window(options: RunOptions) -> None:
    """Abre la ventana y la mantiene hasta que el jugador la cierra o presiona Escape."""
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE, pygame.RESIZABLE)
    pygame.display.set_caption("CircleBH")
    clock = pygame.time.Clock()
    step_clock = FixedStepClock()

    running = True
    while running:
        real_dt = clock.tick(FPS) / 1000 * options.speed
        # Todavía no hay `world` que actualizar, así que los pasos se descartan.
        step_clock.advance(real_dt)
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                running = False
        draw_empty_plane(screen)
        pygame.display.flip()


if __name__ == "__main__":
    main()
