"""Tests de la configuración del juego: `settings.json` contra la dataclass (ADR 0018)."""

import copy
import json
import math
from pathlib import Path

import pytest

from circlebh.datafile import DataFileError
from circlebh.settings import (
    CameraSettings,
    ControlsSettings,
    DebugSettings,
    Settings,
    load_settings,
)

VALIDO = {
    "controls": {"stick_deadzone": 0.2},
    "camera": {"fov": 720.0, "offset": [0.0, 0.0]},
    "debug": {"show_hitboxes": False},
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
            "debug": {"show_hitboxes": True},
        }
    )
    assert load_settings(escribir(tmp_path, texto)) == Settings(
        controls=ControlsSettings(stick_deadzone=0.3),
        camera=CameraSettings(fov=900.0, offset=(10.0, -20.5)),
        debug=DebugSettings(show_hitboxes=True),
    )


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
