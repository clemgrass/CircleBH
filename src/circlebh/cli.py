"""Línea de comandos de `circlebh`.

Los errores salen por `argparse`, con código 2 y un mensaje que dice qué valor falló.
"""

import argparse
import math
import secrets
from collections.abc import Sequence
from dataclasses import dataclass

from circlebh.scenes.scenarios import SCENARIOS


@dataclass(frozen=True)
class RunOptions:
    """Cómo se corre el juego, ya validado."""

    demo: bool
    scenario: str
    seed: int
    seed_fixed: bool
    """Si la semilla se fijó con `--seed`. Si no, cada partida nueva sortea otra."""
    speed: float
    capture: tuple[float, ...]
    window: tuple[int, int]
    """Tamaño inicial de la ventana, o de las capturas, en píxeles."""


def _seed(text: str) -> int:
    try:
        value = int(text)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"no es un entero: {text!r}") from error
    if value < 0:
        raise argparse.ArgumentTypeError(f"debe ser un entero ≥ 0: {value}")
    return value


def _speed(text: str) -> float:
    try:
        value = float(text)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"no es un número: {text!r}") from error
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError(f"debe ser un número mayor que 0: {text!r}")
    return value


def _capture_times(text: str) -> tuple[float, ...]:
    """`"2, 0,2"` → `(0.0, 2.0)`: ordenados, sin repetidos, finitos y ≥ 0."""
    times = set()
    for part in text.split(","):
        try:
            t = float(part)
        except ValueError as error:
            raise argparse.ArgumentTypeError(
                f"tiempo inválido: {part.strip()!r}"
            ) from error
        # Con inf, el modo captura no terminaría nunca.
        if not math.isfinite(t) or t < 0:
            raise argparse.ArgumentTypeError(
                f"cada tiempo debe ser un número finito ≥ 0: {part.strip()!r}"
            )
        times.add(t)
    return tuple(sorted(times))


def _window(text: str) -> tuple[int, int]:
    """`"1600x900"` → `(1600, 900)`, con los dos lados ≥ 1."""
    parts = text.split("x")
    try:
        width, height = (int(part) for part in parts)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            f"se espera ANCHOxALTO, como 1280x720: {text!r}"
        ) from error
    if width < 1 or height < 1:
        raise argparse.ArgumentTypeError(f"cada lado debe ser ≥ 1: {text!r}")
    return width, height


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="circlebh",
        description="Un survivors donde las armas son curvas matemáticas.",
    )
    parser.add_argument(
        "--demo", action="store_true", help="partida simulada, sin teclado"
    )
    parser.add_argument(
        "--scenario",
        choices=sorted(SCENARIOS),
        default="enemigo-persigue",
        help="estado inicial de la demo (por defecto: %(default)s)",
    )
    parser.add_argument(
        "--seed",
        type=_seed,
        default=None,
        help="semilla del azar; por defecto, al azar",
    )
    parser.add_argument(
        "--speed",
        type=_speed,
        default=1.0,
        help="multiplica el tiempo real en el modo con ventana (por defecto: %(default)s)",
    )
    parser.add_argument(
        "--capture",
        type=_capture_times,
        default=(),
        metavar="T1,T2,…",
        help="guarda un PNG en cada tiempo, en segundos, sin abrir ventana; exige --demo",
    )
    parser.add_argument(
        "--window",
        type=_window,
        default=(1280, 720),
        metavar="ANCHOxALTO",
        help="tamaño inicial de la ventana, o de las capturas (por defecto: 1280x720)",
    )
    return parser


def parse_args(argv: Sequence[str] | None = None) -> RunOptions:
    """Lee los argumentos (por defecto, los de `sys.argv`) y devuelve las opciones validadas."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.capture and not args.demo:
        parser.error("--capture exige --demo")
    # La semilla se elige fuera del juego; dentro, el azar sale solo de Random(seed) (ADR 0005).
    seed = args.seed if args.seed is not None else random_seed()
    return RunOptions(
        demo=args.demo,
        scenario=args.scenario,
        seed=seed,
        seed_fixed=args.seed is not None,
        speed=args.speed,
        capture=args.capture,
        window=args.window,
    )


def random_seed() -> int:
    """Una semilla al azar, fuera del juego (ADR 0005)."""
    return secrets.randbelow(2**32)


def next_seed(options: RunOptions, game: int) -> int:
    """La semilla de la partida número `game` (la primera es la 0, con `options.seed`).

    - En la demo y las capturas, `seed + game`: solo depende de la semilla inicial, así
      que repetir con la semilla impresa da lo mismo, también después de morir.
    - Jugando, la misma si se fijó con `--seed`, o una nueva al azar.
    """
    if options.demo:
        return options.seed + game
    return options.seed if options.seed_fixed else random_seed()
