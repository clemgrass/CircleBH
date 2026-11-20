"""Qué hace la reproducción en cada cuadro (ADR 0022).

`scenes/music.py` encadena los bloques en un canal con `Channel.queue()`. Esta función
decide qué hacer según el estado del canal, y vive aquí, sin Pygame, para poder
testearla.

Hay una carrera en pygame-ce 2.5.8 (`src_c/mixer.c`): cuando un sonido termina, el
callback del hilo de audio revisa la cola **sin el GIL**. Si la ve vacía, se queda
esperando el GIL para borrar la marca del sonido actual. Si en ese momento el hilo
principal llama a `queue()`, la marca todavía dice "sonando" y el bloque queda en la
cola. Después el callback borra la marca, y el canal queda mudo con el bloque atascado
para siempre. Pasa cuando un bloque termina sin otro en cola: un *underrun*.
"""

from typing import Literal

PREBUFFER = 2
"""Bloques que tienen que esperar antes de partir en silencio: uno suena y otro queda en
cola. Así, un cuadro atrasado no deja al canal sin nada que tocar."""

type Action = Literal["wait", "play", "play_stuck", "queue"]


def next_action(*, busy: bool, stuck: bool, waiting: int) -> Action:
    """Qué hacer en este cuadro.

    - `busy`: si el canal está sonando (`Channel.get_busy()`).
    - `stuck`: si hay un bloque en la cola del canal (`get_queue()` no es `None`).
    - `waiting`: cuántos bloques listos esperan de este lado.

    Devuelve:
    - `"play_stuck"` si el canal está mudo con un bloque en su cola (la carrera): hay
      que arrancarlo con `play()`, que además limpia la cola;
    - `"play"` si está mudo y ya se juntó el colchón;
    - `"queue"` si suena y su cola está libre;
    - `"wait"` en los demás casos.
    """
    if not busy:
        if stuck:
            return "play_stuck"
        return "play" if waiting >= PREBUFFER else "wait"
    if not stuck and waiting > 0:
        return "queue"
    return "wait"
