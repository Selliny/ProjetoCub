"""Cena: agrega o cubo jogável e o mapa, e expõe um único draw() ao loop principal."""

from OpenGL.GL import GL_CULL_FACE, glDisable, glLoadIdentity

from src.entities.cube import Cube
from src.world.map import Map


class Scene:
    def __init__(self, cube: Cube | None = None, map_: Map | None = None) -> None:
        self.cube = cube if cube is not None else Cube()
        self.map = map_ if map_ is not None else Map()

    def draw(self) -> None:
        glDisable(GL_CULL_FACE)
        glLoadIdentity()
        self.cube.apply_transform()
        self.cube.draw()
        self.map.draw()
