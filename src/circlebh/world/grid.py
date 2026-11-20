"""La grilla espacial: encuentra los pares de círculos que se tocan sin probar todos
contra todos (ADR 0006).

El plano se parte en celdas cuadradas de lado `cell_size`. Cada cuerpo cae en la celda
`(⌊x / cell_size⌋, ⌊y / cell_size⌋)`. Si ningún diámetro pasa `cell_size`, dos círculos
que se tocan quedan a menos de `cell_size` entre centros, o sea, en la misma celda o en
una de las 8 vecinas. Basta revisar esas 9.
"""

import math
from collections import defaultdict
from collections.abc import Sequence

from pygame.math import Vector2

from circlebh.world.collisions import circles_touch

type Cell = tuple[int, int]


class SpatialGrid:
    """Una grilla de celdas de lado `cell_size`, en unidades del plano."""

    def __init__(self, cell_size: float) -> None:
        self.cell_size = cell_size

    def pairs(
        self, positions: Sequence[Vector2], radii: Sequence[float]
    ) -> set[tuple[int, int]]:
        """Los pares `(i, j)`, con `i < j`, cuyos círculos se tocan (`circles_touch`).

        Lanza `ValueError` si un diámetro pasa `cell_size`, porque entonces un par podría
        quedar a dos celdas, o si una posición no es finita: no tiene celda.
        """
        if radii and 2 * max(radii) > self.cell_size:
            raise ValueError(
                f"la celda ({self.cell_size}) es más chica que el diámetro mayor"
                f" ({2 * max(radii)})"
            )
        cells: defaultdict[Cell, list[int]] = defaultdict(list)
        for i, position in enumerate(positions):
            cells[self._cell(i, position)].append(i)
        found: set[tuple[int, int]] = set()
        for (cx, cy), members in cells.items():
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for j in cells.get((cx + dx, cy + dy), ()):
                        for i in members:
                            if i < j and circles_touch(
                                positions[i], radii[i], positions[j], radii[j]
                            ):
                                found.add((i, j))
        return found

    def _cell(self, index: int, position: Vector2) -> Cell:
        if not (math.isfinite(position.x) and math.isfinite(position.y)):
            raise ValueError(f"la posición {index} no es finita: {position}")
        return (
            math.floor(position.x / self.cell_size),
            math.floor(position.y / self.cell_size),
        )
