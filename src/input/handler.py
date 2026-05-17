"""Despacho de eventos de teclado para métodos de Scene/Cube.

Substitui o bloco `if event.key == K_LEFT: ...` procedural do esqueleto
do professor por uma classe que delega para os objetos da cena.
"""

import pygame

from src.world.scene import Scene

_KEY_TO_ROLL: dict[int, tuple[int, int]] = {
    pygame.K_LEFT:  (-1,  0),
    pygame.K_RIGHT: ( 1,  0),
    pygame.K_UP:    ( 0, -1),
    pygame.K_DOWN:  ( 0,  1),
}


class InputHandler:
    def handle(self, event: pygame.event.Event, scene: Scene) -> None:
        if event.type != pygame.KEYDOWN:
            return

        direction = _KEY_TO_ROLL.get(event.key)
        if direction is not None:
            scene.cube.try_roll(*direction)
