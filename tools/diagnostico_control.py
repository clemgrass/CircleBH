"""Graba el stick izquierdo del control, sin ventana, para diagnosticar la entrada.

Uso: `uv run python tools/diagnostico_control.py [segundos] [salida.csv]`

En cada frame (60 por segundo) guarda los ejes crudos y la intención que calcula el
juego. Al final resume dónde los valores se congelaron, dónde el largo cayó en la
zona muerta y dónde la dirección de la intención se alejó de la del stick.
"""

import csv
import itertools
import math
import os
import sys
import time
from pathlib import Path

import pygame
import pygame._sdl2.controller as sdl_controller

from circlebh.controls import axis_to_unit, stick_intent
from circlebh.settings import load_settings

FPS = 60


def main() -> None:
    seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 15.0
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("diagnostico_control.csv")
    deadzone = load_settings().controls.stick_deadzone

    # Sin ventana: el driver `dummy` de SDL, fijado antes de pygame.init(). Los eventos
    # del control llegan igual, y no se abre pantalla (ADR 0016).
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    sdl_controller.init()
    clock = pygame.time.Clock()
    pad = None
    rows = []
    motion_events = 0
    start = time.perf_counter()
    while time.perf_counter() - start < seconds:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.CONTROLLERDEVICEADDED and pad is None:
                pad = sdl_controller.Controller(event.device_index)
                print(f"control: {pad.name}", flush=True)
            elif event.type == pygame.CONTROLLERAXISMOTION:
                motion_events += 1
        if pad is None:
            continue
        raw_x = pad.get_axis(pygame.CONTROLLER_AXIS_LEFTX)
        raw_y = pad.get_axis(pygame.CONTROLLER_AXIS_LEFTY)
        x, y = axis_to_unit(raw_x), axis_to_unit(raw_y)
        intent = stick_intent(x, y, deadzone)
        rows.append(
            {
                "t": round(time.perf_counter() - start, 4),
                "raw_x": raw_x,
                "raw_y": raw_y,
                "largo_stick": round(math.hypot(x, y), 4),
                "intent_x": round(intent.x, 4),
                "intent_y": round(intent.y, 4),
                "largo_intent": round(intent.length(), 4),
            }
        )
    pygame.quit()

    if not rows:
        print("no llegó ningún control")
        return
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summarize(rows, deadzone, motion_events)
    print(f"datos: {out}")


def summarize(rows: list[dict[str, float]], deadzone: float, motion: int) -> None:
    print(f"frames: {len(rows)}, eventos de eje: {motion}, zona muerta: {deadzone}")
    # Rachas de frames con los dos ejes crudos idénticos mientras el stick está inclinado.
    frozen, run_start = [], None
    for prev, row in itertools.pairwise(rows):
        same = (prev["raw_x"], prev["raw_y"]) == (row["raw_x"], row["raw_y"])
        if same and row["largo_stick"] > 0.5:
            run_start = run_start if run_start is not None else prev["t"]
        elif run_start is not None:
            frozen.append((run_start, prev["t"]))
            run_start = None
    long_frozen = [(a, b) for a, b in frozen if b - a >= 0.05]
    print(f"congelados ≥ 50 ms con el stick inclinado: {len(long_frozen)}")
    for a, b in long_frozen[:20]:
        print(f"  {a:.3f} s → {b:.3f} s ({(b - a) * 1000:.0f} ms)")
    # Frames con el stick bastante inclinado (> 0,5) pero intención casi nula.
    dropped = [r for r in rows if r["largo_stick"] > 0.5 and r["largo_intent"] < 0.3]
    print(f"stick > 0,5 pero intención < 0,3: {len(dropped)}")
    # Largo mínimo del stick mientras se mueve (para ver si las transiciones se achican).
    moving = [r["largo_stick"] for r in rows if r["largo_stick"] > deadzone / 2]
    if not moving:
        print("AVISO: el stick no se movió; esta grabación no sirve para diagnosticar")
        return
    print(
        f"largo del stick en movimiento: mín {min(moving):.3f}, máx {max(moving):.3f}"
    )
    low = [r for r in rows if deadzone / 2 < r["largo_stick"] <= deadzone]
    print(f"frames que caen en la zona muerta a medio camino: {len(low)}")


if __name__ == "__main__":
    main()
