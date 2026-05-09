"""Fator de escala por eixo, aplicável a qualquer objeto da cena."""

from OpenGL.GL import glScalef


class Size:
    def __init__(self, sx: float = 1.0, sy: float = 1.0, sz: float = 1.0) -> None:
        self.sx = sx
        self.sy = sy
        self.sz = sz

    @classmethod
    def uniform(cls, factor: float) -> "Size":
        return cls(factor, factor, factor)

    def apply(self) -> None:
        glScalef(self.sx, self.sy, self.sz)
