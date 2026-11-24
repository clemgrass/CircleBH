"""Configuración del juego: cómo se juega y se ve (ADR 0018).

El valor de cada variable vive solo en `settings.json`, dentro del paquete. Aquí están
los campos, sus tipos y qué hace cada uno. Al arrancar, el juego valida el archivo contra
estas clases: si falta un campo, sobra uno o un tipo no calza, no abre y nombra el campo.

Para agregar una variable, escribe el campo en su clase y su valor en `settings.json`.
"""

import json
import math
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from circlebh.datafile import DataFileError, load


@dataclass(frozen=True)
class ControlsSettings:
    """Cómo se lee el control."""

    stick_deadzone: float
    """Zona muerta del stick, de 0 a 1 sin incluir el 1: lo que se mueve menos que esto
    no cuenta. Tapa la deriva de un stick suelto, que no vuelve justo al centro."""

    def __post_init__(self) -> None:
        # Con 1, todo el recorrido sería zona muerta, y `stick_intent` dividiría por 0.
        if not 0 <= self.stick_deadzone < 1:
            raise DataFileError(
                "controls.stick_deadzone",
                f"debe ser ≥ 0 y < 1, llegó {self.stick_deadzone}",
            )


@dataclass(frozen=True)
class CameraSettings:
    """Qué muestra la cámara (ADR 0005)."""

    fov: float
    """Altura visible del plano, en unidades. Con 720, en una ventana de 1280×720,
    una unidad se ve como un píxel."""

    offset: tuple[float, float]
    """Desplazamiento del centro de la cámara respecto del jugador, en unidades."""

    def __post_init__(self) -> None:
        # Con 0, la escala dividiría por 0; con infinito, no se vería nada.
        if not (math.isfinite(self.fov) and self.fov > 0):
            raise DataFileError(
                "camera.fov", f"debe ser un número finito > 0, llegó {self.fov}"
            )
        # Con Infinity, `to_screen` da NaN y no se dibuja nada, sin ningún error.
        if not all(math.isfinite(v) for v in self.offset):
            raise DataFileError(
                "camera.offset", f"debe tener números finitos, llegó {self.offset}"
            )


@dataclass(frozen=True)
class DebugSettings:
    """Ayudas para depurar."""

    show_hitboxes: bool
    """Dibuja el círculo de choque del jugador y el círculo envolvente de cada enemigo."""

    start_section: str
    """La sección del tema en que parte la partida, como `"infinito"`; con `""`, desde el
    comienzo. Es solo para el desarrollo: el juego empaquetado no arranca si no está
    vacío (`check_packaged`, decisión 75)."""


@dataclass(frozen=True)
class AudioSettings:
    """La música (ADR 0022). Es configuración para el jugador: cada capa tiene su
    volumen, y se puede apagar la música entera."""

    music: bool
    """Si suena la música."""

    volume: float
    """Volumen general, de 0 a 1."""

    base_volume: float
    """Volumen de la base de techno (batería, pad y bajo), de 0 a 1."""

    game_volume: float
    """Volumen de lo que sale del juego (loops de enemigos, arma y golpes), de 0 a 1."""

    def __post_init__(self) -> None:
        for name in ("volume", "base_volume", "game_volume"):
            value = getattr(self, name)
            # Con NaN, la comparación da falso y la mezcla quedaría en NaN, sin error.
            if not (math.isfinite(value) and 0 <= value <= 1):
                raise DataFileError(
                    f"audio.{name}", f"debe estar entre 0 y 1, llegó {value}"
                )


@dataclass(frozen=True)
class AccessibilitySettings:
    """Cómo se ve, para quien lo necesita o lo prefiere."""

    invert_colors: bool
    """Invierte la paleta (ADR 0023): fondo blanco y trazo negro en vez de al revés."""


@dataclass(frozen=True)
class Settings:
    """Toda la configuración del juego."""

    controls: ControlsSettings
    """Cómo se lee el control."""

    camera: CameraSettings
    """Qué muestra la cámara."""

    debug: DebugSettings
    """Ayudas para depurar."""

    audio: AudioSettings
    """La música."""

    accessibility: AccessibilitySettings
    """Cómo se ve, para quien lo necesita o lo prefiere."""


def load_settings(path: Path | None = None) -> Settings:
    """Lee y valida `settings.json`: por defecto, el del paquete, con `importlib.resources`.

    Lanza `json.JSONDecodeError` si el archivo no es JSON, y `DataFileError`, con la
    ruta del campo, si no calza con `Settings`.
    """
    if path is None:
        text = resources.files("circlebh").joinpath("settings.json").read_text("utf-8")
    else:
        text = path.read_text(encoding="utf-8")
    return load(Settings, json.loads(text))


def check_packaged(settings: Settings, *, frozen: bool) -> None:
    """Rechaza las ayudas de desarrollo en el juego empaquetado (`frozen`, que pone
    PyInstaller en `sys.frozen`). El smoke del release corre el ejecutable, así que un
    build que parte en otra sección falla antes de publicarse (decisión 75)."""
    if frozen and settings.debug.start_section:
        raise DataFileError(
            "debug.start_section",
            "es solo para el desarrollo, y en el juego empaquetado tiene que ser"
            f' "", llegó {settings.debug.start_section!r}',
        )
