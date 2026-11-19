"""Tests de la configuración del juego: `settings.json` contra la dataclass (ADR 0018)."""

from pathlib import Path

import pytest

from circlebh.datafile import DataFileError
from circlebh.settings import DebugSettings, Settings, load_settings


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


def test_lee_el_valor_del_archivo(tmp_path: Path) -> None:
    path = escribir(tmp_path, '{"debug": {"show_hitboxes": true}}')
    assert load_settings(path) == Settings(debug=DebugSettings(show_hitboxes=True))


def test_campo_que_falta_nombra_el_campo(tmp_path: Path) -> None:
    error = falla_en(escribir(tmp_path, '{"debug": {}}'))
    assert error.field == "debug.show_hitboxes"
    assert "falta" in str(error)


def test_campo_que_sobra_nombra_el_campo(tmp_path: Path) -> None:
    texto = '{"debug": {"show_hitboxes": false, "show_fps": true}}'
    error = falla_en(escribir(tmp_path, texto))
    assert error.field == "debug.show_fps"
    assert "sobra" in str(error)


def test_tipo_equivocado_nombra_el_campo(tmp_path: Path) -> None:
    error = falla_en(escribir(tmp_path, '{"debug": {"show_hitboxes": 1}}'))
    assert str(error) == "debug.show_hitboxes: se esperaba true o false, llegó 1"
