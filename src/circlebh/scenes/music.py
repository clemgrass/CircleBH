"""La música en la escena: lo único que toca `pygame.mixer` (ADR 0022).

El secuenciador de `audio/` entrega bloques de bytes; aquí se vuelven `Sound` y se
encadenan en un canal con `Channel.queue()`, que empieza cada uno justo cuando termina
el anterior. La reproducción corre en el hilo de audio de SDL.
"""

import sys
from collections import deque

import pygame

from circlebh.audio.playback import next_action
from circlebh.audio.rhythm import RATE
from circlebh.cli import RunOptions
from circlebh.settings import Settings

MIXER_FORMAT = (RATE, -16, 2)
"""44 100 Hz, 16 bits con signo y estéreo: el formato de los bloques."""
MIXER_BUFFER = 512
"""Muestras del búfer de SDL: menos es menos latencia, pero puede cortarse."""
MAX_QUEUED = 4
"""Bloques que pueden esperar. Si el audio va más lento que el juego, se botan los más
viejos, para que la música no se quede atrás."""


def music_enabled(options: RunOptions, settings: Settings) -> bool:
    """Suena con la ventana a tiempo real: ni en las capturas ni con `--speed`, porque
    la música avanza con los pasos y sonaría acelerada."""
    return settings.audio.music and not options.capture and options.speed == 1


def init_mixer() -> None:
    """Fija el formato antes de `pygame.init()`.

    Con `allowedchanges=0`, SDL convierte los bloques al formato del dispositivo. Sin
    eso, un dispositivo a 48 kHz tocaría los bloques más rápido y más agudos.
    """
    pygame.mixer.pre_init(*MIXER_FORMAT, MIXER_BUFFER, allowedchanges=0)


class MusicPlayer:
    """Toca los bloques del secuenciador, uno tras otro, en un canal propio."""

    def __init__(self, volume: float) -> None:
        self._waiting: deque[bytes] = deque()
        self._channel: pygame.mixer.Channel | None = None
        mixer = pygame.mixer.get_init()
        if mixer is None:
            print(
                "música: no hay dispositivo de audio; el juego sigue sin sonido",
                file=sys.stderr,
            )
            return
        if mixer != MIXER_FORMAT:
            print(
                f"música: el mixer quedó en {mixer}, no en {MIXER_FORMAT}; sin sonido",
                file=sys.stderr,
            )
            return
        self._channel = pygame.mixer.Channel(0)
        self._channel.set_volume(volume)

    @property
    def available(self) -> bool:
        """Si hay dónde tocar. Sin dispositivo, la escena ni siquiera mezcla."""
        return self._channel is not None

    def update(self, ready: deque[bytes]) -> None:
        """Saca los bloques listos y hace lo que diga `next_action` con el canal.

        Si el canal quedó mudo con un bloque atascado en su cola (la carrera de
        pygame-ce que explica `audio/playback.py`), lo arranca con `play()`.
        """
        while ready:
            self._waiting.append(ready.popleft())
        while len(self._waiting) > MAX_QUEUED:
            self._waiting.popleft()
        channel = self._channel
        if channel is None:
            self._waiting.clear()
            return
        queued = channel.get_queue()
        action = next_action(
            busy=channel.get_busy(),
            stuck=queued is not None,
            waiting=len(self._waiting),
        )
        if action == "play_stuck" and queued is not None:
            channel.play(queued)
        elif action == "play":
            channel.play(self._next_sound())
        elif action == "queue":
            channel.queue(self._next_sound())

    def _next_sound(self) -> pygame.mixer.Sound:
        return pygame.mixer.Sound(buffer=self._waiting.popleft())
