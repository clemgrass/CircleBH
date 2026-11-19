"""Punto de entrada: `uv run circlebh`.

Hay dos modos:
- Con ventana: el tiempo real (× `--speed`) pasa por el reloj de pasos fijos.
- Captura (`--demo --capture t1,t2,…`): sin ventana y sin esperar. Avanza paso a paso
  y guarda un PNG en el paso de cada tiempo. La misma semilla da los mismos PNG.
"""

import json
import os
import random
import sys
from collections.abc import Sequence
from pathlib import Path

import pygame

from circlebh.balance import BALANCE
from circlebh.balance_tools import check
from circlebh.cli import RunOptions, parse_args
from circlebh.datafile import DataFileError
from circlebh.scenes.game import GameScene
from circlebh.scenes.scenarios import SCENARIOS
from circlebh.settings import Settings, load_settings
from circlebh.world.clock import STEP, FixedStepClock, capture_steps
from circlebh.world.game import World

WINDOW_SIZE = (1280, 720)
FPS = 60
CAPTURE_DIR = Path(".capturas")


def main(argv: Sequence[str] | None = None) -> None:
    options = parse_args(argv)
    exit_if_balance_differs()
    settings = load_settings_or_exit()
    print(f"semilla: {options.seed}")
    try:
        if options.capture:
            run_capture(options, settings)
        else:
            run_window(options, settings)
    finally:
        pygame.quit()


def exit_if_balance_differs() -> None:
    """ADR 0004: el juego no abre si `balance.py` y `balance.json` no calzan."""
    errors = check()
    if errors:
        for line in errors:
            print(line, file=sys.stderr)
        print(
            "Iguálalos con `poe balance-exportar` o `poe balance-importar`.",
            file=sys.stderr,
        )
        raise SystemExit(1)


def load_settings_or_exit() -> Settings:
    """ADR 0018: el juego no abre si `settings.json` no calza con `Settings`."""
    try:
        return load_settings()
    except json.JSONDecodeError as error:
        print(f"settings.json: no es JSON válido: {error}", file=sys.stderr)
    except DataFileError as error:
        print(f"settings.json: {error}", file=sys.stderr)
    raise SystemExit(1)


def capture_path(scenario: str, seed: int, t: float) -> Path:
    """`.capturas/<escenario>-seed<N>-t<segundos con 2 decimales>.png`."""
    return CAPTURE_DIR / f"{scenario}-seed{seed}-t{t:.2f}.png"


def new_scene(options: RunOptions, settings: Settings) -> GameScene:
    """Una partida con la semilla de `options`. En la demo, el escenario mueve al jugador."""
    world = World(BALANCE, random.Random(options.seed))
    demo = SCENARIOS[options.scenario] if options.demo else None
    return GameScene(world, settings, demo)


def run_capture(options: RunOptions, settings: Settings) -> None:
    """Avanza paso a paso, sin reloj real, y guarda un PNG en cada tiempo pedido."""
    # El driver sin ventana de SDL; tiene que fijarse antes de pygame.init().
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE)
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    scene = new_scene(options, settings)

    # Varios tiempos pueden caer en el mismo paso: ese paso se captura una sola vez.
    steps = set(capture_steps(options.capture))

    for step in range(max(steps) + 1):
        if step in steps:
            scene.draw(screen)
            # El nombre lleva el tiempo del paso capturado, no el pedido: como un paso
            # (1/60 s) es más que 0,01 s, dos pasos distintos nunca comparten nombre.
            path = capture_path(options.scenario, options.seed, step * STEP)
            pygame.image.save(screen, path)
            print(path)
        # Después de capturar: así el paso 0 es el estado inicial.
        scene.step()


def run_window(options: RunOptions, settings: Settings) -> None:
    """Abre la ventana y la mantiene hasta que el jugador la cierra o presiona Escape."""
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE, pygame.RESIZABLE)
    pygame.display.set_caption("CircleBH")
    clock = pygame.time.Clock()
    step_clock = FixedStepClock()
    scene = new_scene(options, settings)

    running = True
    while running:
        real_dt = clock.tick(FPS) / 1000
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                running = False
            scene.handle_event(event)
        for _ in range(step_clock.advance(real_dt, options.speed)):
            scene.step()
        scene.draw(screen)
        pygame.display.flip()


if __name__ == "__main__":
    main()
