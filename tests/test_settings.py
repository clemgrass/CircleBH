"""Tests de la configuración del juego: `settings.json` contra la dataclass (ADR 0018)."""

import json
from pathlib import Path

import pytest

from circlebh.datafile import DataFileError
from circlebh.settings import ControlsSettings, DebugSettings, Settings, load_settings


def escribir(tmp_path: Path, texto: str) -> Path:
    path = tmp_path / "settings.json"
    path.write_text(texto, encoding="utf-8")
    return path


def falla_en(path: Path) -> DataFileError:
    with pytest.raises(DataFileError) as error:
        load_settings(path)
    return error.value


def test_settings_real_valida() -> None:
    assert isinstance(load_settings(), Settings)


def con_zona_muerta(valor: str) -> str:
    return f'{{"controls": {{"stick_deadzone": {valor}}}, "debug": {{"show_hitboxes": false}}}}'


def test_lee_el_valor_del_archivo(tmp_path: Path) -> None:
    texto = '{"controls": {"stick_deadzone": 0.3}, "debug": {"show_hitboxes": true}}'
    assert load_settings(escribir(tmp_path, texto)) == Settings(
        controls=ControlsSettings(stick_deadzone=0.3),
        debug=DebugSettings(show_hitboxes=True),
    )


def test_zona_muerta_cero_vale(tmp_path: Path) -> None:
    path = escribir(tmp_path, con_zona_muerta("0"))
    assert load_settings(path).controls.stick_deadzone == 0


@pytest.mark.parametrize("valor", ["1", "1.5", "-0.1"])
def test_zona_muerta_fuera_de_rango_nombra_el_campo(tmp_path: Path, valor: str) -> None:
    # Con 1, todo el recorrido del stick sería zona muerta y la reescala dividiría por 0.
    error = falla_en(escribir(tmp_path, con_zona_muerta(valor)))
    assert error.field == "controls.stick_deadzone"


def test_json_mal_escrito_se_rechaza(tmp_path: Path) -> None:
    # La coma final es el error típico al editar a mano.
    path = escribir(tmp_path, '{"debug": {"show_hitboxes": false,}}')
    with pytest.raises(json.JSONDecodeError):
        load_settings(path)


CONTROLS = '"controls": {"stick_deadzone": 0.2}'


def test_campo_que_falta_nombra_el_campo(tmp_path: Path) -> None:
    error = falla_en(escribir(tmp_path, f'{{{CONTROLS}, "debug": {{}}}}'))
    assert error.field == "debug.show_hitboxes"
    assert "falta" in str(error)


def test_campo_que_sobra_nombra_el_campo(tmp_path: Path) -> None:
    texto = f'{{{CONTROLS}, "debug": {{"show_hitboxes": false, "show_fps": true}}}}'
    error = falla_en(escribir(tmp_path, texto))
    assert error.field == "debug.show_fps"
    assert "sobra" in str(error)


def test_tipo_equivocado_nombra_el_campo(tmp_path: Path) -> None:
    texto = f'{{{CONTROLS}, "debug": {{"show_hitboxes": 1}}}}'
    error = falla_en(escribir(tmp_path, texto))
    assert str(error) == "debug.show_hitboxes: se esperaba true o false, llegó 1"
