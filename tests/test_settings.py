"""Tests de la configuración del juego: `settings.json` contra la dataclass (ADR 0018)."""

import copy
import json
import math
from dataclasses import replace
from pathlib import Path

import pytest

from circlebh.datafile import DataFileError
from circlebh.settings import (
    AccessibilitySettings,
    AudioSettings,
    CameraSettings,
    ControlsSettings,
    DebugSettings,
    Settings,
    check_packaged,
    load_settings,
)

VALIDO = {
    "controls": {"stick_deadzone": 0.2},
    "camera": {"fov": 720.0, "offset": [0.0, 0.0]},
    "debug": {"show_hitboxes": False, "start_section": ""},
    "audio": {"music": True, "volume": 0.8, "base_volume": 1.0, "game_volume": 1.0},
    "accessibility": {"invert_colors": False},
}


def escribir(tmp_path: Path, texto: str) -> Path:
    path = tmp_path / "settings.json"
    path.write_text(texto, encoding="utf-8")
    return path


def con(seccion: str, campo: str, valor: object) -> str:
    """El JSON válido con un campo cambiado. `valor=...` lo quita."""
    datos = copy.deepcopy(VALIDO)
    if valor is ...:
        del datos[seccion][campo]
    else:
        datos[seccion][campo] = valor
    return json.dumps(datos)


def falla_en(path: Path) -> DataFileError:
    with pytest.raises(DataFileError) as error:
        load_settings(path)
    return error.value


def test_settings_real_valida() -> None:
    assert isinstance(load_settings(), Settings)


def test_lee_el_valor_del_archivo(tmp_path: Path) -> None:
    texto = json.dumps(
        {
            "controls": {"stick_deadzone": 0.3},
            "camera": {"fov": 900, "offset": [10, -20.5]},
            "debug": {"show_hitboxes": True, "start_section": "infinito"},
            "audio": {
                "music": False,
                "volume": 0.5,
                "base_volume": 0.25,
                "game_volume": 1,
            },
            "accessibility": {"invert_colors": True},
        }
    )
    assert load_settings(escribir(tmp_path, texto)) == Settings(
        controls=ControlsSettings(stick_deadzone=0.3),
        camera=CameraSettings(fov=900.0, offset=(10.0, -20.5)),
        debug=DebugSettings(show_hitboxes=True, start_section="infinito"),
        audio=AudioSettings(music=False, volume=0.5, base_volume=0.25, game_volume=1.0),
        accessibility=AccessibilitySettings(invert_colors=True),
    )


# --- Empezar en una sección, solo para el desarrollo (decisión 75) ---


def con_seccion(nombre: str) -> Settings:
    base = load_settings()
    return replace(base, debug=replace(base.debug, start_section=nombre))


def test_start_section_de_fabrica_vacio() -> None:
    # El juego de fábrica parte desde el comienzo del tema.
    assert load_settings().debug.start_section == ""


def test_empaquetado_rechaza_start_section() -> None:
    # Foco: un build que parte en el infinito no arranca, y el smoke del release falla.
    with pytest.raises(DataFileError, match=r"debug\.start_section"):
        check_packaged(con_seccion("infinito"), frozen=True)


def test_empaquetado_de_fabrica_arranca() -> None:
    # Borde: empaquetado y con el campo vacío, arranca.
    check_packaged(con_seccion(""), frozen=True)


def test_desarrollo_acepta_start_section() -> None:
    # Negativo: desde el código, el campo sirve para probar.
    check_packaged(con_seccion("infinito"), frozen=False)


# --- Accesibilidad ---


def test_los_colores_vienen_sin_invertir() -> None:
    # ADR 0023: el fondo negro es el de fábrica; invertir es una elección del jugador.
    assert load_settings().accessibility.invert_colors is False


def test_invertir_colores_con_otro_tipo_nombra_el_campo(tmp_path: Path) -> None:
    # "true" entre comillas es el error típico al editar a mano.
    error = falla_en(escribir(tmp_path, con("accessibility", "invert_colors", "true")))
    assert error.field == "accessibility.invert_colors"


