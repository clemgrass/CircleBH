"""Punto de entrada: `uv run circlebh`.

Hay dos modos:
- Con ventana: el tiempo real (× `--speed`) pasa por el reloj de pasos fijos.
- Captura (`--demo --capture t1,t2,…`): sin ventana y sin esperar. Avanza paso a paso
  y guarda un PNG en el paso de cada tiempo. La misma semilla da los mismos PNG.
"""

import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path

import pygame

from circlebh.balance import BALANCE
from circlebh.balance_tools import check
from circlebh.cli import RunOptions, parse_args
from circlebh.scenes.game import GameScene
from circlebh.scenes.music import init_mixer
from circlebh.settings import Settings, check_packaged, load_settings
from circlebh.world.clock import STEP, FixedStepClock, capture_steps
from circlebh.world.director import start_from

FPS = 60
CAPTURE_DIR = Path(".capturas")


def main(argv: Sequence[str] | None = None) -> None:
    options = parse_args(argv)
    exit_if_balance_differs()
    settings = load_settings_or_exit()
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
    """ADR 0018: el juego no abre si `settings.json` no calza con `Settings`.

    Tampoco abre si `debug.start_section` nombra una sección que no está en el tema, o
    si no está vacío en el juego empaquetado (decisión 75)."""
    try:
        settings = load_settings()
        check_packaged(settings, frozen=getattr(sys, "frozen", False))
        start_from(BALANCE.director, settings.debug.start_section)
    except json.JSONDecodeError as error:
        print(f"settings.json: no es JSON válido: {error}", file=sys.stderr)
    except ValueError as error:
        # `DataFileError` es un `ValueError`, como el de `start_from`.
        print(f"settings.json: {error}", file=sys.stderr)
    else:
        return settings
    raise SystemExit(1)


def capture_path(scenario: str, seed: int, t: float) -> Path:
    """`.capturas/<escenario>-seed<N>-t<segundos con 2 decimales>.png`."""
    return CAPTURE_DIR / f"{scenario}-seed{seed}-t{t:.2f}.png"


def run_capture(options: RunOptions, settings: Settings) -> None:
    """Avanza paso a paso, sin reloj real, y guarda un PNG en cada tiempo pedido."""
    # El driver sin ventana de SDL; tiene que fijarse antes de pygame.init().
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    screen = pygame.display.set_mode(options.window)
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    scene = GameScene(options, settings)

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


def toggle_fullscreen(
    screen: pygame.Surface, windowed: tuple[int, int] | None
) -> tuple[int, int] | None:
    """F11: entra o sale de la pantalla completa, con la resolución del escritorio.

    `windowed` es el tamaño de la ventana antes de entrar, o `None` si se está en
    ventana. Devuelve el valor nuevo. No usa `pygame.display.toggle_fullscreen()`: en
    Windows falla si el tamaño de la ventana no es un modo de video de la pantalla.
    `screen` sigue valiendo después: pasa sola al modo nuevo.
    """
    if windowed is None:
        size = screen.get_size()
        pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        return size
    pygame.display.set_mode(windowed, pygame.RESIZABLE)
    return None


def run_window(options: RunOptions, settings: Settings) -> None:
    """Abre la ventana y la mantiene hasta que el jugador la cierra o presiona Escape."""
    init_mixer()
    pygame.init()
    # La misma superficie sirve todo el rato: cambia de tamaño al redimensionar y con F11.
    screen = pygame.display.set_mode(options.window, pygame.RESIZABLE)
    pygame.display.set_caption("CircleBH")
    clock = pygame.time.Clock()
    step_clock = FixedStepClock()
    scene = GameScene(options, settings)
    windowed: tuple[int, int] | None = None

    running = True
    while running:
        real_dt = clock.tick(FPS) / 1000
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                windowed = toggle_fullscreen(screen, windowed)
            scene.handle_event(event)
        for _ in range(step_clock.advance(real_dt, options.speed)):
            scene.step()
        scene.play_music()
        scene.draw(screen)
        pygame.display.flip()


if __name__ == "__main__":
    main()
