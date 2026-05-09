"""Entidade jogável principal: o cubo controlado pelo teclado.

Compõe Color, Size e Position e mantém ângulo próprio de rotação.
"""

from src.graphics.color import Color
from src.graphics.position import Position
from src.graphics.size import Size


class Cube:
    def __init__(
        self,
        position: Position | None = None,
        color: Color | None = None,
        size: Size | None = None,
        angle: float = 0.0,
    ) -> None:
        self.position = position if position is not None else Position(0.0, 0.0, -10.0)
        self.color = color if color is not None else Color(1.0, 0.0, 0.0)
        self.size = size if size is not None else Size.uniform(1.0)
        self.angle = angle

    def move(self, dx: float, dy: float, dz: float) -> None:
        self.position.translate(dx, dy, dz)

    def rotate(self, d_angle: float) -> None:
        self.angle += d_angle

    def scale(self, factor: float) -> None:
        self.size.sx *= factor
        self.size.sy *= factor
        self.size.sz *= factor

    def draw(self) -> None:
        # TODO: definir vértices e faces do cubo (glBegin(GL_QUADS) + 8 vértices).
        pass
