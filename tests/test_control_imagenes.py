"""Tests del control de imágenes (ADR 0013)."""

from control_imagenes import find_forbidden_images


def test_detecta_una_imagen_en_la_raiz() -> None:
    assert find_forbidden_images(["README.md", "captura.png"]) == ["captura.png"]


def test_permite_imagenes_dentro_de_docs_media_aunque_esten_anidadas() -> None:
    assert (
        find_forbidden_images(["docs/media/seno.gif", "docs/media/armas/rosa.png"])
        == []
    )


def test_extension_en_mayusculas_tambien_cuenta() -> None:
    assert find_forbidden_images(["src/icono.PNG"]) == ["src/icono.PNG"]


def test_una_carpeta_que_solo_empieza_como_docs_media_no_se_permite() -> None:
    assert find_forbidden_images(["docs/media-vieja/x.png"]) == [
        "docs/media-vieja/x.png"
    ]


def test_sin_imagenes_no_hay_nada_que_reportar() -> None:
    assert (
        find_forbidden_images(["pyproject.toml", "src/circlebh/world/__init__.py"])
        == []
    )