# --- Audio ---


@pytest.mark.parametrize("campo", ["volume", "base_volume", "game_volume"])
@pytest.mark.parametrize("valor", [0, 1])
def test_volumen_en_los_bordes_vale(tmp_path: Path, campo: str, valor: float) -> None:
    path = escribir(tmp_path, con("audio", campo, valor))
    assert getattr(load_settings(path).audio, campo) == valor


@pytest.mark.parametrize("campo", ["volume", "base_volume", "game_volume"])
@pytest.mark.parametrize("valor", [-0.1, 1.1, math.nan, math.inf])
def test_volumen_fuera_de_rango_nombra_el_campo(
    tmp_path: Path, campo: str, valor: float
) -> None:
    error = falla_en(escribir(tmp_path, con("audio", campo, valor)))
    assert error.field == f"audio.{campo}"


# --- Zona muerta ---


def test_zona_muerta_cero_vale(tmp_path: Path) -> None:
    path = escribir(tmp_path, con("controls", "stick_deadzone", 0))
    assert load_settings(path).controls.stick_deadzone == 0


@pytest.mark.parametrize("valor", [1, 1.5, -0.1])
def test_zona_muerta_fuera_de_rango_nombra_el_campo(
    tmp_path: Path, valor: float
) -> None:
    # Con 1, todo el recorrido del stick sería zona muerta y la reescala dividiría por 0.
    error = falla_en(escribir(tmp_path, con("controls", "stick_deadzone", valor)))
    assert error.field == "controls.stick_deadzone"


# --- Cámara ---


def test_fov_pequeno_vale(tmp_path: Path) -> None:
    path = escribir(tmp_path, con("camera", "fov", 0.001))
    assert load_settings(path).camera.fov == 0.001


@pytest.mark.parametrize("valor", [0, -720, math.inf, math.nan])
def test_fov_no_positivo_o_infinito_nombra_el_campo(
    tmp_path: Path, valor: float
) -> None:
    # Con 0, la escala dividiría por 0. `json` de Python lee y escribe Infinity y NaN.
    error = falla_en(escribir(tmp_path, con("camera", "fov", valor)))
    assert error.field == "camera.fov"


@pytest.mark.parametrize("offset", [[math.inf, 0.0], [0.0, math.nan]])
def test_offset_no_finito_nombra_el_campo(tmp_path: Path, offset: list[float]) -> None:
    # Con Infinity, `to_screen` da NaN y el jugador desaparece sin ningún error.
    error = falla_en(escribir(tmp_path, con("camera", "offset", offset)))
    assert error.field == "camera.offset"


def test_offset_con_un_solo_numero_nombra_el_campo(tmp_path: Path) -> None:
    error = falla_en(escribir(tmp_path, con("camera", "offset", [0.0])))
    assert error.field == "camera.offset"


# --- Errores de forma ---


def test_json_mal_escrito_se_rechaza(tmp_path: Path) -> None:
    # La coma final es el error típico al editar a mano.
    path = escribir(tmp_path, '{"debug": {"show_hitboxes": false,}}')
    with pytest.raises(json.JSONDecodeError):
        load_settings(path)


def test_campo_que_falta_nombra_el_campo(tmp_path: Path) -> None:
    error = falla_en(escribir(tmp_path, con("debug", "show_hitboxes", ...)))
    assert error.field == "debug.show_hitboxes"
    assert "falta" in str(error)


def test_campo_que_sobra_nombra_el_campo(tmp_path: Path) -> None:
    error = falla_en(escribir(tmp_path, con("debug", "show_fps", True)))
    assert error.field == "debug.show_fps"
    assert "sobra" in str(error)


def test_tipo_equivocado_nombra_el_campo(tmp_path: Path) -> None:
    error = falla_en(escribir(tmp_path, con("debug", "show_hitboxes", 1)))
    assert str(error) == "debug.show_hitboxes: se esperaba true o false, llegó 1"
