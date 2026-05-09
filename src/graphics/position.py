"""Posição (x, y, z) reutilizável por qualquer entidade da cena."""

from OpenGL.GL import glTranslatef


class Position:
    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> None:
        self.x = x
        self.y = y
        self.z = z

    def translate(self, dx: float, dy: float, dz: float) -> None:
        self.x += dx
        self.y += dy
        self.z += dz

    def apply(self) -> None:
        glTranslatef(self.x, self.y, self.z)
