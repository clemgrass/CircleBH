"""Falla si hay un archivo de imagen fuera de `docs/media/` (ADR 0013).

Revisa los archivos versionados y los nuevos que git no ignora.
"""

import subprocess
import sys
from collections.abc import Iterable
from pathlib import PurePosixPath

IMAGE_SUFFIXES = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tga", ".webp", ".svg", ".ico"}
)
ALLOWED_DIR = PurePosixPath("docs/media")


def find_forbidden_images(paths: Iterable[str]) -> list[str]:
    """Devuelve, ordenadas, las rutas de imagen que no están dentro de `docs/media/`."""
    forbidden = []
    for path in paths:
        pure = PurePosixPath(path)
        if pure.suffix.lower() in IMAGE_SUFFIXES and ALLOWED_DIR not in pure.parents:
            forbidden.append(path)
    return sorted(forbidden)


def repo_files() -> list[str]:
    """Lista los archivos versionados y los nuevos que no están en `.gitignore`."""
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [path for path in result.stdout.split("\0") if path]


def main() -> int:
    forbidden = find_forbidden_images(repo_files())
    for path in forbidden:
        print(f"Imagen fuera de docs/media/: {path} (ADR 0013)")
    if forbidden:
        return 1
    print("Control de imágenes: no hay imágenes fuera de docs/media/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
