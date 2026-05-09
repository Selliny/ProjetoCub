"""Cor RGBA reutilizável por qualquer objeto desenhável da cena."""

from OpenGL.GL import glColor4f


class Color:
    def __init__(self, r: float, g: float, b: float, a: float = 1.0) -> None:
        self.r = r
        self.g = g
        self.b = b
        self.a = a

    def apply(self) -> None:
        glColor4f(self.r, self.g, self.b, self.a)
