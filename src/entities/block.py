"""Bloco do mapa.

Pode evoluir para herdar de uma superclasse comum (ex.: Drawable) junto
com Cube, ou permanecer irmão via composição — decisão a tomar conforme
o jogo cresce.
"""

from src.graphics.color import Color
from src.graphics.position import Position
from src.graphics.size import Size


class Block:
    def __init__(
        self,
        position: Position | None = None,
        color: Color | None = None,
        size: Size | None = None,
        active: bool = True,
        is_special: bool = False,
    ) -> None:
        self.position = position if position is not None else Position()
        self.color = color if color is not None else Color(0.5, 0.5, 0.5)
        self.size = size if size is not None else Size.uniform(1.0)
        self.active = active
        self.is_special = is_special

    def draw(self) -> None:
        if not self.active:
            return
        # TODO: desenhar bloco (provavelmente reutilizando geometria do cubo).
        pass
